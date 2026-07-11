
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QFrame, QSizePolicy,
    QMenu, QMessageBox, QFileDialog,
)
from PySide6.QtCore    import Qt, QTimer, Signal
from PySide6.QtGui     import QColor, QIcon, QFont

from services.estudiante_service import EstudianteService
from utils.importar_estudiantes        import ExcelImportDialog


class ListaEstudiantesWidget(QWidget):
    solicitar_historial = Signal(int)   # emite estudiante_id

    # Columnas de la tabla (índice, título, ancho)
    COLUMNAS = [
        (0, "#",              45),
        (1, "Apellidos",     160),
        (2, "Nombres",       140),
        (3, "DNI",            90),
        (4, "Código",        110),
        (5, "Carrera",       190),
        (6, "Ciclo",          60),
        (7, "Estado",         90),
    ]

    def __init__(self, sesion, parent=None):
        super().__init__(parent)
        self.sesion   = sesion
        self._datos   = []          # cache de los resultados actuales
        self._timer   = QTimer()    
        self._timer.setSingleShot(True)
        self._timer.setInterval(350)   # ms de espera antes de buscar
        self._timer.timeout.connect(self._ejecutar_busqueda)


        self.setWindowTitle("Lista estudiantes")
        self.setWindowFlags(
            self.windowFlags() &
            ~Qt.WindowType.WindowContextHelpButtonHint
        )

        self._construir_ui()
        self._cargar_combos()
        self._ejecutar_busqueda()   # carga inicial

    # ──────────────────────────────────────────────────────────────
    # CONSTRUCCIÓN DE LA INTERFAZ
    # ──────────────────────────────────────────────────────────────
    def _construir_ui(self):
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(24, 20, 24, 16)
        raiz.setSpacing(0)

        # ── Cabecera: título + botones de acción ──────────────────
        raiz.addLayout(self._cabecera())
        raiz.addSpacing(14)

        # ── Barra de filtros ──────────────────────────────────────
        raiz.addWidget(self._barra_filtros())
        raiz.addSpacing(12)

        # ── Tabla ─────────────────────────────────────────────────
        self.tbl_estudiantes = self._construir_tabla()
        self.tbl_estudiantes.setObjectName("tbl_estudiantes")
        raiz.addWidget(self.tbl_estudiantes, 1)   # stretch = 1

        # ── Pie: conteo + botones contextuales ───────────────────
        raiz.addSpacing(10)
        raiz.addLayout(self._pie())

    # ── Cabecera ─────────────────────────────────────────────────
    def _cabecera(self) -> QHBoxLayout:
        lay = QHBoxLayout()

        lbl = QLabel("Estudiantes")
        lbl.setObjectName("lbl_titulo_modulo")
        font = QFont()
        font.setPointSize(20)
        font.setWeight(QFont.Weight.Bold)
        lbl.setFont(font)
        lay.addWidget(lbl)
        lay.addStretch()

        # Botón importar Excel
        self.btn_importar = QPushButton("↑  Importar Excel")
        self.btn_importar.setObjectName("btn_importar")
        self.btn_importar.setFixedHeight(36)
        self.btn_importar.setToolTip(
            "Importar estudiantes masivamente desde un archivo .xlsx")
        self.btn_importar.clicked.connect(self._abrir_importar)
        lay.addWidget(self.btn_importar)

        lay.addSpacing(8)

        # Botón nuevo estudiante
        self.btn_nuevo = QPushButton("+ Nuevo estudiante")
        self.btn_nuevo.setObjectName("btn_nuevo")
        self.btn_nuevo.setFixedHeight(36)
        self.btn_nuevo.clicked.connect(self._abrir_formulario_nuevo)

        # Solo admin/operador pueden crear
        if self.sesion.rol_nombre == "Docente":
            self.btn_nuevo.setEnabled(False)
            self.btn_nuevo.setToolTip("Sin permiso para crear estudiantes")

        lay.addWidget(self.btn_nuevo)
        return lay

    # ── Barra de filtros ─────────────────────────────────────────
    def _barra_filtros(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("frame_filtros")

        lay = QHBoxLayout(frame)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        # Campo búsqueda
        self.inp_buscar = QLineEdit()
        self.inp_buscar.setObjectName("inp_buscar")
        self.inp_buscar.setPlaceholderText("🔍  Buscar por nombre, DNI o código…")

        # Conecta al timer (debounce) para no buscar en cada tecla
        self.inp_buscar.textChanged.connect(self._timer.start)
        lay.addWidget(self.inp_buscar, 2)

        # Combo carrera
        self.cmb_carrera = QComboBox()
        self.cmb_carrera.setObjectName("cmb_carrera")
        self.cmb_carrera.currentIndexChanged.connect(self._ejecutar_busqueda)
        lay.addWidget(self.cmb_carrera, 2)

        # Combo ciclo
        self.cmb_ciclo = QComboBox()
        self.cmb_ciclo.setObjectName("cmb_ciclo")
        self.cmb_ciclo.addItem("Ciclo", None)
        for c in range(1, 11):
            self.cmb_ciclo.addItem(str(c), c)
        self.cmb_ciclo.currentIndexChanged.connect(self._ejecutar_busqueda)
        lay.addWidget(self.cmb_ciclo)

        # Combo estado
        self.cmb_estado = QComboBox()
        self.cmb_estado.setObjectName("cmb_estado")
        self.cmb_estado.addItem("Estado", None)
        self.cmb_estado.addItem("Activo",   "Activo")
        self.cmb_estado.addItem("Inactivo", "Inactivo")
        self.cmb_estado.addItem("Egresado", "Egresado")
        self.cmb_estado.currentIndexChanged.connect(self._ejecutar_busqueda)
        lay.addWidget(self.cmb_estado)

        # Botón limpiar filtros
        self.btn_limpiar = QPushButton("✕ Limpiar")
        self.btn_limpiar.setObjectName("btn_limpiar")

        self.btn_limpiar.clicked.connect(self._limpiar_filtros)
        lay.addWidget(self.btn_limpiar)

        return frame

    # ── Tabla ────────────────────────────────────────────────────
    def _construir_tabla(self) -> QTableWidget:
        tbl = QTableWidget()
        tbl.setColumnCount(len(self.COLUMNAS))
        tbl.setHorizontalHeaderLabels([c[1] for c in self.COLUMNAS])

        # Comportamiento
        tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        tbl.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tbl.setAlternatingRowColors(True)
        tbl.verticalHeader().setVisible(False)
        tbl.setShowGrid(False)
        tbl.setSortingEnabled(True)
        tbl.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        tbl.customContextMenuRequested.connect(self._menu_contextual)
        tbl.doubleClicked.connect(self._abrir_formulario_editar)

        # Anchos de columna
        for idx, _, ancho in self.COLUMNAS:
            tbl.setColumnWidth(idx, ancho)
        tbl.horizontalHeader().setSectionResizeMode(
            5, QHeaderView.ResizeMode.Stretch   
        )

        # Altura de filas
        tbl.verticalHeader().setDefaultSectionSize(38)

        return tbl

    # ── Pie ──────────────────────────────────────────────────────
    def _pie(self) -> QHBoxLayout:
        lay = QHBoxLayout()

        self.lbl_conteo = QLabel("Cargando…")
        self.lbl_conteo.setObjectName("lbl_conteo")
        lay.addWidget(self.lbl_conteo)
        lay.addStretch()

        # Botón cambiar estado (desactivar / egresar)
        self.btn_cambiar_estado = QPushButton("Cambiar estado")
        self.btn_cambiar_estado.setObjectName("btn_cambiar_estado")
        self.btn_cambiar_estado.setFixedHeight(34)
        self.btn_cambiar_estado.setEnabled(False)
        self.btn_cambiar_estado.clicked.connect(self._cambiar_estado)
        lay.addWidget(self.btn_cambiar_estado)

        lay.addSpacing(6)

        # Botón historial
        self.btn_historial = QPushButton("Historial")
        self.btn_historial.setObjectName("btn_historial")
        self.btn_historial.setFixedHeight(34)
        self.btn_historial.setEnabled(False)
        self.btn_historial.clicked.connect(self._abrir_historial)
        lay.addWidget(self.btn_historial)

        lay.addSpacing(6)

        # Botón editar
        self.btn_editar = QPushButton("✎  Editar")
        self.btn_editar.setObjectName("btn_editar")
        self.btn_editar.setFixedHeight(34)
        self.btn_editar.setEnabled(False)
        self.btn_editar.clicked.connect(self._abrir_formulario_editar)
        lay.addWidget(self.btn_editar)

        # Habilitar botones al seleccionar fila
        self.tbl_estudiantes.itemSelectionChanged.connect(
            self._on_seleccion_cambio
        )

        return lay

    # ──────────────────────────────────────────────────────────────
    # CARGA DE DATOS
    # ──────────────────────────────────────────────────────────────
    def _cargar_combos(self):
        """Rellena el combo de carreras al iniciar."""
        self.cmb_carrera.blockSignals(True)
        self.cmb_carrera.addItem("Todas las carreras", None)
        for c in EstudianteService.listar_carreras():
            self.cmb_carrera.addItem(c["nombre"], c["id"])
        self.cmb_carrera.blockSignals(False)

    def _ejecutar_busqueda(self):
        """Lee los filtros activos y repobla la tabla."""
        texto      = self.inp_buscar.text()
        carrera_id = self.cmb_carrera.currentData()
        ciclo      = self.cmb_ciclo.currentData()
        estado     = self.cmb_estado.currentData()

        self._datos = EstudianteService.buscar(
            texto=texto,
            carrera_id=carrera_id,
            ciclo=ciclo,
            estado=estado,
        )
        self._poblar_tabla(self._datos)

    def _poblar_tabla(self, datos: list[dict]):
        """Llena la QTableWidget con la lista de estudiantes."""
        self.tbl_estudiantes.setSortingEnabled(False)
        self.tbl_estudiantes.setRowCount(len(datos))

        for fila, e in enumerate(datos):
            valores = [
                str(fila + 1),
                e["apellidos"],
                e["nombres"],
                e["dni"],
                e["codigo_estudiantil"],
                e["carrera"],
                str(e["ciclo_actual"] or "—"),
                e["estado"],
            ]

            for col, val in enumerate(valores):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter |
                                      Qt.AlignmentFlag.AlignLeft)

                # Columna estado: color según valor
                if col == 7:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    colores = {
                        "Activo":   ("#1D9E75", "#929695"),
                        "Inactivo": ("#8c7b6e", "#929695"),
                        "Egresado": ("#534AB7", "#929695"),
                    }
                    fg, bg = colores.get(val, ("#333", "#fff"))
                    item.setForeground(QColor(fg))
                    item.setBackground(QColor(bg))
                    font = QFont()
                    font.setPointSize(10)
                    item.setFont(font)

                # Guardar el ID del estudiante en la primera celda
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, e["id"])

                self.tbl_estudiantes.setItem(fila, col, item)

        self.tbl_estudiantes.setSortingEnabled(True)

        # Actualizar contador
        n = len(datos)
        sufijo = "" if n == 1 else "s"
        self.lbl_conteo.setText(f"Mostrando {n} estudiante{sufijo}")

    # ──────────────────────────────────────────────────────────────
    # INTERACCIONES
    # ──────────────────────────────────────────────────────────────
    def _on_seleccion_cambio(self):
        """Habilita o deshabilita los botones según si hay fila seleccionada."""
        hay = bool(self.tbl_estudiantes.selectedItems())
        self.btn_editar.setEnabled(hay)
        self.btn_historial.setEnabled(hay)
        # Cambiar estado solo para admin
        self.btn_cambiar_estado.setEnabled(
            hay and self.sesion.rol_nombre == "Administrador"
        )

    def _estudiante_id_seleccionado(self) -> int | None:
        """Retorna el ID del estudiante de la fila seleccionada."""
        filas = self.tbl_estudiantes.selectedItems()
        if not filas:
            return None
        fila = self.tbl_estudiantes.currentRow()
        item = self.tbl_estudiantes.item(fila, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _limpiar_filtros(self):
        self.inp_buscar.clear()
        self.cmb_carrera.setCurrentIndex(0)
        self.cmb_ciclo.setCurrentIndex(0)
        self.cmb_estado.setCurrentIndex(0)
        self._ejecutar_busqueda()

    # ── Abrir formulario nuevo ────────────────────────────────────
    def _abrir_formulario_nuevo(self):
        from ui.estudiantes.formulario_estudiante import FormularioEstudianteDialog
        dlg = FormularioEstudianteDialog(
            sesion=self.sesion, parent=self
        )
        if dlg.exec():
            self._ejecutar_busqueda()   # refrescar tabla

    # ── Abrir formulario editar ───────────────────────────────────
    def _abrir_formulario_editar(self):
        est_id = self._estudiante_id_seleccionado()
        if not est_id:
            return
        from ui.estudiantes.formulario_estudiante import FormularioEstudianteDialog
        dlg = FormularioEstudianteDialog(
            sesion=self.sesion,
            estudiante_id=est_id,
            parent=self
        )
        if dlg.exec():
            self._ejecutar_busqueda()

    # ── Abrir historial ───────────────────────────────────────────
    def _abrir_historial(self):
        est_id = self._estudiante_id_seleccionado()
        if not est_id:
            return
        from ui.estudiantes.historial_dialog import HistorialDialog
        HistorialDialog(est_id, parent=self).exec()

    # ── Cambiar estado ────────────────────────────────────────────
    def _cambiar_estado(self):
        est_id = self._estudiante_id_seleccionado()
        if not est_id:
            return

        datos = EstudianteService.obtener_por_id(est_id)
        if not datos:
            return

        estado_actual = datos["estado"]
        menu = QMenu(self)

        opciones = [e for e in ("Activo", "Inactivo", "Egresado")
                    if e != estado_actual]
        for opcion in opciones:
            menu.addAction(f"Cambiar a {opcion}",lambda o=opcion: self._confirmar_cambio_estado(est_id, o))

        menu.exec(self.btn_cambiar_estado.mapToGlobal(
            self.btn_cambiar_estado.rect().bottomLeft()
        ))

    def _confirmar_cambio_estado(self, est_id: int, nuevo: str):
        datos = EstudianteService.obtener_por_id(est_id)
        resp  = QMessageBox.question(
            self,
            "Confirmar cambio de estado",
            f"¿Cambiar a '{nuevo}' al estudiante\n"
            f"{datos['nombre_completo'] if datos else est_id}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if resp == QMessageBox.StandardButton.Yes:
            res = EstudianteService.cambiar_estado(
                est_id, nuevo, self.sesion.usuario_id
            )
            if res.ok:
                self._ejecutar_busqueda()
            else:
                QMessageBox.warning(self, "Error", res.mensaje)

    # ── Importar Excel ────────────────────────────────────────────
    def _abrir_importar(self):
        dlg = ExcelImportDialog(sesion=self.sesion, parent=self)
        if dlg.exec():
            self._ejecutar_busqueda()

    # ── Menú contextual (clic derecho en la tabla) ────────────────
    def _menu_contextual(self, pos):
        est_id = self._estudiante_id_seleccionado()
        if not est_id:
            return

        menu = QMenu(self)
        menu.addAction("✎  Editar",    self._abrir_formulario_editar)
        menu.addAction("📋  Historial", self._abrir_historial)
        menu.addSeparator()
        menu.addAction("Cambiar estado", self._cambiar_estado)
        menu.exec(self.tbl_estudiantes.mapToGlobal(pos))

    # ──────────────────────────────────────────────────────────────
    # ACTUALIZACIÓN DESDE FUERA (llamado por MainWindow)
    # ──────────────────────────────────────────────────────────────
    def refrescar(self):
        """Permite que MainWindow fuerce un refresco al activar el módulo."""
        self._ejecutar_busqueda()
