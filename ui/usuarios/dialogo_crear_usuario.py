
from PySide6.QtCore import Qt, QRegularExpression
from PySide6.QtGui import QFont, QIcon, QColor, QRegularExpressionValidator
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QComboBox, QPushButton,
    QMessageBox, QFrame, QProgressBar, QCheckBox
)

from services.usuario_service import UsuarioService
from services.auth_service import SesionUsuario


class DialogoCrearUsuario(QDialog):
    """
    Dialog para crear un nuevo usuario en el sistema.
    
    FLUJO:
      1. Usuario rellena formulario
      2. Click en "Crear"
      3. Service valida y crea en BD
      4. Muestra confirmación
      5. Dialog se cierra
    """

    def __init__(self, sesion_usuario: SesionUsuario, parent=None):
        super().__init__(parent)
        self.sesion_usuario = sesion_usuario
        self.usuario_creado = None

        self._configurar_ventana()
        self._construir_ui()
        self._conectar_senales()
        self._cargar_roles()

    def _configurar_ventana(self) -> None:
        """Configura propiedades básicas del dialog."""
        self.setWindowTitle("Crear Nuevo Usuario")
        self.setMinimumSize(450, 480)
        self.setModal(True)

    def _construir_ui(self) -> None:
        """Construye la interfaz del dialog."""
        raiz = QVBoxLayout()
        raiz.setSpacing(8)
        raiz.setContentsMargins(15, 15, 15, 15)

        # ── TÍTULO ───────────────────────────────────────────────
        titulo = QLabel("Crear Nuevo Usuario")
        titulo.setObjectName("titulo")
        raiz.addWidget(titulo)

        subtitulo = QLabel("Completa los datos para crear una nueva cuenta de usuario")
        subtitulo.setObjectName("subtitulo")
        raiz.addWidget(subtitulo)

        # ── SEPARADOR ────────────────────────────────────────────
        sep = QFrame()
        sep.setObjectName("separador")
        raiz.addWidget(sep)

        # ── FORMULARIO ───────────────────────────────────────────
        grid = QGridLayout()
        grid.setSpacing(8)

        # Nombres
        grid.addWidget(QLabel("Nombres *"), 0, 0)
        self.inp_nombres = QLineEdit()
        self.inp_nombres.setObjectName("inp_nombres")
        self.inp_nombres.setPlaceholderText("Juan, Maria, Carlos...")
        self.inp_nombres.textChanged.connect(self._generar_sugerencia_username)
        grid.addWidget(self.inp_nombres, 1, 0)

        # Apellidos
        grid.addWidget(QLabel("Apellidos *"), 0, 1)
        self.inp_apellidos = QLineEdit()
        self.inp_apellidos.setObjectName("inp_apellidos")
        self.inp_apellidos.setPlaceholderText("García, López, Pérez...")
        self.inp_apellidos.textChanged.connect(self._generar_sugerencia_username)
        grid.addWidget(self.inp_apellidos, 1, 1)

        # Username
        grid.addWidget(QLabel("Usuario *"), 2, 0, 1, 2)
        username_layout = QHBoxLayout()
        username_layout.setSpacing(6)
        self.inp_username = QLineEdit()
        self.inp_username.setObjectName("inp_username")
        self.inp_username.setPlaceholderText("jgarcia, mlopez...")
        self.inp_username.setValidator(
            QRegularExpressionValidator(
                QRegularExpression(r"[a-zA-Z0-9._]{3,50}")
            )
        )
        username_layout.addWidget(self.inp_username, 1)

        btn_sugerir = QPushButton("📋 Sugerir")
        btn_sugerir.setFixedWidth(80)
        btn_sugerir.clicked.connect(self._generar_sugerencia_username)
        username_layout.addWidget(btn_sugerir)
        grid.addLayout(username_layout, 3, 0, 1, 2)

        # Email
        grid.addWidget(QLabel("Email *"), 4, 0, 1, 2)
        self.inp_email = QLineEdit()
        self.inp_email.setObjectName("inp_email")
        self.inp_email.setPlaceholderText("usuario@unab.edu.pe")
        self.inp_email.setValidator(
            QRegularExpressionValidator(
                QRegularExpression(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
            )
        )
        grid.addWidget(self.inp_email, 5, 0, 1, 2)

        # Rol
        grid.addWidget(QLabel("Rol *"), 6, 0, 1, 2)
        self.cmb_rol = QComboBox()
        self.cmb_rol.setObjectName("cmb_rol")
        self.cmb_rol.addItem("— Selecciona rol —", None)
        grid.addWidget(self.cmb_rol, 7, 0, 1, 2)

        # Contraseña
        grid.addWidget(QLabel("Contraseña *"), 8, 0, 1, 2)
        self.inp_password = QLineEdit()
        self.inp_password.setObjectName("inp_password")
        self.inp_password.setPlaceholderText("Mínimo 8 caracteres")
        self.inp_password.setEchoMode(QLineEdit.Password)
        self.inp_password.textChanged.connect(self._actualizar_fortaleza_password)
        grid.addWidget(self.inp_password, 9, 0, 1, 2)

        # Indicador de fortaleza
        self.lbl_fortaleza = QLabel("Fortaleza: ")
        self.lbl_fortaleza.setObjectName("subtitulo")
        grid.addWidget(self.lbl_fortaleza, 10, 0, 1, 2)

        self.progress_fortaleza = QProgressBar()
        self.progress_fortaleza.setRange(0, 100)
        self.progress_fortaleza.setValue(0)
        self.progress_fortaleza.setTextVisible(False)
        grid.addWidget(self.progress_fortaleza, 11, 0, 1, 2)

        # Confirmar contraseña
        grid.addWidget(QLabel("Confirmar contraseña *"), 12, 0, 1, 2)
        self.inp_password_conf = QLineEdit()
        self.inp_password_conf.setObjectName("inp_password_conf")
        self.inp_password_conf.setPlaceholderText("Repite la contraseña")
        self.inp_password_conf.setEchoMode(QLineEdit.Password)
        grid.addWidget(self.inp_password_conf, 13, 0, 1, 2)

        # Checkbox: activo
        self.chk_activo = QCheckBox("Usuario activo desde el inicio")
        self.chk_activo.setChecked(True)
        grid.addWidget(self.chk_activo, 14, 0, 1, 2)

        raiz.addLayout(grid)

        # ── BOTONES ──────────────────────────────────────────────
        sep2 = QFrame()
        sep2.setObjectName("separador")
        raiz.addWidget(sep2)

        botones_layout = QHBoxLayout()
        botones_layout.setSpacing(8)
        botones_layout.addStretch()

        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_cancelar.setObjectName("btnCancelar")
        self.btn_cancelar.setFixedSize(90, 32)
        self.btn_cancelar.clicked.connect(self.reject)
        botones_layout.addWidget(self.btn_cancelar)

        self.btn_crear = QPushButton("✓ Crear Usuario")
        self.btn_crear.setFixedSize(130, 32)
        self.btn_crear.clicked.connect(self._crear_usuario)
        botones_layout.addWidget(self.btn_crear)

        raiz.addLayout(botones_layout)
        self.setLayout(raiz)

    def _conectar_senales(self) -> None:
        """Conecta señales de validación."""
        pass  # Ya conectadas en _construir_ui

    def _cargar_roles(self) -> None:
        """Carga los roles disponibles de la BD."""
        # NOTA: Si tu tabla roles no existe, comentar esta sección
        # y agregar roles manualmente como en el ejemplo original

        # Roles típicos (ajusta según tu BD)
        roles = [
            ("Administrador", 1),
            ("Docente", 2),
            ("Operador", 3),
        ]

        for nombre, rol_id in roles:
            self.cmb_rol.addItem(nombre, rol_id)

    # ══════════════════════════════════════════════════════════════
    # VALIDACIONES Y GENERACIÓN
    # ══════════════════════════════════════════════════════════════

    def _generar_sugerencia_username(self) -> None:
        """
        Genera una sugerencia automática de username
        basada en nombres y apellidos.
        """
        nombres = self.inp_nombres.text().strip()
        apellidos = self.inp_apellidos.text().strip()

        if not nombres or not apellidos:
            return

        # Generar sugerencia: primera letra del nombre + apellido completo
        sugerencia = (nombres[0] + apellidos).lower().replace(" ", "")
        # Limitar a 50 caracteres
        sugerencia = sugerencia[:50]

        self.inp_username.setText(sugerencia)

    def _actualizar_fortaleza_password(self) -> None:
        """Calcula y muestra la fortaleza de la contraseña."""
        password = self.inp_password.text()

        if not password:
            self.progress_fortaleza.setValue(0)
            self.lbl_fortaleza.setText("Fortaleza: ")
            return

        fortaleza = 0

        # Criterios
        if len(password) >= 8:
            fortaleza += 25
        if len(password) >= 12:
            fortaleza += 25
        if any(c.isupper() for c in password):
            fortaleza += 25
        if any(c.isdigit() for c in password):
            fortaleza += 25

        self.progress_fortaleza.setValue(fortaleza)

        if fortaleza < 50:
            texto = "Débil"
            color = "#ef4444"
        elif fortaleza < 75:
            texto = "Media"
            color = "#f59e0b"
        else:
            texto = "Fuerte"
            color = "#10b981"

        self.lbl_fortaleza.setText(f"Fortaleza: {texto}")
        self.lbl_fortaleza.setStyleSheet(f"color: {color};")

    def _validar_datos(self) -> tuple[bool, str]:
        """
        Valida todos los datos del formulario.
        Retorna: (válido: bool, mensaje: str)
        """

        # Nombres
        nombres = self.inp_nombres.text().strip()
        if not nombres:
            return False, "El nombre es obligatorio."
        if len(nombres) < 2:
            return False, "El nombre debe tener al menos 2 caracteres."

        # Apellidos
        apellidos = self.inp_apellidos.text().strip()
        if not apellidos:
            return False, "El apellido es obligatorio."
        if len(apellidos) < 2:
            return False, "El apellido debe tener al menos 2 caracteres."

        # Username
        username = self.inp_username.text().strip()
        if not username:
            return False, "El usuario es obligatorio."
        if len(username) < 3:
            return False, "El usuario debe tener al menos 3 caracteres."
        if len(username) > 50:
            return False, "El usuario no puede exceder 50 caracteres."
        if " " in username:
            return False, "El usuario no puede contener espacios."

        # Email
        email = self.inp_email.text().strip()
        if not email:
            return False, "El email es obligatorio."
        if "@" not in email or "." not in email.split("@")[-1]:
            return False, "El email no tiene un formato válido."

        # Rol
        if self.cmb_rol.currentData() is None:
            return False, "Debes seleccionar un rol."

        # Contraseña
        password = self.inp_password.text()
        if not password:
            return False, "La contraseña es obligatoria."
        if len(password) < 8:
            return False, "La contraseña debe tener al menos 8 caracteres."

        # Confirmar contraseña
        password_conf = self.inp_password_conf.text()
        if password != password_conf:
            return False, "Las contraseñas no coinciden."

        return True, "Datos válidos"

    # ══════════════════════════════════════════════════════════════
    # CREAR USUARIO
    # ══════════════════════════════════════════════════════════════

    def _crear_usuario(self) -> None:
        """Crea el usuario en la BD."""

        # Validar
        valido, mensaje = self._validar_datos()
        if not valido:
            QMessageBox.warning(self, "Validación", mensaje)
            return

        # Deshabilitar botón
        self.btn_crear.setEnabled(False)
        self.btn_crear.setText("Creando...")

        try:
            # Llamar al servicio
            resultado = UsuarioService.crear(
                nombres=self.inp_nombres.text().strip(),
                apellidos=self.inp_apellidos.text().strip(),
                username=self.inp_username.text().strip(),
                email=self.inp_email.text().strip(),
                password=self.inp_password.text(),
                rol_id=self.cmb_rol.currentData(),
                usuario_creador_id=self.sesion_usuario.usuario_id
            )

            if resultado.ok:
                # ✓ Éxito
                self.usuario_creado = resultado.usuario

                QMessageBox.information(
                    self,
                    "Éxito",
                    f"✓ {resultado.mensaje}\n\n"
                    f"Usuario: {resultado.usuario.username}\n"
                    f"Email: {resultado.usuario.email}"
                )

                # Cerrar dialog
                self.accept()

            else:
                # ✗ Error
                QMessageBox.warning(
                    self,
                    "Error",
                    f"No se pudo crear el usuario:\n\n{resultado.mensaje}"
                )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Error inesperado:\n\n{str(e)}"
            )

        finally:
            # Reabilitar botón
            self.btn_crear.setEnabled(True)
            self.btn_crear.setText("✓ Crear Usuario")

    def obtener_usuario_creado(self):
        """Retorna el usuario creado (si existe)."""
        return self.usuario_creado
