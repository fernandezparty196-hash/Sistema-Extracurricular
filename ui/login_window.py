"""
ui/login_window.py

Login redesigned:
- Lado IZQUIERDO: Logo grande (imagen)
- Lado DERECHO: Formulario de login
- Logo y nombre DINÁMICOS desde configuracion.json
"""

from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QFont
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QApplication, QFrame, QWidget,
)

from services.auth_service import AuthService
from services.configuracion_service import ConfiguracionService


class LoginWindow(QDialog):

    def __init__(self):
        super().__init__()
        self.sesion_activa = None
        
        self._configurar_ventana()
        self._construir_ui()
        self._cargar_configuracion_dinamica()
        self._conectar_senales()

    # ══════════════════════════════════════════════════════════════
    # CONFIGURACIÓN INICIAL
    # ══════════════════════════════════════════════════════════════

    def _configurar_ventana(self) -> None:
        """Configura la ventana principal del login"""
        self.setWindowTitle("Sistema de Talleres — UNAB")
        self.setFixedSize(800, 480)
        
        # Centrar en pantalla
        pantalla = QApplication.primaryScreen().geometry()
        x = (pantalla.width() - self.width()) // 2
        y = (pantalla.height() - self.height()) // 2
        self.move(x, y)

        self.setStyleSheet("""
            QPushButton#btn_ojo {
                border: none;
                background: transparent;
                font-size: 16px;
                padding: 0 8px;
                color: #73726c;
            }
            QPushButton#btn_ojo:hover { color: #3d3d3a; }
            QLabel#error_msg {
                color: #C0392B;
                font-size: 12px;
                padding: 8px 12px;
                background-color: #fdf0ee;
                border-radius: 6px;
                border: 1px solid #f5c6c0;
            }
            QLabel#version {
                font-size: 11px;
                color: #a09e96;
            }
        """)

    # ══════════════════════════════════════════════════════════════
    # CONSTRUCCIÓN DE LA INTERFAZ
    # ══════════════════════════════════════════════════════════════

    def _construir_ui(self) -> None:
        """Construye la interfaz con dos columnas: Logo | Formulario"""
        
        # Layout principal horizontal (izquierda | derecha)
        layout_principal = QHBoxLayout(self)
        layout_principal.setContentsMargins(0, 0, 0, 0)
        layout_principal.setSpacing(0)

        # ── LADO IZQUIERDO: LOGO ──────────────────────────────────
        self.lbl_logo = QLabel()
        self.lbl_logo.setObjectName("logo_area")
        self.lbl_logo.setFixedSize(400, 400)
        self.lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout_principal.addWidget(self.lbl_logo)

        # ── LADO DERECHO: FORMULARIO ──────────────────────────────
        contenedor_derecha = QWidget()
        layout_derecha = QVBoxLayout(contenedor_derecha)
        layout_derecha.setContentsMargins(50, 60, 50, 50)
        layout_derecha.setSpacing(10)

        # Título: "Sistema de Talleres"
        lbl_titulo = QLabel("Sistema de Talleres")
        lbl_titulo.setObjectName("titulo_login")
        font_titulo = QFont()
        font_titulo.setPointSize(22)
        font_titulo.setBold(True)
        lbl_titulo.setFont(font_titulo)
        lbl_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_derecha.addWidget(lbl_titulo)

        # Subtítulo: "Universidad Nacional de Barranca" (DINÁMICO)
        self.lbl_institucion = QLabel()
        self.lbl_institucion.setObjectName("subtitulo_login")
        font_subtitulo = QFont()
        font_subtitulo.setPointSize(10)
        self.lbl_institucion.setFont(font_subtitulo)
        self.lbl_institucion.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_institucion.setStyleSheet("color: #666;")
        layout_derecha.addWidget(self.lbl_institucion)

        # Espacio
        layout_derecha.addSpacing(25)

        # ── Campo: Usuario ────────────────────────────────────────
        lbl_usuario = QLabel("Usuario")
        lbl_usuario.setObjectName("label_campo")
        font_label = QFont()
        font_label.setPointSize(12)
        font_label.setBold(True)
        lbl_usuario.setFont(font_label)
        layout_derecha.addWidget(lbl_usuario)

        self.input_usuario = QLineEdit()
        self.input_usuario.setObjectName("input_campo")
        self.input_usuario.setPlaceholderText("Ingresa tu usuario")
        self.input_usuario.setMinimumHeight(45)

        layout_derecha.addWidget(self.input_usuario)

        # ── Campo: Contraseña ────────────────────────────────────
        lbl_password = QLabel("Contraseña")
        lbl_password.setObjectName("label_campo")
        lbl_password.setFont(font_label)
        layout_derecha.addWidget(lbl_password)

        # Contenedor: Input + Botón ojo
        layout_password = QHBoxLayout()
        layout_password.setSpacing(5)

        self.input_password = QLineEdit()
        self.input_password.setObjectName("input_campo")
        self.input_password.setPlaceholderText("Ingresa tu contraseña")
        self.input_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_password.setMinimumHeight(45)

        self.btn_ojo = QPushButton("👁")
        self.btn_ojo.setObjectName("btn_ojo")
        self.btn_ojo.setFixedSize(45, 45)
        self.btn_ojo.setCheckable(True)

        layout_password.addWidget(self.input_password)
        layout_password.addWidget(self.btn_ojo)
        layout_derecha.addLayout(layout_password)

        # ── Mensaje de error (oculto) ──────────────────────────────
        self.lbl_error = QLabel()
        self.lbl_error.setObjectName("lbl_error")
        self.lbl_error.setWordWrap(True)
        self.lbl_error.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_error.setVisible(False)
        layout_derecha.addWidget(self.lbl_error)

        # ── Botón Ingresar ────────────────────────────────────────
        self.btn_ingresar = QPushButton("INGRESAR")
        self.btn_ingresar.setObjectName("btn_ingresar")
        self.btn_ingresar.setMinimumHeight(50)
 
        layout_derecha.addWidget(self.btn_ingresar)

        # Espacio flexible
        layout_derecha.addStretch()


        # ── Versión al pie ────────────────────────────────────────
        lbl_version = QLabel("v1.0.0 · UNAB Talleres")
        lbl_version.setObjectName("lbl_version")
        lbl_version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_version.setStyleSheet("""
            QLabel#lbl_version {
                color: #999;
                font-size: 11px;
            }
        """)
        layout_derecha.addWidget(lbl_version)

        # Agregar la columna derecha al layout principal
        layout_principal.addWidget(contenedor_derecha, stretch=1)

    # ══════════════════════════════════════════════════════════════
    # CARGAR CONFIGURACIÓN DINÁMICA
    # ══════════════════════════════════════════════════════════════

    def _cargar_configuracion_dinamica(self) -> None:
        """Carga logo y nombre desde configuracion.json"""
        try:
            # Obtener configuración
            resultado = ConfiguracionService.obtener()
            
            if resultado.ok:
                config = resultado.datos
                
                # ── Cargar nombre institución ──────────────────────
                nombre = config.get("nombre_institucion", "Universidad Nacional de Barranca")
                self.lbl_institucion.setText(nombre)
                
                # ── Cargar logo ────────────────────────────────────
                logo_ruta = config.get("logo_ruta")
                if logo_ruta:
                    self._cargar_logo(logo_ruta)
                else:
                    self._mostrar_placeholder_logo()
            else:
                # Sin configuración, mostrar defaults
                self.lbl_institucion.setText("Universidad Nacional de Barranca")
                self._mostrar_placeholder_logo()
                
        except Exception as e:
            print(f"Error cargando configuración: {e}")
            self.lbl_institucion.setText("Universidad Nacional de Barranca")
            self._mostrar_placeholder_logo()

    def _cargar_logo(self, logo_ruta: str) -> None:
        """Carga y muestra la imagen del logo"""
        try:
            ruta_absoluta = ConfiguracionService.obtener_ruta_logo_absoluta(logo_ruta)
            
            if ruta_absoluta and Path(ruta_absoluta).exists():
                pixmap = QPixmap(ruta_absoluta)
                
                # Escalar para que quepa en el área (450×650)

                ancho_deseado = 250  # Un poco más pequeño que el área para dejar margen
                pixmap_escalado = pixmap.scaledToWidth(
                    ancho_deseado,
                    Qt.TransformationMode.SmoothTransformation  # Evita que se pixele
                )    
                
                self.lbl_logo.setPixmap(pixmap_escalado)
                self.lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
            else:
                self._mostrar_placeholder_logo()
        except Exception as e:
            print(f"Error cargando logo: {e}")
            self._mostrar_placeholder_logo()

    def _mostrar_placeholder_logo(self) -> None:
        """Muestra un placeholder cuando no hay logo"""
        self.lbl_logo.setText("Sin logo\ncargado")
        self.lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_logo.setStyleSheet("""
            QLabel#logo_area {
                background-color: #f0f0f0;
                color: #999;
                font-size: 18px;
                border: none;
            }
        """)

    # ══════════════════════════════════════════════════════════════
    # CONEXIÓN DE SEÑALES (EVENTOS)
    # ══════════════════════════════════════════════════════════════

    def _conectar_senales(self) -> None:
        """Conecta eventos de los widgets"""
        
        # Botón Ingresar
        self.btn_ingresar.clicked.connect(self._intentar_login)
        
        # Enter en campos de texto
        self.input_usuario.returnPressed.connect(self._intentar_login)
        self.input_password.returnPressed.connect(self._intentar_login)
        
        # Botón ojo - mostrar/ocultar contraseña
        self.btn_ojo.toggled.connect(self._toggle_password_visible)
        
        # Limpiar error al escribir
        self.input_usuario.textChanged.connect(self._limpiar_error)
        self.input_password.textChanged.connect(self._limpiar_error)

    # ══════════════════════════════════════════════════════════════
    # LÓGICA DEL LOGIN
    # ══════════════════════════════════════════════════════════════

    def _intentar_login(self) -> None:
        """Intenta hacer login con las credenciales"""
        
        username = self.input_usuario.text().strip()
        password = self.input_password.text()

        # Validación básica
        if not username or not password:
            self._mostrar_error("Por favor completa todos los campos")
            return

        # Deshabilitar botón mientras procesa
        self.btn_ingresar.setEnabled(False)
        self.btn_ingresar.setText("Verificando...")
        QApplication.processEvents()

        # Intentar login
        resultado = AuthService.login(username, password)

        if resultado.ok:
            # ✅ Login exitoso
            self.sesion_activa = resultado.sesion
            self.accept()
        else:
            # ❌ Login fallido
            self._mostrar_error(resultado.mensaje)
            self.btn_ingresar.setEnabled(True)
            self.btn_ingresar.setText("INGRESAR")
            self.input_password.clear()
            self.input_usuario.setFocus()

    def _mostrar_error(self, mensaje: str) -> None:
        """Muestra un mensaje de error"""
        self.lbl_error.setText(mensaje)
        self.lbl_error.setVisible(True)
        
        # Resaltar inputs con error
        self.input_usuario.setProperty("error", "true")
        self.input_password.setProperty("error", "true")
        
        # Recalcular estilos
        self.input_usuario.style().unpolish(self.input_usuario)
        self.input_usuario.style().polish(self.input_usuario)
        self.input_password.style().unpolish(self.input_password)
        self.input_password.style().polish(self.input_password)

    def _limpiar_error(self) -> None:
        """Limpia el mensaje de error cuando el usuario escribe"""
        if self.lbl_error.isVisible():
            self.lbl_error.setVisible(False)
            
            self.input_usuario.setProperty("error", "false")
            self.input_password.setProperty("error", "false")
            
            self.input_usuario.style().unpolish(self.input_usuario)
            self.input_usuario.style().polish(self.input_usuario)
            self.input_password.style().unpolish(self.input_password)
            self.input_password.style().polish(self.input_password)

    def _toggle_password_visible(self, visible: bool) -> None:
        """Alterna entre mostrar y ocultar la contraseña"""
        modo = QLineEdit.EchoMode.Normal if visible else QLineEdit.EchoMode.Password
        self.input_password.setEchoMode(modo)
        self.btn_ojo.setText("🙈" if visible else "👁")