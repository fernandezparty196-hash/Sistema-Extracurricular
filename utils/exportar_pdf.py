from datetime import datetime
from pathlib import Path
from typing import Dict, List
from services.configuracion_service import ConfiguracionService
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,  PageBreak, Image
    from reportlab.platypus import PageBreak
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


class ExportarPDF:
    """Exportación a PDF para varios módulos."""

    @staticmethod
    def lista_aptos(datos: Dict, estudiantes: Dict[str, List],
                    ruta: str = None) -> bool:

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
                        
            titulo_principal = ParagraphStyle(
                "TituloPrincipal",
                parent=styles["Heading1"],
                alignment=TA_CENTER,
                fontSize=20,
                textColor=colors.HexColor("#1E3A8A"),
                spaceAfter=4,
            )

            subtitulo = ParagraphStyle(
                "Subtitulo",
                parent=styles["Normal"],
                alignment=TA_CENTER,
                fontSize=11,
                textColor=colors.HexColor("#374151"),
            )

            titulo_seccion = ParagraphStyle(
                "TituloSeccion",
                parent=styles["Heading2"],
                fontSize=14,
                textColor=colors.white,
                backColor=colors.HexColor("#1E3A8A"),
                alignment=TA_CENTER,
                spaceBefore=10,
                spaceAfter=10,
            )

            texto = ParagraphStyle(
                "Texto",
                parent=styles["Normal"],
                fontSize=10,
                leading=18
            )

            # ── Contenido del documento ─────────────────────────────

            contenido = []

            try:
                resultado = ConfiguracionService.obtener()
                if resultado.ok:
                    config = resultado.datos

                    ruta_logo = ConfiguracionService.obtener_ruta_logo_absoluta(config.get("logo_ruta"))
                    if Path(ruta_logo).exists():
                        logo = Image(ruta_logo)
                        logo.drawWidth = 70
                        logo.drawHeight = 70

                    else:
                        logo = Paragraph("", texto)

            except:
                logo = Paragraph("", texto)

            contenido.append(Paragraph("UNIVERSIDAD NACIONAL DE BARRANCA",
                    ParagraphStyle(
                        "Universidad",
                        parent=styles["Heading2"],
                        alignment=1,
                        textColor=colors.HexColor("#534AB7"),
                        fontSize=16,
                        spaceAfter=4
                    )
                )
            )

            # Título
            contenido.append(Paragraph("LISTA DE APTOS", titulo_principal))
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
                contenido.append(Paragraph(line, subtitulo))

            contenido.append(Spacer(1, 12))

            # ── Tabla de APTOS ───────────────────────────────────────
            aptos = estudiantes.get('aptos', [])
            
            if aptos:
                contenido.append(Paragraph("ESTUDIANTES APTOS", titulo_seccion))
                
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
                contenido.append(Paragraph("ESTUDIANTES NO APTOS", titulo_seccion))
                
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
                f"<b>Estudiantes No aptos:</b> {len(desaptos)}",
                f"<b>Total de Inscritos:</b> {len(aptos) + len(desaptos)}",
            ]

            for line in resumen_lines:
                contenido.append(Paragraph(line, subtitulo))

            # ── Generar PDF ──────────────────────────────────────────
            doc.build(contenido)

            print(f"✅ PDF guardado: {ruta}")
            return True

        except Exception as e:
            print(f"❌ Error al exportar a PDF: {e}")
            return False