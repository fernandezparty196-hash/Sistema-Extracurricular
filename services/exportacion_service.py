"""
services/exportacion_service.py   ──   RF-40 Exportar reportes
════════════════════════════════════════════════════════════════

¿QUÉ HACE?
  Exporta cualquier reporte (una lista de dicts + definición de
  columnas) a Excel, PDF o CSV, con el formato oficial de la UNAB:
  encabezado con el nombre de la institución, título del reporte,
  usuario que lo generó y fecha.

¿POR QUÉ UN SERVICIO SEPARADO DE ReporteService?
  ReporteService arma los DATOS (RF-36 a RF-39, RF-41). Este servicio
  solo sabe convertir "columnas + filas" en un archivo — no le importa
  si esos datos vienen de aptos, bienes, inscritos, etc. Así cualquier
  reporte nuevo se exporta gratis, sin tocar este archivo.

USO TÍPICO (desde la UI, tras generar un reporte):
    columnas = [
        ("codigo", "Código"),
        ("nombre", "Nombre"),
        ("taller_nombre", "Taller"),
        ("porcentaje_asistencia", "% Asistencia"),
    ]
    resultado = ExportacionService.exportar_excel(
        titulo="Reporte de aptos para certificado",
        columnas=columnas,
        filas=reporte.lista,
        usuario_nombre=sesion.nombre_completo,
        ruta_destino="/mnt/user-data/outputs/aptos_certificado.xlsx",
    )
    if resultado.ok:
        abrir_archivo(resultado.ruta)
    else:
        QMessageBox.warning(self, "No se pudo exportar", resultado.mensaje)

DEPENDENCIAS OPCIONALES:
  • exportar_excel() requiere `openpyxl`      (pip install openpyxl)
  • exportar_pdf()   requiere `reportlab`      (pip install reportlab)
  • exportar_csv()   no requiere nada (usa el módulo csv de la stdlib)
  Si falta la librería, el método retorna ok=False con un mensaje
  claro en vez de lanzar una excepción no controlada.
"""

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple


NOMBRE_INSTITUCION = "UNAB — Sistema de Talleres Extracurriculares"

# Definición de columna: (clave_en_el_dict, etiqueta_visible)
Columna = Tuple[str, str]


@dataclass
class ResultadoExportacion:
    """Estructura de respuesta estándar de este servicio."""
    ok:      bool
    mensaje: str
    ruta:    Optional[str] = None


class ExportacionService:
    """RF-40: Exportar cualquier reporte a Excel, PDF o CSV."""

    # ══════════════════════════════════════════════════════════════
    # CSV
    # ══════════════════════════════════════════════════════════════
    @staticmethod
    def exportar_csv(
        titulo: str,
        columnas: List[Columna],
        filas: List[Dict[str, Any]],
        usuario_nombre: str,
        ruta_destino: str,
    ) -> ResultadoExportacion:
        try:
            ruta = Path(ruta_destino)
            ruta.parent.mkdir(parents=True, exist_ok=True)

            # utf-8-sig para que Excel reconozca tildes/ñ al abrir el CSV.
            with open(ruta, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow([NOMBRE_INSTITUCION])
                writer.writerow([titulo])
                writer.writerow([
                    f"Generado por: {usuario_nombre}",
                    f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
                ])
                writer.writerow([])
                writer.writerow([etiqueta for _, etiqueta in columnas])
                for fila in filas:
                    writer.writerow([fila.get(clave, "") for clave, _ in columnas])

            return ResultadoExportacion(
                ok=True,
                mensaje=f"Reporte exportado correctamente a {ruta.name}.",
                ruta=str(ruta),
            )
        except Exception as e:
            return ResultadoExportacion(ok=False, mensaje=f"Error al exportar CSV: {e}")

    # ══════════════════════════════════════════════════════════════
    # EXCEL
    # ══════════════════════════════════════════════════════════════
    @staticmethod
    def exportar_excel(
        titulo: str,
        columnas: List[Columna],
        filas: List[Dict[str, Any]],
        usuario_nombre: str,
        ruta_destino: str,
    ) -> ResultadoExportacion:
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font, Alignment, PatternFill
            from openpyxl.utils import get_column_letter
        except ImportError:
            return ResultadoExportacion(
                ok=False,
                mensaje="Falta instalar 'openpyxl' para exportar a Excel "
                        "(pip install openpyxl).",
            )

        try:
            ruta = Path(ruta_destino)
            ruta.parent.mkdir(parents=True, exist_ok=True)

            wb = Workbook()
            ws = wb.active
            ws.title = "Reporte"
            total_columnas = len(columnas)

            ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=total_columnas)
            ws.cell(row=1, column=1, value=NOMBRE_INSTITUCION).font = Font(bold=True, size=13)

            ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=total_columnas)
            ws.cell(row=2, column=1, value=titulo).font = Font(bold=True, size=11)

            ws.cell(row=3, column=1, value=f"Generado por: {usuario_nombre}")
            ws.cell(row=3, column=3, value=f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

            fila_encabezado = 5
            for col, (_, etiqueta) in enumerate(columnas, start=1):
                celda = ws.cell(row=fila_encabezado, column=col, value=etiqueta)
                celda.font = Font(bold=True, color="FFFFFF")
                celda.fill = PatternFill("solid", fgColor="4F46E5")
                celda.alignment = Alignment(horizontal="center")

            for i, fila_datos in enumerate(filas, start=fila_encabezado + 1):
                for col, (clave, _) in enumerate(columnas, start=1):
                    ws.cell(row=i, column=col, value=fila_datos.get(clave, ""))

            for col in range(1, total_columnas + 1):
                ws.column_dimensions[get_column_letter(col)].width = 22

            wb.save(ruta)

            return ResultadoExportacion(
                ok=True,
                mensaje=f"Reporte exportado correctamente a {ruta.name}.",
                ruta=str(ruta),
            )
        except Exception as e:
            return ResultadoExportacion(ok=False, mensaje=f"Error al exportar Excel: {e}")

    # ══════════════════════════════════════════════════════════════
    # PDF
    # ══════════════════════════════════════════════════════════════
    @staticmethod
    def exportar_pdf(
        titulo: str,
        columnas: List[Columna],
        filas: List[Dict[str, Any]],
        usuario_nombre: str,
        ruta_destino: str,
    ) -> ResultadoExportacion:
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib.units import cm
            from reportlab.platypus import (
                SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            )
        except ImportError:
            return ResultadoExportacion(
                ok=False,
                mensaje="Falta instalar 'reportlab' para exportar a PDF "
                        "(pip install reportlab).",
            )

        try:
            ruta = Path(ruta_destino)
            ruta.parent.mkdir(parents=True, exist_ok=True)

            doc = SimpleDocTemplate(
                str(ruta),
                pagesize=landscape(A4),
                topMargin=1.5 * cm,
                bottomMargin=1.5 * cm,
                leftMargin=1.2 * cm,
                rightMargin=1.2 * cm,
            )
            estilos = getSampleStyleSheet()

            elementos = [
                Paragraph(NOMBRE_INSTITUCION, estilos["Title"]),
                Paragraph(titulo, estilos["Heading2"]),
                Paragraph(
                    f"Generado por: {usuario_nombre}  |  "
                    f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
                    estilos["Normal"],
                ),
                Spacer(1, 12),
            ]

            encabezados = [etiqueta for _, etiqueta in columnas]
            datos_tabla = [encabezados]
            for fila_datos in filas:
                datos_tabla.append([str(fila_datos.get(clave, "")) for clave, _ in columnas])

            tabla = Table(datos_tabla, repeatRows=1)
            tabla.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4F46E5")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]))
            elementos.append(tabla)

            doc.build(elementos)

            return ResultadoExportacion(
                ok=True,
                mensaje=f"Reporte exportado correctamente a {ruta.name}.",
                ruta=str(ruta),
            )
        except Exception as e:
            return ResultadoExportacion(ok=False, mensaje=f"Error al exportar PDF: {e}")