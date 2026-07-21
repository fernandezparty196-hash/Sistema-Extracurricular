from pathlib import Path

from PySide6.QtCore import (
    Qt, QEvent, QPoint, QRectF, QPropertyAnimation, QEasingCurve, Property
)
from PySide6.QtGui import QPixmap, QFont, QPainterPath, QRegion, QPainter,QPainterPath 
from PySide6.QtWidgets import (
    QDialog, QWidget, QFrame, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QApplication, QStackedLayout,
    QGraphicsDropShadowEffect, QSizePolicy
)

from services.auth_service import AuthService
from services.configuracion_service import ConfiguracionService


# ── Paleta institucional ─────────────────────────────────────────
AZUL_INSTITUCIONAL = "#0f2440"
AZUL_CLARO         = "#60A5FA"
AZUL_OSCURO        = "#1D4ED8"
GRIS_CLARO         = "#F5F7FA"
GRIS_OSCURO        = "#374151"

RADIO_TARJETA   = 20
MARGEN_SOMBRA   = 28
ANCHO_TARJETA   = 1000
ALTO_TARJETA    = 550


# ════════════════════════════════════════════════════════════════
# Campo con ícono 
# ════════════════════════════════════════════════════════════════
class CampoLogin(QFrame):

    def __init__(self, icono: str, placeholder: str, es_password: bool = False, parent=None):
        super().__init__(parent)
        self.setObjectName("campo_login")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        fila = QHBoxLayout()
        fila.setContentsMargins(0, 0, 0, 0)
        fila.setSpacing(10)

        lbl_icono = QLabel(icono)
        lbl_icono.setObjectName("icono_campo")
        fila.addWidget(lbl_icono)

        self.input = QLineEdit()
        self.input.setObjectName("input_login")
        self.input.setPlaceholderText(placeholder)
        self.input.setMinimumHeight(34)
        if es_password:
            self.input.setEchoMode(QLineEdit.EchoMode.Password)
        self.input.installEventFilter(self)
        fila.addWidget(self.input, 1)

        self.btn_ojo = None
        if es_password:
            self.btn_ojo = QPushButton("👁")
            self.btn_ojo.setObjectName("btn_ojo")
            self.btn_ojo.setFixedSize(30, 30)
            self.btn_ojo.setCheckable(True)
            self.btn_ojo.setCursor(Qt.CursorShape.PointingHandCursor)
            fila.addWidget(self.btn_ojo)

        layout.addLayout(fila)

    def texto(self) -> str:
        return self.input.text()


# ════════════════════════════════════════════════════════════════
# Panel derecho: imagen "cover" + degradado + contenido institucional
# ════════════════════════════════════════════════════════════════
class PanelImagenInstitucional(QWidget):

    def __init__(self, radio_esquinas: int, parent=None):
        super().__init__(parent)
        self._radio = radio_esquinas
        self._pixmap_original = QPixmap()
        self.setMinimumWidth(1)
        self._construir_ui()

    def _construir_ui(self) -> None:
        stack = QStackedLayout(self)
        stack.setStackingMode(QStackedLayout.StackingMode.StackAll)

        self.lbl_imagen = QLabel()
        self.lbl_imagen.setScaledContents(False)
        stack.addWidget(self.lbl_imagen)

        overlay = QWidget()
        overlay.setObjectName("overlay_gradiente")
        stack.addWidget(overlay)

        capa = QWidget()
        capa.setStyleSheet("background: transparent;")
        layout_capa = QVBoxLayout(capa)
        layout_capa.setContentsMargins(24, 20, 24, 40)

        layout_capa.addStretch()

        self.lbl_logo_institucional = QLabel()
        self.lbl_logo_institucional.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_logo_institucional.setFixedHeight(80)
        layout_capa.addWidget(self.lbl_logo_institucional)
        layout_capa.addSpacing(18)

        self.lbl_universidad = QLabel("UNIVERSIDAD NACIONAL DE BARRANCA")
        self.lbl_universidad.setObjectName("nombre_universidad")
        self.lbl_universidad.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_universidad.setWordWrap(True)
        layout_capa.addWidget(self.lbl_universidad)
        layout_capa.addSpacing(4)

        self.lbl_sistema_hero = QLabel("Sistema de Gestión de Talleres")
        self.lbl_sistema_hero.setObjectName("nombre_sistema_hero")
        self.lbl_sistema_hero.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_capa.addWidget(self.lbl_sistema_hero)
        layout_capa.addSpacing(16)

        self.lbl_frase = QLabel("“Transformando la gestión de talleres universitarios”")
        self.lbl_frase.setObjectName("frase_motivadora")
        self.lbl_frase.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_frase.setWordWrap(True)
        layout_capa.addWidget(self.lbl_frase)

        layout_capa.addStretch()
        stack.addWidget(capa)

    def establecer_imagen(self, ruta: str | None) -> None:
        self._pixmap_original = QPixmap(ruta) if ruta and Path(ruta).exists() else QPixmap()
        self._actualizar_imagen()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._actualizar_imagen()

    def paintEvent(self, event):

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        path = QPainterPath()

        path.moveTo(0,0)
        path.lineTo(self.width()-self._radio,0)
        path.quadTo(self.width(),0,self.width(),self._radio)
        path.lineTo(self.width(),self.height()-self._radio)
        path.quadTo(
            self.width(),
            self.height(),
            self.width()-self._radio,
            self.height()
        )
        path.lineTo(0,self.height())
        path.closeSubpath()

        painter.setClipPath(path)

        super().paintEvent(event)

    def _actualizar_imagen(self) -> None:
        self.lbl_imagen.setFixedSize(self.size())

        if self._pixmap_original.isNull():
            self.lbl_imagen.setPixmap(QPixmap())
            self.lbl_imagen.setStyleSheet(
                "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, "
                f"stop:0 {AZUL_OSCURO}, stop:1 {AZUL_CLARO});"
            )
            return

        self.lbl_imagen.setStyleSheet("")
        escalado = self._pixmap_original.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation
        )
        x = max(0, (escalado.width() - self.width()) // 2)
        y = max(0, (escalado.height() - self.height()) // 2)
        self.lbl_imagen.setPixmap(escalado.copy(x, y, self.width(), self.height()))


# ════════════════════════════════════════════════════════════════
# Ventana de login
# ════════════════════════════════════════════════════════════════
class LoginWindow(QDialog):

    def __init__(self):
        super().__init__()
        self.sesion_activa = None
        self._drag_pos: QPoint | None = None

        self._configurar_ventana()
        self._construir_ui()
        self._cargar_configuracion_dinamica()
        self._conectar_senales()

    # ══════════════════════════════════════════════════════════════
    # CONFIGURACIÓN INICIAL
    # ══════════════════════════════════════════════════════════════

    def _configurar_ventana(self) -> None:
        self.setWindowTitle("Sistema de Talleres — UNAB")
        self.setWindowFlags(Qt.Window)

        self.resize(ANCHO_TARJETA + 40, ALTO_TARJETA + 40)
        self.setFont(QFont("Segoe UI", 10))

        self.setStyleSheet(f"""
            * {{ font-family: 'Segoe UI', 'Inter', 'Roboto', sans-serif; }}

            QFrame#panel_formulario {{
                background-color: #ffffff;
                border-top-left-radius: {RADIO_TARJETA}px;
                border-bottom-left-radius: {RADIO_TARJETA}px;
            }}

            QLabel#nombre_sistema {{
                font-size: 26px;
                font-weight: 700;
                color: {GRIS_OSCURO};
            }}
            QLabel#subtitulo_sistema {{
                font-size: 13px;
                color: #6B7280;
            }}
            QLabel#bienvenida_login {{
                font-size: 14px;
                color: {GRIS_OSCURO};
                padding-top: 6px;
            }}

            QLabel#icono_campo{{
                background: transparent;
            }}
            QPushButton#btn_ojo {{
                border: none;
                background: transparent;
                font-size: 14px;
                color: #9CA3AF;
            }}
            QPushButton#btn_ojo {{
                border: none;
                background: transparent;
                font-size: 16px;
                padding: 0 8px;
                color: #73726c;
            }}
            QPushButton#btn_ojo:hover {{ color: #3d3d3a; }}

            QLabel#lbl_error {{
                color: #B91C1C;
                font-size: 11px;
                padding: 6px 10px;
                background-color: #FEF2F2;
                border: 1px solid #FECACA;
                border-radius: 6px;
            }}

            QPushButton#btn_ingresar {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 {AZUL_INSTITUCIONAL}, stop:1 {AZUL_CLARO}
                );
                color: #ffffff;
                border: none;
                border-radius: 10px;
                font-size: 14px;
                font-weight: 700;
                padding: 12px;
            }}
            QPushButton#btn_ingresar:hover {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 {AZUL_OSCURO}, stop:1 {AZUL_INSTITUCIONAL}
                );
            }}
            QPushButton#btn_ingresar:pressed {{
                background: {AZUL_OSCURO};
                padding-top: 13px;
                padding-bottom: 11px;
            }}
            QPushButton#btn_ingresar:disabled {{
                background: #93C5FD;
            }}

            QLabel#lbl_version {{
                color: #9CA3AF;
                font-size: 11px;
            }}

            QWidget#overlay_gradiente {{
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(15,23,42,60),
                    stop:0.55 rgba(15,23,42,110),
                    stop:1 rgba(15,23,42,170)
                );
            }}
            QLabel#nombre_universidad {{
                color: #ffffff;
                font-size: 16px;
                font-weight: 700;
                letter-spacing: 1px;
            }}
            QLabel#nombre_sistema_hero {{
                color: #ffffff;
                font-size: 24px;
                font-weight: 700;
            }}
            QLabel#frase_motivadora {{
                color: #E5E7EB;
                font-size: 13px;
                font-style: italic;
                padding: 0 20px;
            }}
        """)

    # ══════════════════════════════════════════════════════════════
    # CONSTRUCCIÓN DE LA INTERFAZ
    # ══════════════════════════════════════════════════════════════

    def _construir_ui(self) -> None:
        # Margen transparente alrededor de la tarjeta: aquí "respira"
        # la sombra (QGraphicsDropShadowEffect) sin que se corte.
        layout_ventana = QVBoxLayout(self)
        layout_ventana.setContentsMargins(
            MARGEN_SOMBRA, MARGEN_SOMBRA, MARGEN_SOMBRA, MARGEN_SOMBRA
        )

        self.tarjeta = QWidget()
        self.tarjeta.setFixedSize(ANCHO_TARJETA, ALTO_TARJETA)
        layout_ventana.addWidget(self.tarjeta)

        sombra = QGraphicsDropShadowEffect(self.tarjeta)
        sombra.setBlurRadius(46)
        sombra.setOffset(0, 14)
        sombra.setColor(Qt.GlobalColor.black)
        self.tarjeta.setGraphicsEffect(sombra)

        layout_tarjeta = QHBoxLayout(self.tarjeta)
        layout_tarjeta.setContentsMargins(0, 0, 0, 0)
        layout_tarjeta.setSpacing(0)

        layout_tarjeta.addWidget(self._construir_panel_formulario(), stretch=5)
        self.panel_imagen = PanelImagenInstitucional(RADIO_TARJETA)
        layout_tarjeta.addWidget(self.panel_imagen, stretch=6)

    def _construir_panel_formulario(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("panel_formulario")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(56, 44, 56, 36)
        layout.setSpacing(4)

        # ── Logo del sistema ───────────────────────────────────────
        self.lbl_logo = QLabel()
        self.lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_logo.setFixedHeight(84)
        layout.addWidget(self.lbl_logo)
        layout.addSpacing(14)

        # ── Nombre + subtítulo ───────────────────────────────────────
        lbl_nombre = QLabel("Sistema de Talleres")
        lbl_nombre.setObjectName("nombre_sistema")
        lbl_nombre.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_nombre)

        self.lbl_subtitulo = QLabel("Universidad Nacional de Barranca")
        self.lbl_subtitulo.setObjectName("subtitulo_sistema")
        self.lbl_subtitulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_subtitulo)

        lbl_bienvenida = QLabel("Bienvenido de nuevo, ingresa tus credenciales")
        lbl_bienvenida.setObjectName("bienvenida_login")
        lbl_bienvenida.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_bienvenida)

        layout.addSpacing(26)

        # ── Campo usuario ────────────────────────────────────────
        self.campo_usuario = CampoLogin("👤", "Usuario")
        layout.addWidget(self.campo_usuario)
        layout.addSpacing(18)

        # ── Campo contraseña ─────────────────────────────────────
        self.campo_password = CampoLogin("🔒", "Contraseña", es_password=True)
        layout.addWidget(self.campo_password)
        layout.addSpacing(14)

        # ── Mensaje de error (oculto) ────────────────────────────
        self.lbl_error = QLabel()
        self.lbl_error.setObjectName("lbl_error")
        self.lbl_error.setWordWrap(True)
        self.lbl_error.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_error.setVisible(False)
        layout.addWidget(self.lbl_error)

        layout.addSpacing(10)

        # ── Botón Ingresar ────────────────────────────────────────
        self.btn_ingresar = QPushButton("INICIAR SESIÓN")
        self.btn_ingresar.setObjectName("btn_ingresar")
        self.btn_ingresar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_ingresar.setMinimumHeight(44)
        layout.addWidget(self.btn_ingresar)

        layout.addStretch()

        # ── Versión al pie ────────────────────────────────────────
        lbl_version = QLabel("v1.0.0 · UNAB Talleres")
        lbl_version.setObjectName("lbl_version")
        lbl_version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_version)

        return panel


    # ══════════════════════════════════════════════════════════════
    # CARGAR CONFIGURACIÓN DINÁMICA
    # ══════════════════════════════════════════════════════════════

    def _cargar_configuracion_dinamica(self) -> None:
        """Carga logo, nombre institucional y (si existe) imagen de fondo."""
        try:
            resultado = ConfiguracionService.obtener()

            if resultado.ok:
                config = resultado.datos
                nombre = config.get("nombre_institucion", "Universidad Nacional de Barranca")
                self.lbl_subtitulo.setText(nombre)
                self.panel_imagen.lbl_universidad.setText(nombre.upper())

                logo_ruta = config.get("logo_ruta")
                if logo_ruta:
                    self._cargar_logo(logo_ruta)
                else:
                    self._mostrar_placeholder_logo()


                fondo_ruta = config.get("fondo_ruta")
                if fondo_ruta:
                    ruta_fondo_abs = ConfiguracionService.obtener_ruta_logo_absoluta(fondo_ruta)
                    self.panel_imagen.establecer_imagen(ruta_fondo_abs)
                else:
                    self.panel_imagen.establecer_imagen(None)
            else:
                self._mostrar_placeholder_logo()
                self.panel_imagen.establecer_imagen(None)

        except Exception as e:
            print(f"Error cargando configuración: {e}")
            self._mostrar_placeholder_logo()
            self.panel_imagen.establecer_imagen(None)

    def _cargar_logo(self, logo_ruta: str) -> None:
        try:
            ruta_absoluta = ConfiguracionService.obtener_ruta_logo_absoluta(logo_ruta)
            if ruta_absoluta and Path(ruta_absoluta).exists():
                pixmap = QPixmap(ruta_absoluta)

                logo_form = pixmap.scaledToHeight(
                    80, Qt.TransformationMode.SmoothTransformation
                )
                self.lbl_logo.setPixmap(logo_form)

                logo_hero = pixmap.scaledToHeight(
                    72, Qt.TransformationMode.SmoothTransformation
                )
                self.panel_imagen.lbl_logo_institucional.setPixmap(logo_hero)
            else:
                self._mostrar_placeholder_logo()
        except Exception as e:
            print(f"Error cargando logo: {e}")
            self._mostrar_placeholder_logo()

    def _mostrar_placeholder_logo(self) -> None:
        self.lbl_logo.setText("🎓")
        self.lbl_logo.setStyleSheet("font-size: 46px;")
        self.panel_imagen.lbl_logo_institucional.setText("🎓")
        self.panel_imagen.lbl_logo_institucional.setStyleSheet("font-size: 40px; color: white;")

    # ══════════════════════════════════════════════════════════════
    # CONEXIÓN DE SEÑALES (EVENTOS)
    # ══════════════════════════════════════════════════════════════

    def _conectar_senales(self) -> None:
        self.btn_ingresar.clicked.connect(self._intentar_login)

        self.campo_usuario.input.returnPressed.connect(self._intentar_login)
        self.campo_password.input.returnPressed.connect(self._intentar_login)

        self.campo_password.btn_ojo.toggled.connect(self._toggle_password_visible)

        self.campo_usuario.input.textChanged.connect(self._limpiar_error)
        self.campo_password.input.textChanged.connect(self._limpiar_error)

    # ══════════════════════════════════════════════════════════════
    # LÓGICA DEL LOGIN
    # ══════════════════════════════════════════════════════════════

    def _intentar_login(self) -> None:
        username = self.campo_usuario.texto().strip()
        password = self.campo_password.texto()

        if not username or not password:
            self._mostrar_error("Por favor completa todos los campos")
            return

        self.btn_ingresar.setEnabled(False)
        self.btn_ingresar.setText("VERIFICANDO...")
        QApplication.processEvents()

        resultado = AuthService.login(username, password)

        if resultado.ok:
            self.sesion_activa = resultado.sesion
            self.accept()
        else:
            self._mostrar_error(resultado.mensaje)
            self.btn_ingresar.setEnabled(True)
            self.btn_ingresar.setText("INICIAR SESIÓN")
            self.campo_password.input.clear()
            self.campo_usuario.input.setFocus()

    def _mostrar_error(self, mensaje: str) -> None:
        self.lbl_error.setText(mensaje)
        self.lbl_error.setVisible(True)

    def _limpiar_error(self) -> None:
        if self.lbl_error.isVisible():
            self.lbl_error.setVisible(False)

    def _toggle_password_visible(self, visible: bool) -> None:
        modo = QLineEdit.EchoMode.Normal if visible else QLineEdit.EchoMode.Password
        self.campo_password.input.setEchoMode(modo)
        self.campo_password.btn_ojo.setText("🙈" if visible else "👁")