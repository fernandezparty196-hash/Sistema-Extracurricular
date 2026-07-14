"""
services/lista_aptos_service.py   ──   EP-05 Lista de Aptos 
═════════════════════════════════════════════════════════════════
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import and_, func
from sqlalchemy.exc import SQLAlchemyError

from database.connection import get_session
from models.taller import Taller
from models.estudiante import Estudiante
from models.inscripcion import Inscripcion
from models.asistencia import Asistencia
from models.sesion import Sesion
from models.auditoria import Auditoria


@dataclass
class ResultadoListaAptos:
    """Estructura de respuesta estándar."""
    ok: bool
    mensaje: str
    datos: Optional[Any] = None
    lista: Optional[List[Dict]] = None


class ListaAptosService:
    """Servicio de gestión de lista de aptos."""

    @staticmethod
    def generar_lista(taller_id: int, usuario_id: int) -> ResultadoListaAptos:
        """
        ✅ Genera la lista de aptos para un taller basada en asistencia.

        CRITERIOS DE APTITUD:
          - Asistencia >= Umbral del taller
        """
        try:
            with get_session() as session:
                # ── Verificar taller existe ──────────────────────────────
                taller = session.query(Taller).filter_by(id=taller_id).first()
                if not taller:
                    return ResultadoListaAptos(
                        ok=False,
                        mensaje="Taller no encontrado"
                    )

                umbral = taller.umbral_asistencia
                
                # ── Obtener inscripciones activas ────────────────────────
                inscripciones = session.query(Inscripcion).filter(
                    and_(
                        Inscripcion.taller_id == taller_id,
                        Inscripcion.estado == "Activo"
                    )
                ).all()

                if not inscripciones:
                    return ResultadoListaAptos(
                        ok=False,
                        mensaje="No hay estudiantes inscritos en este taller"
                    )

                # ── Contar total de sesiones del taller ──────────────────
                total_sesiones = session.query(func.count(Sesion.id)).filter(
                    Sesion.taller_id == taller_id
                ).scalar() or 0

                if total_sesiones == 0:
                    return ResultadoListaAptos(
                        ok=False,
                        mensaje="El taller no tiene sesiones registradas"
                    )

                # ── Procesar cada inscripción ───────────────────────────
                aptos = []
                desaptos = []

                for inscripcion in inscripciones:
                    estudiante = inscripcion.estudiante
                    
                    # Contar asistencias (P + J cuentan como presentes)
                    asistencias_validas = session.query(func.count(Asistencia.id)).filter(
                        and_(
                            Asistencia.inscripcion_id == inscripcion.id,
                            Asistencia.estado.in_(["P", "J"])
                        )
                    ).scalar() or 0

                    # Calcular porcentaje
                    porcentaje = (asistencias_validas / total_sesiones * 100) \
                                if total_sesiones > 0 else 0.0

                    # Determinar aptitud
                    es_apto = porcentaje >= umbral

                    dato = {
                        "inscripcion_id": inscripcion.id,
                        "estudiante_id": estudiante.id,
                        "nombre_completo": estudiante.nombre_completo,
                        "dni": estudiante.dni,
                        "codigo_estudiantil": estudiante.codigo_estudiantil,
                        "carrera": estudiante.carrera.nombre if estudiante.carrera else "N/A",
                        "asistencia_porcentaje": round(porcentaje, 2),
                        "apto": es_apto,
                        "asistencias_registradas": asistencias_validas,
                        "total_sesiones": total_sesiones,
                    }

                    if es_apto:
                        aptos.append(dato)
                    else:
                        desaptos.append(dato)

                # ── Registrar auditoría (usando INSERT en lugar de GENERATE) ──
                session.add(Auditoria(
                    usuario_id       = usuario_id,
                    tabla_afectada   = "lista_aptos",
                    accion           = "INSERT",  # ✅ Válido en ENUM
                    registro_id      = taller_id,
                    datos_nuevos     = {
                        "taller_id": taller_id,
                        "umbral": umbral,
                        "aptos_count": len(aptos),
                        "desaptos_count": len(desaptos),
                    },
                ))
                
                # ✅ COMMIT DENTRO DEL WITH
                session.commit()

                return ResultadoListaAptos(
                    ok=True,
                    mensaje=f"Lista generada: {len(aptos)} aptos, {len(desaptos)} desaptos",
                    datos={
                        "taller_id": taller_id,
                        "taller_nombre": taller.nombre,
                        "umbral": umbral,
                        "total_inscritos": len(inscripciones),
                        "aptos_count": len(aptos),
                        "desaptos_count": len(desaptos),
                        "fecha_generacion": datetime.now().isoformat(),
                    },
                    lista={
                        "aptos": aptos,
                        "desaptos": desaptos,
                    }
                )

        except SQLAlchemyError as e:
            return ResultadoListaAptos(
                ok=False,
                mensaje=f"Error de BD: {str(e)}"
            )
        except Exception as e:
            return ResultadoListaAptos(
                ok=False,
                mensaje=f"Error inesperado: {str(e)}"
            )

    @staticmethod
    def obtener_resumen_taller(taller_id: int) -> ResultadoListaAptos:
        """
        Obtiene un resumen rápido de aptitud para un taller.
        """
        try:
            with get_session() as session:
                taller = session.query(Taller).filter_by(id=taller_id).first()
                if not taller:
                    return ResultadoListaAptos(
                        ok=False,
                        mensaje="Taller no encontrado"
                    )

                inscripciones = session.query(Inscripcion).filter(
                    and_(
                        Inscripcion.taller_id == taller_id,
                        Inscripcion.estado == "Activo"
                    )
                ).count()

                total_sesiones = session.query(func.count(Sesion.id)).filter(
                    Sesion.taller_id == taller_id
                ).scalar() or 0

                if total_sesiones == 0:
                    aptos_count = 0
                else:
                    aptos_count = 0
                    for insc in session.query(Inscripcion).filter(
                        and_(
                            Inscripcion.taller_id == taller_id,
                            Inscripcion.estado == "Activo"
                        )
                    ).all():
                        asistencias = session.query(func.count(Asistencia.id)).filter(
                            and_(
                                Asistencia.inscripcion_id == insc.id,
                                Asistencia.estado.in_(["P", "J"])
                            )
                        ).scalar() or 0
                        
                        pct = (asistencias / total_sesiones * 100) if total_sesiones > 0 else 0
                        if pct >= taller.umbral_asistencia:
                            aptos_count += 1

                return ResultadoListaAptos(
                    ok=True,
                    mensaje="Resumen obtenido",
                    datos={
                        "taller_id": taller_id,
                        "taller_nombre": taller.nombre,
                        "umbral": taller.umbral_asistencia,
                        "total_inscritos": inscripciones,
                        "aptos_count": aptos_count,
                        "desaptos_count": inscripciones - aptos_count,
                        "porcentaje_aptos": round(
                            (aptos_count / inscripciones * 100) if inscripciones > 0 else 0,
                            2
                        ),
                    }
                )

        except Exception as e:
            return ResultadoListaAptos(
                ok=False,
                mensaje=f"Error: {str(e)}"
            )

    @staticmethod
    def exportar_lista(taller_id: int) -> ResultadoListaAptos:
        """
        Exporta lista de aptos para descarga en Excel/PDF.
        
        Retorna datos formateados para exportación.
        """
        try:
            with get_session() as session:
                taller = session.query(Taller).filter_by(id=taller_id).first()
                if not taller:
                    return ResultadoListaAptos(
                        ok=False,
                        mensaje="Taller no encontrado"
                    )

                inscripciones = session.query(Inscripcion).filter(
                    and_(
                        Inscripcion.taller_id == taller_id,
                        Inscripcion.estado == "Activo"
                    )
                ).all()

                total_sesiones = session.query(func.count(Sesion.id)).filter(
                    Sesion.taller_id == taller_id
                ).scalar() or 0

                export_data = []
                
                for insc in inscripciones:
                    estudiante = insc.estudiante
                    
                    asistencias = session.query(func.count(Asistencia.id)).filter(
                        and_(
                            Asistencia.inscripcion_id == insc.id,
                            Asistencia.estado.in_(["P", "J"])
                        )
                    ).scalar() or 0

                    pct = (asistencias / total_sesiones * 100) if total_sesiones > 0 else 0
                    es_apto = pct >= taller.umbral_asistencia

                    export_data.append({
                        "nombre_completo": estudiante.nombre_completo,
                        "dni": estudiante.dni,
                        "codigo": estudiante.codigo_estudiantil,
                        "carrera": estudiante.carrera.nombre if estudiante.carrera else "N/A",
                        "asistencia": f"{pct:.1f}%",
                        "umbral": f"{taller.umbral_asistencia}%",
                        "estado": "APTO" if es_apto else "DESAPTO",
                    })

                return ResultadoListaAptos(
                    ok=True,
                    mensaje="Lista exportada",
                    datos={
                        "taller_nombre": taller.nombre,
                        "taller_codigo": taller.codigo,
                        "ciclo":         taller.ciclo_academico.nombre,
                        "docente":       taller.docente.nombre_completo,
                        "fecha_generacion": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "umbral": taller.umbral_asistencia,
                    },
                    lista=export_data
                )

        except Exception as e:
            return ResultadoListaAptos(
                ok=False,
                mensaje=f"Error: {str(e)}"
            )

    @staticmethod
    def listar_talleres_activos() -> List[Dict]:
        """Lista talleres activos para seleccionar y generar lista."""
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
                        "docente": t.docente.nombre_completo if t.docente else "N/A",
                        "ciclo": t.ciclo_academico.nombre if t.ciclo_academico else "N/A",
                        "umbral": t.umbral_asistencia,
                        "inscritos": t.total_inscritos,
                    }
                    for t in talleres
                ]
        except Exception:
            return []