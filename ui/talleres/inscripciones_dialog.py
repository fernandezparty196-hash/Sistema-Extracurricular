from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QFrame, QMenu,
    QMessageBox, QTabWidget, QWidget, QListWidget,
    QListWidgetItem, QLineEdit
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui  import QColor, QFont

from services.taller_service import TallerService
from services.estudiante_service import EstudianteService
from ui.talleres.inscripcion_masiva_dialog import InscripcionMasivaDialog


class InscripcionesDialog(QDialog):
    """
    USO:
        dlg = InscripcionesDialog(taller_id=5, sesion=sesion_usuario, parent=self)
        dlg.exec()
    """

    COLUMNAS = [
        (0, "Nombre",      200),
        (1, "DNI",         100),
        (2, "Código",      100),
        (3, "Carrera",     180),
        (4, "Ciclo",        70),
        (5, "Estado",       80),
    ]

    def __init__(self, taller_id: int, sesion, parent=None):
        super().__init__(parent)
        self.taller_id  = taller_id
        self.sesion     = sesion
        self._datos_activos = []
        self._datos_retirados = []

        self.setModal(True)
        self.setMinimumSize(920, 520)
        self.setWindowTitle("Gestión de inscripciones")
        self.setWindowFlags(
            self.windowFlags() &
            ~Qt.WindowType.WindowContextHelpButtonHint
        )

        self._construir_ui()
        self._cargar_datos()

    # ──────────────────────────────────────────────────────────────
    def _construir_ui(self):
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(22, 18, 22, 18)
        raiz.setSpacing(0)

        # Título
        self.lbl_titulo = QLabel("Inscritos en el taller")
        self.lbl_titulo.setObjectName("lbl_titulo_dialogo")
        f = QFont(); f.setPointSize(16); f.setWeight(QFont.Weight.Medium)
        self.lbl_titulo.setFont(f)
        raiz.addWidget(self.lbl_titulo)
        raiz.addSpacing(8)

        self.lbl_cupo = QLabel("")
        self.lbl_cupo.setObjectName("lbl_cupo_info")
        raiz.addWidget(self.lbl_cupo)
        raiz.addSpacing(12)

        # Pestañas
        self.tab_inscripciones = QTabWidget()
        self.tab_inscripciones.setObjectName("tab_inscripciones")

        self.tbl_activos = self._construir_tabla()
        self.tbl_activos.setObjectName("tbl_activos")
        self.tab_inscripciones.addTab(self.tbl_activos, "✓  Activos")

        self.tbl_retirados = self._construir_tabla()
        self.tbl_retirados.setObjectName("tbl_retirados")
        self.tab_inscripciones.addTab(self.tbl_retirados, "↺  Retirados")

        raiz.addWidget(self.tab_inscripciones, 1)

        raiz.addSpacing(12)

        # Botones
        pie = QHBoxLayout()

        self.btn_inscribir = QPushButton("+ Inscribir estudiante")
        self.btn_inscribir.setObjectName("btn_inscribir")
        self.btn_inscribir.setFixedHeight(34)
        self.btn_inscribir.clicked.connect(self._abrir_dialogo_inscribir)
        pie.addWidget(self.btn_inscribir)

        pie.addSpacing(6)

        self.btn_inscripcion_masiva = QPushButton("📥 Importar desde Excel")
        self.btn_inscripcion_masiva.setObjectName("btn_inscripcion_masiva")
        self.btn_inscripcion_masiva.setFixedHeight(34)
        self.btn_inscripcion_masiva.clicked.connect(self._abrir_dialogo_inscripcion_masiva)
        pie.addWidget(self.btn_inscripcion_masiva)

        pie.addSpacing(6)

        self.btn_retirar = QPushButton("Retirar")
        self.btn_retirar.setObjectName("btn_retirar")
        self.btn_retirar.setFixedHeight(34)
        self.btn_retirar.setEnabled(False)
        self.btn_retirar.clicked.connect(self._retirar_seleccionado)
        pie.addWidget(self.btn_retirar)

        pie.addSpacing(6)

        self.btn_reactivar = QPushButton("Reactivar")
        self.btn_reactivar.setObjectName("btn_reactivar")
        self.btn_reactivar.setFixedHeight(34)
        self.btn_reactivar.setEnabled(False)
        self.btn_reactivar.clicked.connect(self._reactivar_seleccionado)
        pie.addWidget(self.btn_reactivar)

        pie.addStretch()

        self.btn_cerrar = QPushButton("Cerrar")
        self.btn_cerrar.setObjectName("btn_cerrar")
        self.btn_cerrar.setFixedSize(100, 34)
        self.btn_cerrar.clicked.connect(self.accept)
        pie.addWidget(self.btn_cerrar)

        raiz.addLayout(pie)

        # Conectar cambios de pestaña
        self.tab_inscripciones.currentChanged.connect(
            self._on_tab_cambio)
        self.tbl_activos.itemSelectionChanged.connect(
            lambda: self.btn_retirar.setEnabled(bool(self.tbl_activos.selectedItems())))
        self.tbl_retirados.itemSelectionChanged.connect(
            lambda: self.btn_reactivar.setEnabled(bool(self.tbl_retirados.selectedItems())))

    def _construir_tabla(self) -> QTableWidget:
        tbl = QTableWidget()
        tbl.setColumnCount(len(self.COLUMNAS))
        tbl.setHorizontalHeaderLabels([c[1] for c in self.COLUMNAS])
        tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        tbl.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tbl.setAlternatingRowColors(True)
        tbl.setShowGrid(False)
        tbl.setSortingEnabled(True)
        tbl.verticalHeader().setVisible(False)
        tbl.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        tbl.customContextMenuRequested.connect(self._menu_contextual)

        for idx, _, ancho in self.COLUMNAS:
            tbl.setColumnWidth(idx, ancho)
        tbl.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        tbl.verticalHeader().setDefaultSectionSize(36)
        return tbl

    # ──────────────────────────────────────────────────────────────
    def _cargar_datos(self):
        """Carga datos del taller e inscripciones."""
        t_datos = TallerService.obtener_por_id(self.taller_id)
        if not t_datos:
            self.lbl_titulo.setText("Taller no encontrado")
            return

        self.lbl_titulo.setText(f"Inscritos — {t_datos['nombre']}")
        self.lbl_cupo.setText(
            f"<b>Cupo:</b> {t_datos['total_inscritos']}/{t_datos['cupo_maximo']} "
            f"inscritos "
            f"({t_datos['cupo_disponible']} disponibles)"
        )

        # Cargar inscritos activos
        self._datos_activos = [
            i for i in TallerService.listar_inscritos(
                self.taller_id, solo_activos=False
            ) if i["estado"] == "Activo"
        ]
        self._poblar_tabla(self.tbl_activos, self._datos_activos)

        # Cargar retirados
        self._datos_retirados = [
            i for i in TallerService.listar_inscritos(
                self.taller_id, solo_activos=False
            ) if i["estado"] == "Retirado"
        ]
        self._poblar_tabla(self.tbl_retirados, self._datos_retirados)

    def _poblar_tabla(self, tbl: QTableWidget, datos: list[dict]):
        tbl.setSortingEnabled(False)
        tbl.setRowCount(len(datos))

        for fila, est in enumerate(datos):
            valores = [
                est["nombre_completo"],
                est["dni"],
                est["codigo"],
                est["carrera"],
                est["ciclo"],
                est["estado"],
            ]

            for col, val in enumerate(valores):
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter |
                                      Qt.AlignmentFlag.AlignLeft)

                if col in (1, 2, 4, 5):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole,
                                est["estudiante_id"])

                if col == 5:
                    if val == "Activo":
                        item.setForeground(QColor("#1D9E75"))
                        item.setBackground(QColor("#E8F8F2"))
                    else:
                        item.setForeground(QColor("#73726c"))
                        item.setBackground(QColor("#f0eee8"))

                tbl.setItem(fila, col, item)

        tbl.setSortingEnabled(True)

    # ──────────────────────────────────────────────────────────────
    def _on_tab_cambio(self):
        """Maneja el cambio de pestaña."""
        self.btn_retirar.setEnabled(False)
        self.btn_reactivar.setEnabled(False)

    def _estudiante_id_seleccionado(self) -> int | None:
        tbl_actual = (self.tbl_activos if
                      self.tab_inscripciones.currentIndex() == 0
                      else self.tbl_retirados)
        fila = tbl_actual.currentRow()
        if fila < 0:
            return None
        item = tbl_actual.item(fila, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    # ──────────────────────────────────────────────────────────────
    def _abrir_dialogo_inscribir(self):
        """Abre un diálogo para buscar e inscribir un estudiante."""
        dlg = _BuscadorEstudiantesDialog(
            taller_id=self.taller_id,
            sesion=self.sesion,
            parent=self
        )
        if dlg.exec():
            self._cargar_datos()
            self.tab_inscripciones.setCurrentIndex(0)

    def _abrir_dialogo_inscripcion_masiva(self):
        """Abre el diálogo de inscripción masiva desde Excel."""
        dlg = InscripcionMasivaDialog(
            taller_id=self.taller_id,
            sesion=self.sesion,
            parent=self
        )
        if dlg.exec():
            self._cargar_datos()
            self.tab_inscripciones.setCurrentIndex(0)

    def _retirar_seleccionado(self):
        """Retira el estudiante seleccionado."""
        est_id = self._estudiante_id_seleccionado()
        if not est_id:
            return

        fila = self.tbl_activos.currentRow()
        nombre = self.tbl_activos.item(fila, 0).text()

        r = QMessageBox.question(self, "Confirmar",
            f"¿Retirar a '{nombre}' del taller?\n"
            f"El registro se conservará en el historial.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if r == QMessageBox.StandardButton.Yes:
            res = TallerService.retirar(
                self.taller_id, est_id, self.sesion.usuario_id)
            if res.ok:
                self._cargar_datos()
                QMessageBox.information(self, "Éxito", res.mensaje)
            else:
                QMessageBox.warning(self, "Error", res.mensaje)

    def _reactivar_seleccionado(self):
        """Reactiva la inscripción de un estudiante retirado."""
        est_id = self._estudiante_id_seleccionado()
        if not est_id:
            return

        fila = self.tbl_retirados.currentRow()
        nombre = self.tbl_retirados.item(fila, 0).text()

        r = QMessageBox.question(self, "Confirmar",
            f"¿Reactivar inscripción de '{nombre}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if r == QMessageBox.StandardButton.Yes:
            res = TallerService.inscribir(
                self.taller_id, est_id, self.sesion.usuario_id)
            if res.ok:
                self._cargar_datos()
                self.tab_inscripciones.setCurrentIndex(0)
                QMessageBox.information(self, "Éxito", res.mensaje)
            else:
                QMessageBox.warning(self, "Error", res.mensaje)

    def _menu_contextual(self, pos):
        est_id = self._estudiante_id_seleccionado()
        if not est_id:
            return
        menu = QMenu(self)
        if self.tab_inscripciones.currentIndex() == 0:
            menu.addAction("Retirar", self._retirar_seleccionado)
        else:
            menu.addAction("Reactivar", self._reactivar_seleccionado)
        menu.exec(self.sender().mapToGlobal(pos))


# ══════════════════════════════════════════════════════════════
# DIÁLOGO DE BÚSQUEDA DE ESTUDIANTES
# ══════════════════════════════════════════════════════════════
class _BuscadorEstudiantesDialog(QDialog):
    """Diálogo para buscar e inscribir un estudiante."""

    def __init__(self, taller_id: int, sesion, parent=None):
        super().__init__(parent)
        self.taller_id = taller_id
        self.sesion    = sesion
        self._resultados = []
        self._timer = QTimer(singleShot=True, interval=300)
        self._timer.timeout.connect(self._ejecutar_busqueda)

        self.setModal(True)
        self.setMinimumSize(600, 400)
        self.setWindowTitle("Buscar estudiante")
        self.setWindowFlags(
            self.windowFlags() &
            ~Qt.WindowType.WindowContextHelpButtonHint
        )
        self._construir_ui()

    def _construir_ui(self):
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(18, 16, 18, 16)

        lbl = QLabel("Buscar estudiante para inscribir")
        f = QFont(); f.setPointSize(13); f.setWeight(QFont.Weight.Medium)
        lbl.setFont(f)
        raiz.addWidget(lbl)
        raiz.addSpacing(10)

        # Búsqueda
        self.inp_buscar = QLineEdit()
        self.inp_buscar.setObjectName("inp_buscar")
        self.inp_buscar.setPlaceholderText("Nombre, DNI o código…")
        self.inp_buscar.setFixedHeight(36)
        self.inp_buscar.textChanged.connect(self._timer.start)
        raiz.addWidget(self.inp_buscar)

        raiz.addSpacing(10)

        # Lista de resultados
        self.lst_resultados = QListWidget()
        self.lst_resultados.setObjectName("lst_resultados")
        self.lst_resultados.itemDoubleClicked.connect(self._inscribir_seleccionado)
        raiz.addWidget(self.lst_resultados, 1)

        raiz.addSpacing(10)

        # Botones
        pie = QHBoxLayout()
        pie.addStretch()

        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setFixedSize(100, 34)
        btn_cancelar.clicked.connect(self.reject)
        pie.addWidget(btn_cancelar)

        pie.addSpacing(8)

        self.btn_inscribir = QPushButton("Inscribir")
        self.btn_inscribir.setFixedSize(100, 34)
        self.btn_inscribir.setEnabled(False)
        self.btn_inscribir.clicked.connect(self._inscribir_seleccionado)
        self.lst_resultados.itemSelectionChanged.connect(
            lambda: self.btn_inscribir.setEnabled(
                bool(self.lst_resultados.selectedItems())))
        pie.addWidget(self.btn_inscribir)

        raiz.addLayout(pie)

    def _ejecutar_busqueda(self):
        texto = self.inp_buscar.text().strip()
        if len(texto) < 2:
            self.lst_resultados.clear()
            return

        # Buscar estudiantes activos no inscritos
        todos = EstudianteService.buscar(texto)
        inscritos_ids = {
            i["estudiante_id"]
            for i in TallerService.listar_inscritos(self.taller_id)
        }

        self._resultados = [
            e for e in todos
            if e["estado"] == "Activo" and e["id"] not in inscritos_ids
        ]

        self.lst_resultados.clear()
        for est in self._resultados:
            item = QListWidgetItem()
            item.setText(
                f"{est['nombre_completo']} "
                f"({est['dni']}) — {est['carrera']}"
            )
            item.setData(Qt.ItemDataRole.UserRole, est["id"])
            self.lst_resultados.addItem(item)

    def _inscribir_seleccionado(self):
        items = self.lst_resultados.selectedItems()
        if not items:
            return

        est_id = items[0].data(Qt.ItemDataRole.UserRole)
        res = TallerService.inscribir(
            self.taller_id, est_id, self.sesion.usuario_id)

        if res.ok:
            QMessageBox.information(self, "Éxito", res.mensaje)
            self.accept()
        else:
            QMessageBox.warning(self, "Error", res.mensaje)
