from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QFileDialog
)

from services.configuracion_service import ConfiguracionService
from services.auth_service import SesionUsuario


class ConfiguracionSistemaDialog(QDialog):
    """
    Diálogo para personalizar:
    - Nombre de la institución
    - Logo de la institución
    Guarda en config/configuracion.json
    Solo accesible para Administrador.
    """

    def __init__(self, sesion: SesionUsuario, parent=None):
        super().__init__(parent)
        self.sesion = sesion
        
        # Verificar que solo administrador acceda
        if sesion.rol_nombre != "Administrador":
            QMessageBox.warning(
                self,
                "Acceso denegado",
                "Solo los administradores pueden acceder a esta configuración."
            )
            self.reject()
            return

        self.setWindowTitle("Configuración del Sistema")
        self.setFixedSize(500, 500)
        self.setModal(True)
        
        self._cargar_configuracion_actual()
        self._construir_ui()

    def _cargar_configuracion_actual(self) -> None:
        """Carga la configuración actual desde el archivo JSON"""
        resultado = ConfiguracionService.obtener()
        
        if resultado.ok:
            self.config_actual = resultado.datos
        else:
            self.config_actual = {
                "nombre_institucion": "Universidad Nacional de Barranca",
                "logo_ruta": None
            }

    def _construir_ui(self) -> None:
        """Construye la interfaz del diálogo"""
        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(30, 25, 30, 25)
        layout_principal.setSpacing(10)

        # ── Título ────────────────────────────────────────────────
        lbl_titulo = QLabel("Personalización del Sistema")
        lbl_titulo.setObjectName("titulo_dialog")
        layout_principal.addWidget(lbl_titulo)
        layout_principal.setSpacing(10)

        # ── Sección: Logo ─────────────────────────────────────────
        lbl_logo_titulo = QLabel("Logo de la institución")
        lbl_logo_titulo.setObjectName("subtitulo_dialog")
        layout_principal.addWidget(lbl_logo_titulo)
        layout_principal.setSpacing(10)

        # Vista previa del logo
        self.lbl_logo_preview = QLabel()
        self.lbl_logo_preview.setFixedSize(150, 150)
        self.lbl_logo_preview.setStyleSheet("""
            QLabel {
                border: 2px dashed #ccc;
                border-radius: 8px;
                background-color: #f5f5f5;
            }
        """)
        self.lbl_logo_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._cargar_preview_logo()

        # Botones para el logo
        layout_logo_botones = QHBoxLayout()
        
        btn_cargar_logo = QPushButton("📁 Cargar logo")
        btn_cargar_logo.setObjectName("btn_cargar_logo")
        btn_cargar_logo.clicked.connect(self._seleccionar_logo)
        
        btn_limpiar_logo = QPushButton("🗑 Limpiar")
        btn_limpiar_logo.setObjectName("btn_limpiar_logo")
        btn_limpiar_logo.clicked.connect(self._limpiar_logo)
        
        layout_logo_botones.addWidget(btn_cargar_logo)
        layout_logo_botones.addWidget(btn_limpiar_logo)

        layout_principal.addWidget(self.lbl_logo_preview)
        layout_principal.addLayout(layout_logo_botones)

        # ── Sección: Nombre ───────────────────────────────────────
        lbl_nombre_titulo = QLabel("Nombre de la institución")
        lbl_nombre_titulo.setObjectName("subtitulo_dialog")
        layout_principal.addWidget(lbl_nombre_titulo)

        self.inp_nombre = QLineEdit()
        self.inp_nombre.setPlaceholderText("Ej: Universidad Nacional de Barranca")
        self.inp_nombre.setText(self.config_actual.get("nombre_institucion", ""))
        self.inp_nombre.setMinimumHeight(40)

        layout_principal.addWidget(self.inp_nombre)

        # ── Botones: Guardar y Cancelar ───────────────────────────
        layout_principal.addSpacing(10)
        
        layout_botones = QHBoxLayout()
        layout_botones.setSpacing(10)

        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setObjectName("btn_cancelar")
        btn_cancelar.clicked.connect(self.reject)

        btn_guardar = QPushButton("💾 Guardar cambios")
        btn_guardar.setObjectName("btn_guardar")
        btn_guardar.clicked.connect(self._guardar_cambios)

        layout_botones.addWidget(btn_cancelar)
        layout_botones.addWidget(btn_guardar)

        layout_principal.addLayout(layout_botones)

        # Guardar referencia para el logo
        self.ruta_logo_nueva = self.config_actual.get("logo_ruta")

        # ── Estilos globales ─────────────────────────────────────
        self.setStyleSheet("""
            QLabel#titulo_dialog {
                font-size: 20px;
                font-weight: bold;
                color: #2c3e50;
            }
            QLabel#subtitulo_dialog {
                font-size: 14px;
                font-weight: bold;
                color: #34495e;
            }
            QLineEdit {
                border: 2px solid #bdc3c7;
                border-radius: 6px;
                padding: 8px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #2980b9;
                background-color: #ecf6fc;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 8px 14px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton#btn_cancelar {
                background-color: #e74c3c;
            }
            QPushButton#btn_cancelar:hover {
                background-color: #c0392b;
            }
            QPushButton#btn_guardar {
                background-color: #27ae60;
            }
            QPushButton#btn_guardar:hover {
                background-color: #1e8449;
            }
        """)

    def _cargar_preview_logo(self) -> None:
        """Carga y muestra la vista previa del logo actual"""
        ruta_logo = self.config_actual.get("logo_ruta")
        
        if ruta_logo:
            ruta_absoluta = ConfiguracionService.obtener_ruta_logo_absoluta(ruta_logo)
            
            if ruta_absoluta and Path(ruta_absoluta).exists():
                pixmap = QPixmap(ruta_absoluta)
                # Escalar manteniendo proporción
                pixmap_escalado = pixmap.scaledToWidth(
                    140,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.lbl_logo_preview.setPixmap(pixmap_escalado)
                return
        
        # Si no hay logo, mostrar placeholder
        self.lbl_logo_preview.setText("Sin logo")
        self.lbl_logo_preview.setStyleSheet("""
            QLabel {
                border: 2px dashed #ccc;
                border-radius: 8px;
                background-color: #f5f5f5;
                color: #999;
                font-size: 14px;
            }
        """)

    def _seleccionar_logo(self) -> None:
        """Abre un diálogo para seleccionar un nuevo logo"""
        ruta_archivo, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar logo",
            "",
            "Imágenes (*.png *.jpg *.jpeg *.gif *.bmp);;Todos (*.*)"
        )

        if ruta_archivo:
            # Guardar el archivo en assets/logos/
            resultado = ConfiguracionService.guardar_logo(ruta_archivo)
            
            if resultado.ok:
                self.ruta_logo_nueva = resultado.datos["ruta_relativa"]
                
                # Recargar la vista previa
                pixmap = QPixmap(ruta_archivo)
                pixmap_escalado = pixmap.scaledToWidth(
                    140,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.lbl_logo_preview.setPixmap(pixmap_escalado)
                self.lbl_logo_preview.setStyleSheet("")  # Limpiar estilos de placeholder
            else:
                QMessageBox.warning(
                    self,
                    "Error",
                    f"No se pudo guardar el logo:\n{resultado.mensaje}"
                )

    def _limpiar_logo(self) -> None:
        """Elimina el logo actual"""
        self.ruta_logo_nueva = None
        self._cargar_preview_logo()

    def _guardar_cambios(self) -> None:
        """Guarda los cambios en el archivo JSON"""
        nombre_institucion = self.inp_nombre.text().strip()
        
        if not nombre_institucion:
            QMessageBox.warning(
                self,
                "Validación",
                "El nombre de la institución no puede estar vacío."
            )
            return

        # Actualizar archivo JSON
        resultado = ConfiguracionService.actualizar(
            nombre_institucion=nombre_institucion,
            logo_ruta=self.ruta_logo_nueva
        )

        if resultado.ok:
            QMessageBox.information(
                self,
                "Éxito",
                "Configuración actualizada correctamente.\n\n"
                "Los cambios se verán reflejados en próximos accesos al sistema."
            )
            self.accept()
        else:
            QMessageBox.warning(
                self,
                "Error",
                f"No se pudo guardar la configuración:\n{resultado.mensaje}"
            )