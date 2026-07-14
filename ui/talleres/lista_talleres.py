"""
ui/talleres/lista_talleres.py   ──   Sprint 3 / HU-06
═══════════════════════════════════════════════════════

Pantalla principal del módulo Talleres.

LAYOUT:
  ┌──────────────────────────────────────────────────────────┐
  │  Talleres                         [+ Nuevo taller]       │
  │──────────────────────────────────────────────────────────│
  │  🔍 [Buscar…]  [Ciclo ▼]  [Docente ▼]  [Estado ▼]       │
  │──────────────────────────────────────────────────────────│
  │  Código │ Nombre │ Docente │ Inscritos │ Sesiones │Estado │
  │──────────────────────────────────────────────────────────│
  │  …filas…                                                 │
  │──────────────────────────────────────────────────────────│
  │  N talleres        [Sesiones] [Inscritos] [Editar]       │
  └──────────────────────────────────────────────────────────┘

NOMBRES DE PROPIEDADES (objectName):
  inp_buscar      QLineEdit   búsqueda en tiempo real
  cmb_ciclo       QComboBox   filtro por ciclo académico
  cmb_docente     QComboBox   filtro por docente
  cmb_estado      QComboBox   Activo / Suspendido / Finalizado
  btn_nuevo       QPushButton abre FormularioTallerDialog
  btn_editar      QPushButton edita el taller seleccionado
  btn_sesiones    QPushButton abre SesionesDialog
  btn_inscritos   QPushButton abre InscripcionesDialog
  btn_estado      QPushButton cambia estado del taller
  tbl_talleres    QTableWidget tabla principal
  lbl_conteo      QLabel      "Mostrando N talleres"
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QFrame, QMenu, QMessageBox,QFileDialog
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui  import QColor, QFont

from services.taller_service import TallerService


class ListaTalleresWidget(QWidget):
    """
    Widget principal del módulo Talleres.
    Se inserta en el QStackedWidget de MainWindow (índice 2).
    """

    COLUMNAS = [
        (0, "Código",     130),
        (1, "Nombre",     190),
        (2, "Docente",    160),
        (3, "Ciclo",      110),
        (4, "Inscritos",   80),
        (5, "Sesiones",    80),
        (6, "Umbral",      70),
        (7, "Estado",      90),
    ]

    def __init__(self, sesion, parent=None):
        super().__init__(parent)
        self.sesion  = sesion
        self._datos  = []
        self._timer  = QTimer(singleShot=True, interval=350)
        self._timer.timeout.connect(self._ejecutar_busqueda)

        self._construir_ui()
        self._cargar_combos()
        self._ejecutar_busqueda()

    # ──────────────────────────────────────────────────────────────
    def _construir_ui(self):
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0,0,0,12)
        raiz.setSpacing(2)

        raiz.addLayout(self._cabecera())
        raiz.addSpacing(14)
        raiz.addWidget(self._barra_filtros())
        raiz.addSpacing(12)

        self.tbl_talleres = self._construir_tabla()
        self.tbl_talleres.setObjectName("tbl_talleres")
        raiz.addWidget(self.tbl_talleres, 1)

        raiz.addSpacing(10)
        raiz.addLayout(self._pie())

    def _cabecera(self) -> QHBoxLayout:
        lay = QHBoxLayout()
        lay.addStretch()

        self.btn_nuevo = QPushButton("+ Nuevo taller")
        self.btn_nuevo.setObjectName("btn_nuevo")
        self.btn_nuevo.setFixedHeight(36)
        self.btn_nuevo.clicked.connect(self._abrir_formulario_nuevo)
        if self.sesion.rol_nombre == "Docente":
            self.btn_nuevo.setEnabled(False)
        lay.addWidget(self.btn_nuevo)
        return lay

    def _barra_filtros(self) -> QFrame:
        frame = QFrame()
        lay   = QHBoxLayout(frame)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        self.inp_buscar = QLineEdit()
        self.inp_buscar.setObjectName("inp_buscar")
        self.inp_buscar.setPlaceholderText("🔍  Buscar por nombre o código…")
        self.inp_buscar.setFixedHeight(36)
        self.inp_buscar.setMinimumWidth(220)
        self.inp_buscar.textChanged.connect(self._timer.start)
        lay.addWidget(self.inp_buscar, 2)

        self.cmb_ciclo = QComboBox()
        self.cmb_ciclo.setObjectName("cmb_ciclo")
        self.cmb_ciclo.setFixedHeight(36)
        self.cmb_ciclo.setMinimumWidth(160)
        self.cmb_ciclo.currentIndexChanged.connect(self._ejecutar_busqueda)
        lay.addWidget(self.cmb_ciclo, 1)

        self.cmb_docente = QComboBox()
        self.cmb_docente.setObjectName("cmb_docente")
        self.cmb_docente.setFixedHeight(36)
        self.cmb_docente.setMinimumWidth(160)
        self.cmb_docente.currentIndexChanged.connect(self._ejecutar_busqueda)
        lay.addWidget(self.cmb_docente, 1)

        self.cmb_estado = QComboBox()
        self.cmb_estado.setObjectName("cmb_estado")
        self.cmb_estado.setFixedHeight(36)
        self.cmb_estado.setFixedWidth(130)
        for item in [("Estado", None), ("Activo", "Activo"),
                     ("Suspendido", "Suspendido"), ("Finalizado", "Finalizado")]:
            self.cmb_estado.addItem(item[0], item[1])
        self.cmb_estado.currentIndexChanged.connect(self._ejecutar_busqueda)
        lay.addWidget(self.cmb_estado)

        btn_limpiar = QPushButton("✕ Limpiar")
        btn_limpiar.setObjectName("btn_limpiar")
        btn_limpiar.clicked.connect(self._limpiar_filtros)
        lay.addWidget(btn_limpiar)
        return frame

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
        tbl.doubleClicked.connect(self._abrir_formulario_editar)

        for idx, _, ancho in self.COLUMNAS:
            tbl.setColumnWidth(idx, ancho)
        tbl.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch)
        tbl.verticalHeader().setDefaultSectionSize(38)
        return tbl

    def _pie(self) -> QHBoxLayout:
        lay = QHBoxLayout()

        self.lbl_conteo = QLabel("Cargando…")
        self.lbl_conteo.setObjectName("lbl_conteo")
        lay.addWidget(self.lbl_conteo)
        lay.addStretch()

        for nombre, attr, slot in [
            ("Cambiar estado", "btn_estado",    self._cambiar_estado),
            ("Sesiones",       "btn_sesiones",  self._abrir_sesiones),
            ("Inscritos",      "btn_inscritos", self._abrir_inscritos),
            ("✎  Editar",      "btn_editar",    self._abrir_formulario_editar),
        ]:
            btn = QPushButton(nombre)
            btn.setObjectName(attr)
            btn.setEnabled(False)
            btn.clicked.connect(slot)
            setattr(self, attr, btn)
            lay.addWidget(btn)
            lay.addSpacing(4)

        self.tbl_talleres.itemSelectionChanged.connect(
            self._on_seleccion_cambio)
        
        btn_exportar_celulares = QPushButton("📱 Exportar celulares")
        btn_exportar_celulares.setObjectName("btn_exportar_celulares")
        btn_exportar_celulares.setEnabled(False)
        btn_exportar_celulares.clicked.connect(self._exportar_celulares)
        self.btn_exportar_celulares = btn_exportar_celulares
        lay.addWidget(btn_exportar_celulares)
        lay.addSpacing(4)

        return lay

    # ──────────────────────────────────────────────────────────────
    def _cargar_combos(self):
        self.cmb_ciclo.blockSignals(True)
        self.cmb_ciclo.addItem("Todos los ciclos", None)
        for c in TallerService.listar_ciclos():
            self.cmb_ciclo.addItem(c["nombre"], c["id"])
        self.cmb_ciclo.blockSignals(False)

        self.cmb_docente.blockSignals(True)
        if self.sesion.rol_nombre == "Docente":
            # Solo mostrar su propio nombre y bloquear el combo
            self.cmb_docente.addItem(self.sesion.nombre_completo, self.sesion.usuario_id)
            self.cmb_docente.setEnabled(False)
        else:
            self.cmb_docente.addItem("Todos los docentes", None)
            for d in TallerService.listar_docentes():
                self.cmb_docente.addItem(d["nombre"], d["id"])
        self.cmb_docente.blockSignals(False)

    def _ejecutar_busqueda(self):
        if self.sesion.rol_nombre == "Docente":
            # Solo talleres del docente logueado
            self._datos = TallerService.listar_para_asistencia(
                usuario_id=self.sesion.usuario_id,
                rol_nombre=self.sesion.rol_nombre,
                estado=self.cmb_estado.currentData()
            )
        else:
            # Administrador u otros roles → búsqueda normal
            self._datos = TallerService.buscar(
                texto      = self.inp_buscar.text(),
                ciclo_id   = self.cmb_ciclo.currentData(),
                docente_id = self.cmb_docente.currentData(),
                estado     = self.cmb_estado.currentData(),
            )
        self._poblar_tabla(self._datos)


    def _poblar_tabla(self, datos: list[dict]):
        self.tbl_talleres.setSortingEnabled(False)
        self.tbl_talleres.setRowCount(len(datos))

        COLORES_ESTADO = {
            "Activo":     ("#1D9E75", "#E8F8F2"),
            "Suspendido": ("#E67E22", "#FEF3E7"),
            "Finalizado": ("#73726c", "#f0eee8"),
        }

        for fila, t in enumerate(datos):
            cupo_txt = f"{t['total_inscritos']}/{t['cupo_maximo']}"
            ses_txt  = f"{t['sesiones_realizadas']}/{t['total_sesiones']}"

            valores = [
                t["codigo"], t["nombre"], t["docente"],
                t["ciclo"], cupo_txt, ses_txt,
                f"{t['umbral']}%", t["estado"],
            ]

            for col, val in enumerate(valores):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter |
                                      Qt.AlignmentFlag.AlignLeft)

                if col in (4, 5, 6):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                if col == 7:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    fg, bg = COLORES_ESTADO.get(val, ("#333", "#fff"))
                    item.setForeground(QColor(fg))
                    item.setBackground(QColor(bg))

                if col == 4:
                    # Cupo lleno → rojo
                    if t["total_inscritos"] >= t["cupo_maximo"]:
                        item.setForeground(QColor("#C0392B"))

                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, t["id"])

                self.tbl_talleres.setItem(fila, col, item)

        self.tbl_talleres.setSortingEnabled(True)
        n = len(datos)
        self.lbl_conteo.setText(
            f"Mostrando {n} taller{'es' if n != 1 else ''}")

    # ──────────────────────────────────────────────────────────────
    def _on_seleccion_cambio(self):
        hay = bool(self.tbl_talleres.selectedItems())
        es_admin = self.sesion.rol_nombre == "Administrador"
        self.btn_editar.setEnabled(hay and es_admin)
        self.btn_sesiones.setEnabled(hay)
        self.btn_inscritos.setEnabled(hay)
        self.btn_estado.setEnabled(hay and es_admin)
        self.btn_exportar_celulares.setEnabled(hay)


    def _taller_id_seleccionado(self) -> int | None:
        fila = self.tbl_talleres.currentRow()
        if fila < 0:
            return None
        item = self.tbl_talleres.item(fila, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _limpiar_filtros(self):
        self.inp_buscar.clear()
        self.cmb_ciclo.setCurrentIndex(0)
        self.cmb_docente.setCurrentIndex(0)
        self.cmb_estado.setCurrentIndex(0)
        self._ejecutar_busqueda()

    # ── Acciones ─────────────────────────────────────────────────
    def _abrir_formulario_nuevo(self):
        from ui.talleres.formulario_taller import FormularioTallerDialog
        dlg = FormularioTallerDialog(sesion=self.sesion, parent=self)
        if dlg.exec():
            self._ejecutar_busqueda()

    def _abrir_formulario_editar(self):
        tid = self._taller_id_seleccionado()
        if not tid:
            return
        from ui.talleres.formulario_taller import FormularioTallerDialog
        dlg = FormularioTallerDialog(sesion=self.sesion,
                                    taller_id=tid, parent=self)
        if dlg.exec():
            self._limpiar_filtros()
            self._ejecutar_busqueda()

    def _abrir_sesiones(self):
        tid = self._taller_id_seleccionado()
        if not tid:
            return
        from ui.talleres.sesiones_widget import SesionesDialog
        SesionesDialog(taller_id=tid, sesion=self.sesion,
                       parent=self).exec()
        self._ejecutar_busqueda()

    def _abrir_inscritos(self):
        tid = self._taller_id_seleccionado()
        if not tid:
            return
        from ui.talleres.inscripciones_dialog import InscripcionesDialog
        InscripcionesDialog(taller_id=tid, sesion=self.sesion,
                            parent=self).exec()
        self._ejecutar_busqueda()

    def _cambiar_estado(self):
        tid = self._taller_id_seleccionado()
        if not tid:
            return
        datos = TallerService.obtener_por_id(tid)
        if not datos:
            return
        menu = QMenu(self)
        for opcion in [e for e in ("Activo","Suspendido","Finalizado")
                       if e != datos["estado"]]:
            menu.addAction(f"Cambiar a {opcion}",
                lambda o=opcion: self._confirmar_cambio(tid, o))
        menu.exec(self.btn_estado.mapToGlobal(
            self.btn_estado.rect().bottomLeft()))

    def _confirmar_cambio(self, tid: int, nuevo: str):
        datos = TallerService.obtener_por_id(tid)
        r = QMessageBox.question(self, "Confirmar",
            f"¿Cambiar estado del taller\n'{datos['nombre']}'\na '{nuevo}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if r == QMessageBox.StandardButton.Yes:
            res = TallerService.cambiar_estado(
                tid, nuevo, self.sesion.usuario_id)
            if res.ok:
                self._ejecutar_busqueda()
            else:
                QMessageBox.warning(self, "Error", res.mensaje)

    def _menu_contextual(self, pos):
        if not self._taller_id_seleccionado():
            return
        menu = QMenu(self)
        menu.addAction("✎  Editar",    self._abrir_formulario_editar)
        menu.addAction("📅  Sesiones",  self._abrir_sesiones)
        menu.addAction("👥  Inscritos", self._abrir_inscritos)
        menu.addSeparator()
        menu.addAction("Cambiar estado", self._cambiar_estado)
        menu.exec(self.tbl_talleres.mapToGlobal(pos))

    def _exportar_celulares(self):
        tid = self._taller_id_seleccionado()
        if not tid:
            return

        # Obtener inscritos desde el service
        inscritos = TallerService.listar_inscritos(tid)
        if not inscritos:
            QMessageBox.information(self, "Sin datos", "No hay inscritos en este taller.")
            return

        # Extraer teléfonos
        telefonos = [i["telefono"] for i in inscritos if i.get("telefono")]

        if not telefonos:
            QMessageBox.information(self, "Sin teléfonos", "Ningún inscrito tiene número registrado.")
            return

        # Guardar archivo
        archivo, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar lista de celulares",
            f"Celulares_Taller_{tid}.txt",
            "Texto (*.txt);;CSV (*.csv)"
        )
        if not archivo:
            return

        try:
            with open(archivo, "w", encoding="utf-8") as f:
                for tel in telefonos:
                    f.write(f"{tel}\n")
            QMessageBox.information(self, "Éxito", f"Celulares exportados a:\n{archivo}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo exportar: {str(e)}")


    def refrescar(self):
        self._ejecutar_busqueda()
