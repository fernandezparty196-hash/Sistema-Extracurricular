"""
services/asignacion_bien_taller_service.py   ──   Asignación de Bienes a Talleres
═══════════════════════════════════════════════════════════════════════════════

Gestiona la asignación de bienes patrimoniales a TALLERES EXTRACURRICULARES
con seguimiento de devoluciones y alertas.

RF-31: Registro nuevo bien (ya existe lista)
RF-33: Registrar devolución y estado
RF-34: Cambiar estado de bien
RF-35: Alertas bienes vencidos/dañados
"""

from dataclasses import dataclass
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any

from sqlalchemy import and_
from sqlalchemy.exc import SQLAlchemyError

from database.connection import get_session
from models.bienes import BienPatrimonial
from models.auditoria import Auditoria


@dataclass
class ResultadoAsignacion:
    """Respuesta estándar."""
    ok: bool
    mensaje: str
    datos: Optional[Any] = None
    lista: Optional[List[Dict]] = None


class AsignacionBienTallerService:
    """Gestión de asignaciones de bienes a talleres."""

    # ══════════════════════════════════════════════════════════════
    # ASIGNAR BIEN A TALLER
    # ══════════════════════════════════════════════════════════════

    @staticmethod
    def asignar_a_taller(bien_id: int, taller_id: int, fecha_limite_dias: int,
                        usuario_id: int, observacion: str = "") -> ResultadoAsignacion:
        """
        Asigna un bien a un taller extracurricular.

        PARÁMETROS:
          bien_id: ID del bien patrimonial
          taller_id: ID del taller
          fecha_limite_dias: Días para devolver (ej: 30)
          usuario_id: Quién asigna
          observacion: Notas sobre la asignación

        RETORNA:
          ResultadoAsignacion con datos de asignación
        """

        if fecha_limite_dias < 1:
            return ResultadoAsignacion(False,
                "Fecha límite debe ser mínimo 1 día.")

        try:
            with get_session() as session:
                # Verificar bien existe y está disponible
                bien = session.get(BienPatrimonial, bien_id)

                if not bien:
                    return ResultadoAsignacion(False, "Bien no encontrado.")

                if bien.estado_disponibilidad != "Disponible":
                    return ResultadoAsignacion(False,
                        f"Bien en estado '{bien.estado_disponibilidad}'. "
                        f"Debe estar 'Disponible' para asignar.")

                # Verificar taller existe
                from models.taller import Taller
                taller = session.get(Taller, taller_id)

                if not taller:
                    return ResultadoAsignacion(False, "Taller no encontrado.")

                # Crear asignación usando el modelo si existe
                # Si no, guardar en auditoría y cambiar estado
                fecha_asignacion = date.today()
                fecha_limite = fecha_asignacion + timedelta(days=fecha_limite_dias)

                # Cambiar estado del bien a Asignado
                bien.estado_disponibilidad = "Asignado"
                bien.updated_at = datetime.now()

                session.flush()

                # Auditar la asignación
                session.add(Auditoria(
                    usuario_id=usuario_id,
                    tabla_afectada="bienes_patrimoniales",
                    accion="ASIGNACION_TALLER",
                    registro_id=bien_id,
                    datos_nuevos={
                        "bien_codigo": bien.codigo,
                        "taller_id": taller_id,
                        "taller_nombre": taller.nombre,
                        "fecha_asignacion": str(fecha_asignacion),
                        "fecha_limite_devolucion": str(fecha_limite),
                        "observacion": observacion,
                        "estado_anterior": "Disponible",
                        "estado_nuevo": "Asignado"
                    }
                ))

                session.commit()

                return ResultadoAsignacion(True,
                    f"Bien '{bien.codigo}' asignado a taller '{taller.nombre}' "
                    f"hasta {fecha_limite.strftime('%d/%m/%Y')}",
                    datos={
                        "bien_id": bien_id,
                        "bien_codigo": bien.codigo,
                        "taller_id": taller_id,
                        "fecha_limite": str(fecha_limite)
                    })

        except SQLAlchemyError as e:
            return ResultadoAsignacion(False, f"Error en BD: {str(e)}")

    # ══════════════════════════════════════════════════════════════
    # RF-33: REGISTRAR DEVOLUCIÓN
    # ══════════════════════════════════════════════════════════════

    @staticmethod
    def registrar_devolucion_taller(bien_id: int, estado_retorno: str,
                                   usuario_id: int, observacion: str = "") -> ResultadoAsignacion:
        """
        ✅ RF-33: Registra la devolución de un bien asignado a taller.

        FLUJO:
          1. Verificar bien está asignado
          2. Registrar fecha de devolución (hoy)
          3. Registrar estado físico al retorno: Bueno/Regular/Malo
          4. Cambiar bien a Disponible
          5. Activar alerta si está dañado

        PARÁMETROS:
          bien_id: ID del bien
          estado_retorno: "Bueno" | "Regular" | "Malo"
          usuario_id: Quién recibe
          observacion: Notas sobre devolución

        RETORNA:
          ResultadoAsignacion con alerta si hay daño
        """

        if estado_retorno not in ("Bueno", "Regular", "Malo"):
            return ResultadoAsignacion(False,
                f"Estado inválido: {estado_retorno}")

        try:
            with get_session() as session:
                bien = session.get(BienPatrimonial, bien_id)

                if not bien:
                    return ResultadoAsignacion(False, "Bien no encontrado.")

                if bien.estado_disponibilidad != "Asignado":
                    return ResultadoAsignacion(False,
                        f"Bien en estado '{bien.estado_disponibilidad}'. "
                        f"Solo se puede devolver bien 'Asignado'.")

                # Guardar estado anterior para auditoría
                estado_anterior = bien.estado_bien
                fecha_devolucion = date.today()

                # Cambiar bien a Disponible
                bien.estado_disponibilidad = "Disponible"
                bien.estado_bien = estado_retorno
                bien.updated_at = datetime.now()

                session.flush()

                # Auditar devolución
                session.add(Auditoria(
                    usuario_id=usuario_id,
                    tabla_afectada="bienes_patrimoniales",
                    accion="DEVOLUCION_TALLER",
                    registro_id=bien_id,
                    datos_nuevos={
                        "bien_codigo": bien.codigo,
                        "fecha_devolucion": str(fecha_devolucion),
                        "estado_retorno": estado_retorno,
                        "estado_anterior": estado_anterior,
                        "observacion_devolucion": observacion
                    }
                ))

                session.commit()

                # Preparar mensaje con alerta si corresponde
                alerta = ""
                if estado_retorno == "Malo":
                    alerta = " ⚠️ ALERTA: Bien devuelto en ESTADO MALO"
                elif estado_retorno == "Regular":
                    alerta = " ⚠️ AVISO: Bien devuelto en estado regular"

                return ResultadoAsignacion(True,
                    f"Devolución registrada correctamente.{alerta}",
                    datos={
                        "bien_codigo": bien.codigo,
                        "estado_retorno": estado_retorno,
                        "alerta": bool(alerta),
                        "fecha_devolucion": str(fecha_devolucion)
                    })

        except SQLAlchemyError as e:
            return ResultadoAsignacion(False, f"Error: {str(e)}")

    # ══════════════════════════════════════════════════════════════
    # RF-34: CAMBIAR ESTADO DE BIEN
    # ══════════════════════════════════════════════════════════════

    @staticmethod
    def cambiar_estado_bien(bien_id: int, nuevo_estado: str,
                           usuario_id: int) -> ResultadoAsignacion:
        """
        ✅ RF-34: Cambia el estado de disponibilidad del bien.

        TRANSICIONES VÁLIDAS:
          Disponible → Asignado | Mantenimiento
          Asignado → Disponible | Mantenimiento
          Mantenimiento → Disponible | Asignado

        PARÁMETROS:
          bien_id: ID del bien
          nuevo_estado: "Disponible" | "Asignado" | "Mantenimiento"
          usuario_id: Quién hace cambio

        RETORNA:
          ResultadoAsignacion con resultado
        """

        estados_validos = ("Disponible", "Asignado", "Mantenimiento")

        if nuevo_estado not in estados_validos:
            return ResultadoAsignacion(False,
                f"Estado inválido. Use: {', '.join(estados_validos)}")

        try:
            with get_session() as session:
                bien = session.get(BienPatrimonial, bien_id)

                if not bien:
                    return ResultadoAsignacion(False, "Bien no encontrado.")

                estado_anterior = bien.estado_disponibilidad

                # Validar transición
                transiciones_validas = {
                    "Disponible": ["Asignado", "Mantenimiento"],
                    "Asignado": ["Disponible", "Mantenimiento"],
                    "Mantenimiento": ["Disponible", "Asignado"]
                }

                if nuevo_estado not in transiciones_validas.get(estado_anterior, []):
                    return ResultadoAsignacion(False,
                        f"Transición no válida: {estado_anterior} → {nuevo_estado}")

                bien.estado_disponibilidad = nuevo_estado
                bien.updated_at = datetime.now()

                session.flush()

                # Auditar cambio de estado
                session.add(Auditoria(
                    usuario_id=usuario_id,
                    tabla_afectada="bienes_patrimoniales",
                    accion="CAMBIO_ESTADO",
                    registro_id=bien_id,
                    datos_anteriores={"estado_disponibilidad": estado_anterior},
                    datos_nuevos={"estado_disponibilidad": nuevo_estado}
                ))

                session.commit()

                return ResultadoAsignacion(True,
                    f"Estado cambiado: {estado_anterior} → {nuevo_estado}")

        except SQLAlchemyError as e:
            return ResultadoAsignacion(False, f"Error: {str(e)}")

    # ══════════════════════════════════════════════════════════════
    # RF-35: DETECTAR ALERTAS
    # ══════════════════════════════════════════════════════════════

    @staticmethod
    def obtener_alertas_bienes() -> Dict[str, Any]:
        """
        ✅ RF-35: Detecta alertas de bienes vencidos o dañados.

        RETORNA:
          {
            "vencidos": [bienes sin devolver y vencidos],
            "dañados": [bienes devueltos en mal estado],
            "en_mantenimiento": [bienes en mantenimiento],
            "total_alertas": N
          }
        """

        try:
            with get_session() as session:
                hoy = date.today()

                # Obtener bienes ASIGNADOS (sin devolver)
                # Comparar con auditoría para saber fecha límite
                asignados = session.query(BienPatrimonial).filter(
                    BienPatrimonial.estado_disponibilidad == "Asignado"
                ).all()

                vencidos_list = []
                en_mantenimiento = []

                for bien in asignados:
                    # Buscar auditoría de asignación más reciente
                    ultima_asignacion = session.query(Auditoria).filter(
                        Auditoria.registro_id == bien.id,
                        Auditoria.tabla_afectada == "bienes_patrimoniales",
                        Auditoria.accion.in_(["ASIGNACION_TALLER", "UPDATE"])
                    ).order_by(Auditoria.created_at.desc()).first()

                    if ultima_asignacion and ultima_asignacion.datos_nuevos:
                        fecha_limite_str = ultima_asignacion.datos_nuevos.get(
                            "fecha_limite_devolucion"
                        )

                        if fecha_limite_str:
                            try:
                                fecha_limite = datetime.strptime(
                                    fecha_limite_str, "%Y-%m-%d"
                                ).date()

                                if fecha_limite < hoy:
                                    dias_vencidos = (hoy - fecha_limite).days
                                    vencidos_list.append({
                                        "bien_id": bien.id,
                                        "bien_codigo": bien.codigo,
                                        "bien_descripcion": bien.descripcion,
                                        "estado_bien": bien.estado_bien,
                                        "valor": bien.valor,
                                        "fecha_limite": str(fecha_limite),
                                        "dias_vencidos": dias_vencidos,
                                        "alerta": f"🔴 VENCIDO ({dias_vencidos} días)"
                                    })
                            except:
                                pass

                # Obtener bienes DAÑADOS (en estado Malo)
                dañados = session.query(BienPatrimonial).filter(
                    BienPatrimonial.estado_bien == "Malo",
                    BienPatrimonial.estado_disponibilidad == "Disponible"
                ).all()

                dañados_list = [
                    {
                        "bien_id": b.id,
                        "bien_codigo": b.codigo,
                        "bien_descripcion": b.descripcion,
                        "valor": b.valor,
                        "alerta": "💔 DAÑADO"
                    }
                    for b in dañados
                ]

                # Obtener bienes en MANTENIMIENTO
                mantenimiento = session.query(BienPatrimonial).filter(
                    BienPatrimonial.estado_disponibilidad == "Mantenimiento"
                ).all()

                mantenimiento_list = [
                    {
                        "bien_id": b.id,
                        "bien_codigo": b.codigo,
                        "bien_descripcion": b.descripcion,
                        "estado_bien": b.estado_bien,
                        "alerta": "🔧 EN MANTENIMIENTO"
                    }
                    for b in mantenimiento
                ]

                return {
                    "vencidos": vencidos_list,
                    "dañados": dañados_list,
                    "en_mantenimiento": mantenimiento_list,
                    "total_alertas": len(vencidos_list) + len(dañados_list)
                }

        except SQLAlchemyError:
            return {
                "vencidos": [],
                "dañados": [],
                "en_mantenimiento": [],
                "total_alertas": 0
            }

    # ══════════════════════════════════════════════════════════════
    # CONSULTAS ÚTILES
    # ══════════════════════════════════════════════════════════════

    @staticmethod
    def obtener_bienes_disponibles() -> List[Dict]:
        """Obtiene lista de bienes disponibles para asignar."""
        try:
            with get_session() as session:
                bienes = session.query(BienPatrimonial).filter(
                    BienPatrimonial.estado_disponibilidad == "Disponible"
                ).order_by(BienPatrimonial.codigo).all()

                return [
                    {
                        "id": b.id,
                        "codigo": b.codigo,
                        "descripcion": b.descripcion,
                        "estado_bien": b.estado_bien,
                        "valor": b.valor,
                        "estado_disponibilidad": b.estado_disponibilidad
                    }
                    for b in bienes
                ]

        except SQLAlchemyError:
            return []

    @staticmethod
    def obtener_bienes_asignados() -> List[Dict]:
        """Obtiene lista de bienes actualmente asignados."""
        try:
            with get_session() as session:
                bienes = session.query(BienPatrimonial).filter(
                    BienPatrimonial.estado_disponibilidad == "Asignado"
                ).order_by(BienPatrimonial.codigo).all()

                return [
                    {
                        "id": b.id,
                        "codigo": b.codigo,
                        "descripcion": b.descripcion,
                        "estado_bien": b.estado_bien,
                        "valor": b.valor,
                        "estado_disponibilidad": b.estado_disponibilidad
                    }
                    for b in bienes
                ]

        except SQLAlchemyError:
            return []

    @staticmethod
    def obtener_bien_por_id(bien_id: int) -> Optional[Dict]:
        """Obtiene detalles de un bien."""
        try:
            with get_session() as session:
                bien = session.get(BienPatrimonial, bien_id)

                if not bien:
                    return None

                return {
                    "id": bien.id,
                    "codigo": bien.codigo,
                    "descripcion": bien.descripcion,
                    "estado_bien": bien.estado_bien,
                    "valor": bien.valor,
                    "estado_disponibilidad": bien.estado_disponibilidad,
                    "created_at": str(bien.created_at),
                    "updated_at": str(bien.updated_at)
                }

        except SQLAlchemyError:
            return None
