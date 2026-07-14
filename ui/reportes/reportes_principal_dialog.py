"""
ui/reportes/reportes_principal_dialog.py   ──   Panel Principal de Reportes
═════════════════════════════════════════════════════════════════════════════

Diálogo inicial que permite elegir:
  1. Reporte de Estudiante (con filtros)
  2. Reporte de Taller (con selección de sesiones)
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFrame, QMessageBox, QWidget
)

from services.reporte_service import ReporteService


class ReportesPrincipalDialog(QWidget):
    """Diálogo principal para seleccionar tipo de reporte."""
    
    def __init__(self, sesion_usuario, parent=None):
        super().__init__(parent)
        self.sesion = sesion_usuario
        self.reporte_service = ReporteService()
        
        self.setWindowTitle("Lista estudiantes")
        self.setWindowFlags(
            self.windowFlags() &
            ~Qt.WindowType.WindowContextHelpButtonHint
        )
        self._configurar_ventana()
        self._construir_ui()
    
    def _configurar_ventana(self) -> None:
        self.setStyleSheet("""
            QLabel#titulo {
                font-size: 20px;
                font-weight: bold;
            }
            QLabel#subtitulo {
                font-size: 14px;
            }
            QFrame#tarjeta {
                border: 2px solid #ddd;
                border-radius: 12px;
                padding: 20px;
            }
            QFrame#tarjeta:hover {
                border: 2px solid #534AB7;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            }
            QPushButton#btnReporte {
                padding: 12px 24px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton#btnReporte:hover {
                background-color: #3D3580;
            }
            QPushButton#btnCerrar {
                padding: 10px 20px;
                border-radius: 6px;
            }

        """)
    
    def _construir_ui(self) -> None:
        """Construye la interfaz del dialog."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(2)

        subtitulo = QLabel("Selecciona el tipo de reporte que deseas generar")
        subtitulo.setObjectName("subtitulo")
        layout.addWidget(subtitulo)
        
        layout.addSpacing(20)
    
        # ── OPCIONES DE REPORTES ───────────────────────────────────
        opciones_layout = QHBoxLayout()
        opciones_layout.setSpacing(20)
        
        # Opción 1: Reporte de Estudiante
        tarjeta_estudiante = self._crear_tarjeta_opcion(
            titulo="👤 Reporte de Estudiante",
            descripcion="Visualiza el desempeño académico de un estudiante\ncon filtros por ciclo, carrera y taller.",
            callback=self._abrir_reporte_estudiante
        )
        opciones_layout.addWidget(tarjeta_estudiante)
        
        # Opción 2: Reporte de Taller
        tarjeta_taller = self._crear_tarjeta_opcion(
            titulo="🎯 Reporte de Taller",
            descripcion="Visualiza la asistencia completa de un taller\ncon datos por sesión y estudiante.",
            callback=self._abrir_reporte_taller
        )
        opciones_layout.addWidget(tarjeta_taller)
        
        layout.addLayout(opciones_layout)
        layout.addStretch()
        
    
    def _crear_tarjeta_opcion(self, titulo: str, descripcion: str, 
                             callback) -> QFrame:
        """Crea una tarjeta de opción de reporte."""
        tarjeta = QFrame()
        tarjeta.setObjectName("tarjeta")
        tarjeta.setCursor(Qt.CursorShape.PointingHandCursor)
        
        layout = QVBoxLayout(tarjeta)
        layout.setSpacing(15)
        
        # Título
        lbl_titulo = QLabel(titulo)
        font_titulo = QFont()
        font_titulo.setPointSize(14)
        font_titulo.setBold(True)
        lbl_titulo.setFont(font_titulo)
        layout.addWidget(lbl_titulo)
        
        # Descripción
        lbl_descripcion = QLabel(descripcion)
        lbl_descripcion.setObjectName("subtitulo")
        lbl_descripcion.setWordWrap(True)
        layout.addWidget(lbl_descripcion)
        
        layout.addStretch()
        
        # Botón
        btn = QPushButton("Generar →")
        btn.setObjectName("btnReporte")
        btn.clicked.connect(callback)
        layout.addWidget(btn)
        
        # Hacer clickeable toda la tarjeta
        tarjeta.mousePressEvent = lambda event: callback()
        
        return tarjeta
    
    def _abrir_reporte_estudiante(self) -> None:
        """Abre el diálogo de reporte de estudiante."""
        from .reporte_estudiante_dialog import ReporteEstudianteDialog
        
        dlg = ReporteEstudianteDialog(parent=self)
        dlg.exec()
    
    def _abrir_reporte_taller(self) -> None:
        """Abre el diálogo de reporte de taller."""
        from .reporte_taller_dialog import ReporteTallerDialog
        
        dlg = ReporteTallerDialog(parent=self)
        dlg.exec()

