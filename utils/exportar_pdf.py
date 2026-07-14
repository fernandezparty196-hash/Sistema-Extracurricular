"""
utils/exportar_pdf.py   ──   Exportación a PDF
═════════════════════════════════════════════════

Utilidades para exportar datos a archivos PDF.
Requiere: pip install reportlab

USO:
    from utils.exportar_pdf import ExportarPDF
    
    ExportarPDF.lista_aptos(
        datos=resultado.datos,
        estudiantes=resultado.lista,
        ruta="/ruta/al/archivo.pdf"
    )
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, List

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.platypus import PageBreak
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


class ExportarPDF:
    """Exportación a PDF para varios módulos."""

    @staticmethod
    def lista_aptos(datos: Dict, estudiantes: Dict[str, List],
                    ruta: str = None) -> bool:
        """
        Exporta lista de aptos a PDF con formato profesional.
        
        PARÁMETROS:
            datos: dict con información del taller
            estudiantes: dict con "aptos" y "desaptos"
            ruta: ruta de descarga (si None, usa Desktop)
        
        RETORNA:
            bool: True si éxito
        """
        if not REPORTLAB_AVAILABLE:
            print("❌ reportlab no está instalado. Usa: pip install reportlab")
            return False

        try:
            # ── Determinar ruta de guardado ──────────────────────────
            if not ruta:
                home = Path.home()
                desktop = home / "Desktop"
                if not desktop.exists():
                    desktop = home / "Documents"
                if not desktop.exists():
                    desktop = home
                
                fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
                nombre_taller = datos.get('taller_nombre', 'taller').replace(' ', '_')
                ruta = desktop / f"Lista_Aptos_{nombre_taller}_{fecha}.pdf"
            else:
                ruta = Path(ruta)

            ruta.parent.mkdir(parents=True, exist_ok=True)

            # ── Crear documento ─────────────────────────────────────
            doc = SimpleDocTemplate(str(ruta), pagesize=letter,
                                   topMargin=0.5*inch,
                                   bottomMargin=0.5*inch,
                                   leftMargin=0.5*inch,
                                   rightMargin=0.5*inch)

            # ── Estilos ──────────────────────────────────────────────
            styles = getSampleStyleSheet()
            
            titulo_style = ParagraphStyle(
                'Titulo',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#534AB7'),
                spaceAfter=12,
                alignment=1  # Center
            )

            subtitulo_style = ParagraphStyle(
                'Subtitulo',
                parent=styles['Normal'],
                fontSize=11,
                textColor=colors.HexColor('#000000'),
                spaceAfter=6
            )

            # ── Contenido del documento ──────────────────────────────
            contenido = []

            # Título
            contenido.append(Paragraph("LISTA DE APTOS", titulo_style))
            contenido.append(Spacer(1, 12))

            # Información del taller
            info_lines = [
                f"<b>Taller:</b> {datos.get('taller_nombre', 'N/A')}",
                f"<b>Código:</b> {datos.get('taller_codigo', 'N/A')}",
                f"<b>Docente:</b> {datos.get('docente', 'N/A')}",
                f"<b>Ciclo:</b> {datos.get('ciclo', 'N/A')}",
                f"<b>Umbral de Asistencia:</b> {datos.get('umbral', 0)}%",
                f"<b>Fecha de Generación:</b> {datos.get('fecha_generacion', datetime.now().strftime('%d/%m/%Y'))}",
            ]

            for line in info_lines:
                contenido.append(Paragraph(line, subtitulo_style))

            contenido.append(Spacer(1, 12))

            # ── Tabla de APTOS ───────────────────────────────────────
            aptos = estudiantes.get('aptos', [])
            
            if aptos:
                contenido.append(Paragraph("✅ ESTUDIANTES APTOS", titulo_style))
                
                tabla_data = [["Nombre", "DNI", "Código", "Carrera", "Asistencia", "Estado"]]
                
                for est in aptos:
                    tabla_data.append([
                        est.get('nombre_completo', ''),
                        est.get('dni', 'N/A'),
                        est.get('codigo_estudiantil', 'N/A'),
                        est.get('carrera', 'N/A'),
                        f"{est.get('asistencia_porcentaje', 0):.1f}%",
                        "APTO"
                    ])

                tabla_aptos = Table(tabla_data, colWidths=[2.5*inch, 0.9*inch, 1*inch, 1.5*inch, 0.8*inch, 0.7*inch])
                tabla_aptos.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#534AB7')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#E8F8F2')),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('FONTSIZE', (0, 1), (-1, -1), 9),
                    ('ROWHEIGHT', (0, 0), (-1, -1), 20),
                ]))
                
                contenido.append(tabla_aptos)
                contenido.append(Spacer(1, 12))

            # ── Tabla de DESAPTOS ────────────────────────────────────
            desaptos = estudiantes.get('desaptos', [])
            
            if desaptos:
                contenido.append(PageBreak())  # Nueva página si es necesario
                contenido.append(Paragraph("❌ ESTUDIANTES DESAPTOS", titulo_style))
                
                tabla_data = [["Nombre", "DNI", "Código", "Carrera", "Asistencia", "Estado"]]
                
                for est in desaptos:
                    tabla_data.append([
                        est.get('nombre_completo', ''),
                        est.get('dni', 'N/A'),
                        est.get('codigo_estudiantil', 'N/A'),
                        est.get('carrera', 'N/A'),
                        f"{est.get('asistencia_porcentaje', 0):.1f}%",
                        "DESAPTO"
                    ])

                tabla_desaptos = Table(tabla_data, colWidths=[1.8*inch, 0.9*inch, 1*inch, 1.5*inch, 0.8*inch, 0.7*inch])
                tabla_desaptos.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#534AB7')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#FDF0EE')),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('FONTSIZE', (0, 1), (-1, -1), 9),
                    ('ROWHEIGHT', (0, 0), (-1, -1), 20),
                ]))
                
                contenido.append(tabla_desaptos)
                contenido.append(Spacer(1, 12))

            # ── Resumen ──────────────────────────────────────────────
            contenido.append(Spacer(1, 12))
            contenido.append(Paragraph("RESUMEN", styles['Heading2']))
            
            resumen_lines = [
                f"<b>Estudiantes Aptos:</b> {len(aptos)}",
                f"<b>Estudiantes Desaptos:</b> {len(desaptos)}",
                f"<b>Total de Inscritos:</b> {len(aptos) + len(desaptos)}",
            ]

            for line in resumen_lines:
                contenido.append(Paragraph(line, subtitulo_style))

            # ── Generar PDF ──────────────────────────────────────────
            doc.build(contenido)

            print(f"✅ PDF guardado: {ruta}")
            return True

        except Exception as e:
            print(f"❌ Error al exportar a PDF: {e}")
            return False