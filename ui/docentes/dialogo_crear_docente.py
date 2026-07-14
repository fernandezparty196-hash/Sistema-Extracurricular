"""
ui/dialogo_crear_docente.py   ──   Dialog para crear Docente
═════════════════════════════════════════════════════════════════

¿QUÉ HACE?
  Dialog modal para crear un nuevo docente con:
  • Validaciones de campos
  • Opción de vincular con usuario existente
  • Opción de crear usuario nuevo directamente
  • Estilos CSS modernos y compactos
  • Auditoría automática

USO:
  from ui.dialogo_crear_docente import DialogoCrearDocente
  
  dialogo = DialogoCrearDocente(sesion_usuario=self.sesion, parent=self)
  if dialogo.exec():
      docente = dialogo.obtener_docente_creado()
      print(f"✓ Docente creado: {docente.nombre_completo}")
"""

from PySide6.QtCore import Qt, QRegularExpression
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QComboBox, QPushButton, QMessageBox,
    QFrame, QTabWidget, QWidget
)

from services.docente_service import DocenteService
from services.usuario_service import UsuarioService
from services.auth_service import SesionUsuario


class DialogoCrearDocente(QDialog):
    """
    Dialog para crear un nuevo docente.
    
    FLUJO:
      1. Rellena datos del docente
      2. Elige: usuario existente o crear nuevo
      3. Click "Crear"
      4. Guarda en BD
      5. Dialog se cierra
    """

    def __init__(self, sesion_usuario: SesionUsuario, parent=None):
        super().__init__(parent)
        self.sesion_usuario = sesion_usuario
        self.docente_creado = None

        self._configurar_ventana()
        self._construir_ui()
        self._cargar_usuarios_existentes()

    def _configurar_ventana(self) -> None:
        """Configura el dialog."""
        self.setWindowTitle("Crear Nuevo Docente")
        self.setMinimumSize(480, 420)
        self.setModal(True)

    def _construir_ui(self) -> None:
        """Construye la interfaz."""
        raiz = QVBoxLayout()
        raiz.setSpacing(8)
        raiz.setContentsMargins(15, 15, 15, 15)

        # ── TÍTULO ───────────────────────────────────────────────
        titulo = QLabel("Crear Nuevo Docente")
        titulo.setObjectName("titulo")
        raiz.addWidget(titulo)

        subtitulo = QLabel("Completa los datos del docente")
        subtitulo.setObjectName("subtitulo")
        raiz.addWidget(subtitulo)

        # ── SEPARADOR ────────────────────────────────────────────
        sep = QFrame()
        sep.setObjectName("separador")
        raiz.addWidget(sep)

        # ── DATOS DEL DOCENTE ────────────────────────────────────
        grid = QGridLayout()
        grid.setSpacing(8)

        # DNI
        grid.addWidget(QLabel("DNI *"), 0, 0)
        self.inp_dni = QLineEdit()
        self.inp_dni.setPlaceholderText("1234567")
        self.inp_dni.setValidator(QRegularExpressionValidator(QRegularExpression(r"[0-9]{6,20}")))
        grid.addWidget(self.inp_dni, 0, 1)

        # Nombres
        grid.addWidget(QLabel("Nombres *"), 1, 0)
        self.inp_nombres = QLineEdit()
        self.inp_nombres.setPlaceholderText("Juan")
        grid.addWidget(self.inp_nombres, 1, 1)

        # Apellidos
        grid.addWidget(QLabel("Apellidos *"), 2, 0)
        self.inp_apellidos = QLineEdit()
        self.inp_apellidos.setPlaceholderText("García")
        grid.addWidget(self.inp_apellidos, 2, 1)

        # Especialidad
        grid.addWidget(QLabel("Especialidad"), 3, 0)
        self.inp_especialidad = QLineEdit()
        self.inp_especialidad.setPlaceholderText("Ej: Sistemas, Contabilidad")
        grid.addWidget(self.inp_especialidad, 3, 1)

        # Email institucional
        grid.addWidget(QLabel("Email"), 4, 0)
        self.inp_email = QLineEdit()
        self.inp_email.setPlaceholderText("usuario@unab.edu.pe")
        grid.addWidget(self.inp_email, 4, 1)

        # Teléfono
        grid.addWidget(QLabel("Teléfono"), 5, 0)
        self.inp_telefono = QLineEdit()
        self.inp_telefono.setPlaceholderText("+51 999 000 000")
        grid.addWidget(self.inp_telefono, 5, 1)

        raiz.addLayout(grid)

        # ── PESTAÑA: USUARIO ─────────────────────────────────────
        sep2 = QFrame()
        sep2.setObjectName("separador")
        raiz.addWidget(sep2)

        self.tabs = QTabWidget()

        # TAB 1: Usuario existente
        tab1 = QWidget()
        layout1 = QVBoxLayout()
        layout1.setSpacing(8)

        layout1.addWidget(QLabel("Selecciona un usuario existente"))
        self.cmb_usuario = QComboBox()
        self.cmb_usuario.addItem("— Sin usuario —", None)
        layout1.addWidget(self.cmb_usuario)

        layout1.addWidget(QLabel("O crea uno nuevo desde el diálogo de usuarios"))
        layout1.addStretch()

        tab1.setLayout(layout1)
        self.tabs.addTab(tab1, "Usuario Existente")

        raiz.addWidget(self.tabs)

        # ── BOTONES ──────────────────────────────────────────────
        sep3 = QFrame()
        sep3.setObjectName("separador")
        raiz.addWidget(sep3)

        botones = QHBoxLayout()
        botones.setSpacing(8)
        botones.addStretch()

        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_cancelar.setObjectName("btnCancelar")
        self.btn_cancelar.setFixedSize(90, 32)
        self.btn_cancelar.clicked.connect(self.reject)
        botones.addWidget(self.btn_cancelar)

        self.btn_crear = QPushButton("✓ Crear Docente")
        self.btn_crear.setFixedSize(130, 32)
        self.btn_crear.clicked.connect(self._crear_docente)
        botones.addWidget(self.btn_crear)

        raiz.addLayout(botones)
        self.setLayout(raiz)

    def _cargar_usuarios_existentes(self) -> None:
        """Carga la lista de usuarios sin docente asignado."""
        resultado = UsuarioService.listar(activos_solo=True)

        if resultado.ok and resultado.lista:
            for usuario in resultado.lista:
                self.cmb_usuario.addItem(
                    f"{usuario['nombre']} ({usuario['username']})",
                    usuario['id']
                )

    def _validar_datos(self) -> tuple[bool, str]:
        """Valida los datos del formulario."""

        # DNI
        dni = self.inp_dni.text().strip()
        if not dni:
            return False, "El DNI es obligatorio."
        if len(dni) < 6:
            return False, "El DNI debe tener al menos 6 caracteres."

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

        # Email (validación si se proporciona)
        email = self.inp_email.text().strip()
        if email and ("@" not in email or "." not in email.split("@")[-1]):
            return False, "El formato del email no es válido."

        return True, "Datos válidos"

    def _crear_docente(self) -> None:
        """Crea el docente en la BD."""

        # Validar
        valido, mensaje = self._validar_datos()
        if not valido:
            QMessageBox.warning(self, "Validación", mensaje)
            return

        self.btn_crear.setEnabled(False)
        self.btn_crear.setText("Creando...")

        try:
            resultado = DocenteService.crear(
                dni=self.inp_dni.text().strip(),
                nombres=self.inp_nombres.text().strip(),
                apellidos=self.inp_apellidos.text().strip(),
                especialidad=self.inp_especialidad.text().strip() or None,
                email_institucional=self.inp_email.text().strip() or None,
                telefono=self.inp_telefono.text().strip() or None,
                usuario_id=self.cmb_usuario.currentData(),
                usuario_creador_id=self.sesion_usuario.usuario_id
            )

            if resultado.ok:
                self.docente_creado = resultado.docente

                usuario_info = ""
                if resultado.docente.usuario:
                    usuario_info = f"\nUsuario: {resultado.docente.usuario.username}"

                QMessageBox.information(
                    self,
                    "Éxito",
                    f"✓ {resultado.mensaje}\n\n"
                    f"DNI: {resultado.docente.dni}\n"
                    f"Nombre: {resultado.docente.nombre_completo}"
                    f"{usuario_info}"
                )
                self.accept()

            else:
                QMessageBox.warning(self, "Error", resultado.mensaje)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error inesperado: {str(e)}")

        finally:
            self.btn_crear.setEnabled(True)
            self.btn_crear.setText("✓ Crear Docente")

    def obtener_docente_creado(self):
        """Retorna el docente creado."""
        return self.docente_creado
