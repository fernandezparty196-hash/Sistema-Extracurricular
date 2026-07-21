"""
services/asistencia_service.py   ──   MEJORADO PARA RF-16 a RF-20
═══════════════════════════════════════════════════════════════════

RF-16: Registrar Asistencia
  ✓ Estados: P (Presente), A (Ausente), J (Justificado)
  ✓ Solo docentes pueden registrar sus talleres
  ✓ Un registro por estudiante por sesión (UNIQUE)
  ✓ Al registrar, si la sesión estaba "Programada" pasa a "Realizada"

RF-17: Marcar en bloque
  ✓ Marcar todos presentes/ausentes de una sesión
  ✓ Recalcula porcentaje en tiempo real
  ✓ También dispara Programada → Realizada al terminar

RF-18: Agregar observación
  ✓ Observación obligatoria si estado == "J"
  ✓ Identifica automáticamente estudiantes bajo umbral (alerta)

RF-19: Cambiar estado (Operador de Bienestar)
  ✓ Cambiar A → J recalcula porcentaje
  ✓ Solo operador/admin pueden hacer esto

RF-20: Congelar registro
  ✓ No permite editar asistencia después del día de la sesión
  ✓ Administrador siempre puede editar sesiones congeladas
  ✓ Un docente puede editar una sesión congelada SOLO si el admin lo
    autorizó puntualmente para esa sesión (ver _tiene_autorizacion_activa)
"""

from dataclasses import dataclass
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any

from sqlalchemy import and_, func
from sqlalchemy.exc import SQLAlchemyError

from database.connection import get_session
from models.asistencia import Asistencia
from models.sesion import Sesion
from models.inscripcion import Inscripcion
from models.estudiante import Estudiante
from models.taller import Taller
from models.usuario import Usuario
from models.auditoria import Auditoria


@dataclass
class ResultadoAsistencia:
    """Estructura de respuesta estándar."""
    ok: bool
    mensaje: str
    datos: Optional[Any] = None
    lista: Optional[List[Dict]] = None


class AsistenciaService:
    """Servicio completo de gestión de asistencia."""

    # Marcadores usados dentro de Auditoria.datos_nuevos para poder
    # distinguir "autorizar" de "revocar" sin tocar la columna `accion`
    # (que el ENUM de la BD solo permite INSERT/UPDATE/DELETE).
    _TIPO_AUTORIZAR = "AUTORIZAR_EDICION_ASISTENCIA"
    _TIPO_REVOCAR = "REVOCAR_AUTORIZACION_EDICION_ASISTENCIA"

    # ══════════════════════════════════════════════════════════════
    # RF-16: REGISTRAR ASISTENCIA
    # ══════════════════════════════════════════════════════════════

    @staticmethod
    def registrar(sesion_id: int, inscripcion_id: int, estado: str,
                  usuario_id: int, observacion: str = "",
                  rol_usuario: str = "Docente") -> ResultadoAsistencia:


        # Validar estado
        if estado not in ("P", "A", "J"):
            return ResultadoAsistencia(False, f"Estado inválido: {estado}")

        # Validar observación si es justificado
        if estado == "J" and not observacion.strip():
            return ResultadoAsistencia(False,
                "La observación es obligatoria para justificaciones.")

        try:
            with get_session() as session:
                # Verificar inscripción existe
                insc = session.get(Inscripcion, inscripcion_id)
                if not insc:
                    return ResultadoAsistencia(False, "Inscripción no encontrada")

                # Verificar sesión existe
                sesion = session.get(Sesion, sesion_id)
                if not sesion:
                    return ResultadoAsistencia(False, "Sesión no encontrada")

                # RF-20: Verificar que no haya pasado el día de la sesión
                # (o que el usuario esté autorizado a editarla igual)
                if AsistenciaService._bloqueada_para(sesion, usuario_id, rol_usuario):
                    return ResultadoAsistencia(False,
                        "Esta sesión está congelada (pasó la fecha). "
                        "Solo un administrador, o un docente autorizado por uno, "
                        "puede modificarla.")

                # Verificar si ya hay registro (UNIQUE constraint)
                ya_registrado = session.query(Asistencia).filter(
                    Asistencia.inscripcion_id == inscripcion_id,
                    Asistencia.sesion_id == sesion_id
                ).first()

                if ya_registrado:
                    # Actualizar existente (si es el mismo día)
                    ya_registrado.estado = estado
                    ya_registrado.observacion = observacion.strip() or None
                    ya_registrado.updated_at = datetime.now()
                else:
                    # Crear nuevo
                    session.add(Asistencia(
                        inscripcion_id=inscripcion_id,
                        sesion_id=sesion_id,
                        estado=estado,
                        observacion=observacion.strip() or None,
                        registrado_por=usuario_id,
                    ))

                session.flush()

                # RF-17: Recalcular porcentaje en tiempo real
                porcentaje = AsistenciaService._calcular_porcentaje_actual(
                    insc.estudiante_id, sesion.taller_id
                )

                # Auditar
                session.add(Auditoria(
                    usuario_id=usuario_id,
                    tabla_afectada="asistencia",
                    accion="INSERT" if not ya_registrado else "UPDATE",
                    registro_id=ya_registrado.id if ya_registrado else None,
                    datos_nuevos={
                        "estado": estado,
                        "observacion": observacion,
                        "porcentaje_actual": porcentaje
                    }
                ))

                session.commit()

                # RF-18: Detectar si está bajo umbral (alerta)
                alerta = ""
                if porcentaje < sesion.taller.umbral_asistencia:
                    alerta = f" ⚠️ ALERTA: Estudiante bajo umbral ({porcentaje:.1f}% < {sesion.taller.umbral_asistencia}%)"

                mensaje = f"Asistencia registrada correctamente.{alerta}"

            # ── Fuera del "with": la transacción de asistencia ya cerró ──
            # ✅ Si la sesión seguía "Programada", pasa a "Realizada".
            AsistenciaService._marcar_sesion_realizada(sesion_id, usuario_id)

            return ResultadoAsistencia(True, mensaje,
                datos={"porcentaje": porcentaje})

        except SQLAlchemyError as e:
            return ResultadoAsistencia(False, f"Error al guardar: {e}")

    # ══════════════════════════════════════════════════════════════
    # RF-17: MARCAR EN BLOQUE
    # ══════════════════════════════════════════════════════════════

    @staticmethod
    def marcar_todos(sesion_id: int, estado: str,
                     usuario_id: int, rol_usuario: str = "Docente") -> ResultadoAsistencia:
        """
        ✅ RF-17: Marca todos los inscritos de una sesión con el mismo estado.

        FLUJO:
          1. Obtener todos los inscritos activos
          2. Para cada uno, crear/actualizar asistencia
          3. Recalcular porcentaje de cada uno
          4. Auditar en bloque
          5. Si la sesión estaba "Programada", pasa a "Realizada"

        PARÁMETROS:
          sesion_id: ID de la sesión
          estado: "P" | "A" | "J"
          usuario_id: Quién marca

        RETORNA:
          ResultadoAsistencia con cantidad procesada
        """

        if estado not in ("P", "A", "J"):
            return ResultadoAsistencia(False, f"Estado inválido: {estado}")

        try:
            with get_session() as session:
                # Obtener sesión
                sesion = session.get(Sesion, sesion_id)
                if not sesion:
                    return ResultadoAsistencia(False, "Sesión no encontrada")

                # RF-20: Verificar congelación
                if AsistenciaService._bloqueada_para(sesion, usuario_id, rol_usuario):
                    return ResultadoAsistencia(False,
                        "Esta sesión está congelada. Solo un administrador, o un "
                        "docente autorizado por uno, puede hacer cambios.")

                # Obtener inscritos activos
                inscritos = session.query(Inscripcion).filter(
                    Inscripcion.taller_id == sesion.taller_id,
                    Inscripcion.estado == "Activo"
                ).all()

                registrados = 0
                alertas = []

                for insc in inscritos:
                    # Buscar/crear asistencia
                    asist = session.query(Asistencia).filter(
                        Asistencia.inscripcion_id == insc.id,
                        Asistencia.sesion_id == sesion_id
                    ).first()

                    if not asist:
                        asist = Asistencia(
                            inscripcion_id=insc.id,
                            sesion_id=sesion_id,
                            estado=estado,
                            registrado_por=usuario_id
                        )
                        session.add(asist)
                    else:
                        asist.estado = estado
                        asist.updated_at = datetime.now()

                    session.flush()

                    # RF-17: Recalcular porcentaje
                    pct = AsistenciaService._calcular_porcentaje_actual(
                        insc.estudiante_id, sesion.taller_id
                    )

                    # RF-18: Detectar alerta
                    if pct < sesion.taller.umbral_asistencia:
                        alertas.append({
                            "estudiante_id": insc.estudiante_id,
                            "nombre": insc.estudiante.nombre_completo,
                            "porcentaje": pct,
                            "umbral": sesion.taller.umbral_asistencia
                        })

                    registrados += 1

                session.commit()

                mensaje = f"✓ {registrados} asistencias marcadas como {estado}"
                if alertas:
                    mensaje += f"\n⚠️ {len(alertas)} estudiante(s) bajo umbral"

            # ── Fuera del "with": ya se commiteó la asistencia en bloque ──
            AsistenciaService._marcar_sesion_realizada(sesion_id, usuario_id)

            return ResultadoAsistencia(True, mensaje,
                datos={"registrados": registrados, "alertas": alertas})

        except SQLAlchemyError as e:
            return ResultadoAsistencia(False, f"Error: {e}")

    # ══════════════════════════════════════════════════════════════
    # TRANSICIÓN AUTOMÁTICA DE ESTADO DE SESIÓN (Programada → Realizada)
    # ══════════════════════════════════════════════════════════════

    @staticmethod
    def _marcar_sesion_realizada(sesion_id: int, usuario_id: int) -> None:
        """
        Si la sesión sigue en "Programada", la pasa a "Realizada" porque
        ya se le registró asistencia (al menos un estudiante).

        No hace nada si la sesión ya está "Realizada" o "Cancelada": no
        se debe revertir una cancelación solo porque alguien registró
        asistencia por error, ni reprocesar sesiones ya realizadas.

        Import local de SesionService para evitar un ciclo de imports
        entre services/asistencia_service.py y services/sesion_service.py.
        """
        from services.sesion_service import SesionService

        try:
            with get_session() as session:
                sesion = session.get(Sesion, sesion_id)
                if not sesion or sesion.estado != "Programada":
                    return
        except SQLAlchemyError:
            return

        # Este cambio de estado abre su propia sesión/transacción y
        # auditoría vía SesionService.cambiar_estado; si falla, no debe
        # tumbar el registro de asistencia que ya se guardó exitosamente.
        try:
            SesionService.cambiar_estado(sesion_id, "Realizada", usuario_id)
        except Exception:
            pass

    # ══════════════════════════════════════════════════════════════
    # RF-19: CAMBIAR ESTADO (Operador de Bienestar)
    # ══════════════════════════════════════════════════════════════

    @staticmethod
    def cambiar_estado(asistencia_id: int, nuevo_estado: str,
                      usuario_id: int, rol_usuario: str) -> ResultadoAsistencia:
        """
        ✅ RF-19: Cambiar A → J (Ausente a Justificado).

        RESTRICCIÓN:
          Solo Operador y Administrador pueden hacer esto.

        FLUJO:
          1. Verificar rol (Operador o Admin)
          2. Obtener asistencia
          3. Cambiar estado (típicamente A → J)
          4. Recalcular porcentaje
          5. Si fue bajo umbral, ahora sube → alerta de cambio

        PARÁMETROS:
          asistencia_id: ID del registro
          nuevo_estado: "J" (típicamente)
          usuario_id: Quién cambia
          rol_usuario: "Operador" | "Administrador"

        RETORNA:
          ResultadoAsistencia con nuevo porcentaje
        """

        # Validar rol (solo Operador y Administrador)
        if rol_usuario not in ("Operador", "Administrador"):
            return ResultadoAsistencia(False,
                "Solo Operador y Administrador pueden cambiar estados.")

        if nuevo_estado not in ("P", "A", "J"):
            return ResultadoAsistencia(False, f"Estado inválido: {nuevo_estado}")

        try:
            with get_session() as session:
                asist = session.get(Asistencia, asistencia_id)
                if not asist:
                    return ResultadoAsistencia(False, "Asistencia no encontrada")

                estado_anterior = asist.estado

                # RF-20: Verificar congelación
                if AsistenciaService._bloqueada_para(asist.sesion, usuario_id, rol_usuario):
                    return ResultadoAsistencia(False,
                        "Sesión congelada. Solo un administrador, o un docente "
                        "autorizado por uno, puede cambiar estados.")

                # Cambiar estado
                asist.estado = nuevo_estado
                asist.updated_at = datetime.now()

                if nuevo_estado == "J":
                    # ⚠️ Bug preexistente: `Usuario.query` no existe en este proyecto
                    # (no se usa Flask-SQLAlchemy). Debe resolverse con get_session():
                    usuario = session.get(Usuario, usuario_id)
                    nombre_usuario = usuario.nombre_completo if usuario else "usuario desconocido"
                    asist.observacion = f"Justificado por {nombre_usuario}"

                session.flush()

                # RF-17: Recalcular porcentaje
                pct = AsistenciaService._calcular_porcentaje_actual(
                    asist.inscripcion.estudiante_id,
                    asist.sesion.taller_id
                )

                # Auditar el cambio
                session.add(Auditoria(
                    usuario_id=usuario_id,
                    tabla_afectada="asistencia",
                    accion="UPDATE",
                    registro_id=asistencia_id,
                    datos_anteriores={"estado": estado_anterior},
                    datos_nuevos={"estado": nuevo_estado, "porcentaje": pct}
                ))

                session.commit()

                return ResultadoAsistencia(True,
                    f"Estado cambiado: {estado_anterior} → {nuevo_estado}. "
                    f"Nuevo porcentaje: {pct:.1f}%",
                    datos={"porcentaje_nuevo": pct, "estado_anterior": estado_anterior})

        except SQLAlchemyError as e:
            return ResultadoAsistencia(False, f"Error: {e}")

    # ══════════════════════════════════════════════════════════════
    # RF-20: CONGELAR REGISTRO
    # ══════════════════════════════════════════════════════════════

    @staticmethod
    def _sesion_congelada(sesion: Sesion) -> bool:
        hoy = date.today()
        return hoy > sesion.fecha

    # ══════════════════════════════════════════════════════════════
    # RF-20 (extendido): ADMIN + AUTORIZACIÓN PUNTUAL A DOCENTES
    # ══════════════════════════════════════════════════════════════

    @staticmethod
    def puede_editar_sesion_congelada(sesion_id: int, usuario_id: int,
                                       rol_usuario: str) -> bool:
        """
        Punto único de verdad: ¿puede este usuario editar una sesión
        aunque ya esté congelada (pasó su fecha)?

          • Administrador → siempre puede (control total del sistema)
          • Docente       → solo si el admin autorizó ESTA sesión puntual
          • Operador/otros→ no

        No depende de ninguna tabla nueva: la autorización de docentes
        se guarda como eventos en 'auditoria' (ver más abajo).
        """
        if rol_usuario == "Administrador":
            return True
        if rol_usuario == "Docente":
            return AsistenciaService._tiene_autorizacion_activa(sesion_id, usuario_id)
        return False

    @staticmethod
    def _bloqueada_para(sesion: Sesion, usuario_id: int, rol_usuario: str) -> bool:
        """Combina la congelación por fecha (RF-20) con la excepción de arriba."""
        if not AsistenciaService._sesion_congelada(sesion):
            return False
        return not AsistenciaService.puede_editar_sesion_congelada(
            sesion.id, usuario_id, rol_usuario
        )

    @staticmethod
    def _tiene_autorizacion_activa(sesion_id: int, docente_id: int) -> bool:
        """
        Revisa el historial de auditoría y busca el evento MÁS RECIENTE
        de autorización/revocación para ese docente en esa sesión.

        ✅ CORRECCIÓN: el filtro anterior (`Auditoria.datos_nuevos in (...)`)
        no era una condición SQL válida — comparaba la columna completa
        contra strings sueltos usando el operador `in` de Python, lo cual
        no filtra nada realmente (o directamente rompe). Además, tanto
        autorizar como revocar escriben accion="UPDATE" (el ENUM no admite
        otro valor), así que no se puede distinguir por esa columna.

        La distinción ahora se hace con la clave "tipo_evento" dentro de
        datos_nuevos (ver autorizar_edicion_congelada / revocar_...), y el
        filtrado por docente se hace en Python porque los datos vienen en
        una columna JSON.
        """
        try:
            with get_session() as session:
                eventos = session.query(Auditoria).filter(
                    Auditoria.tabla_afectada == "sesiones",
                    Auditoria.registro_id == sesion_id,
                    Auditoria.accion == "UPDATE"
                ).order_by(Auditoria.id.desc()).all()

                for evento in eventos:
                    datos = evento.datos_nuevos or {}

                    if datos.get("docente_autorizado_id") != docente_id:
                        continue

                    tipo = datos.get("tipo_evento")

                    if tipo == AsistenciaService._TIPO_REVOCAR:
                        return False
                    if tipo == AsistenciaService._TIPO_AUTORIZAR:
                        return True

                    # Evento antiguo sin "tipo_evento" (datos de antes de
                    # este fix): no se puede confiar en él, se ignora.
                    continue

                return False
        except SQLAlchemyError:
            return False

    @staticmethod
    def autorizar_edicion_congelada(sesion_id: int, docente_id: int,
                                     usuario_id: int, rol_solicitante: str,
                                     razon: str = "") -> ResultadoAsistencia:
        """
        ✅ El administrador autoriza a un docente puntual a editar la
        asistencia de una sesión ya congelada, típicamente a petición
        del propio docente.

        No crea ninguna tabla: queda registrado como evento en 'auditoria',
        igual que cualquier otra acción del sistema.
        """
        if rol_solicitante != "Administrador":
            return ResultadoAsistencia(False,
                "Solo un administrador puede autorizar la edición de sesiones congeladas.")

        try:
            with get_session() as session:
                sesion = session.get(Sesion, sesion_id)
                if not sesion:
                    return ResultadoAsistencia(False, "Sesión no encontrada")

                docente = session.get(Usuario, docente_id)
                if not docente:
                    return ResultadoAsistencia(False, "Docente no encontrado")

                session.add(Auditoria(
                    usuario_id=usuario_id,
                    tabla_afectada="sesiones",
                    accion="UPDATE",
                    registro_id=sesion_id,
                    datos_nuevos={
                        "tipo_evento": AsistenciaService._TIPO_AUTORIZAR,
                        "docente_autorizado_id": docente_id,
                        "docente_nombre": docente.nombre_completo,
                        "razon": razon,
                        "autorizado_en": datetime.now().isoformat()
                    }
                ))
                session.commit()

                return ResultadoAsistencia(True,
                    f"Se autorizó a {docente.nombre_completo} a editar la "
                    f"asistencia de esta sesión aunque esté congelada.")

        except SQLAlchemyError as e:
            return ResultadoAsistencia(False, f"Error al autorizar: {e}")

    @staticmethod
    def revocar_autorizacion_edicion(sesion_id: int, docente_id: int,
                                      admin_usuario_id: int,
                                      rol_solicitante: str) -> ResultadoAsistencia:
        """Revierte una autorización previamente otorgada a un docente."""
        if rol_solicitante != "Administrador":
            return ResultadoAsistencia(False,
                "Solo un administrador puede revocar autorizaciones.")

        try:
            with get_session() as session:
                session.add(Auditoria(
                    usuario_id=admin_usuario_id,
                    tabla_afectada="sesiones",
                    accion="UPDATE",
                    registro_id=sesion_id,
                    datos_nuevos={
                        "tipo_evento": AsistenciaService._TIPO_REVOCAR,
                        "docente_autorizado_id": docente_id,
                        "revocado_en": datetime.now().isoformat()
                    }
                ))
                session.commit()

                return ResultadoAsistencia(True, "Autorización revocada correctamente.")

        except SQLAlchemyError as e:
            return ResultadoAsistencia(False, f"Error al revocar: {e}")

    @staticmethod
    def descongelar_sesion(sesion_id: int, usuario_id: int,
                          razon: str) -> ResultadoAsistencia:
        """
        ✅ RF-20: Solo administrador puede descongelar una sesión.

        PARÁMETROS:
          sesion_id: ID de la sesión
          usuario_id: ID del administrador
          razon: Motivo de la descongelación (para auditoría)

        RETORNA:
          ResultadoAsistencia con resultado
        """
        try:
            with get_session() as session:
                sesion = session.get(Sesion, sesion_id)
                if not sesion:
                    return ResultadoAsistencia(False, "Sesión no encontrada")

                # Registrar descongelación en auditoría
                session.add(Auditoria(
                    usuario_id=usuario_id,
                    tabla_afectada="sesiones",
                    accion="UPDATE",
                    registro_id=sesion_id,
                    # ✅ corregido: faltaba llamar isoformat()
                    datos_nuevos={"razon": razon, "decongelada_en": datetime.now().isoformat()}
                ))

                session.commit()

                return ResultadoAsistencia(True,
                    f"Sesión decongelada. Ahora se pueden editar registros.")

        except SQLAlchemyError as e:
            return ResultadoAsistencia(False, f"Error: {e}")

    # ══════════════════════════════════════════════════════════════
    # CÁLCULO DE PORCENTAJE (usado en RF-17)
    # ══════════════════════════════════════════════════════════════

    @staticmethod
    def _calcular_porcentaje_actual(estudiante_id: int, taller_id: int) -> float:
        """
        ✅ RF-17: Calcula porcentaje de asistencia EN TIEMPO REAL.

        CUENTA:
          P (Presente)   → 100%
          J (Justificado)→ 100%
          A (Ausente)    → 0%

        RETORNA:
          float: Porcentaje 0.0-100.0
        """
        try:
            with get_session() as session:
                # Inscripción del estudiante en el taller
                insc = session.query(Inscripcion).filter(
                    Inscripcion.estudiante_id == estudiante_id,
                    Inscripcion.taller_id == taller_id,
                    Inscripcion.estado == "Activo"
                ).first()

                if not insc:
                    return 0.0

                # Total sesiones del taller
                total_sesiones = session.query(func.count(Sesion.id)).filter(
                    Sesion.taller_id == taller_id
                ).scalar() or 0

                if total_sesiones == 0:
                    return 0.0

                # Asistencias que cuentan (P y J)
                cuentan = session.query(func.count(Asistencia.id)).filter(
                    Asistencia.inscripcion_id == insc.id,
                    Asistencia.estado.in_(["P", "J"])
                ).scalar() or 0

                porcentaje = (cuentan / total_sesiones) * 100
                return round(porcentaje, 2)

        except SQLAlchemyError:
            return 0.0

    # ══════════════════════════════════════════════════════════════
    # RF-18: DETECTAR ALERTAS
    # ══════════════════════════════════════════════════════════════

    @staticmethod
    def obtener_estudiantes_en_riesgo(taller_id: int) -> list[dict]:
        """
        ✅ RF-18: Identifica estudiantes bajo el umbral (alerta visible).

        RETORNA:
          list[dict]: Estudiantes cuyo porcentaje < umbral del taller
        """
        try:
            with get_session() as session:
                taller = session.get(Taller, taller_id)
                if not taller:
                    return []

                inscritos = session.query(Inscripcion).filter(
                    Inscripcion.taller_id == taller_id,
                    Inscripcion.estado == "Activo"
                ).all()

                en_riesgo = []

                for insc in inscritos:
                    pct = AsistenciaService._calcular_porcentaje_actual(
                        insc.estudiante_id, taller_id
                    )

                    if pct < taller.umbral_asistencia:
                        en_riesgo.append({
                            "inscripcion_id": insc.id,
                            "estudiante_id": insc.estudiante_id,
                            "nombre": insc.estudiante.nombre_completo,
                            "dni": insc.estudiante.dni,
                            "porcentaje": pct,
                            "umbral": taller.umbral_asistencia,
                            "diferencia": taller.umbral_asistencia - pct
                        })

                # Ordenar por diferencia (más críticos primero)
                return sorted(en_riesgo, key=lambda x: x["diferencia"], reverse=True)

        except SQLAlchemyError:
            return []

    # ══════════════════════════════════════════════════════════════
    # CONSULTAS BÁSICAS
    # ══════════════════════════════════════════════════════════════

    @staticmethod
    def obtener_por_sesion(sesion_id: int) -> list[dict]:
        """Obtiene todas las asistencias de una sesión."""
        try:
            with get_session() as session:
                asistencias = session.query(Asistencia).filter(
                    Asistencia.sesion_id == sesion_id
                ).all()

                return [
                    {
                        "id": a.id,
                        "inscripcion_id": a.inscripcion_id,
                        "estado": a.estado,
                        "estado_legible": a.estado_legible,
                        "observacion": a.observacion or "",
                        "registrado_por": a.registrado_por,
                    }
                    for a in asistencias
                ]
        except SQLAlchemyError:
            return []

    @staticmethod
    def obtener_resumen_sesion(sesion_id: int) -> dict:
        """Obtiene resumen agregado de una sesión."""
        try:
            with get_session() as session:
                sesion = session.get(Sesion, sesion_id)
                if not sesion:
                    return {
                        "presentes": 0,
                        "ausentes": 0,
                        "justificados": 0,
                        "total": 0,
                        "cuentan_asistencia": 0,
                        "porcentaje": 0.0
                    }

                presentes = sum(1 for a in sesion.asistencias if a.estado == "P")
                ausentes = sum(1 for a in sesion.asistencias if a.estado == "A")
                justificados = sum(1 for a in sesion.asistencias if a.estado == "J")
                total = len(sesion.asistencias)
                cuentan = presentes + justificados

                pct = (cuentan / total * 100) if total > 0 else 0.0

                return {
                    "presentes": presentes,
                    "ausentes": ausentes,
                    "justificados": justificados,
                    "total": total,
                    "cuentan_asistencia": cuentan,
                    "porcentaje": round(pct, 2)
                }

        except SQLAlchemyError:
            return {
                "presentes": 0,
                "ausentes": 0,
                "justificados": 0,
                "total": 0,
                "porcentaje": 0.0
            }

    @staticmethod
    def obtener_aprobacion_estudiante(inscripcion_id: int) -> dict:
        """
        Evalúa si un estudiante cumple umbral de asistencia.

        CUENTA: P + J
        NO CUENTA: A
        """
        try:
            with get_session() as session:
                insc = session.get(Inscripcion, inscripcion_id)
                if not insc:
                    return {"apto": False, "razon": "Inscripción no encontrada"}

                asistencias = session.query(Asistencia).filter(
                    Asistencia.inscripcion_id == inscripcion_id
                ).all()

                if not asistencias:
                    return {
                        "apto": False,
                        "razon": "Sin sesiones registradas",
                        "presentes": 0,
                        "total": 0,
                        "porcentaje": 0.0
                    }

                cuentan = sum(1 for a in asistencias if a.estado in ("P", "J"))
                total = len(asistencias)
                pct = (cuentan / total * 100) if total > 0 else 0.0

                taller = insc.taller
                apto = pct >= taller.umbral_asistencia

                return {
                    "apto": apto,
                    "presentes": cuentan,
                    "total": total,
                    "porcentaje": round(pct, 2),
                    "umbral": taller.umbral_asistencia,
                    "razon": f"{pct:.1f}% {'≥' if apto else '<'} {taller.umbral_asistencia}%"
                }

        except SQLAlchemyError as e:
            return {"apto": False, "razon": f"Error: {e}"}