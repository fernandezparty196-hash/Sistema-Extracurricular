"""
services/inscripcion_service.py   ──   Gestión de Inscripciones
═════════════════════════════════════════════════════════════════

Servicio para manejar inscripciones de estudiantes en talleres.
Usado por asistencia y reportes.
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from sqlalchemy import and_
from sqlalchemy.exc import SQLAlchemyError

from database.connection import get_session
from models import Inscripcion, Estudiante, Taller, Sesion, Asistencia


@dataclass
class ResultadoInscripcion:
    """Respuesta estándar para operaciones de inscripción."""
    ok: bool
    mensaje: str
    lista: Optional[List[Dict[str, Any]]] = None
    datos: Optional[Dict[str, Any]] = None


class InscripcionService:
    """Servicio de gestión de inscripciones."""

    @staticmethod
    def obtener_inscritos_taller(taller_id: int, activos_solo: bool = True) -> List[Dict[str, Any]]:
        """
        Obtiene lista de estudiantes inscritos en un taller.
        
        Retorna:
          List[dict] con:
            - id (inscripcion_id)
            - estudiante_id
            - nombre_completo
            - dni
            - codigo_estudiantil
            - carrera
            - ciclo
            - estado (Activo/Retirado)
        """
        try:
            with get_session() as session:
                query = (
                    session.query(Inscripcion)
                    .filter(Inscripcion.taller_id == taller_id)
                    .join(Estudiante)
                )

                if activos_solo:
                    query = query.filter(Inscripcion.estado == "Activo")

                inscripciones = query.order_by(
                    Estudiante.apellidos, Estudiante.nombres
                ).all()

                return [
                    {
                        "inscripcion_id": insc.id,
                        "estudiante_id": insc.estudiante_id,
                        "nombre_completo": f"{insc.estudiante.nombres} {insc.estudiante.apellidos}",
                        "nombres": insc.estudiante.nombres,
                        "apellidos": insc.estudiante.apellidos,
                        "dni": insc.estudiante.dni,
                        "codigo_estudiantil": insc.estudiante.codigo_estudiantil or "—",
                        "carrera": insc.estudiante.carrera.nombre if insc.estudiante.carrera else "—",
                        "ciclo": insc.estudiante.ciclo_actual or "—",
                        "estado": insc.estado,
                    }
                    for insc in inscripciones
                ]

        except SQLAlchemyError as e:
            print(f"Error al obtener inscritos: {str(e)}")
            return []

    @staticmethod
    def obtener_inscritos_sesion(sesion_id: int) -> List[Dict[str, Any]]:
        """
        Obtiene inscritos de un taller que corresponde a una sesión.
        """
        try:
            with get_session() as session:
                sesion = session.query(Sesion).filter_by(id=sesion_id).first()
                if not sesion:
                    return []

                return InscripcionService.obtener_inscritos_taller(
                    sesion.taller_id, activos_solo=True
                )

        except SQLAlchemyError:
            return []

    @staticmethod
    def obtener_inscripcion(taller_id: int, estudiante_id: int) -> Optional[Dict[str, Any]]:
        """Obtiene inscripción específica de un estudiante en un taller."""
        try:
            with get_session() as session:
                insc = (
                    session.query(Inscripcion)
                    .filter(
                        and_(
                            Inscripcion.taller_id == taller_id,
                            Inscripcion.estudiante_id == estudiante_id
                        )
                    )
                    .first()
                )

                if not insc:
                    return None

                return {
                    "inscripcion_id": insc.id,
                    "taller_id": insc.taller_id,
                    "estudiante_id": insc.estudiante_id,
                    "estado": insc.estado,
                    "fecha_inscripcion": insc.fecha_inscripcion.isoformat(),
                }

        except SQLAlchemyError:
            return None

    @staticmethod
    def listar_por_estudiante(estudiante_id: int, activas_solo: bool = True) -> List[Dict[str, Any]]:
        """Lista todos los talleres en los que está inscrito un estudiante."""
        try:
            with get_session() as session:
                query = (
                    session.query(Inscripcion)
                    .filter(Inscripcion.estudiante_id == estudiante_id)
                    .join(Taller)
                )

                if activas_solo:
                    query = query.filter(Inscripcion.estado == "Activo")

                inscripciones = query.all()

                return [
                    {
                        "inscripcion_id": insc.id,
                        "taller_id": insc.taller_id,
                        "taller_nombre": insc.taller.nombre,
                        "estado": insc.estado,
                    }
                    for insc in inscripciones
                ]

        except SQLAlchemyError:
            return []