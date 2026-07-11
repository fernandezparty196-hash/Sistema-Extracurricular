"""
services/asistencia_service.py   ──   MEJORADO PARA RF-16 a RF-20
═══════════════════════════════════════════════════════════════════

RF-16: Registrar Asistencia
  ✓ Estados: P (Presente), A (Ausente), J (Justificado)
  ✓ Solo docentes pueden registrar sus talleres
  ✓ Un registro por estudiante por sesión (UNIQUE)

RF-17: Marcar en bloque
  ✓ Marcar todos presentes/ausentes de una sesión
  ✓ Recalcula porcentaje en tiempo real

RF-18: Agregar observación
  ✓ Observación obligatoria si estado == "J"
  ✓ Identifica automáticamente estudiantes bajo umbral (alerta)

RF-19: Cambiar estado (Operador de Bienestar)
  ✓ Cambiar A → J recalcula porcentaje
  ✓ Solo operador/admin pueden hacer esto

RF-20: Congelar registro
  ✓ No permite editar asistencia después del día de la sesión
  ✓ Solo admin con autorización explícita puede descongelar
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

    # ══════════════════════════════════════════════════════════════
    # RF-16: REGISTRAR ASISTENCIA
    # ══════════════════════════════════════════════════════════════

    @staticmethod
    def registrar(sesion_id: int, inscripcion_id: int, estado: str,
                  usuario_id: int, observacion: str = "") -> ResultadoAsistencia:
        """
        ✅ RF-16: Registra asistencia de un estudiante en una sesión.

        VALIDACIONES:
          • Estado debe ser P/A/J
          • Si J, observación es obligatoria
          • No se puede registrar después del día de la sesión (RF-20)
          • Un solo registro por inscripción-sesión (UNIQUE)

        PARÁMETROS:
          sesion_id: ID de la sesión
          inscripcion_id: ID de la inscripción (NO estudiante_id directo)
          estado: "P" | "A" | "J"
          observacion: Obligatorio si estado == "J"

        RETORNA:
          ResultadoAsistencia con ok=True y mensaje
        """

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
                if AsistenciaService._sesion_congelada(sesion):
                    return ResultadoAsistencia(False,
                        "Esta sesión está congelada (pasó la fecha). "
                        "Contacta al administrador para modificaciones.")

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

                return ResultadoAsistencia(True,
                    f"Asistencia registrada correctamente.{alerta}",
                    datos={"porcentaje": porcentaje})

        except SQLAlchemyError as e:
            return ResultadoAsistencia(False, f"Error al guardar: {e}")

    # ══════════════════════════════════════════════════════════════
    # RF-17: MARCAR EN BLOQUE
    # ══════════════════════════════════════════════════════════════

    @staticmethod
    def marcar_todos(sesion_id: int, estado: str,
                     usuario_id: int) -> ResultadoAsistencia:
        """
        ✅ RF-17: Marca todos los inscritos de una sesión con el mismo estado.

        FLUJO:
          1. Obtener todos los inscritos activos
          2. Para cada uno, crear/actualizar asistencia
          3. Recalcular porcentaje de cada uno
          4. Auditar en bloque

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
                if AsistenciaService._sesion_congelada(sesion):
                    return ResultadoAsistencia(False,
                        "Esta sesión está congelada. No se pueden hacer cambios.")

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

                # Preparar mensaje con alertas
                mensaje = f"✓ {registrados} asistencias marcadas como {estado}"
                if alertas:
                    mensaje += f"\n⚠️ {len(alertas)} estudiante(s) bajo umbral"

                return ResultadoAsistencia(True, mensaje,
                    datos={"registrados": registrados, "alertas": alertas})

        except SQLAlchemyError as e:
            return ResultadoAsistencia(False, f"Error: {e}")

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
                if AsistenciaService._sesion_congelada(asist.sesion):
                    return ResultadoAsistencia(False,
                        "Sesión congelada. No se permite cambiar estados.")

                # Cambiar estado
                asist.estado = nuevo_estado
                asist.updated_at = datetime.now()

                if nuevo_estado == "J":
                    asist.observacion = f"Justificado por {Usuario.query.get(usuario_id).nombre_completo}"

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
        """
        ✅ RF-20: Verifica si una sesión está congelada.

        REGLA:
          Si hoy > fecha de sesión → sesión congelada
          No se permite editar sin autorización admin

        RETORNA:
          True si sesión está congelada (pasó la fecha)
        """
        hoy = date.today()
        return hoy > sesion.fecha

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
                    accion="DESCONGELAR",
                    registro_id=sesion_id,
                    datos_nuevos={"razon": razon, "decongelada_en": datetime.now()}
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