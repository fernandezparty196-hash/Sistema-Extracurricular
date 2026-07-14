"""
ui/panel_gestionar_usuarios.py   ──   Panel completo de gestión de usuarios
═════════════════════════════════════════════════════════════════════════════

¿QUÉ HACE?
  Panel completo para gestionar usuarios:
  • Tabla con lista de usuarios
  • Crear usuario (DialogoCrearUsuario)
  • Editar usuario
  • Desactivar/Activar usuario
  • Desbloquear usuario bloqueado
  • Buscar/filtrar usuarios
  • Refrescar lista

USO:
  from ui.panel_gestionar_usuarios import PanelGestionarUsuarios
  
  panel = PanelGestionarUsuarios(sesion_usuario=self.sesion, parent=self)
  self.setCentralWidget(panel)

INTEGRACIÓN EN MAIN_WINDOW:
  def abrir_gestionar_usuarios(self):
      panel = PanelGestionarUsuarios(self.sesion, parent=self)
      self.setCentralWidget(panel)
"""

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QLineEdit, QComboBox,
    QLabel, QMessageBox, QHeaderView, QFrame,QAbstractItemView
)

from services.usuario_service import UsuarioService
from services.auth_service import SesionUsuario
from ui.usuarios.dialogo_crear_usuario import DialogoCrearUsuario
from ui.usuarios.dialog_editar_usuario import DialogEditarUsuario

class PanelGestionarUsuarios(QWidget):
    """
    Panel completo para gestionar usuarios del sistema.
    Incluye: crear, editar, desactivar, desbloquear, eliminar.
    """

    def __init__(self, sesion_usuario: SesionUsuario, parent=None):
        super().__init__(parent)
        self.sesion_usuario = sesion_usuario
        self.usuario_seleccionado = None

        self._construir_ui()
        self._cargar_usuarios()

    def _construir_ui(self) -> None:
        """Construye la interfaz."""
        layout = QVBoxLayout()
        layout.setSpacing(2)
        layout.setContentsMargins(0,0,0,0)


        # ── BARRA DE HERRAMIENTAS ────────────────────────────────
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setSpacing(10)

        # Crear usuario
        btn_crear = QPushButton("➕ Crear Usuario")
        btn_crear.setMinimumHeight(36)
        btn_crear.clicked.connect(self._abrir_crear_usuario)
        toolbar_layout.addWidget(btn_crear)

        # Refrescar
        btn_refrescar = QPushButton("🔄 Refrescar")
        btn_refrescar.setMinimumHeight(36)
        btn_refrescar.clicked.connect(self._cargar_usuarios)
        toolbar_layout.addWidget(btn_refrescar)

        toolbar_layout.addSpacing(20)

        # Buscar
        toolbar_layout.addWidget(QLabel("Buscar:"))
        self.inp_buscar = QLineEdit()
        self.inp_buscar.setPlaceholderText("Nombre, usuario o email...")
        self.inp_buscar.setMaximumWidth(300)
        self.inp_buscar.setMinimumHeight(36)
        self.inp_buscar.textChanged.connect(self._filtrar_tabla)
        toolbar_layout.addWidget(self.inp_buscar)

        # Filtrar por rol
        toolbar_layout.addWidget(QLabel("Rol:"))
        self.cmb_filtro_rol = QComboBox()
        self.cmb_filtro_rol.setMinimumHeight(36)
        self.cmb_filtro_rol.setMaximumWidth(150)
        self.cmb_filtro_rol.addItem("Todos", None)
        self.cmb_filtro_rol.addItem("Administrador", 1)
        self.cmb_filtro_rol.addItem("Docente", 2)
        self.cmb_filtro_rol.addItem("Operador", 3)
        self.cmb_filtro_rol.currentIndexChanged.connect(self._filtrar_tabla)
        toolbar_layout.addWidget(self.cmb_filtro_rol)

        toolbar_layout.addStretch()
        layout.addLayout(toolbar_layout)
        layout.addSpacing(10)
        
        # ── TABLA DE USUARIOS ────────────────────────────────────
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(7)
        self.tabla.setHorizontalHeaderLabels([
            "ID", "Usuario", "Nombre Completo", "Email", "Rol", "Estado", "Acciones"
        ])

        # Configurar ancho de columnas
        header = self.tabla.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # ID
        header.setSectionResizeMode(1, QHeaderView.Stretch)           # Usuario
        header.setSectionResizeMode(2, QHeaderView.Stretch)           # Nombre
        header.setSectionResizeMode(3, QHeaderView.Stretch)           # Email
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Rol
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Estado
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # Acciones

        self.tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setShowGrid(False)
        self.tabla.setSortingEnabled(True)
        self.tabla.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    
        self.tabla.itemSelectionChanged.connect(self._on_seleccionar_usuario)

        layout.addWidget(self.tabla)

        # ── BOTONES DE ACCIÓN ────────────────────────────────────
        acciones_layout = QHBoxLayout()
        acciones_layout.setSpacing(10)

        self.btn_editar = QPushButton("✎ Editar")
        self.btn_editar.setMinimumHeight(36)
        self.btn_editar.setEnabled(False)
        self.btn_editar.clicked.connect(self._editar_usuario)
        acciones_layout.addWidget(self.btn_editar)

        self.btn_desbloquear = QPushButton("🔓 Desbloquear")
        self.btn_desbloquear.setObjectName("btnWarning")
        self.btn_desbloquear.setMinimumHeight(36)
        self.btn_desbloquear.setEnabled(False)
        self.btn_desbloquear.clicked.connect(self._desbloquear_usuario)
        acciones_layout.addWidget(self.btn_desbloquear)

        self.btn_desactivar = QPushButton("⊘ Desactivar")
        self.btn_desactivar.setObjectName("btnWarning")
        self.btn_desactivar.setMinimumHeight(36)
        self.btn_desactivar.setEnabled(False)
        self.btn_desactivar.clicked.connect(self._desactivar_usuario)
        acciones_layout.addWidget(self.btn_desactivar)

        self.btn_eliminar = QPushButton("🗑 Eliminar")
        self.btn_eliminar.setObjectName("btnDanger")
        self.btn_eliminar.setMinimumHeight(36)
        self.btn_eliminar.setEnabled(False)
        self.btn_eliminar.clicked.connect(self._eliminar_usuario)
        acciones_layout.addWidget(self.btn_eliminar)

        acciones_layout.addStretch()
        layout.addLayout(acciones_layout)

        self.setLayout(layout)

    # ══════════════════════════════════════════════════════════════
    # CARGAR Y FILTRAR DATOS
    # ══════════════════════════════════════════════════════════════

    def _cargar_usuarios(self) -> None:
        """Carga la lista de usuarios de la BD."""
        resultado = UsuarioService.listar(activos_solo=False)

        if not resultado.ok:
            QMessageBox.warning(self, "Error", resultado.mensaje)
            return

        self.usuarios_datos = resultado.lista or []
        self._actualizar_tabla()

    def _actualizar_tabla(self) -> None:
        """Actualiza la tabla con los datos cargados."""
        self.tabla.setRowCount(len(self.usuarios_datos))

        for row, usuario in enumerate(self.usuarios_datos):
            # ID
            item = QTableWidgetItem(str(usuario["id"]))
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self.tabla.setItem(row, 0, item)

            # Usuario
            item = QTableWidgetItem(usuario["username"])
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self.tabla.setItem(row, 1, item)

            # Nombre
            item = QTableWidgetItem(usuario["nombre"])
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self.tabla.setItem(row, 2, item)

            # Email
            item = QTableWidgetItem(usuario["email"])
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self.tabla.setItem(row, 3, item)

            # Rol
            item = QTableWidgetItem(usuario["rol"])
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self.tabla.setItem(row, 4, item)

            # Estado
            estado_texto = "✓ Activo" if usuario["activo"] else "⊘ Inactivo"
            item = QTableWidgetItem(estado_texto)
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            if not usuario["activo"]:
                item.setForeground(QColor("#ef4444"))
            self.tabla.setItem(row, 5, item)

            # Acciones (solo info, no editable)
            bloqueado = usuario.get("esta_bloqueado", False)
            acciones_texto = "Bloqueado" if bloqueado else "Normal"
            item = QTableWidgetItem(acciones_texto)
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            if bloqueado:
                item.setForeground(QColor("#f59e0b"))
            self.tabla.setItem(row, 6, item)

    def _filtrar_tabla(self) -> None:
        """Filtra la tabla según búsqueda y rol seleccionado."""
        buscar = self.inp_buscar.text().lower()
        rol_filtro = self.cmb_filtro_rol.currentData()

        self.tabla.setRowCount(len(self.usuarios_datos))

        visible_count = 0
        for row, usuario in enumerate(self.usuarios_datos):
            # Filtrar por búsqueda
            if buscar:
                coincide = (
                    buscar in usuario["username"].lower() or
                    buscar in usuario["nombre"].lower() or
                    buscar in usuario["email"].lower()
                )
                if not coincide:
                    self.tabla.hideRow(row)
                    continue

            # Filtrar por rol
            if rol_filtro and usuario.get("rol") != self.cmb_filtro_rol.currentText():
                # Aquí podrías agregar lógica más sofisticada
                pass

            self.tabla.showRow(row)
            visible_count += 1

    # ══════════════════════════════════════════════════════════════
    # SELECCIÓN Y ACCIONES
    # ══════════════════════════════════════════════════════════════

    def _on_seleccionar_usuario(self) -> None:
        """Se ejecuta cuando selecciona un usuario en la tabla."""
        rows = self.tabla.selectedIndexes()
        if not rows:
            self.usuario_seleccionado = None
            self.btn_editar.setEnabled(False)
            self.btn_desactivar.setEnabled(False)
            self.btn_desbloquear.setEnabled(False)
            self.btn_eliminar.setEnabled(False)
            return

        row = rows[0].row()
        self.usuario_seleccionado = self.usuarios_datos[row]

        # Habilitar botones
        self.btn_editar.setEnabled(True)
        self.btn_desactivar.setEnabled(True)
        self.btn_eliminar.setEnabled(True)

        # Habilitar desbloquear solo si está bloqueado
        if self.usuario_seleccionado.get("esta_bloqueado"):
            self.btn_desbloquear.setEnabled(True)
        else:
            self.btn_desbloquear.setEnabled(False)

    def _abrir_crear_usuario(self) -> None:
        """Abre el dialog para crear usuario."""
        dialogo = DialogoCrearUsuario(
            sesion_usuario=self.sesion_usuario,
            parent=self
        )

        if dialogo.exec():
            # Recargar tabla
            self._cargar_usuarios()
            QMessageBox.information(
                self,
                "Éxito",
                "✓ Usuario creado correctamente."
            )

    def _editar_usuario(self):
        if not self.usuario_seleccionado:
            QMessageBox.warning(
                self,
                "Editar usuario",
                "Seleccione un usuario."
            )
            return

        dialog = DialogEditarUsuario(usuario_id=self.usuario_seleccionado["id"],sesion_usuario=self.sesion_usuario,parent=self)
        if dialog.exec():
            self._cargar_usuarios()

    def _desbloquear_usuario(self) -> None:
        """Desbloquea el usuario seleccionado."""
        if not self.usuario_seleccionado:
            return

        resultado = QMessageBox.question(
            self,
            "Confirmar",
            f"¿Desbloquear usuario '{self.usuario_seleccionado['username']}'?"
        )

        if resultado != QMessageBox.Yes:
            return

        res = UsuarioService.desbloquear(
            usuario_id=self.usuario_seleccionado["id"],
            usuario_editor_id=self.sesion_usuario.usuario_id
        )

        if res.ok:
            QMessageBox.information(self, "Éxito", res.mensaje)
            self._cargar_usuarios()
        else:
            QMessageBox.warning(self, "Error", res.mensaje)

    def _desactivar_usuario(self) -> None:
        """Desactiva el usuario seleccionado."""
        if not self.usuario_seleccionado:
            return

        es_activo = self.usuario_seleccionado.get("activo", True)
        accion = "desactivar" if es_activo else "activar"
        titulo = "Desactivar" if es_activo else "Activar"

        resultado = QMessageBox.question(
            self,
            f"Confirmar {titulo}",
            f"¿{titulo} usuario '{self.usuario_seleccionado['username']}'?"
        )

        if resultado != QMessageBox.Yes:
            return

        if es_activo:
            res = UsuarioService.desactivar(
                usuario_id=self.usuario_seleccionado["id"],
                usuario_editor_id=self.sesion_usuario.usuario_id
            )
        else:
            res = UsuarioService.activar(
                usuario_id=self.usuario_seleccionado["id"],
                usuario_editor_id=self.sesion_usuario.usuario_id
            )

        if res.ok:
            QMessageBox.information(self, "Éxito", res.mensaje)
            self._cargar_usuarios()
        else:
            QMessageBox.warning(self, "Error", res.mensaje)

    def _eliminar_usuario(self) -> None:
        """Elimina el usuario seleccionado (con confirmación)."""
        if not self.usuario_seleccionado:
            return

        # Confirmación con dos pasos
        resultado1 = QMessageBox.warning(
            self,
            "⚠️ Advertencia",
            f"¿Estás seguro de que quieres eliminar a\n'{self.usuario_seleccionado['username']}'?\n\n"
            f"Esta acción NO se puede deshacer.",
            QMessageBox.Yes | QMessageBox.No
        )

        if resultado1 != QMessageBox.Yes:
            return

        # Confirmación final
        resultado2 = QMessageBox.critical(
            self,
            "Confirmar eliminación",
            "Escribe 'CONFIRMAR' para eliminar definitivamente:\n\n"
            f"Usuario: {self.usuario_seleccionado['username']}",
            QMessageBox.Yes | QMessageBox.No
        )

        if resultado2 != QMessageBox.Yes:
            return

        res = UsuarioService.eliminar(
            usuario_id=self.usuario_seleccionado["id"],
            usuario_editor_id=self.sesion_usuario.usuario_id
        )

        if res.ok:
            QMessageBox.information(self, "Éxito", res.mensaje)
            self._cargar_usuarios()
        else:
            QMessageBox.warning(self, "Error", res.mensaje)


