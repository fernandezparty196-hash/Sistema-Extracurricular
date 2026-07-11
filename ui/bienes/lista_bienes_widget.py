
"""
ui/bienes/lista_bienes_widget.py   ──   EP-06 Gestión de Bienes
═══════════════════════════════════════════════════════════════
Widget para listar, agregar, editar y gestionar bienes patrimoniales.
"""

from PySide6.QtCore import Qt,QTimer
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QMessageBox, QHeaderView,
    QLineEdit, QComboBox, QFrame
)

from services.bienes_service import BienesService
from services.auth_service import SesionUsuario
from .formulario_bien_dialog import FormularioBienDialog


class ListaBienesWidget(QWidget):
    """Widget principal de gestión de bienes patrimoniales."""

    def __init__(self, sesion: SesionUsuario):
        super().__init__()
        self.sesion = sesion
        self.bienes_service = BienesService()
        self.bienes_filtrados = []
        self._timer   = QTimer()    
        self._timer.setSingleShot(True)
        self._timer.setInterval(350) 


        self.setWindowTitle("Lista de bienes")
        self.setWindowFlags(
            self.windowFlags() &
            ~Qt.WindowType.WindowContextHelpButtonHint
        )

        self._construir_ui()
        self._cargar_datos()

    def _construir_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 16)
        layout.setSpacing(0)

        # ── TÍTULO ────────────────────────────────────────────────
        titulo = QLabel("Bienes Patrimoniales")
        font = QFont()
        font.setPointSize(20)
        font.setWeight(QFont.Weight.Bold)
        titulo.setFont(font)
        layout.addWidget(titulo)

        # ── FILTROS ───────────────────────────────────────────────
        layout.addWidget(self._crear_panel_filtros())
        layout.addSpacing(24)

        # ── TABLA ────────────────────────────────────────────────
        self.tabla_bienes = QTableWidget()
        self.tabla_bienes.setColumnCount(6)
        self.tabla_bienes.verticalHeader().setVisible(False)
        self.tabla_bienes.setWordWrap(False)

        header = self.tabla_bienes.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)

        self.tabla_bienes.setHorizontalHeaderLabels([
            "Código", "Descripción", "Categoría", "Estado", "Valor", "Acciones"])
        self.tabla_bienes.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tabla_bienes.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.tabla_bienes, 1)


    def _crear_panel_filtros(self) -> QFrame:
        panel = QFrame()
        layout = QHBoxLayout(panel)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.inp_buscar = QLineEdit()
        self.inp_buscar.setPlaceholderText("🔍 Buscar código o descripción...")
        self.inp_buscar.textChanged.connect(self._filtrar_tabla)
        layout.addWidget(self.inp_buscar, 1)

        layout.addWidget(QLabel("Categoría:"))
        self.cmb_categoria = QComboBox()
        self.cmb_categoria.addItem("Todos", None)
        self.cmb_categoria.addItem("Audio", "Audio")
        self.cmb_categoria.addItem("Vestuario", "Vestuario")
        self.cmb_categoria.addItem("Instrumento musicales", "Instrumento musicales")
        self.cmb_categoria.addItem("Implementos de danza", "Implementos de danza")
        self.cmb_categoria.addItem("Iluminación","Iluminación")
        self.cmb_categoria.currentIndexChanged.connect(self._filtrar_tabla)
        layout.addWidget(self.cmb_categoria)

        layout.addWidget(QLabel("Estado:"))
        self.cmb_estado = QComboBox()
        self.cmb_estado.addItem("Todos", None)
        self.cmb_estado.addItem("Disponible", "Disponible")
        self.cmb_estado.addItem("Asignado", "Asignado")
        self.cmb_estado.addItem("Mantenimiento", "Mantenimiento")
        self.cmb_estado.addItem("De Baja", "DeBaja")
        self.cmb_estado.currentIndexChanged.connect(self._filtrar_tabla)
        layout.addWidget(self.cmb_estado)

        self.btn_agregar = QPushButton("+ Nuevo Bien")
        self.btn_agregar.setMinimumHeight(34)
        self.btn_agregar.clicked.connect(self._abrir_agregar)
        layout.addWidget(self.btn_agregar)
        layout.addSpacing(8)

        self.btn_actualizar = QPushButton("🔄 Actualizar")
        self.btn_actualizar.setMinimumHeight(34)
        self.btn_actualizar.clicked.connect(self._cargar_datos)
        layout.addWidget(self.btn_actualizar)
        layout.addSpacing(8)

        return panel
    
    def _cargar_datos(self) -> None:
        """Carga la lista de bienes."""

        try:
            resultado = self.bienes_service.listar()

            if not resultado.ok:
                QMessageBox.warning(
                    self,
                    "Error al cargar información",
                    resultado.mensaje
                )
                return

            self.bienes_filtrados = resultado.lista or []
            self._mostrar_bienes()

        except Exception:
            QMessageBox.critical(
                self,
                "Error inesperado",
                "No fue posible cargar los bienes patrimoniales.\n"
                "Intente nuevamente o comuníquese con el administrador."
            )

    def _mostrar_bienes(self) -> None:
        self.tabla_bienes.setRowCount(len(self.bienes_filtrados))
        self.tabla_bienes.verticalHeader().setDefaultSectionSize(32)

        for fila, bien in enumerate(self.bienes_filtrados):

            self.tabla_bienes.setItem(fila, 0, QTableWidgetItem(bien["codigo_patrimonial"]))
            self.tabla_bienes.setItem(fila, 1, QTableWidgetItem(bien["descripcion"]))
            self.tabla_bienes.setItem(fila, 2, QTableWidgetItem(bien["categoria"]))

            # Estado con color
            item_estado = QTableWidgetItem(bien["estado"])
            if bien["estado"] == "Disponible":
                item_estado.setBackground(QColor("#d1fae5"))
            elif bien["estado"] == "Asignado":
                item_estado.setBackground(QColor("#fef3c7"))
            elif bien["estado"] == "Mantenimiento":
                item_estado.setBackground(QColor("#fde68a"))
            elif bien["estado"] == "DeBaja":
                item_estado.setBackground(QColor("#fee2e2"))
            item_estado.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tabla_bienes.setItem(fila, 3, item_estado)

            # Valor
            self.tabla_bienes.setItem(fila, 4, QTableWidgetItem(bien["valor"]))

            # Acciones
            btn_widget = QWidget()
            btn_widget.setFixedHeight(40)

            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(2, 2, 2, 2)
            btn_layout.setSpacing(4)
            btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            # Botón Editar
            btn_editar = QPushButton("Editar")
            btn_editar.setFixedSize(40, 24)
            btn_editar.setCursor(Qt.PointingHandCursor)
            btn_editar.setStyleSheet("""
            QPushButton{
                background-color:#2563eb;
                color:white;
                border:none;
                border-radius:4px;
                font-size:10px;
                font-weight:bold;
                padding:0px;
            }
            QPushButton:hover{
                background-color:#1d4ed8;
            }
            """)
            btn_editar.clicked.connect(lambda _, b=bien: self._editar_bien(b))
            btn_layout.addWidget(btn_editar)

            # Botón Dar baja
            btn_eliminar = QPushButton("Baja")
            btn_eliminar.setFixedSize(40, 24)
            btn_eliminar.setCursor(Qt.PointingHandCursor)
            btn_eliminar.setStyleSheet("""
            QPushButton{
                background-color:#dc2626;
                color:white;
                border:none;
                border-radius:4px;
                font-size:10px;
                font-weight:bold;
                padding:0px;
            }
            QPushButton:hover{
                background-color:#b91c1c;
            }
            """)
            btn_eliminar.clicked.connect(lambda _, b=bien: self._dar_de_baja(b))
            btn_layout.addWidget(btn_eliminar)

            self.tabla_bienes.setCellWidget(fila, 5, btn_widget)
            self.tabla_bienes.setRowHeight(fila, 48)

    def _filtrar_tabla(self) -> None:
        """Filtra los bienes."""
        try:
            buscar = self.inp_buscar.text().strip()
            categoria = self.cmb_categoria.currentData()
            estado = self.cmb_estado.currentData()
            resultado = self.bienes_service.listar(
                filtro={
                    "codigo": buscar or None,
                    "descripcion": buscar or None,
                    "categoria": categoria,
                    "estado": estado
                }
            )

            if resultado.ok:
                self.bienes_filtrados = resultado.lista or []
                self._mostrar_bienes()
            else:
                QMessageBox.warning(
                    self,
                    "Búsqueda",
                    resultado.mensaje
                )

        except Exception:
            QMessageBox.critical(
                self,
                "Error",
                "Ocurrió un problema al realizar la búsqueda."
            )

            if resultado.ok:
                self.bienes_filtrados = resultado.lista or []
                self._mostrar_bienes()

    def _abrir_agregar(self) -> None:
        dlg = FormularioBienDialog(sesion=self.sesion,parent=self)
        if dlg.exec():
            self._cargar_datos()

    def _editar_bien(self, bien: dict) -> None:
        dlg = FormularioBienDialog(sesion=self.sesion,bien_id=bien["id"],parent=self)
        if dlg.exec():
            self._cargar_datos()

    def _dar_de_baja(self, bien: dict) -> None:
        respuesta = QMessageBox.question(
            self,
            "Confirmar",
            f"¿Desea dar de baja el bien\n\n{bien['codigo_patrimonial']}?",
            QMessageBox.StandardButton.Yes |
            QMessageBox.StandardButton.No)

        if respuesta != QMessageBox.StandardButton.Yes:
            return

        try:
            resultado = self.bienes_service.cambiar_estado(bien["id"],"DeBaja",self.sesion.usuario_id)

            if resultado.ok:
                QMessageBox.information(self,"Operación realizada",resultado.mensaje)
                self._cargar_datos()
            else:
                QMessageBox.warning(self,"No se pudo completar la operación",resultado.mensaje)

        except Exception:
            QMessageBox.critical(self,"Error inesperado","No fue posible dar de baja el bien.")

