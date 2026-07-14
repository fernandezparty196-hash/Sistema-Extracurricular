"""
services/auditoria_service.py   ──   Consulta de Auditoría
═══════════════════════════════════════════════════════════

¿QUÉ HACE ESTE ARCHIVO?
  Servicio de SOLO LECTURA sobre la tabla `auditoria`. La UI Qt
  (ui/auditoria/panel_auditoria.py) nunca consulta SQLAlchemy
  directamente — todo pasa por aquí, igual que el resto de módulos.

FILTROS SOPORTADOS:
  usuario_id, tabla_afectada, accion (INSERT/UPDATE/DELETE),
  rango de fechas, y texto libre (busca en usuario y tabla).

PAGINACIÓN:
  listar() siempre devuelve una página acotada (por_pagina),
  junto con el total de registros y el total de páginas, para
  que la UI pueda dibujar controles de "anterior/siguiente".
"""

from dataclasses import dataclass, field
from datetime    import datetime, date
from typing      import Optional

from sqlalchemy      import desc
from sqlalchemy.exc  import SQLAlchemyError

from database.connection import get_session
from models               import Auditoria, Usuario


ACCIONES_DISPONIBLES = ("INSERT", "UPDATE", "DELETE")
POR_PAGINA_DEFAULT   = 25


# ══════════════════════════════════════════════════════════════════
# DATACLASSES DE SALIDA
# ══════════════════════════════════════════════════════════════════

@dataclass
class RegistroAuditoria:
    """
    Snapshot 'plano' de una fila de auditoría, ya desacoplado del
    objeto SQLAlchemy (evita usar el modelo fuera de la sesión,
    lo que provocaría DetachedInstanceError en la UI).
    """
    id:                int
    usuario_id:        Optional[int]
    usuario_nombre:    str
    tabla_afectada:    str
    accion:            str
    registro_id:       Optional[int]
    datos_anteriores:  Optional[dict]
    datos_nuevos:      Optional[dict]
    ip_address:        Optional[str]
    created_at:        datetime


@dataclass
class ResultadoAuditoria:
    """Resultado estándar de las consultas de este servicio."""
    ok:            bool
    mensaje:       str
    registros:     list[RegistroAuditoria] = field(default_factory=list)
    total:         int = 0
    pagina:        int = 1
    total_paginas: int = 1


# ══════════════════════════════════════════════════════════════════
# SERVICIO
# ══════════════════════════════════════════════════════════════════

class AuditoriaService:
    """Todas las funciones son @staticmethod; no requiere instancia."""

    @staticmethod
    def listar(
        usuario_id:      Optional[int]  = None,
        tabla_afectada:  Optional[str]  = None,
        accion:          Optional[str]  = None,
        fecha_desde:     Optional[date] = None,
        fecha_hasta:     Optional[date] = None,
        texto_libre:     Optional[str]  = None,
        pagina:          int = 1,
        por_pagina:      int = POR_PAGINA_DEFAULT,
    ) -> ResultadoAuditoria:
        """
        Lista registros de auditoría aplicando filtros opcionales,
        ordenados del más reciente al más antiguo, con paginación.
        """
        pagina = max(1, pagina)

        try:
            with get_session() as session:
                query = session.query(Auditoria)

                if usuario_id:
                    query = query.filter(Auditoria.usuario_id == usuario_id)

                if tabla_afectada:
                    query = query.filter(Auditoria.tabla_afectada == tabla_afectada)

                if accion:
                    query = query.filter(Auditoria.accion == accion)

                if fecha_desde:
                    query = query.filter(
                        Auditoria.created_at >= datetime.combine(fecha_desde, datetime.min.time())
                    )

                if fecha_hasta:
                    query = query.filter(
                        Auditoria.created_at <= datetime.combine(fecha_hasta, datetime.max.time())
                    )

                if texto_libre and texto_libre.strip():
                    patron = f"%{texto_libre.strip()}%"
                    query = (
                        query.join(Usuario, Auditoria.usuario_id == Usuario.id, isouter=True)
                        .filter(
                            (Usuario.nombre_completo.ilike(patron)) |
                            (Usuario.username.ilike(patron)) |
                            (Auditoria.tabla_afectada.ilike(patron))
                        )
                    )

                total = query.count()
                total_paginas = max(1, (total + por_pagina - 1) // por_pagina)
                pagina = min(pagina, total_paginas)

                filas = (
                    query.order_by(desc(Auditoria.created_at))
                    .offset((pagina - 1) * por_pagina)
                    .limit(por_pagina)
                    .all()
                )

                registros = [
                    RegistroAuditoria(
                        id               = f.id,
                        usuario_id       = f.usuario_id,
                        usuario_nombre   = (f.usuario.nombre_completo if f.usuario else "Sistema"),
                        tabla_afectada   = f.tabla_afectada,
                        accion           = f.accion,
                        registro_id      = f.registro_id,
                        datos_anteriores = f.datos_anteriores,
                        datos_nuevos     = f.datos_nuevos,
                        ip_address       = f.ip_address,
                        created_at       = f.created_at,
                    )
                    for f in filas
                ]

                return ResultadoAuditoria(
                    ok            = True,
                    mensaje       = "Consulta exitosa.",
                    registros     = registros,
                    total         = total,
                    pagina        = pagina,
                    total_paginas = total_paginas,
                )

        except SQLAlchemyError as e:
            return ResultadoAuditoria(ok=False, mensaje=f"Error al consultar auditoría: {e}")

    @staticmethod
    def listar_tablas_disponibles() -> list[str]:
        """
        Devuelve los nombres de tabla distintos que existen en
        `auditoria`, para poblar dinámicamente el filtro de tabla.
        """
        try:
            with get_session() as session:
                filas = (
                    session.query(Auditoria.tabla_afectada)
                    .distinct()
                    .order_by(Auditoria.tabla_afectada)
                    .all()
                )
                return [f[0] for f in filas]
        except SQLAlchemyError:
            return []
