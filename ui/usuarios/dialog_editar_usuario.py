"""
ui/usuarios/dialog_editar_usuario.py

Diálogo para editar usuarios del sistema.
"""

from PySide6.QtWidgets import (QCheckBox,QComboBox,QDialog,QFrame,QGridLayout,
    QHBoxLayout,QLabel,QLineEdit,QMessageBox,QPushButton,QVBoxLayout,)

from services.usuario_service import UsuarioService
from services.auth_service import SesionUsuario
from ui.usuarios.dialog_reset_password_admin import DialogResetPasswordAdmin


class DialogEditarUsuario(QDialog):
    """Permite editar la información de un usuario."""

    def __init__(
        self,
        usuario_id: int,
        sesion_usuario: SesionUsuario,
        parent=None,
    ):
        super().__init__(parent)

        self.usuario_id = usuario_id
        self.sesion_usuario = sesion_usuario
        self.usuario = None

        self._configurar_ventana()
        self._construir_ui()
        self._cargar_roles()
        self._cargar_usuario()

    # ==========================================================
    # CONFIGURACIÓN
    # ==========================================================

    def _configurar_ventana(self):

        self.setWindowTitle("Editar usuario")
        self.setMinimumWidth(500)
        self.setModal(True)

    # ==========================================================
    # INTERFAZ
    # ==========================================================

    def _construir_ui(self):

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        lbl_titulo = QLabel("Editar usuario")
        lbl_titulo.setObjectName("titulo")

        lbl_subtitulo = QLabel(
            "Actualice la información del usuario."
        )
        lbl_subtitulo.setObjectName("subtitulo")

        layout.addWidget(lbl_titulo)
        layout.addWidget(lbl_subtitulo)

        linea = QFrame()
        linea.setObjectName("separador")
        layout.addWidget(linea)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)

        # Nombres

        grid.addWidget(QLabel("Nombres"), 0, 0)

        self.inp_nombres = QLineEdit()
        grid.addWidget(self.inp_nombres, 1, 0)

        # Apellidos

        grid.addWidget(QLabel("Apellidos"), 0, 1)

        self.inp_apellidos = QLineEdit()
        grid.addWidget(self.inp_apellidos, 1, 1)

        # Usuario

        grid.addWidget(QLabel("Usuario"), 2, 0, 1, 2)

        self.inp_username = QLineEdit()
        self.inp_username.setReadOnly(True)

        grid.addWidget(self.inp_username, 3, 0, 1, 2)

        # Email

        grid.addWidget(QLabel("Correo electrónico"), 4, 0, 1, 2)

        self.inp_email = QLineEdit()
        grid.addWidget(self.inp_email, 5, 0, 1, 2)

        # Rol

        grid.addWidget(QLabel("Rol"), 6, 0, 1, 2)

        self.cmb_rol = QComboBox()
        grid.addWidget(self.cmb_rol, 7, 0, 1, 2)

        # Estado

        self.chk_activo = QCheckBox("Usuario activo")
        grid.addWidget(self.chk_activo, 8, 0, 1, 2)

        layout.addLayout(grid)

        linea2 = QFrame()
        linea2.setObjectName("separador")
        layout.addWidget(linea2)

        self.btn_password = QPushButton("🔑 Restablecer contraseña")
        self.btn_password.setObjectName("btnPassword")
        self.btn_password.clicked.connect(self._restablecer_password)

        layout.addWidget(self.btn_password)

        botones = QHBoxLayout()
        botones.addStretch()

        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_cancelar.setObjectName("btnCancelar")
        self.btn_cancelar.clicked.connect(self.reject)

        self.btn_guardar = QPushButton("Guardar cambios")
        self.btn_guardar.clicked.connect(self._guardar)

        botones.addWidget(self.btn_cancelar)
        botones.addWidget(self.btn_guardar)

        layout.addLayout(botones)

    # ==========================================================
    # CARGA DE DATOS
    # ==========================================================

    def _cargar_roles(self):
        """Carga los roles disponibles."""

        self.cmb_rol.clear()
        self.cmb_rol.addItem("Administrador", 1)
        self.cmb_rol.addItem("Docente", 2)
        self.cmb_rol.addItem("Operador", 3)

    def _cargar_usuario(self):
        """Obtiene la información del usuario."""

        resultado = UsuarioService.obtener_por_id(self.usuario_id)

        if not resultado.ok:
            QMessageBox.warning(self, "Error", resultado.mensaje)
            self.reject()
            return

        self.usuario = resultado.datos

        self.inp_nombres.setText(self.usuario["nombres"])
        self.inp_apellidos.setText(self.usuario["apellidos"])
        self.inp_username.setText(self.usuario["username"])
        self.inp_email.setText(self.usuario["email"])

        indice = self.cmb_rol.findData(self.usuario["rol_id"])
        if indice >= 0:
            self.cmb_rol.setCurrentIndex(indice)

        self.chk_activo.setChecked(self.usuario["activo"])

    # ==========================================================
    # VALIDACIONES
    # ==========================================================

    def _validar(self) -> tuple[bool, str]:

        nombres = self.inp_nombres.text().strip()

        if not nombres:
            return False, "Debe ingresar los nombres."

        if len(nombres) < 2:
            return False, "Los nombres deben tener al menos 2 caracteres."

        apellidos = self.inp_apellidos.text().strip()

        if not apellidos:
            return False, "Debe ingresar los apellidos."

        if len(apellidos) < 2:
            return False, "Los apellidos deben tener al menos 2 caracteres."

        email = self.inp_email.text().strip()

        if not email:
            return False, "Debe ingresar un correo electrónico."

        if "@" not in email or "." not in email.split("@")[-1]:
            return False, "Correo electrónico inválido."

        if self.cmb_rol.currentData() is None:
            return False, "Debe seleccionar un rol."

        return True, ""

    # ==========================================================
    # GUARDAR CAMBIOS
    # ==========================================================

    def _guardar(self):

        valido, mensaje = self._validar()

        if not valido:
            QMessageBox.warning(self, "Validación", mensaje)
            return

        self.btn_guardar.setEnabled(False)
        self.btn_guardar.setText("Guardando...")

        try:

            resultado = UsuarioService.actualizar(

                usuario_id=self.usuario_id,

                nombres=self.inp_nombres.text().strip(),

                apellidos=self.inp_apellidos.text().strip(),

                email=self.inp_email.text().strip(),

                rol_id=self.cmb_rol.currentData(),

                activo=self.chk_activo.isChecked(),

                usuario_editor_id=self.sesion_usuario.usuario_id
            )

            if resultado.ok:

                QMessageBox.information(
                    self,
                    "Usuario actualizado",
                    resultado.mensaje
                )

                self.accept()

            else:

                QMessageBox.warning(
                    self,
                    "Error",
                    resultado.mensaje
                )

        except Exception as e:

            QMessageBox.critical(
                self,
                "Error",
                str(e)
            )

        finally:

            self.btn_guardar.setEnabled(True)
            self.btn_guardar.setText("Guardar cambios")

    # ==========================================================
    # RESTABLECER CONTRASEÑA
    # ==========================================================

    def _restablecer_password(self):
        """
        Abre el diálogo para que el administrador
        restablezca la contraseña del usuario.
        """

        dialog = DialogResetPasswordAdmin(
            usuario_id=self.usuario_id,
            sesion=self.sesion_usuario,
            parent=self
        )

        dialog.exec()

    # ==========================================================
    # EVENTOS
    # ==========================================================

    def closeEvent(self, event):
        """Libera referencias antes de cerrar."""

        self.usuario = None
        super().closeEvent(event)

    # ==========================================================
    # GETTERS
    # ==========================================================

    def obtener_usuario(self):
        """Retorna la información cargada del usuario."""
        return self.usuario

    # ==========================================================
    # UTILIDADES
    # ==========================================================

    def _mostrar_error(self, mensaje: str):

        QMessageBox.warning(
            self,
            "Error",
            mensaje
        )

    def _mostrar_exito(self, mensaje: str):

        QMessageBox.information(
            self,
            "Éxito",
            mensaje
        )

    def limpiar(self):
        """
        Limpia el formulario.
        """

        self.inp_nombres.clear()
        self.inp_apellidos.clear()
        self.inp_email.clear()
        self.inp_username.clear()

        self.cmb_rol.setCurrentIndex(0)
        self.chk_activo.setChecked(True)