
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QFrame, QHeaderView, QAbstractItemView,
)
from PySide6.QtCore import Qt
from PySide6.QtGui  import QColor, QFont

from services.estudiante_service import EstudianteService


class HistorialDialog(QDialog):

    COLUMNAS = [
        (0, "Ciclo",           110),
        (1, "Taller",          190),
        (2, "Docente",         150),
        (3, "Asistidas/Total",  110),
        (4, "% Asistencia",     95),
        (5, "Aptitud",          90),
    ]

    def __init__(self, estudiante_id: int, parent=None):
        super().__init__(parent)
        self.estudiante_id = estudiante_id
        self.setModal(True)
        self.setMinimumSize(780, 480)
        self.setWindowFlags(self.windowFlags() &
                            ~Qt.WindowType.WindowContextHelpButtonHint)
        self._construir_ui()
        self._cargar_datos()

    # ──────────────────────────────────────────────────────────────
    # CONSTRUCCIÓN DE LA INTERFAZ
    # ──────────────────────────────────────────────────────────────
    def _construir_ui(self):
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(24, 20, 24, 20)
        raiz.setSpacing(0)

        # Nombre del estudiante como título
        self.lbl_nombre_completo = QLabel("Cargando…")
        self.lbl_nombre_completo.setObjectName("lbl_nombre_completo")
        font = QFont()
        font.setPointSize(16)
        font.setWeight(QFont.Weight.Medium)
        self.lbl_nombre_completo.setFont(font)
        raiz.addWidget(self.lbl_nombre_completo)

        raiz.addSpacing(4)

        # Fila info: código, carrera, ciclo
        self.lbl_info_estudiante = QLabel("")
        self.lbl_info_estudiante.setObjectName("lbl_info_estudiante")
        raiz.addWidget(self.lbl_info_estudiante)

        raiz.addSpacing(12)

        # Tarjeta de estadísticas globales
        raiz.addWidget(self._tarjeta_stats())
        raiz.addSpacing(14)

        # Tabla de historial
        self.tbl_historial = self._construir_tabla()
        self.tbl_historial.setObjectName("tbl_historial")
        raiz.addWidget(self.tbl_historial, 1)

        raiz.addSpacing(14)

        # Botón cerrar
        pie = QHBoxLayout()
        pie.addStretch()
        self.btn_cerrar = QPushButton("Cerrar")
        self.btn_cerrar.setObjectName("btn_cerrar")
        self.btn_cerrar.setFixedSize(100, 36)
        self.btn_cerrar.clicked.connect(self.accept)
        pie.addWidget(self.btn_cerrar)
        raiz.addLayout(pie)

    def _tarjeta_stats(self) -> QFrame:
        """Tarjeta con estadísticas globales del estudiante."""
        frame = QFrame()
        frame.setObjectName("frame_stats")

        lay = QHBoxLayout(frame)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(32)

        def stat(titulo, valor, color=None):
            col = QVBoxLayout()
            col.setSpacing(2)
            lv = QLabel(valor)
            lv.setObjectName("lbl_stats")
            f = QFont()
            f.setPointSize(22)
            f.setWeight(QFont.Weight.Medium)
            lv.setFont(f)
            if color:
                lv.setStyleSheet(f"color:{color};")
            lt = QLabel(titulo)
            col.addWidget(lv)
            col.addWidget(lt)
            return col

        self.lbl_stat_asistencia = QLabel("—%")
        self.lbl_stat_asistencia.setObjectName("lbl_stat_asistencia")
        self.lbl_stat_talleres   = QLabel("—")
        self.lbl_stat_talleres.setObjectName("lbl_stat_talleres")

        lay.addLayout(stat("Asistencia global", "—%"))
        lay.addLayout(stat("Talleres cursados", "—"))
        lay.addLayout(stat("Sesiones totales",  "—"))
        lay.addStretch()

        return frame

    def _construir_tabla(self) -> QTableWidget:
        tbl = QTableWidget()
        tbl.setColumnCount(len(self.COLUMNAS))
        tbl.setHorizontalHeaderLabels([c[1] for c in self.COLUMNAS])
        tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        tbl.setAlternatingRowColors(True)
        tbl.setShowGrid(False)
        tbl.verticalHeader().setVisible(False)

        for idx, _, ancho in self.COLUMNAS:
            tbl.setColumnWidth(idx, ancho)
        tbl.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch   # columna Taller se estira
        )
        tbl.verticalHeader().setDefaultSectionSize(36)
        return tbl

    # ──────────────────────────────────────────────────────────────
    # CARGA DE DATOS
    # ──────────────────────────────────────────────────────────────
    def _cargar_datos(self):
        datos_est = EstudianteService.obtener_por_id(self.estudiante_id)
        historial = EstudianteService.obtener_historial(self.estudiante_id)

        if datos_est:
            self.setWindowTitle(
                f"Historial — {datos_est['nombre_completo']}"
            )
            self.lbl_nombre_completo.setText(datos_est['nombre_completo'])
            self.lbl_info_estudiante.setText(
                f"Código: {datos_est['codigo_estudiantil']}   ·   "
                f"Carrera: {datos_est['carrera']}   ·   "
                f"Ciclo actual: {datos_est['ciclo_actual'] or '—'}   ·   "
                f"Estado: {datos_est['estado']}"
            )
        else:
            self.lbl_nombre_completo.setText("contrado")
            return

        # Actualizar tarjeta stats
        asist  = historial.get("asistencia_global", 0)
        n_tall = historial.get("total_talleres", 0)
        n_ses  = historial.get("total_sesiones", 0)

        # Color de asistencia: verde ≥70, naranja ≥50, rojo <50
        color_asist = "#1D9E75" if asist >= 70 else ("#E67E22" if asist >= 50 else "#C0392B")

        # Repoblar la tarjeta con valores reales
        frame = self.findChild(QFrame, "frame_stats")
        if frame:
            lay = frame.layout()
            # Limpiar y reponer
            while lay.count():
                item = lay.takeAt(0)
                if item.layout():
                    while item.layout().count():
                        child = item.layout().takeAt(0)
                        if child.widget():
                            child.widget().deleteLater()

            def stat_lbl(titulo, valor, color=None):
                col = QVBoxLayout()
                lv  = QLabel(valor)
                f   = QFont(); f.setPointSize(22); f.setWeight(QFont.Weight.Medium)
                lv.setFont(f)
                if color:
                    lv.setStyleSheet(f"color:{color};")
                lt = QLabel(titulo)
                col.addWidget(lv)
                col.addWidget(lt)
                return col

            lay.addLayout(stat_lbl("Asistencia global",
                                   f"{asist:.1f}%", color_asist))
            lay.addLayout(stat_lbl("Talleres cursados", str(n_tall)))
            lay.addLayout(stat_lbl("Sesiones totales",  str(n_ses)))
            lay.addStretch()

        # Tabla
        talleres = historial.get("talleres", [])
        self.tbl_historial.setRowCount(len(talleres))

        for fila, t in enumerate(talleres):
            pct   = t["porcentaje"]
            apto  = t["apto"]

            valores = [
                t["ciclo"],
                t["taller_nombre"],
                t["docente"],
                f"{t['sesiones_asistidas']} / {t['sesiones_totales']}",
                f"{pct:.1f}%",
                apto,
            ]

            for col, val in enumerate(valores):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter |
                                      Qt.AlignmentFlag.AlignLeft)

                # Colorear columna % asistencia
                if col == 4:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    if pct >= 70:
                        item.setForeground(QColor("#1D9E75"))
                    elif pct >= 50:
                        item.setForeground(QColor("#E67E22"))
                    else:
                        item.setForeground(QColor("#C0392B"))

                # Colorear columna aptitud
                if col == 5:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    if "Apto" in apto:
                        item.setForeground(QColor("#1D9E75"))
                    elif "No apto" in apto:
                        item.setForeground(QColor("#C0392B"))
                    elif "Excluido" in apto:
                        item.setForeground(QColor("#E67E22"))

                self.tbl_historial.setItem(fila, col, item)
