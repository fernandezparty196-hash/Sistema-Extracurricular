from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError

from database.connection import get_session
from models import Sesion, Auditoria


class ResultadoSesion:
    def __init__(self, ok: bool, mensaje: str, datos=None):
        self.ok = ok
        self.mensaje = mensaje
        self.datos = datos


class SesionService:

    ESTADOS_VALIDOS = (
        "Programada",
        "Realizada",
        "Cancelada",
    )

    # ══════════════════════════════════════════════════════════════
    # CAMBIAR ESTADO DE SESIÓN
    # ══════════════════════════════════════════════════════════════
    @staticmethod
    def cambiar_estado(
        sesion_id: int,
        nuevo_estado: str,
        usuario_id: int
    ) -> ResultadoSesion:

        if nuevo_estado not in SesionService.ESTADOS_VALIDOS:
            return ResultadoSesion(
                False,
                f"Estado inválido. Use: {SesionService.ESTADOS_VALIDOS}"
            )

        try:
            with get_session() as session:

                sesion = session.get(Sesion, sesion_id)

                if not sesion:
                    return ResultadoSesion(
                        False,
                        "Sesión no encontrada."
                    )

                estado_anterior = sesion.estado

                if estado_anterior == nuevo_estado:
                    return ResultadoSesion(
                        False,
                        f"La sesión ya está en estado '{nuevo_estado}'."
                    )

                # Regla de negocio:
                # Si tiene asistencias registradas no puede volver
                # a Programada.
                if (
                    nuevo_estado == "Programada"
                    and len(sesion.asistencias) > 0
                ):
                    return ResultadoSesion(
                        False,
                        "No se puede volver a Programada porque ya existen asistencias registradas."
                    )

                sesion.estado = nuevo_estado
                sesion.updated_at = datetime.now()

                session.add(
                    Auditoria(
                        usuario_id=usuario_id,
                        tabla_afectada="sesiones",
                        accion="UPDATE",
                        registro_id=sesion.id,
                        datos_anteriores={
                            "estado": estado_anterior
                        },
                        datos_nuevos={
                            "estado": nuevo_estado
                        }
                    )
                )

                session.commit()

                return ResultadoSesion(
                    True,
                    f"Estado cambiado a '{nuevo_estado}'.",
                    datos={
                        "sesion_id": sesion.id,
                        "estado_anterior": estado_anterior,
                        "estado_nuevo": nuevo_estado
                    }
                )

        except SQLAlchemyError as e:
            return ResultadoSesion(
                False,
                f"Error al actualizar la sesión: {e}"
            )