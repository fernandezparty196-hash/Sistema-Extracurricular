from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional, List, Dict, Any

from sqlalchemy import and_, func, or_
from sqlalchemy.exc import SQLAlchemyError

from database.connection import get_session
from models import (
    Estudiante, Taller, Sesion, Asistencia, Inscripcion,
    CicloAcademico, Carrera, Usuario
)


@dataclass
class ResultadoReporte:
    """Estructura de respuesta estándar para reportes."""
    ok: bool
    mensaje: str
    datos: Optional[Any] = None
    lista: Optional[List[Dict]] = None


class ReporteService:
    """Servicio mejorado de generación de reportes."""

    # ══════════════════════════════════════════════════════════════════════════
    # FILTROS Y BÚSQUEDAS
    # ══════════════════════════════════════════════════════════════════════════

    @staticmethod
    def listar_estudiantes_filtrados(
        ciclo_id: int = None,nombre: str = None,
        carrera_id: int = None,taller_id: int = None) -> ResultadoReporte:

        try:
            with get_session() as session:
                query = session.query(Estudiante).filter(Estudiante.estado == "Activo")
                
                # Filtro por ciclo
                if ciclo_id:
                    query = query.filter(Estudiante.ciclo_actual == ciclo_id)
                
                # Filtro por nombre/apellido
                if nombre:
                    nombre_busqueda = f"%{nombre}%"
                    query = query.filter(
                        or_(
                            Estudiante.nombres.ilike(nombre_busqueda),
                            Estudiante.apellidos.ilike(nombre_busqueda),
                            Estudiante.codigo_estudiantil.ilike(nombre_busqueda)
                        )
                    )
                
                # Filtro por carrera
                if carrera_id:
                    query = query.filter(Estudiante.carrera_id == carrera_id)
                
                # Filtro por taller (inscripción)
                if taller_id:
                    query = query.join(Inscripcion).filter(
                        and_(Inscripcion.taller_id == taller_id,Inscripcion.estado == "Activo")).distinct()
                
                estudiantes = query.order_by(Estudiante.apellidos, Estudiante.nombres).all()
                
                lista = [
                    {
                        "id": e.id,
                        "codigo": e.codigo_estudiantil,
                        "nombre": e.nombre_completo,
                        "email": e.email,
                        "carrera": e.carrera.nombre if e.carrera else "N/A",
                        "ciclo": e.ciclo_actual
                    }
                    for e in estudiantes
                ]
                
                return ResultadoReporte(
                    ok=True,
                    mensaje=f"Se encontraron {len(lista)} estudiantes",
                    lista=lista
                )
        
        except Exception as e:
            return ResultadoReporte(ok=False, mensaje=f"Error: {str(e)}")

    @staticmethod
    def listar_ciclos() -> List[Dict]:
        """Lista ciclos académicos activos."""
        try:
            with get_session() as session:
                ciclos = session.query(CicloAcademico).filter(
                    CicloAcademico.activo == True
                ).order_by(CicloAcademico.nombre).all()
                
                return [
                    {"id": c.id, "nombre": c.nombre}
                    for c in ciclos
                ]
        except:
            return []

    @staticmethod
    def listar_carreras() -> List[Dict]:
        """Lista carreras."""
        try:
            with get_session() as session:
                carreras = session.query(Carrera).order_by(Carrera.nombre).all()
                return [
                    {"id": c.id, "nombre": c.nombre}
                    for c in carreras
                ]
        except:
            return []

    @staticmethod
    def listar_talleres_activos() -> List[Dict]:
        """Lista talleres activos."""
        try:
            with get_session() as session:
                talleres = session.query(Taller).filter(
                    Taller.estado == "Activo"
                ).order_by(Taller.nombre).all()
                
                return [
                    {
                        "id": t.id,
                        "codigo": t.codigo,
                        "nombre": t.nombre,
                        "docente": t.docente.nombre_completo if t.docente else "N/A"
                    }
                    for t in talleres
                ]
        except:
            return []

    # ══════════════════════════════════════════════════════════════════════════
    # REPORTE DE ESTUDIANTE (MEJORADO)
    # ══════════════════════════════════════════════════════════════════════════

    @staticmethod
    def obtener_reporte_estudiante(estudiante_id: int) -> ResultadoReporte:
        try:
            with get_session() as session:
                estudiante = session.query(Estudiante).filter(
                    and_(
                        Estudiante.id == estudiante_id,
                        Estudiante.estado == "Activo"
                    )
                ).first()
                if not estudiante:
                    return ResultadoReporte(
                        ok=False,
                        mensaje="Estudiante no encontrado"
                    )

                # Obtener inscripciones activas
                inscripciones = session.query(Inscripcion).filter(
                    and_(
                        Inscripcion.estudiante_id == estudiante_id,
                        Inscripcion.estado == "Activo"
                    )
                ).all()

                talleres_list = []
                asistencias_totales = []

                for inscripcion in inscripciones:
                    taller = inscripcion.taller

                    # ✅ Contar sesiones del taller
                    total_sesiones = session.query(func.count(Sesion.id)).filter(
                        Sesion.taller_id == taller.id
                    ).scalar() or 0

                    # ✅ Contar PRESENTES (P)
                    presentes = session.query(func.count(Asistencia.id)).filter(
                        and_(
                            Asistencia.inscripcion_id == inscripcion.id,
                            Asistencia.estado == "P"
                        )
                    ).scalar() or 0

                    # ✅ Contar JUSTIFICADOS (J)
                    justificados = session.query(func.count(Asistencia.id)).filter(
                        and_(
                            Asistencia.inscripcion_id == inscripcion.id,
                            Asistencia.estado == "J"
                        )
                    ).scalar() or 0

                    # ✅ Contar AUSENTES (A)
                    ausentes = session.query(func.count(Asistencia.id)).filter(
                        and_(
                            Asistencia.inscripcion_id == inscripcion.id,
                            Asistencia.estado == "A"
                        )
                    ).scalar() or 0

                    # ✅ Porcentaje: (P + J) / Total
                    asistencias_validas = presentes + justificados
                    porcentaje = (asistencias_validas / total_sesiones * 100) \
                               if total_sesiones > 0 else 0.0

                    # ✅ Estado (semáforo)
                    if porcentaje >= 90:
                        estado = "✅ Verde"
                    elif porcentaje >= 80:
                        estado = "⚠️ Amarillo"
                    else:
                        estado = "❌ Rojo"

                    talleres_list.append({
                        "taller_id": taller.id,
                        "taller_nombre": taller.nombre,
                        "taller_codigo": taller.codigo,
                        "docente": taller.docente.nombre_completo if taller.docente else "N/A",
                        "total_sesiones": total_sesiones,
                        "presentes": presentes,
                        "justificados": justificados,
                        "ausentes": ausentes,
                        "asistencias_validas": asistencias_validas,
                        "porcentaje_asistencia": round(porcentaje, 2),
                        "estado": estado
                    })

                    asistencias_totales.append(porcentaje)

                # Estadísticas generales
                promedio_asistencia = (
                    sum(asistencias_totales) / len(asistencias_totales)
                    if asistencias_totales else 0.0
                )

                datos = {
                    "estudiante": {
                        "id": estudiante.id,
                        "codigo": estudiante.codigo_estudiantil,
                        "nombre": estudiante.nombre_completo,
                        "email": estudiante.email,
                        "carrera": estudiante.carrera.nombre if estudiante.carrera else "N/A",
                        "ciclo": estudiante.ciclo_actual 
                    },
                    "talleres": talleres_list,
                    "estadisticas_generales": {
                        "total_talleres": len(talleres_list),
                        "promedio_asistencia": round(promedio_asistencia, 2),
                        "fecha_generacion": datetime.now().strftime("%d/%m/%Y %H:%M")
                    }
                }

                return ResultadoReporte(ok=True,
                    mensaje="Reporte de estudiante generado correctamente",datos=datos,
                    lista=talleres_list)

        except Exception as e:
            return ResultadoReporte(
                ok=False,
                mensaje=f"Error al generar reporte: {str(e)}"
            )

    # ══════════════════════════════════════════════════════════════════════════
    # REPORTE DE TALLER
    # ══════════════════════════════════════════════════════════════════════════

    @staticmethod
    def obtener_reporte_taller(taller_id: int,sesion_ids: List[int] = None) -> ResultadoReporte:
        try:
            with get_session() as session:
                taller = session.query(Taller).filter_by(id=taller_id).first()
                
                if not taller:
                    return ResultadoReporte(
                        ok=False,
                        mensaje="Taller no encontrado"
                    )

                # Obtener sesiones
                query_sesiones = session.query(Sesion).filter(
                    Sesion.taller_id == taller_id
                )
                
                if sesion_ids:
                    query_sesiones = query_sesiones.filter(
                        Sesion.id.in_(sesion_ids)
                    )
                
                sesiones = query_sesiones.order_by(Sesion.numero_sesion).all()

                if not sesiones:
                    return ResultadoReporte(
                        ok=False,
                        mensaje="No hay sesiones en este taller"
                    )

                # Obtener estudiantes inscritos
                inscripciones = session.query(Inscripcion).filter(
                    and_(
                        Inscripcion.taller_id == taller_id,
                        Inscripcion.estado == "Activo"
                    )
                ).all()

                # Construir matriz de asistencia
                estudiantes_list = []

                for inscripcion in inscripciones:
                    estudiante = inscripcion.estudiante
                    
                    presentes = 0
                    justificados = 0
                    ausentes = 0

                    asistencias_por_sesion = []

                    for sesion in sesiones:
                        asistencia = session.query(Asistencia).filter(
                            and_(
                                Asistencia.inscripcion_id == inscripcion.id,
                                Asistencia.sesion_id == sesion.id
                            )
                        ).first()

                        estado = "Sin registrar"
                        if asistencia:
                            if asistencia.estado == "P":
                                estado = "✅ P"
                                presentes += 1
                            elif asistencia.estado == "J":
                                estado = "✅ J"
                                justificados += 1
                            elif asistencia.estado == "A":
                                estado = "❌ A"
                                ausentes += 1

                        asistencias_por_sesion.append({
                            "sesion_id": sesion.id,
                            "sesion_numero": sesion.numero_sesion,
                            "estado": estado
                        })

                    total_registros = presentes + justificados + ausentes
                    porcentaje = ((presentes + justificados) / total_registros * 100) \
                               if total_registros > 0 else 0.0

                    estudiantes_list.append({
                        "estudiante_id": estudiante.id,
                        "codigo": estudiante.codigo_estudiantil,
                        "nombre": estudiante.nombre_completo,
                        "carrera": estudiante.carrera.nombre if estudiante.carrera else "N/A",
                        "ciclo": estudiante.ciclo_actual,
                        "presentes": presentes,
                        "justificados": justificados,
                        "ausentes": ausentes,
                        "porcentaje": round(porcentaje, 2),
                        "asistencias_por_sesion": asistencias_por_sesion
                    })

                # Estadísticas generales
                sesiones_info = [
                    {
                        "id": s.id,
                        "numero": s.numero_sesion,
                        "fecha": s.fecha.strftime("%d/%m/%Y") if s.fecha else "N/A"
                    }
                    for s in sesiones
                ]

                datos = {
                    "taller": {
                        "id": taller.id,
                        "codigo": taller.codigo,
                        "nombre": taller.nombre,
                        "docente": taller.docente.nombre_completo if taller.docente else "N/A",
                        "periodo_academico": taller.ciclo_academico.nombre if taller.ciclo_academico else "N/A"
                    },
                    "sesiones": sesiones_info,
                    "estudiantes": estudiantes_list,
                    "estadisticas": {
                        "total_estudiantes": len(estudiantes_list),
                        "total_sesiones": len(sesiones),
                        "asistencia_promedio": round(
                            sum(e["porcentaje"] for e in estudiantes_list) / len(estudiantes_list)
                            if estudiantes_list else 0,
                            2
                        ),
                        "fecha_generacion": datetime.now().strftime("%d/%m/%Y %H:%M")
                    }
                }

                return ResultadoReporte(
                    ok=True,
                    mensaje="Reporte de taller generado correctamente",
                    datos=datos,
                    lista=estudiantes_list
                )

        except Exception as e:
            return ResultadoReporte(
                ok=False,
                mensaje=f"Error al generar reporte: {str(e)}"
            )

    # ══════════════════════════════════════════════════════════════════════════
    # DASHBOARD (HU-12) — con alcance por rol
    # ══════════════════════════════════════════════════════════════════════════

    @staticmethod
    def obtener_datos_dashboard(usuario_id: int = None, rol_nombre: str = None) -> ResultadoReporte:
        """
        Datos para el dashboard.

        ALCANCE POR ROL:
          • rol_nombre == "Docente": todo se filtra a los talleres que
            dicta ese usuario (mismo patrón que
            TallerService.listar_para_asistencia: Usuario → Docente →
            Taller). Su "horario" son las sesiones futuras de SUS
            talleres únicamente.
          • Cualquier otro rol (Administrador, Operador) o si no se
            pasan usuario_id/rol_nombre: vista global, sin filtrar
            (comportamiento original, por compatibilidad hacia atrás).
        """
        try:
            with get_session() as session:
                query_talleres = session.query(Taller).filter(Taller.estado == "Activo")

                docente_id = None
                if rol_nombre == "Docente" and usuario_id:
                    usuario = session.get(Usuario, usuario_id)
                    if not usuario or not usuario.docente:
                        # Usuario con rol Docente pero sin registro de
                        # docente asociado → dashboard vacío, sin error.
                        return ResultadoReporte(
                            ok=True,
                            mensaje="No hay un docente asociado a este usuario.",
                            datos={
                                "resumen": {
                                    "total_talleres": 0,
                                    "total_estudiantes": 0,
                                    "sesiones_hoy": 0,
                                    "proxima_sesion": "No hay sesiones próximas",
                                    "estudiantes_en_riesgo": 0,
                                },
                                "proximas_sesiones": [],
                            }
                        )
                    docente_id = usuario.docente.id
                    query_talleres = query_talleres.filter(Taller.docente_id == docente_id)

                talleres_alcance = query_talleres.all()
                ids_talleres = [t.id for t in talleres_alcance]
                alcance_docente = docente_id is not None

                total_talleres = len(talleres_alcance)

                if alcance_docente:
                    total_estudiantes = (
                        session.query(func.count(Inscripcion.id)).filter(
                            Inscripcion.taller_id.in_(ids_talleres),
                            Inscripcion.estado == "Activo"
                        ).scalar() or 0
                    ) if ids_talleres else 0
                else:
                    total_estudiantes = session.query(Estudiante).count()

                hoy = datetime.now().date()
                query_sesiones_hoy = session.query(Sesion).filter(func.date(Sesion.fecha) == hoy)
                if alcance_docente:
                    query_sesiones_hoy = (
                        query_sesiones_hoy.filter(Sesion.taller_id.in_(ids_talleres))
                        if ids_talleres else query_sesiones_hoy.filter(Sesion.id.is_(None))
                    )
                sesiones_hoy = query_sesiones_hoy.count()

                query_proxima = session.query(Sesion).filter(Sesion.fecha >= datetime.today())
                if alcance_docente:
                    query_proxima = (
                        query_proxima.filter(Sesion.taller_id.in_(ids_talleres))
                        if ids_talleres else query_proxima.filter(Sesion.id.is_(None))
                    )
                proxima_sesion = query_proxima.order_by(Sesion.fecha).first()

                proxima_sesion_dict = None
                if proxima_sesion:
                    taller = session.get(Taller, proxima_sesion.taller_id)
                    proxima_sesion_dict = {
                        "taller": f"{taller.codigo} - {taller.nombre}" if taller else "",
                        "sesion": proxima_sesion.numero_sesion,
                        "fecha": proxima_sesion.fecha.strftime("%d/%m/%Y") if proxima_sesion.fecha else "",
                        "ubicacion": taller.sede if taller else ""
                    }

                # Estudiantes en riesgo: reutiliza AsistenciaService, no
                # se duplica el cálculo de porcentaje/umbral aquí.
                estudiantes_en_riesgo = ReporteService._contar_en_riesgo(
                    ids_talleres if alcance_docente else None
                )

                datos = {
                    "resumen": {
                        "total_talleres": total_talleres,
                        "total_estudiantes": total_estudiantes,
                        "sesiones_hoy": sesiones_hoy,
                        "proxima_sesion": proxima_sesion_dict or "No hay sesiones próximas",
                        "estudiantes_en_riesgo": estudiantes_en_riesgo
                    },
                    "proximas_sesiones": ReporteService._obtener_proximas_sesiones(
                        session, 8, ids_talleres if alcance_docente else None
                    )
                }

                return ResultadoReporte(
                    ok=True,
                    mensaje="Datos de dashboard obtenidos",
                    datos=datos
                )

        except Exception as e:
            return ResultadoReporte(
                ok=False,
                mensaje=f"Error al obtener datos de dashboard: {str(e)}"
            )

    @staticmethod
    def _contar_en_riesgo(ids_talleres: Optional[List[int]]) -> int:
        """
        Cuenta estudiantes bajo el umbral de asistencia de su taller.
        Reutiliza AsistenciaService.obtener_estudiantes_en_riesgo() por
        taller (ya implementa correctamente el cálculo P/J vs umbral),
        en vez de duplicar esa lógica aquí.

        ids_talleres=None → alcance global (todos los talleres activos).
        ids_talleres=[]   → sin talleres (docente sin talleres a cargo).
        """
        try:
            from services.asistencia_service import AsistenciaService

            with get_session() as session:
                if ids_talleres is None:
                    ids_talleres = [
                        row[0] for row in
                        session.query(Taller.id).filter(Taller.estado == "Activo").all()
                    ]

            if not ids_talleres:
                return 0

            total = 0
            for taller_id in ids_talleres:
                total += len(AsistenciaService.obtener_estudiantes_en_riesgo(taller_id))
            return total
        except Exception:
            return 0

    @staticmethod
    def _obtener_proximas_sesiones(
        session, limite: int = 5, talleres_filtro: Optional[List[int]] = None
    ) -> List[Dict]:
        """
        Helper: obtiene próximas sesiones (el "horario" que ve el
        docente cuando talleres_filtro trae solo sus talleres).

        talleres_filtro=None → sin filtrar (todas las sesiones futuras).
        talleres_filtro=[]   → docente sin talleres, retorna lista vacía.
        """
        try:
            query = session.query(Sesion).filter(Sesion.fecha >= datetime.today())

            if talleres_filtro is not None:
                if not talleres_filtro:
                    return []
                query = query.filter(Sesion.taller_id.in_(talleres_filtro))

            sesiones = query.order_by(Sesion.fecha).limit(limite).all()

            lista = []
            for sesion in sesiones:
                taller = session.query(Taller).filter_by(
                    id=sesion.taller_id
                ).first()

                # Contar inscritos activos (antes comparaba contra
                # "Activa" en vez de "Activo" y siempre daba 0).
                inscritos = session.query(Inscripcion).filter(
                    and_(
                        Inscripcion.taller_id == sesion.taller_id,
                        Inscripcion.estado == "Activo"
                    )
                ).count()

                lista.append({
                    "taller": f"{taller.codigo} - {taller.nombre}" if taller else "",
                    "sesion": sesion.numero_sesion,
                    "fecha": sesion.fecha.strftime("%d/%m/%Y %H:%M") if sesion.fecha else "",
                    "ubicacion": taller.sede if taller else "",
                    "inscritos": inscritos
                })

            return lista
        except:
            return []

    # ══════════════════════════════════════════════════════════════════════════
    # UTILIDADES
    # ══════════════════════════════════════════════════════════════════════════

    @staticmethod
    def calcular_porcentaje_asistencia(
        estudiante_id: int,
        taller_id: int
    ) -> float:
        """Calcula porcentaje de asistencia de estudiante en taller."""
        try:
            with get_session() as session:
                # Total de sesiones
                total = session.query(Sesion).filter(
                    Sesion.taller_id == taller_id
                ).count()

                if total == 0:
                    return 0.0

                # Asistencias registradas
                presentes = session.query(Asistencia).filter(
                    and_(
                        Asistencia.estudiante_id == estudiante_id,
                        Asistencia.estado == "P",
                        Asistencia.sesion_id.in_(
                            session.query(Sesion.id).filter(
                                Sesion.taller_id == taller_id
                            )
                        )
                    )
                ).count()

                return (presentes / total * 100)
        except:
            return 0.0

    # ══════════════════════════════════════════════════════════════════════════
    # RF-36 · REPORTE DE ASISTENCIA POR TALLER (con tendencia para gráficos)
    # ══════════════════════════════════════════════════════════════════════════

    @staticmethod
    def obtener_reporte_asistencia_taller(
        taller_id: int = None,
        docente_id: int = None,
        fecha_inicio: date = None,
        fecha_fin: date = None
    ) -> ResultadoReporte:
        """
        RF-36: Reporte de asistencia por taller, filtrable por período,
        taller y docente.

        Por cada taller que cumpla el filtro devuelve una "tendencia":
        una lista ordenada [{sesion_numero, fecha, porcentaje_asistencia}]
        lista para que la UI la dibuje como gráfico de líneas (una serie
        por taller), más el promedio general del taller.
        """
        try:
            with get_session() as session:
                query = session.query(Taller).filter(Taller.estado == "Activo")
                if taller_id:
                    query = query.filter(Taller.id == taller_id)
                if docente_id:
                    query = query.filter(Taller.docente_id == docente_id)

                talleres = query.order_by(Taller.nombre).all()
                if not talleres:
                    return ResultadoReporte(
                        ok=False,
                        mensaje="No se encontraron talleres con los filtros indicados."
                    )

                reporte_talleres = []

                for taller in talleres:
                    query_sesiones = session.query(Sesion).filter(
                        Sesion.taller_id == taller.id
                    )
                    if fecha_inicio:
                        query_sesiones = query_sesiones.filter(Sesion.fecha >= fecha_inicio)
                    if fecha_fin:
                        query_sesiones = query_sesiones.filter(Sesion.fecha <= fecha_fin)

                    sesiones = query_sesiones.order_by(Sesion.numero_sesion).all()

                    total_inscritos = session.query(func.count(Inscripcion.id)).filter(
                        Inscripcion.taller_id == taller.id,
                        Inscripcion.estado == "Activo"
                    ).scalar() or 0

                    tendencia = []
                    for s in sesiones:
                        validos = session.query(func.count(Asistencia.id)).filter(
                            Asistencia.sesion_id == s.id,
                            Asistencia.estado.in_(["P", "J"])
                        ).scalar() or 0
                        registrados = session.query(func.count(Asistencia.id)).filter(
                            Asistencia.sesion_id == s.id
                        ).scalar() or 0
                        pct = (validos / registrados * 100) if registrados > 0 else 0.0

                        tendencia.append({
                            "sesion_numero": s.numero_sesion,
                            "fecha": s.fecha.strftime("%d/%m/%Y") if s.fecha else "N/A",
                            "porcentaje_asistencia": round(pct, 2)
                        })

                    promedio_taller = (
                        sum(p["porcentaje_asistencia"] for p in tendencia) / len(tendencia)
                        if tendencia else 0.0
                    )

                    reporte_talleres.append({
                        "taller_id": taller.id,
                        "taller_codigo": taller.codigo,
                        "taller_nombre": taller.nombre,
                        "docente": taller.docente.nombre_completo if taller.docente else "N/A",
                        "total_inscritos": total_inscritos,
                        "total_sesiones": len(sesiones),
                        "promedio_asistencia": round(promedio_taller, 2),
                        "tendencia": tendencia,
                    })

                return ResultadoReporte(
                    ok=True,
                    mensaje=f"Reporte generado para {len(reporte_talleres)} taller(es).",
                    datos={
                        "periodo": {
                            "desde": fecha_inicio.strftime("%d/%m/%Y") if fecha_inicio else "Sin límite",
                            "hasta": fecha_fin.strftime("%d/%m/%Y") if fecha_fin else "Sin límite",
                        },
                        "fecha_generacion": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    },
                    lista=reporte_talleres
                )

        except Exception as e:
            return ResultadoReporte(ok=False, mensaje=f"Error al generar reporte de asistencia: {e}")

    # ══════════════════════════════════════════════════════════════════════════
    # RF-37 · REPORTE DE INSCRITOS (por taller, categoría y ciclo)
    # ══════════════════════════════════════════════════════════════════════════

    @staticmethod
    def obtener_reporte_inscritos(ciclo_id: int = None, categoria: str = None) -> ResultadoReporte:
        """
        RF-37: Total de estudiantes inscritos por taller, con resumen
        agrupado por categoría y por ciclo académico.
        """
        try:
            with get_session() as session:
                query = session.query(Taller).filter(Taller.estado == "Activo")
                if ciclo_id:
                    query = query.filter(Taller.ciclo_academico_id == ciclo_id)
                if categoria:
                    query = query.filter(Taller.categoria == categoria)

                talleres = query.order_by(Taller.nombre).all()

                detalle = []
                resumen_categoria: Dict[str, int] = {}
                resumen_ciclo: Dict[str, int] = {}

                for t in talleres:
                    total = session.query(func.count(Inscripcion.id)).filter(
                        Inscripcion.taller_id == t.id,
                        Inscripcion.estado == "Activo"
                    ).scalar() or 0

                    cat = t.categoria or "Sin categoría"
                    ciclo_nombre = t.ciclo_academico.nombre if t.ciclo_academico else "N/A"

                    detalle.append({
                        "taller_id": t.id,
                        "taller_codigo": t.codigo,
                        "taller_nombre": t.nombre,
                        "categoria": cat,
                        "ciclo": ciclo_nombre,
                        "cupo_maximo": t.cupo_maximo,
                        "total_inscritos": total,
                    })

                    resumen_categoria[cat] = resumen_categoria.get(cat, 0) + total
                    resumen_ciclo[ciclo_nombre] = resumen_ciclo.get(ciclo_nombre, 0) + total

                return ResultadoReporte(
                    ok=True,
                    mensaje=f"{len(detalle)} taller(es) incluidos en el reporte.",
                    datos={
                        "por_categoria": [
                            {"categoria": k, "total_inscritos": v}
                            for k, v in resumen_categoria.items()
                        ],
                        "por_ciclo": [
                            {"ciclo": k, "total_inscritos": v}
                            for k, v in resumen_ciclo.items()
                        ],
                        "total_general": sum(d["total_inscritos"] for d in detalle),
                        "fecha_generacion": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    },
                    lista=detalle
                )

        except Exception as e:
            return ResultadoReporte(ok=False, mensaje=f"Error al generar reporte de inscritos: {e}")

    # ══════════════════════════════════════════════════════════════════════════
    # RF-38 · REPORTE DE APTOS PARA CERTIFICADO
    # ══════════════════════════════════════════════════════════════════════════

    @staticmethod
    def obtener_reporte_aptos_certificado(taller_id: int = None, ciclo_id: int = None) -> ResultadoReporte:
        """
        RF-38: Listado de estudiantes aptos (porcentaje de asistencia >=
        umbral del taller), con nombre, código, taller y porcentaje.
        """
        try:
            with get_session() as session:
                query = session.query(Inscripcion).join(Taller).filter(
                    Inscripcion.estado == "Activo",
                    Taller.estado == "Activo"
                )
                if taller_id:
                    query = query.filter(Inscripcion.taller_id == taller_id)
                if ciclo_id:
                    query = query.filter(Taller.ciclo_academico_id == ciclo_id)

                inscripciones = query.all()
                aptos = []

                for insc in inscripciones:
                    taller = insc.taller
                    total_sesiones = session.query(func.count(Sesion.id)).filter(
                        Sesion.taller_id == taller.id
                    ).scalar() or 0

                    if total_sesiones == 0:
                        continue

                    cuentan = session.query(func.count(Asistencia.id)).filter(
                        Asistencia.inscripcion_id == insc.id,
                        Asistencia.estado.in_(["P", "J"])
                    ).scalar() or 0

                    pct = (cuentan / total_sesiones) * 100

                    if pct >= taller.umbral_asistencia:
                        aptos.append({
                            "estudiante_id": insc.estudiante_id,
                            "codigo": insc.estudiante.codigo_estudiantil,
                            "nombre": insc.estudiante.nombre_completo,
                            "taller_codigo": taller.codigo,
                            "taller_nombre": taller.nombre,
                            "porcentaje_asistencia": round(pct, 2),
                            "umbral_requerido": taller.umbral_asistencia,
                        })

                aptos.sort(key=lambda a: a["nombre"])

                return ResultadoReporte(
                    ok=True,
                    mensaje=f"{len(aptos)} estudiante(s) aptos para certificado.",
                    datos={
                        "total_aptos": len(aptos),
                        "fecha_generacion": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    },
                    lista=aptos
                )

        except Exception as e:
            return ResultadoReporte(ok=False, mensaje=f"Error al generar reporte de aptos: {e}")

    # ══════════════════════════════════════════════════════════════════════════
    # RF-39 · REPORTE DE BIENES PATRIMONIALES
    # ══════════════════════════════════════════════════════════════════════════

    @staticmethod
    def obtener_reporte_bienes() -> ResultadoReporte:
        """
        RF-39: Reporte de inventario completo de bienes patrimoniales,
        con el estado actual de cada bien (Disponible/Asignado/
        Mantenimiento/DeBaja).

        No se duplica la lógica de estado/alertas aquí: se reutiliza
        BienesService.listar(), que ya es la fuente de verdad para
        el módulo de bienes (ver ui/panel_bienes.py).
        """
        try:
            from services.bienes_service import BienesService

            resultado = BienesService.listar(None)
            if not resultado.ok:
                return ResultadoReporte(ok=False, mensaje=resultado.mensaje)

            bienes = resultado.lista or []
            resumen_estado: Dict[str, int] = {}
            for b in bienes:
                estado = b.get("estado", "Desconocido")
                resumen_estado[estado] = resumen_estado.get(estado, 0) + 1

            detalle = [
                {
                    "codigo": b.get("codigo_patrimonial"),
                    "descripcion": b.get("descripcion"),
                    "categoria": b.get("categoria"),
                    "estado": b.get("estado"),
                    "asignado_a": b.get("asignado_a") or "—",
                    "valor_adquisicion": b.get("valor_adquisicion"),
                }
                for b in bienes
            ]

            return ResultadoReporte(
                ok=True,
                mensaje=f"{len(detalle)} bien(es) en el inventario.",
                datos={
                    "resumen_por_estado": [
                        {"estado": k, "cantidad": v} for k, v in resumen_estado.items()
                    ],
                    "total_bienes": len(detalle),
                    "fecha_generacion": datetime.now().strftime("%d/%m/%Y %H:%M"),
                },
                lista=detalle
            )

        except Exception as e:
            return ResultadoReporte(ok=False, mensaje=f"Error al generar reporte de bienes: {e}")

    # ══════════════════════════════════════════════════════════════════════════
    # RF-41 · REPORTE CONSOLIDADO POR PERÍODO
    # ══════════════════════════════════════════════════════════════════════════

    @staticmethod
    def obtener_reporte_consolidado(fecha_inicio: date = None, fecha_fin: date = None) -> ResultadoReporte:
        """
        RF-41: KPIs consolidados de un período: total de talleres
        activos, estudiantes inscritos, % de asistencia global y
        número de aptos.
        """
        try:
            with get_session() as session:
                total_talleres_activos = session.query(func.count(Taller.id)).filter(
                    Taller.estado == "Activo"
                ).scalar() or 0

                total_inscritos = session.query(func.count(Inscripcion.id)).join(Taller).filter(
                    Inscripcion.estado == "Activo",
                    Taller.estado == "Activo"
                ).scalar() or 0

                query_asist = session.query(Asistencia).join(Sesion)
                if fecha_inicio:
                    query_asist = query_asist.filter(Sesion.fecha >= fecha_inicio)
                if fecha_fin:
                    query_asist = query_asist.filter(Sesion.fecha <= fecha_fin)

                total_registros = query_asist.count()
                registros_validos = query_asist.filter(Asistencia.estado.in_(["P", "J"])).count()
                asistencia_global = (
                    (registros_validos / total_registros * 100) if total_registros > 0 else 0.0
                )

                # Número de aptos: reutiliza RF-38 (sin duplicar la lógica de cálculo).
                aptos_resultado = ReporteService.obtener_reporte_aptos_certificado()
                numero_aptos = aptos_resultado.datos.get("total_aptos", 0) if aptos_resultado.ok else 0

                datos = {
                    "total_talleres_activos": total_talleres_activos,
                    "total_estudiantes_inscritos": total_inscritos,
                    "porcentaje_asistencia_global": round(asistencia_global, 2),
                    "numero_aptos": numero_aptos,
                    "periodo": {
                        "desde": fecha_inicio.strftime("%d/%m/%Y") if fecha_inicio else "Sin límite",
                        "hasta": fecha_fin.strftime("%d/%m/%Y") if fecha_fin else "Sin límite",
                    },
                    "fecha_generacion": datetime.now().strftime("%d/%m/%Y %H:%M"),
                }

                return ResultadoReporte(
                    ok=True,
                    mensaje="Reporte consolidado generado correctamente.",
                    datos=datos
                )

        except Exception as e:
            return ResultadoReporte(ok=False, mensaje=f"Error al generar reporte consolidado: {e}")