"""
ui/dialogo_editar_docente.py   ──   Dialog para editar Docente
═════════════════════════════════════════════════════════════════

¿QUÉ HACE?
  Dialog modal para editar datos de un docente existente:
  • Carga datos actuales del docente
  • Permite modificar: nombres, apellidos, especialidad, email, teléfono
  • Validaciones completas
  • NO permite cambiar DNI (campo único)
  • Auditoría automática de cambios
  • Detecta cambios reales para no hacer updates innecesarios

USO:
  from ui.dialogo_editar_docente import DialogoEditarDocente
  
  dialogo = DialogoEditarDocente(
      docente_id=5,
      sesion_usuario=self.sesion,
      parent=self
  )
  if dialogo.exec():
      print("Docente actualizado")
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QMessageBox,
    QFrame
)

from services.docente_service import DocenteService
from services.auth_service import SesionUsuario


class DialogoEditarDocente(QDialog):
    """
    Dialog para editar datos de un docente.
    
    FLUJO:
      1. Carga datos del docente
      2. Usuario modifica campos
      3. Click "Guardar cambios"
      4. Valida y guarda en BD
      5. Dialog se cierra
    """

    def __init__(self, docente_id: int, sesion_usuario: SesionUsuario, parent=None):
        super().__init__(parent)
        self.docente_id = docente_id
        self.sesion_usuario = sesion_usuario
        self.docente_original = None

        self._configurar_ventana()
        self._cargar_docente()
        self._construir_ui()

    def _configurar_ventana(self) -> None:
        """Configura el dialog."""
        self.setWindowTitle("Editar Docente")
        self.setMinimumSize(450, 380)
        self.setModal(True)

    def _cargar_docente(self) -> None:
        """Carga los datos del docente."""
        resultado = DocenteService.obtener_por_id(self.docente_id)

        if not resultado.ok:
            QMessageBox.critical(self, "Error", resultado.mensaje)
            self.reject()
            return

        self.docente_original = resultado.datos

    def _construir_ui(self) -> None:
        """Construye la interfaz."""
        if not self.docente_original:
            return

        raiz = QVBoxLayout()
        raiz.setSpacing(8)
        raiz.setContentsMargins(15, 15, 15, 15)

        # ── TÍTULO ───────────────────────────────────────────────
        titulo = QLabel("Editar Docente")
        titulo.setObjectName("titulo")
        raiz.addWidget(titulo)

        nombre_original = self.docente_original.get("nombre_completo", "")
        subtitulo = QLabel(f"Actualizando: {nombre_original}")
        subtitulo.setObjectName("subtitulo")
        raiz.addWidget(subtitulo)

        # ── SEPARADOR ────────────────────────────────────────────
        sep = QFrame()
        sep.setObjectName("separador")
        raiz.addWidget(sep)

        # ── FORMULARIO ───────────────────────────────────────────
        grid = QGridLayout()
        grid.setSpacing(8)

        # DNI (no editable)
        grid.addWidget(QLabel("DNI"), 0, 0)
        inp_dni = QLineEdit()
        inp_dni.setText(self.docente_original.get("dni", ""))
        inp_dni.setEnabled(False)
        inp_dni.setStyleSheet("""
            QLineEdit {
                background-color: #f0f0f0;
                color: #999;
            }
        """)
        grid.addWidget(inp_dni, 0, 1)

        # Nombres
        grid.addWidget(QLabel("Nombres *"), 1, 0)
        self.inp_nombres = QLineEdit()
        self.inp_nombres.setText(self.docente_original.get("nombres", ""))
        grid.addWidget(self.inp_nombres, 1, 1)

        # Apellidos
        grid.addWidget(QLabel("Apellidos *"), 2, 0)
        self.inp_apellidos = QLineEdit()
        self.inp_apellidos.setText(self.docente_original.get("apellidos", ""))
        grid.addWidget(self.inp_apellidos, 2, 1)

        # Especialidad
        grid.addWidget(QLabel("Especialidad"), 3, 0)
        self.inp_especialidad = QLineEdit()
        self.inp_especialidad.setText(self.docente_original.get("especialidad", "") or "")
        grid.addWidget(self.inp_especialidad, 3, 1)

        # Email
        grid.addWidget(QLabel("Email"), 4, 0)
        self.inp_email = QLineEdit()
        self.inp_email.setText(self.docente_original.get("email_institucional", "") or "")
        grid.addWidget(self.inp_email, 4, 1)

        # Teléfono
        grid.addWidget(QLabel("Teléfono"), 5, 0)
        self.inp_telefono = QLineEdit()
        self.inp_telefono.setText(self.docente_original.get("telefono", "") or "")
        grid.addWidget(self.inp_telefono, 5, 1)

        raiz.addLayout(grid)

        # ── BOTONES ──────────────────────────────────────────────
        sep2 = QFrame()
        sep2.setObjectName("separador")
        raiz.addWidget(sep2)

        botones = QHBoxLayout()
        botones.setSpacing(8)
        botones.addStretch()

        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_cancelar.setObjectName("btnCancelar")
        self.btn_cancelar.setFixedSize(90, 32)
        self.btn_cancelar.clicked.connect(self.reject)
        botones.addWidget(self.btn_cancelar)

        self.btn_guardar = QPushButton("✓ Guardar Cambios")
        self.btn_guardar.setFixedSize(140, 32)
        self.btn_guardar.clicked.connect(self._guardar_cambios)
        botones.addWidget(self.btn_guardar)

        raiz.addLayout(botones)
        self.setLayout(raiz)

    def _validar_datos(self) -> tuple[bool, str]:
        """Valida los datos del formulario."""

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

    def _detectar_cambios(self) -> dict:
        """
        Detecta qué campos cambiaron.
        Retorna dict con solo los campos modificados.
        """
        cambios = {}

        nombres = self.inp_nombres.text().strip()
        if nombres != self.docente_original.get("nombres", ""):
            cambios["nombres"] = nombres

        apellidos = self.inp_apellidos.text().strip()
        if apellidos != self.docente_original.get("apellidos", ""):
            cambios["apellidos"] = apellidos

        especialidad = self.inp_especialidad.text().strip() or None
        original_esp = self.docente_original.get("especialidad") or None
        if especialidad != original_esp:
            cambios["especialidad"] = especialidad

        email = self.inp_email.text().strip() or None
        original_email = self.docente_original.get("email_institucional") or None
        if email != original_email:
            cambios["email_institucional"] = email

        telefono = self.inp_telefono.text().strip() or None
        original_tel = self.docente_original.get("telefono") or None
        if telefono != original_tel:
            cambios["telefono"] = telefono

        return cambios

    def _guardar_cambios(self) -> None:
        """Guarda los cambios en la BD."""

        # Validar
        valido, mensaje = self._validar_datos()
        if not valido:
            QMessageBox.warning(self, "Validación", mensaje)
            return

        # Detectar cambios
        cambios = self._detectar_cambios()

        if not cambios:
            QMessageBox.information(
                self,
                "Sin cambios",
                "No hay cambios que guardar."
            )
            return

        # Confirmar
        campos_modificados = ", ".join(cambios.keys())
        resultado = QMessageBox.question(
            self,
            "Confirmar cambios",
            f"¿Guardar cambios en:\n\n{campos_modificados}?"
        )

        if resultado != QMessageBox.Yes:
            return

        self.btn_guardar.setEnabled(False)
        self.btn_guardar.setText("Guardando...")

        try:
            # Llamar al servicio con solo los cambios
            res = DocenteService.actualizar(
                docente_id=self.docente_id,
                nombres=cambios.get("nombres"),
                apellidos=cambios.get("apellidos"),
                especialidad=cambios.get("especialidad"),
                email_institucional=cambios.get("email_institucional"),
                telefono=cambios.get("telefono"),
                usuario_editor_id=self.sesion_usuario.usuario_id
            )

            if res.ok:
                QMessageBox.information(
                    self,
                    "✓ Éxito",
                    "Docente actualizado correctamente."
                )
                self.accept()

            else:
                QMessageBox.warning(self, "Error", res.mensaje)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error inesperado: {str(e)}")

        finally:
            self.btn_guardar.setEnabled(True)
            self.btn_guardar.setText("✓ Guardar Cambios")
