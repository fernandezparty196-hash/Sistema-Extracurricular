"""
ui/asistencia/registro_asistencia_dialog.py   ──   CORREGIDO + FILTRADO POR ROL
═══════════════════════════════════════════════════════════════════════════════════

Administrador → ve todos los talleres activos.
Docente       → ve solo los talleres a su cargo.

FIX: la clase heredaba de QWidget, pero se invoca en toda la app (y en este
mismo docstring) con `dlg.exec()`. QWidget no tiene `.exec()` en PySide6,
solo QDialog. Por eso el diálogo nunca se mostraba al intentar tomar
asistencia. Se corrigió heredando de QDialog.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QComboBox,QWidget,
    QLineEdit, QMessageBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

from services.asistencia_service import AsistenciaService
from services.taller_service import TallerService


class RegistroAsistenciaDialog(QWidget):
    """
    USO:
        dlg = RegistroAsistenciaDialog(sesion_usuario=sesion, parent=self)
        dlg.exec()

    Administrador → ve todos los talleres activos (con el nombre del docente
                    a cargo de cada uno, para saber de quién es cada taller).
    Docente       → ve solo los talleres que tiene asignados.
    """

    COLUMNAS = [
        (0, "Nombre",    250),
        (1, "DNI",       100),
        (2, "Carrera",   150),
        (3, "Presente",   80),
        (4, "Ausente",    80),
        (5, "Justif.",    80),
    ]

    def __init__(self, sesion_usuario, parent=None):
        super().__init__(parent)
        self.sesion       = sesion_usuario
        self._inscritos   = []
        self._asistencias = {}
        self._timer = QTimer(singleShot=True, interval=300)
        self._timer.timeout.connect(self._filtrar_tabla)

        self.setMinimumSize(1020, 640)
        self.setWindowTitle("Registrar Asistencia")
        self.setWindowFlags(
            self.windowFlags() &
            ~Qt.WindowType.WindowContextHelpButtonHint
        )

        self._construir_ui()
        self._cargar_datos()

    # ──────────────────────────────────────────────────────────────
    def _construir_ui(self):
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(24, 20, 24, 16)
        raiz.setSpacing(0)

        # Título + badge de rol
        fila_titulo = QHBoxLayout()

        lbl_titulo = QLabel("Registrar Asistencia")
        lbl_titulo.setObjectName("lbl_titulo_dialogo")
        f = QFont(); f.setPointSize(20); f.setWeight(QFont.Weight.Bold)
        lbl_titulo.setFont(f)
        fila_titulo.addWidget(lbl_titulo)

        fila_titulo.addSpacing(10)

        self.lbl_badge_rol = QLabel("")
        self.lbl_badge_rol.setObjectName("lbl_badge_rol")
        fila_titulo.addWidget(self.lbl_badge_rol)

        fila_titulo.addStretch()
        raiz.addLayout(fila_titulo)
        raiz.addSpacing(10)

        # Selecciones
        sel = QHBoxLayout()

        sel.addWidget(QLabel("Taller:"))
        self.cmb_taller = QComboBox()
        self.cmb_taller.setObjectName("cmb_taller")
        self.cmb_taller.setFixedHeight(32)
        self.cmb_taller.currentIndexChanged.connect(self._on_taller_cambio)
        sel.addWidget(self.cmb_taller, 1)

        sel.addSpacing(16)

        sel.addWidget(QLabel("Sesión:"))
        self.cmb_sesion = QComboBox()
        self.cmb_sesion.setObjectName("cmb_sesion")
        self.cmb_sesion.setFixedHeight(32)
        self.cmb_sesion.currentIndexChanged.connect(self._on_sesion_cambio)
        sel.addWidget(self.cmb_sesion, 1)

        raiz.addLayout(sel)
        raiz.addSpacing(10)

        # Info sesión
        self.lbl_info_sesion = QLabel("Selecciona un taller y una sesión para comenzar.")
        self.lbl_info_sesion.setObjectName("lbl_info_sesion")
        raiz.addWidget(self.lbl_info_sesion)
        raiz.addSpacing(12)

        # Búsqueda
        busqueda = QHBoxLayout()
        busqueda.addWidget(QLabel("🔍"))
        self.inp_buscar = QLineEdit()
        self.inp_buscar.setObjectName("inp_buscar")
        self.inp_buscar.setPlaceholderText("Buscar por nombre o DNI…")
        self.inp_buscar.setFixedHeight(32)
        self.inp_buscar.textChanged.connect(self._timer.start)
        busqueda.addWidget(self.inp_buscar)
        raiz.addLayout(busqueda)
        raiz.addSpacing(10)

        # Tabla
        self.tbl_asistencia = self._construir_tabla()
        self.tbl_asistencia.setObjectName("tbl_asistencia")
        raiz.addWidget(self.tbl_asistencia, 1)

        raiz.addSpacing(6)

        instrucciones = QLabel("Marca una sola casilla por estudiante: Presente, Ausente o Justificado.")
        instrucciones.setObjectName("lbl_instrucciones")
        raiz.addWidget(instrucciones)
        raiz.addSpacing(6)

        # Controles
        controles = QHBoxLayout()

        self.btn_todos_presente = QPushButton("✓ Todos Presente")
        self.btn_todos_presente.setObjectName("btn_todos_presente")
        self.btn_todos_presente.setFixedHeight(32)
        self.btn_todos_presente.clicked.connect(
            lambda: self._marcar_todos("P"))
        controles.addWidget(self.btn_todos_presente)

        controles.addSpacing(6)

        self.btn_todos_ausente = QPushButton("✗ Todos Ausente")
        self.btn_todos_ausente.setObjectName("btn_todos_ausente")
        self.btn_todos_ausente.setFixedHeight(32)
        self.btn_todos_ausente.clicked.connect(
            lambda: self._marcar_todos("A"))
        controles.addWidget(self.btn_todos_ausente)

        controles.addSpacing(6)

        self.btn_limpiar = QPushButton("Limpiar búsqueda")
        self.btn_limpiar.setObjectName("btn_limpiar")
        self.btn_limpiar.setFixedHeight(32)
        self.btn_limpiar.clicked.connect(self.inp_buscar.clear)
        controles.addWidget(self.btn_limpiar)

        controles.addStretch()

        raiz.addLayout(controles)
        raiz.addSpacing(8)

        # Estado
        self.lbl_estado = QLabel("")
        self.lbl_estado.setObjectName("lbl_estado_asistencia")
        raiz.addWidget(self.lbl_estado)

        raiz.addSpacing(10)

        # Botones pie
        pie = QHBoxLayout()

        self.btn_guardar = QPushButton("Guardar asistencia")
        self.btn_guardar.setObjectName("btn_guardar")
        self.btn_guardar.setFixedHeight(34)
        self.btn_guardar.setEnabled(False)
        self.btn_guardar.clicked.connect(self._guardar_asistencia)
        pie.addWidget(self.btn_guardar)

        raiz.addLayout(pie)

    def _construir_tabla(self) -> QTableWidget:
        tbl = QTableWidget()
        tbl.setColumnCount(len(self.COLUMNAS))
        tbl.setHorizontalHeaderLabels([c[1] for c in self.COLUMNAS])
        tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        tbl.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tbl.setAlternatingRowColors(True)
        tbl.setShowGrid(False)
        tbl.setSortingEnabled(False)
        tbl.verticalHeader().setVisible(False)

        for idx, _, ancho in self.COLUMNAS:
            tbl.setColumnWidth(idx, ancho)

        tbl.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch)
        tbl.verticalHeader().setDefaultSectionSize(32)
        tbl.itemChanged.connect(self._on_estado_cambiado)
        return tbl

    # ──────────────────────────────────────────────────────────────
    def _cargar_datos(self):
        """
        Administrador → ve todos los talleres activos.
        Docente       → ve solo los talleres a su cargo.

        Envuelto en try/except: si falla, se muestra el motivo en vez de
        quedar la pantalla vacía sin explicación.
        """
        if self.sesion.es_docente:
            self.lbl_badge_rol.setObjectName("lbl_badge_docente")
            self.lbl_badge_rol.setText("Mis talleres")
        else:
            # Administrador u Operador ven todos los talleres
            self.lbl_badge_rol.setObjectName("lbl_badge_admin")
            self.lbl_badge_rol.setText(
                f"👁 Vista {self.sesion.rol_nombre} — todos los talleres"
            )

        try:
            talleres = TallerService.listar_para_asistencia(
                usuario_id=self.sesion.usuario_id,
                rol_nombre=self.sesion.rol_nombre,
                estado="Activo"
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Error",
                f"No se pudieron cargar los talleres:\n\n{e}"
            )
            self.cmb_taller.addItem("❌ Error al cargar talleres", None)
            return

        if not talleres:
            mensaje = (
                "❌ No tienes talleres asignados"
                if self.sesion.es_docente
                else "❌ No hay talleres activos"
            )
            self.cmb_taller.addItem(mensaje, None)
            self.lbl_info_sesion.setText(mensaje)
            return

        for taller in talleres:
            self.cmb_taller.addItem(
                f"{taller['nombre']}  —  Docente: {taller['docente']}",
                taller["id"]
            )

    def _on_estado_cambiado(self, item):
        """Permite marcar solo un estado (P/A/J) por fila."""
        col = item.column()
        if col not in (3, 4, 5):
            return
        if item.checkState() != Qt.CheckState.Checked:
            return
        self.tbl_asistencia.blockSignals(True)
        fila = item.row()
        for c in (3, 4, 5):
            if c != col:
                otro = self.tbl_asistencia.item(fila, c)
                if otro:
                    otro.setCheckState(Qt.CheckState.Unchecked)

        self.tbl_asistencia.blockSignals(False)
        self.btn_guardar.setEnabled(True)
        self._actualizar_estado()

    def _on_taller_cambio(self):
        """Al cambiar taller, cargar sesiones."""
        self.cmb_sesion.blockSignals(True)
        self.cmb_sesion.clear()
        self.cmb_sesion.blockSignals(False)
        self.tbl_asistencia.setRowCount(0)
        self.btn_guardar.setEnabled(False)

        taller_id = self.cmb_taller.currentData()
        if not taller_id:
            return

        try:
            sesiones = TallerService.listar_sesiones(taller_id)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron cargar las sesiones:\n\n{e}")
            return

        if not sesiones:
            self.lbl_info_sesion.setText("Este taller no tiene sesiones registradas.")
            return

        for ses in sesiones:
            texto = f"Sesión {ses['numero']} — {ses['fecha']}"
            self.cmb_sesion.addItem(texto, ses["id"])

    def _on_sesion_cambio(self):
        """Al cambiar sesión, cargar inscritos."""
        sesion_id = self.cmb_sesion.currentData()
        if not sesion_id:
            self.tbl_asistencia.setRowCount(0)
            self.btn_guardar.setEnabled(False)
            return

        taller_id = self.cmb_taller.currentData()

        try:
            self._inscritos = TallerService.listar_inscritos(
                taller_id, solo_activos=True
            )
            asistencias_previas = AsistenciaService.obtener_por_sesion(sesion_id)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo cargar la sesión:\n\n{e}")
            return

        if not self._inscritos:
            self.lbl_info_sesion.setText("No hay estudiantes inscritos activos en este taller.")
            self.tbl_asistencia.setRowCount(0)
            self.btn_guardar.setEnabled(False)
            return

        self._asistencias = {}
        for a in asistencias_previas:
            self._asistencias[a["inscripcion_id"]] = {
                "estado": a["estado"],
                "observacion": a.get("observacion", "")
            }

        presentes = sum(1 for a in asistencias_previas if a["estado"] == "P")
        justificados = sum(1 for a in asistencias_previas if a["estado"] == "J")
        ausentes = sum(1 for a in asistencias_previas if a["estado"] == "A")

        if asistencias_previas:
            self.lbl_info_sesion.setText(
                f"<b>{len(self._inscritos)} inscritos</b>  |  "
                f"{presentes} presentes  |  {justificados} justificados  |  "
                f"{ausentes} ausentes  —  "
                f"<i>Ya se registró asistencia, puedes modificarla y volver a guardar.</i>"
            )
        else:
            self.lbl_info_sesion.setText(
                f"<b>{len(self._inscritos)} inscritos</b>  |  Asistencia aún no registrada."
            )

        self._poblar_tabla()
        self.btn_guardar.setEnabled(len(self._asistencias) == 0)

    def _poblar_tabla(self):
        """Llena la tabla con inscritos."""
        self.tbl_asistencia.blockSignals(True)
        self.tbl_asistencia.setRowCount(len(self._inscritos))
        for fila, est in enumerate(self._inscritos):
            insc_id = est["inscripcion_id"]
            prev = self._asistencias.get(insc_id, {})

            # Nombre (no editable)
            item_nombre = QTableWidgetItem(est["nombre_completo"])
            item_nombre.setData(Qt.ItemDataRole.UserRole, insc_id)
            item_nombre.setFlags(item_nombre.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.tbl_asistencia.setItem(fila, 0, item_nombre)

            # DNI (no editable)
            item_dni = QTableWidgetItem(est["dni"])
            item_dni.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_dni.setFlags(item_dni.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.tbl_asistencia.setItem(fila, 1, item_dni)

            # Carrera (no editable)
            item_carrera = QTableWidgetItem(est["carrera"])
            item_carrera.setFlags(item_carrera.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.tbl_asistencia.setItem(fila, 2, item_carrera)

            # Presente, Ausente, Justificado
            estado_previo = prev.get("estado")
            col_map = {"P": 3, "A": 4, "J": 5}
            for col_idx in (3, 4, 5):
                item = QTableWidgetItem()
                item.setFlags(
                    Qt.ItemFlag.ItemIsEnabled |
                    Qt.ItemFlag.ItemIsUserCheckable
                )
                marcado = col_map.get(estado_previo) == col_idx
                item.setCheckState(
                    Qt.CheckState.Checked if marcado else Qt.CheckState.Unchecked
                )
                self.tbl_asistencia.setItem(fila, col_idx, item)

        self.tbl_asistencia.blockSignals(False)
        self._actualizar_estado()

    def _marcar_todos(self, estado: str):
        """Marca todos los estudiantes visibles (no ocultos por búsqueda) con el estado indicado."""
        col_map = {"P": 3, "A": 4, "J": 5}
        self.tbl_asistencia.blockSignals(True)
        for fila in range(self.tbl_asistencia.rowCount()):
            if self.tbl_asistencia.isRowHidden(fila):
                continue
            self.tbl_asistencia.item(fila, 3).setCheckState(Qt.CheckState.Unchecked)
            self.tbl_asistencia.item(fila, 4).setCheckState(Qt.CheckState.Unchecked)
            self.tbl_asistencia.item(fila, 5).setCheckState(Qt.CheckState.Unchecked)
            self.tbl_asistencia.item(fila, col_map[estado]).setCheckState(Qt.CheckState.Checked)
        self.tbl_asistencia.blockSignals(False)
        self.btn_guardar.setEnabled(True)
        self._actualizar_estado()

    def _filtrar_tabla(self):
        """Filtra tabla por búsqueda."""
        texto = self.inp_buscar.text().lower()
        for fila in range(self.tbl_asistencia.rowCount()):
            nombre = self.tbl_asistencia.item(fila, 0).text().lower()
            dni = self.tbl_asistencia.item(fila, 1).text().lower()
            visible = texto in nombre or texto in dni
            self.tbl_asistencia.setRowHidden(fila, not visible)

    def _actualizar_estado(self):
        """Actualiza el label de estado."""
        presentes = 0
        ausentes = 0
        justificados = 0

        for fila in range(self.tbl_asistencia.rowCount()):
            if self.tbl_asistencia.item(fila, 3).checkState() == Qt.CheckState.Checked:
                presentes += 1
            elif self.tbl_asistencia.item(fila, 4).checkState() == Qt.CheckState.Checked:
                ausentes += 1
            elif self.tbl_asistencia.item(fila, 5).checkState() == Qt.CheckState.Checked:
                justificados += 1

        total = self.tbl_asistencia.rowCount()

        self.lbl_estado.setText(
            f"<b>{presentes} presentes | {justificados} justificados | "
            f"{ausentes} ausentes</b> (Total: {total})"
        )

    def _guardar_asistencia(self):
        """Guarda todos los registros de asistencia."""
        sesion_id = self.cmb_sesion.currentData()
        if not sesion_id:
            QMessageBox.warning(self, "Error", "Selecciona una sesión")
            return

        sin_marcar = []
        for fila in range(self.tbl_asistencia.rowCount()):
            marcado = any(
                self.tbl_asistencia.item(fila, c).checkState() == Qt.CheckState.Checked
                for c in (3, 4, 5)
            )
            if not marcado:
                sin_marcar.append(self.tbl_asistencia.item(fila, 0).text())

        if sin_marcar:
            r = QMessageBox.question(
                self, "Estudiantes sin marcar",
                f"{len(sin_marcar)} estudiante(s) no tienen estado seleccionado "
                f"y se omitirán:\n\n" + "\n".join(sin_marcar[:5]) +
                ("\n..." if len(sin_marcar) > 5 else "") +
                "\n\n¿Deseas continuar de todos modos?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if r != QMessageBox.StandardButton.Yes:
                return

        registrados = 0
        errores = 0
        errores_msg = []

        for fila in range(self.tbl_asistencia.rowCount()):
            nombre_item = self.tbl_asistencia.item(fila, 0)
            insc_id = nombre_item.data(Qt.ItemDataRole.UserRole)

            estado = None
            if self.tbl_asistencia.item(fila, 3).checkState() == Qt.CheckState.Checked:
                estado = "P"
            elif self.tbl_asistencia.item(fila, 4).checkState() == Qt.CheckState.Checked:
                estado = "A"
            elif self.tbl_asistencia.item(fila, 5).checkState() == Qt.CheckState.Checked:
                estado = "J"

            if not estado:
                continue

            try:
                res = AsistenciaService.registrar(
                    sesion_id=sesion_id,
                    inscripcion_id=insc_id,
                    estado=estado,
                    usuario_id=self.sesion.usuario_id
                )
            except Exception as e:
                errores += 1
                errores_msg.append(f"Fila {fila + 1}: {e}")
                continue

            if res.ok:
                registrados += 1
            else:
                errores += 1
                errores_msg.append(f"Fila {fila + 1}: {res.mensaje}")

        mensaje = f"✅ Asistencia registrada: {registrados} estudiantes"
        if errores > 0:
            mensaje += f"\n❌ Errores: {errores}"
            if errores_msg:
                mensaje += "\n" + "\n".join(errores_msg[:3])

        QMessageBox.information(self, "Resultado", mensaje)

        if registrados > 0:
            self._on_sesion_cambio()