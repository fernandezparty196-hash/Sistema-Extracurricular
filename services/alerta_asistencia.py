"""
services/alerta_asistencia_service.py
═══════════════════════════════════════════════════════════════

Servicio de gestión de alertas de asistencia.

RF-20
• Crear alertas por bajo porcentaje.
• Listar alertas.
• Desactivar alertas.
• Obtener alertas por taller.
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any

from sqlalchemy.exc import SQLAlchemyError

from database.connection import get_session
from models.alerta_asistencia import AlertaAsistencia
from models.estudiante import Estudiante
from models.taller import Taller


@dataclass
class ResultadoAlerta:
    ok: bool
    mensaje: str
    datos: Optional[Any] = None
    lista: Optional[List[Dict]] = None


class AlertaAsistenciaService:

    @staticmethod
    def crear(
        estudiante_id: int,
        taller_id: int,
        porcentaje: float,
        tipo: str = "riesgo_desaprobacion"
    ) -> ResultadoAlerta:
        """
        Crea una alerta si aún no existe una activa.
        """

        try:
            with get_session() as session:

                alerta = session.query(AlertaAsistencia).filter_by(
                    estudiante_id=estudiante_id,
                    taller_id=taller_id,
                    activa=True
                ).first()

                if alerta:

                    alerta.porcentaje_asistencia = porcentaje

                else:

                    alerta = AlertaAsistencia(
                        estudiante_id=estudiante_id,
                        taller_id=taller_id,
                        tipo_alerta=tipo,
                        porcentaje_asistencia=porcentaje,
                        activa=True
                    )

                    session.add(alerta)

                session.commit()

                return ResultadoAlerta(
                    True,
                    "Alerta registrada correctamente."
                )

        except SQLAlchemyError as e:

            return ResultadoAlerta(
                False,
                str(e)
            )

    @staticmethod
    def desactivar(alerta_id: int) -> ResultadoAlerta:

        try:
            with get_session() as session:

                alerta = session.get(AlertaAsistencia, alerta_id)

                if not alerta:
                    return ResultadoAlerta(False, "Alerta no encontrada.")

                alerta.activa = False

                session.commit()

                return ResultadoAlerta(
                    True,
                    "Alerta desactivada."
                )

        except SQLAlchemyError as e:

            return ResultadoAlerta(False, str(e))

    @staticmethod
    def listar_activas() -> ResultadoAlerta:

        try:

            with get_session() as session:

                alertas = (
                    session.query(AlertaAsistencia)
                    .join(Estudiante)
                    .join(Taller)
                    .filter(AlertaAsistencia.activa == True)
                    .order_by(
                        AlertaAsistencia.porcentaje_asistencia.asc()
                    )
                    .all()
                )

                lista = []

                for a in alertas:

                    lista.append({

                        "id": a.id,
                        "estudiante_id": a.estudiante_id,
                        "taller_id": a.taller_id,
                        "estudiante": f"{a.estudiante.nombres} {a.estudiante.apellidos}",
                        "taller": a.taller.nombre,
                        "tipo": a.tipo_alerta,
                        "porcentaje": a.porcentaje_asistencia,
                        "activa": a.activa,
                        "fecha": a.fecha_creacion.strftime("%d/%m/%Y")

                    })

                return ResultadoAlerta(
                    True,
                    f"{len(lista)} alertas encontradas.",
                    lista=lista
                )

        except SQLAlchemyError as e:

            return ResultadoAlerta(False, str(e))

    @staticmethod
    def listar_por_taller(taller_id: int) -> ResultadoAlerta:

        try:

            with get_session() as session:

                alertas = (
                    session.query(AlertaAsistencia)
                    .filter(
                        AlertaAsistencia.taller_id == taller_id,
                        AlertaAsistencia.activa == True
                    )
                    .all()
                )

                lista = []

                for a in alertas:

                    lista.append({

                        "id": a.id,
                        "estudiante": f"{a.estudiante.nombres} {a.estudiante.apellidos}",
                        "tipo": a.tipo_alerta,
                        "porcentaje": a.porcentaje_asistencia,
                        "fecha": a.fecha_creacion.strftime("%d/%m/%Y")

                    })

                return ResultadoAlerta(
                    True,
                    "",
                    lista=lista
                )

        except SQLAlchemyError as e:

            return ResultadoAlerta(False, str(e))

    @staticmethod
    def existe_alerta_activa(
        estudiante_id: int,
        taller_id: int
    ) -> bool:

        try:

            with get_session() as session:

                return (
                    session.query(AlertaAsistencia)
                    .filter_by(
                        estudiante_id=estudiante_id,
                        taller_id=taller_id,
                        activa=True
                    )
                    .count() > 0
                )

        except SQLAlchemyError:

            return False