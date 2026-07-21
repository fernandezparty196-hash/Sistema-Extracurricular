
from datetime import datetime, date

from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
    QLabel, QLineEdit, QComboBox, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QCheckBox, QDateEdit,
    QAbstractItemView, QSizePolicy, QFrame, QFileDialog
)

try:
    from PySide6.QtCharts import (
        QChart, QChartView, QLineSeries, QValueAxis, QBarSeries, QBarSet,
        QBarCategoryAxis, QPieSeries
    )
    from PySide6.QtGui import QPainter
    QTCHARTS_DISPONIBLE = True
except ImportError:
    QTCHARTS_DISPONIBLE = False

from services.reporte_service import ReporteService
from services.exportacion_service import ExportacionService
from services.taller_service import TallerService


# ────────────────────────────────────────────────────────────────
# Colores de acento por reporte (borde de la tarjeta + gráficos)
# ────────────────────────────────────────────────────────────────
COLOR_ASISTENCIA  = "#4f46e5"   # índigo
COLOR_INSCRITOS   = "#16a34a"   # verde
COLOR_APTOS       = "#2563eb"   # azul
COLOR_BIENES      = "#d97706"   # ámbar
COLOR_CONSOLIDADO = "#9333ea"   # púrpura

PALETA_GRAFICOS = ["#e546a3", "#16a34a", "#2563eb", "#d97706", "#dc2626",
                   "#9333ea", "#0891b2", "#ea580c"]


# ══════════════════════════════════════════════════════════════════
# QSS LOCAL — igual criterio que panel_bienes.py / panel_auditoria.py
# ══════════════════════════════════════════════════════════════════
ESTILO_PANEL = """
    QFrame#cardReporte {
        border: 2px solid #94a3b8;
        border-radius: 10px;
    }
    QFrame#cardReporte[tipo="asistencia"]  { border-color: #4f46e5; }
    QFrame#cardReporte[tipo="inscritos"]   { border-color: #16a34a; }
    QFrame#cardReporte[tipo="aptos"]       { border-color: #2563eb; }
    QFrame#cardReporte[tipo="bienes"]      { border-color: #d97706; }
    QFrame#cardReporte[tipo="consolidado"] { border-color: #9333ea; }

    QLabel#tituloReporteCard {
        font-size: 12px;
        font-weight: 700;
    }
    QLabel#descripcionReporteCard {
        font-size: 10px;
    }
    QLabel#rfReporteCard {
        font-size: 9px;
        font-weight: 700;
    }
"""

ESTILO_DIALOGOS = """
    QLineEdit, QComboBox, QDateEdit {
        border: 1px solid #d1d5db;
        border-radius: 6px;
        padding: 4px 8px;
        min-height: 28px;
        font-size: 10px;
    }
    QLineEdit:focus, QComboBox:focus, QDateEdit:focus {
        border: 1px solid #4f46e5;
    }
    QDateEdit::drop-down {
        border: none;
        width: 24px;
    }

    QCalendarWidget {
        border: 1px solid #e0e7ff;
        border-radius: 8px;
    }
    QCalendarWidget QWidget#qt_calendar_navigationbar {
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
        padding: 4px;
    }
    QCalendarWidget QToolButton {
        color: #312e81;
        font-weight: 600;
        font-size: 11px;
        border-radius: 6px;
        padding: 4px 8px;
        margin: 2px;
    }
    QCalendarWidget QToolButton:hover { background: #e0e7ff; }
    QCalendarWidget QToolButton::menu-indicator { image: none; }
    QCalendarWidget QAbstractItemView {
        selection-background-color: #4f46e5;
        selection-color: #ffffff;
        outline: none;
        font-size: 11px;
    }
    QCalendarWidget QAbstractItemView:disabled { color: #cbd5e1; }

    QFrame#cardFiltrosReporte {
        border: 1px solid #e0e7ff;
        border-left: 4px solid #4f46e5;
        border-radius: 10px;
    }

    QLabel#tituloDialogoReporte {
        font-size: 14px;
        font-weight: 700;
    }

    QTableWidget {
        border: none;
        gridline-color: #f1f5f9;
        font-size: 10px;
    }
    QHeaderView::section {
        font-weight: 600;
        font-size: 10px;
        padding: 3px px;
        border: none;
        border-bottom: 1px solid #e2e8f0;
    }

    QPushButton#btn_ghost {
        border: 1px solid #d1d5db;
        border-radius: 6px;
        padding: 4px 12px;
        font-size: 10px;
    }
    QPushButton#btn_ghost:hover { background: #f1f5f9; }

    QPushButton#botonGenerar {
        border: none;
        border-radius: 6px;
        padding: 6px 16px;
        font-weight: 600;
        font-size: 10px;
    }
    QPushButton#botonGenerar:hover { background: #4338ca; }
"""
 
def _cargar_docentes_taller() -> list:
    """Docentes que dictan al menos un taller (para el filtro de RF-36)."""
    try:
        return TallerService.listar_docentes() or []
    except Exception:
        return []
 
 
# ════════════════════════════════════════════════════════════════
# Base común para los diálogos de reporte
# ════════════════════════════════════════════════════════════════
class _DialogoReporteBase(QDialog):
    """
    Provee el esqueleto compartido por todos los diálogos de reporte:
    encabezado, card de filtros, botón "Generar", área de contenido
    (tabla + gráfico) y pie con exportación a Excel/PDF/CSV (RF-40).
 
    Las subclases solo implementan:
      • _construir_filtros(layout): arma sus propios campos de filtro
      • _generar(): llama al servicio, puebla self._filas_export /
        self._columnas_export y renderiza tabla + gráfico(s) en
        self.contenido
    """
 
    TITULO = "Reporte"
    RF = ""
 
    def __init__(self, usuario_id: int, usuario_nombre: str, parent=None):
        super().__init__(parent)
        self.usuario_id = usuario_id
        self.usuario_nombre = usuario_nombre
        self._columnas_export: list = []
        self._filas_export: list = []
 
        self.setWindowTitle(f"{self.RF} — {self.TITULO}")
        self.setMinimumSize(1020, 720)
        self.setStyleSheet(ESTILO_DIALOGOS)
        self._armar_ui()
 
    # ── Esqueleto común ─────────────────────────────────────────
    def _armar_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
 
        titulo = QLabel(f"{self.TITULO} ")
        titulo.setObjectName("tituloDialogoReporte")
        layout.addWidget(titulo)
 
        card_filtros = QFrame()
        card_filtros.setObjectName("cardFiltrosReporte")
        fila_filtros = QHBoxLayout(card_filtros)
        fila_filtros.setContentsMargins(16, 12, 16, 12)
        fila_filtros.setSpacing(10)
 
        self._construir_filtros(fila_filtros)
 
        btn_generar = QPushButton("📊 Generar reporte")
        btn_generar.setObjectName("botonGenerar")
        btn_generar.clicked.connect(self._generar)
        fila_filtros.addStretch()
        fila_filtros.addWidget(btn_generar)
 
        layout.addWidget(card_filtros)
 
        # Área de contenido: la llenan las subclases en cada _generar()
        self.contenido = QVBoxLayout()
        self.contenido.setSpacing(10)
        layout.addLayout(self.contenido, 1)
 
        self.lbl_estado = QLabel("Configura los filtros y presiona «Generar reporte».")
        self.lbl_estado.setObjectName("subtitulo")
        self.contenido.addWidget(self.lbl_estado)
 
        # ── Pie: exportación + cerrar ────────────────────────────
        pie = QHBoxLayout()
        pie.addStretch()
 
        self.btn_excel = QPushButton("⬇ Excel")
        self.btn_excel.setObjectName("btn_ghost")
        self.btn_excel.setEnabled(False)
        self.btn_excel.clicked.connect(lambda: self._exportar("excel"))
 
        self.btn_pdf = QPushButton("⬇ PDF")
        self.btn_pdf.setObjectName("btn_ghost")
        self.btn_pdf.setEnabled(False)
        self.btn_pdf.clicked.connect(lambda: self._exportar("pdf"))
 
        self.btn_csv = QPushButton("⬇ CSV")
        self.btn_csv.setObjectName("btn_ghost")
        self.btn_csv.setEnabled(False)
        self.btn_csv.clicked.connect(lambda: self._exportar("csv"))
 
        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.setObjectName("btn_ghost")
        btn_cerrar.clicked.connect(self.reject)
 
        pie.addWidget(self.btn_excel)
        pie.addWidget(self.btn_pdf)
        pie.addWidget(self.btn_csv)
        pie.addWidget(btn_cerrar)
        layout.addLayout(pie)
 
    def _campo(self, etiqueta: str, widget: QWidget) -> QWidget:
        contenedor = QWidget()
        v = QVBoxLayout(contenedor)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(2)
        lbl = QLabel(etiqueta.upper())
        lbl.setObjectName("subtitulo")
        v.addWidget(lbl)
        v.addWidget(widget)
        return contenedor
 
    def _limpiar_contenido(self):
        """Vacía self.contenido antes de volver a renderizar."""
        while self.contenido.count():
            item = self.contenido.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
            elif item.layout() is not None:
                self._limpiar_layout(item.layout())
 
    def _limpiar_layout(self, lay):
        while lay.count():
            item = lay.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
 
    def _crear_tabla(self, columnas: list, filas: list) -> QTableWidget:
        """columnas: [(clave, etiqueta), ...] · filas: [dict, ...]"""
        tabla = QTableWidget()
        tabla.setColumnCount(len(columnas))
        tabla.setHorizontalHeaderLabels([etiqueta for _, etiqueta in columnas])
        tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        tabla.setAlternatingRowColors(True)
        tabla.setShowGrid(False)
        tabla.setWordWrap(True)
        tabla.verticalHeader().setVisible(False)
        tabla.verticalHeader().setDefaultSectionSize(14)
        tabla.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
 
        header = tabla.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        for i in range(1, len(columnas)):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
 
        tabla.setRowCount(len(filas))
        for fila_idx, fila in enumerate(filas):
            for col_idx, (clave, _) in enumerate(columnas):
                texto = str(fila.get(clave, "—"))
                item = QTableWidgetItem(texto)
                item.setToolTip(texto)
                tabla.setItem(fila_idx, col_idx, item)
 
        tabla.resizeRowsToContents()
        return tabla
 
    def _sin_graficos(self, mensaje: str = None) -> QLabel:
        lbl = QLabel(
            mensaje or "📉 Instala el paquete 'PySide6-Addons' para ver gráficos "
                       "(pip install PySide6-Addons)."
        )
        lbl.setObjectName("subtitulo")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return lbl
 
    def _wrap_chart(self, chart) -> "QChartView":
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        chart.legend().setVisible(True)
        chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)
        view = QChartView(chart)
        view.setRenderHint(QPainter.RenderHint.Antialiasing)
        view.setMinimumHeight(260)
        return view
 
    # ── A implementar por cada subclase ─────────────────────────
    def _construir_filtros(self, layout: QHBoxLayout):
        pass
 
    def _generar(self):
        raise NotImplementedError
 
    def _habilitar_exportacion(self, habilitar: bool):
        self.btn_excel.setEnabled(habilitar)
        self.btn_pdf.setEnabled(habilitar)
        self.btn_csv.setEnabled(habilitar)
 
    # ── Exportación (RF-40) ─────────────────────────────────────
    def _exportar(self, formato: str):
        if not self._filas_export:
            QMessageBox.warning(self, "Sin datos", "Genera el reporte antes de exportar.")
            return
 
        opciones = {
            "excel": ("Excel (*.xlsx)", ".xlsx", ExportacionService.exportar_excel),
            "pdf":   ("PDF (*.pdf)", ".pdf", ExportacionService.exportar_pdf),
            "csv":   ("CSV (*.csv)", ".csv", ExportacionService.exportar_csv),
        }
        filtro, extension, metodo = opciones[formato]
 
        base = self.RF.lower().replace("-", "_")
        sugerido = f"{base}_{datetime.now().strftime('%Y%m%d_%H%M')}{extension}"
 
        ruta, _ = QFileDialog.getSaveFileName(self, "Guardar reporte", sugerido, filtro)
        if not ruta:
            return
 
        resultado = metodo(self.TITULO, self._columnas_export, self._filas_export,
                            self.usuario_nombre, ruta)
 
        if resultado.ok:
            QMessageBox.information(self, "Exportado", resultado.mensaje)
        else:
            QMessageBox.warning(self, "No se pudo exportar", resultado.mensaje)
 
 
# ════════════════════════════════════════════════════════════════
# RF-36 · Asistencia por taller (tendencia)
# ════════════════════════════════════════════════════════════════
class DialogoReporteAsistencia(_DialogoReporteBase):
    TITULO = "Asistencia por taller"
 
    def _construir_filtros(self, layout: QHBoxLayout):
        self.combo_taller = QComboBox()
        self.combo_taller.addItem("Todos los talleres", None)
        for t in TallerService.listar_activos():
            self.combo_taller.addItem(f"{t['codigo']} - {t['nombre']}", t["id"])
 
        self.combo_docente = QComboBox()
        self.combo_docente.addItem("Todos los docentes", None)
        for d in _cargar_docentes_taller():
            self.combo_docente.addItem(d["nombre"], d["id"])
 
        self.check_fecha = QCheckBox("Filtrar por período")
        self.date_desde = QDateEdit(calendarPopup=True)
        self.date_desde.setDisplayFormat("dd/MM/yyyy")
        self.date_desde.setDate(QDate.currentDate().addMonths(-3))
        self.date_hasta = QDateEdit(calendarPopup=True)
        self.date_hasta.setDisplayFormat("dd/MM/yyyy")
        self.date_hasta.setDate(QDate.currentDate())
 
        layout.addWidget(self._campo("Taller", self.combo_taller))
        layout.addWidget(self._campo("Docente", self.combo_docente))
        layout.addWidget(self._campo("Desde", self.date_desde))
        layout.addWidget(self._campo("Hasta", self.date_hasta))
        layout.addWidget(self.check_fecha)
 
    def _generar(self):
        fecha_inicio = self.date_desde.date().toPython() if self.check_fecha.isChecked() else None
        fecha_fin = self.date_hasta.date().toPython() if self.check_fecha.isChecked() else None
 
        resultado = ReporteService.obtener_reporte_asistencia_taller(
            taller_id=self.combo_taller.currentData(),
            docente_id=self.combo_docente.currentData(),
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
        )
 
        self._limpiar_contenido()
 
        if not resultado.ok:
            self.contenido.addWidget(QLabel(resultado.mensaje))
            self._habilitar_exportacion(False)
            return
 
        talleres = resultado.lista or []
 
        columnas = [
            ("taller_codigo", "Código"), ("taller_nombre", "Taller"),
            ("docente", "Docente"), ("total_inscritos", "Inscritos"),
            ("total_sesiones", "Sesiones"), ("promedio_asistencia", "% Promedio"),
        ]
        self.contenido.addWidget(self._crear_tabla(columnas, talleres), 1)
 
        if QTCHARTS_DISPONIBLE:
            chart = QChart()
            chart.setTitle("Tendencia de asistencia por sesión")
            eje_x = QValueAxis()
            eje_x.setTitleText("Sesión Nº")
            eje_x.setLabelFormat("%d")
            eje_y = QValueAxis()
            eje_y.setTitleText("% Asistencia")
            eje_y.setRange(0, 100)
            chart.addAxis(eje_x, Qt.AlignmentFlag.AlignBottom)
            chart.addAxis(eje_y, Qt.AlignmentFlag.AlignLeft)
 
            hay_datos = False
            for i, t in enumerate(talleres):
                tendencia = t.get("tendencia") or []
                if not tendencia:
                    continue
                serie = QLineSeries()
                serie.setName(t["taller_nombre"])
                color = QColor(PALETA_GRAFICOS[i % len(PALETA_GRAFICOS)])
                serie.setColor(color)
                for punto in tendencia:
                    serie.append(punto["sesion_numero"], punto["porcentaje_asistencia"])
                chart.addSeries(serie)
                serie.attachAxis(eje_x)
                serie.attachAxis(eje_y)
                hay_datos = True
 
            if hay_datos:
                self.contenido.addWidget(self._wrap_chart(chart), 2)
            else:
                self.contenido.addWidget(self._sin_graficos(
                    "No hay sesiones registradas en el período seleccionado."))
        else:
            self.contenido.addWidget(self._sin_graficos())
 
        self._columnas_export = columnas
        self._filas_export = talleres
        self._habilitar_exportacion(True)
 
 
# ════════════════════════════════════════════════════════════════
# RF-37 · Inscritos por taller / categoría / ciclo
# ════════════════════════════════════════════════════════════════
class DialogoReporteInscritos(_DialogoReporteBase):
    TITULO = "Inscritos por taller"

    def _construir_filtros(self, layout: QHBoxLayout):
        self.combo_ciclo = QComboBox()
        self.combo_ciclo.addItem("Todos los ciclos", None)
        for c in ReporteService.listar_ciclos():
            self.combo_ciclo.addItem(c["nombre"], c["id"])

        self.input_categoria = QLineEdit()
        self.input_categoria.setPlaceholderText("Categoría exacta (opcional)…")

        layout.addWidget(self._campo("Ciclo académico", self.combo_ciclo))
        layout.addWidget(self._campo("Categoría", self.input_categoria))

    def _generar(self):
        resultado = ReporteService.obtener_reporte_inscritos(
            ciclo_id=self.combo_ciclo.currentData(),
            categoria=self.input_categoria.text().strip() or None,
        )

        self._limpiar_contenido()

        if not resultado.ok:
            self.contenido.addWidget(QLabel(resultado.mensaje))
            self._habilitar_exportacion(False)
            return

        detalle = resultado.lista or []
        por_categoria = resultado.datos.get("por_categoria", [])
        por_ciclo = resultado.datos.get("por_ciclo", [])

        columnas = [
            ("taller_codigo", "Código"), ("taller_nombre", "Taller"),
            ("categoria", "Categoría"), ("ciclo", "Ciclo"),
            ("cupo_maximo", "Cupo"), ("total_inscritos", "Inscritos"),
        ]
        self.contenido.addWidget(self._crear_tabla(columnas, detalle), 1)

        if QTCHARTS_DISPONIBLE and detalle:
            fila_graficos = QHBoxLayout()
            fila_graficos.addWidget(self._grafico_barras(
                "Inscritos por categoría", por_categoria, "categoria", "total_inscritos"))
            fila_graficos.addWidget(self._grafico_barras(
                "Inscritos por ciclo", por_ciclo, "ciclo", "total_inscritos"))
            self.contenido.addLayout(fila_graficos, 2)
        elif not QTCHARTS_DISPONIBLE:
            self.contenido.addWidget(self._sin_graficos())

        self._columnas_export = columnas
        self._filas_export = detalle
        self._habilitar_exportacion(True)

    def _grafico_barras(self, titulo: str, datos: list, clave_categoria: str, clave_valor: str) -> "QChartView":
        chart = QChart()
        chart.setTitle(titulo)

        conjunto = QBarSet("Inscritos")
        conjunto.setColor(QColor(COLOR_INSCRITOS))
        categorias = []
        for d in datos:
            conjunto.append(d[clave_valor])
            categorias.append(str(d[clave_categoria]))

        series = QBarSeries()
        series.append(conjunto)
        chart.addSeries(series)

        eje_x = QBarCategoryAxis()
        eje_x.append(categorias)
        chart.addAxis(eje_x, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(eje_x)

        eje_y = QValueAxis()
        eje_y.setLabelFormat("%d")
        chart.addAxis(eje_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(eje_y)

        grafico = self._wrap_chart(chart)
        grafico.setMinimumWidth(400)
        grafico.setMaximumWidth(500)
        grafico.setMinimumHeight(280)
        grafico.setMaximumHeight(320)

        return grafico


# ════════════════════════════════════════════════════════════════
# RF-38 · Aptos para certificado
# ════════════════════════════════════════════════════════════════
class DialogoReporteAptos(_DialogoReporteBase):
    TITULO = "Aptos para certificado"

    def _construir_filtros(self, layout: QHBoxLayout):
        self.combo_taller = QComboBox()
        self.combo_taller.addItem("Todos los talleres", None)
        for t in TallerService.listar_activos():
            self.combo_taller.addItem(f"{t['codigo']} - {t['nombre']}", t["id"])

        self.combo_ciclo = QComboBox()
        self.combo_ciclo.addItem("Todos los ciclos", None)
        for c in ReporteService.listar_ciclos():
            self.combo_ciclo.addItem(c["nombre"], c["id"])

        layout.addWidget(self._campo("Taller", self.combo_taller))
        layout.addWidget(self._campo("Ciclo académico", self.combo_ciclo))

    def _generar(self):
        resultado = ReporteService.obtener_reporte_aptos_certificado(
            taller_id=self.combo_taller.currentData(),
            ciclo_id=self.combo_ciclo.currentData(),
        )

        self._limpiar_contenido()

        if not resultado.ok:
            self.contenido.addWidget(QLabel(resultado.mensaje))
            self._habilitar_exportacion(False)
            return

        aptos = resultado.lista or []

        columnas = [
            ("codigo", "Código"), ("nombre", "Estudiante"),
            ("taller_nombre", "Taller"), ("porcentaje_asistencia", "% Asistencia"),
            ("umbral_requerido", "Umbral requerido"),
        ]
        self.contenido.addWidget(self._crear_tabla(columnas, aptos), 1)

        if QTCHARTS_DISPONIBLE and aptos:
            conteo = {}
            for a in aptos:
                conteo[a["taller_nombre"]] = conteo.get(a["taller_nombre"], 0) + 1

            chart = QChart()
            chart.setTitle("Aptos por taller")
            conjunto = QBarSet("Aptos")
            conjunto.setColor(QColor(COLOR_APTOS))
            categorias = list(conteo.keys())
            for cat in categorias:
                conjunto.append(conteo[cat])

            series = QBarSeries()
            series.append(conjunto)
            chart.addSeries(series)

            eje_x = QBarCategoryAxis()
            eje_x.append(categorias)
            chart.addAxis(eje_x, Qt.AlignmentFlag.AlignBottom)
            series.attachAxis(eje_x)

            eje_y = QValueAxis()
            eje_y.setLabelFormat("%d")
            chart.addAxis(eje_y, Qt.AlignmentFlag.AlignLeft)
            series.attachAxis(eje_y)

            self.contenido.addWidget(self._wrap_chart(chart), 2)
        elif not QTCHARTS_DISPONIBLE:
            self.contenido.addWidget(self._sin_graficos())

        self._columnas_export = columnas
        self._filas_export = aptos
        self._habilitar_exportacion(True)


# ════════════════════════════════════════════════════════════════
# RF-39 · Bienes patrimoniales
# ════════════════════════════════════════════════════════════════
class DialogoReporteBienes(_DialogoReporteBase):
    TITULO = "Inventario de bienes patrimoniales"

    def _construir_filtros(self, layout: QHBoxLayout):
        aviso = QLabel("Sin filtros — muestra el inventario completo con su estado actual.")
        aviso.setObjectName("subtitulo")
        layout.addWidget(aviso)

    def _generar(self):
        resultado = ReporteService.obtener_reporte_bienes()
        self._limpiar_contenido()

        if not resultado.ok:
            self.contenido.addWidget(QLabel(resultado.mensaje))
            self._habilitar_exportacion(False)
            return

        bienes = resultado.lista or []
        resumen = resultado.datos.get("resumen_por_estado", [])

        columnas = [
            ("codigo", "Código"), ("descripcion", "Descripción"),
            ("categoria", "Categoría"), ("estado", "Estado"),
            ("asignado_a", "Asignado a"), ("valor_adquisicion", "Valor S/."),
        ]
        self.contenido.addWidget(self._crear_tabla(columnas, bienes), 1)

        if QTCHARTS_DISPONIBLE and resumen:
            chart = QChart()
            chart.setTitle("Bienes por estado")
            series = QPieSeries()
            for i, r in enumerate(resumen):
                slice_ = series.append(f"{r['estado']} ({r['cantidad']})", r["cantidad"])
                slice_.setBrush(QColor(PALETA_GRAFICOS[i % len(PALETA_GRAFICOS)]))
                slice_.setLabelVisible(True)
            chart.addSeries(series)
            self.contenido.addWidget(self._wrap_chart(chart), 2)
        elif not QTCHARTS_DISPONIBLE:
            self.contenido.addWidget(self._sin_graficos())

        self._columnas_export = columnas
        self._filas_export = bienes
        self._habilitar_exportacion(True)


# ════════════════════════════════════════════════════════════════
# RF-41 · Consolidado por período
# ════════════════════════════════════════════════════════════════
class DialogoReporteConsolidado(_DialogoReporteBase):
    TITULO = "Consolidado del período"

    def _construir_filtros(self, layout: QHBoxLayout):
        self.check_fecha = QCheckBox("Filtrar por período")
        self.date_desde = QDateEdit(calendarPopup=True)
        self.date_desde.setDisplayFormat("dd/MM/yyyy")
        self.date_desde.setDate(QDate.currentDate().addMonths(-3))
        self.date_hasta = QDateEdit(calendarPopup=True)
        self.date_hasta.setDisplayFormat("dd/MM/yyyy")
        self.date_hasta.setDate(QDate.currentDate())

        layout.addWidget(self._campo("Desde", self.date_desde))
        layout.addWidget(self._campo("Hasta", self.date_hasta))
        layout.addWidget(self.check_fecha)

    def _generar(self):
        fecha_inicio = self.date_desde.date().toPython() if self.check_fecha.isChecked() else None
        fecha_fin = self.date_hasta.date().toPython() if self.check_fecha.isChecked() else None

        resultado = ReporteService.obtener_reporte_consolidado(fecha_inicio, fecha_fin)
        self._limpiar_contenido()

        if not resultado.ok:
            self.contenido.addWidget(QLabel(resultado.mensaje))
            self._habilitar_exportacion(False)
            return

        datos = resultado.datos

        # ── Tarjetas KPI ─────────────────────────────────────────
        fila_kpis = QHBoxLayout()
        kpis = [
            ("Talleres activos", datos["total_talleres_activos"], "#4f46e5"),
            ("Estudiantes inscritos", datos["total_estudiantes_inscritos"], "#16a34a"),
            ("% Asistencia global", f"{datos['porcentaje_asistencia_global']}%", "#2563eb"),
            ("N° Aptos", datos["numero_aptos"], "#d97706"),
        ]
        for titulo_kpi, valor_kpi, color in kpis:
            caja = QFrame()
            caja.setStyleSheet(
                f"QFrame {{ background:#fff; border:2px solid {color}; "
                f"border-radius:10px; }}"
            )
            v = QVBoxLayout(caja)
            v.setContentsMargins(14, 10, 14, 10)
            lbl_valor = QLabel(str(valor_kpi))
            lbl_valor.setStyleSheet("font-size:20px; color:#1e293b; border:transparent")
            lbl_nombre = QLabel(titulo_kpi)
            lbl_nombre.setStyleSheet("font-size:10px; color:#64748b; border:transparent")
            v.addWidget(lbl_valor)
            v.addWidget(lbl_nombre)
            fila_kpis.addWidget(caja)
        self.contenido.addLayout(fila_kpis)

        lbl_periodo = QLabel(
            f"Período: {datos['periodo']['desde']} — {datos['periodo']['hasta']}  ·  "
            f"Generado: {datos['fecha_generacion']}"
        )
        lbl_periodo.setObjectName("subtitulo")
        self.contenido.addWidget(lbl_periodo)

        # ── Gráfico: aptos vs. resto de inscritos ────────────────
        if QTCHARTS_DISPONIBLE:
            total = datos["total_estudiantes_inscritos"]
            aptos = datos["numero_aptos"]
            resto = max(total - aptos, 0)

            if total > 0:
                chart = QChart()
                chart.setTitle("Aptos vs. resto de inscritos")
                series = QPieSeries()
                s1 = series.append(f"Aptos ({aptos})", aptos)
                s1.setBrush(QColor(COLOR_CONSOLIDADO))
                s1.setLabelVisible(True)
                s2 = series.append(f"Resto ({resto})", resto)
                s2.setBrush(QColor("#e2e8f0"))
                s2.setLabelVisible(True)
                chart.addSeries(series)
                self.contenido.addWidget(self._wrap_chart(chart), 1)
            else:
                self.contenido.addWidget(self._sin_graficos("No hay inscritos en el período."))
        else:
            self.contenido.addWidget(self._sin_graficos())

        self.contenido.addStretch()

        columnas = [
            ("talleres_activos", "Talleres activos"),
            ("inscritos", "Inscritos"),
            ("asistencia_global", "% Asistencia global"),
            ("aptos", "N° Aptos"),
            ("desde", "Desde"),
            ("hasta", "Hasta"),
        ]
        fila_export = {
            "talleres_activos": datos["total_talleres_activos"],
            "inscritos": datos["total_estudiantes_inscritos"],
            "asistencia_global": datos["porcentaje_asistencia_global"],
            "aptos": datos["numero_aptos"],
            "desde": datos["periodo"]["desde"],
            "hasta": datos["periodo"]["hasta"],
        }
        self._columnas_export = columnas
        self._filas_export = [fila_export]
        self._habilitar_exportacion(True)


# ════════════════════════════════════════════════════════════════
# Panel principal — una tarjeta por reporte
# ════════════════════════════════════════════════════════════════
class PanelReportes(QWidget):
    """
    Panel de entrada al módulo de reportes. Cada tarjeta abre su
    diálogo correspondiente (RF-36 a RF-39, RF-41); la exportación
    (RF-40) vive dentro de cada diálogo.
    """

    REPORTES = [
        ("asistencia", "📈", "Asistencia por taller",
         "Tendencia de asistencia sesión a sesión, filtrable por período, taller y docente.",
         DialogoReporteAsistencia),
        ("inscritos", "🧑‍🎓", "Inscritos",
         "Total de estudiantes inscritos por taller, categoría y ciclo académico.",
         DialogoReporteInscritos),
        ("aptos", "🎓", "Aptos para certificado",
         "Listado de estudiantes aptos con nombre, código, taller y % de asistencia.",
         DialogoReporteAptos),
        ("bienes", "📦", "Bienes patrimoniales",
         "Inventario completo con el estado actual de cada bien.",
         DialogoReporteBienes),
        ("consolidado", "📊", "Consolidado del período",
         "KPIs generales: talleres activos, inscritos, % asistencia global y N° de aptos.",
         DialogoReporteConsolidado),
    ]

    def __init__(self, sesion_usuario, parent=None):
        super().__init__(parent)
        self.usuario_id = getattr(sesion_usuario, "usuario_id", sesion_usuario)
        self.usuario_nombre = getattr(sesion_usuario, "nombre_completo", "Usuario")
        self.setObjectName("panelReportes")
        self.setStyleSheet(ESTILO_PANEL)
        self._armar_ui()

    def _armar_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        encabezado = QVBoxLayout()
        subtitulo = QLabel("Genera, visualiza y exporta los reportes del sistema de talleres.")
        subtitulo.setObjectName("subtitulo")
        encabezado.addWidget(subtitulo)
        layout.addLayout(encabezado)

        grid = QGridLayout()
        grid.setSpacing(14)
        for i, (tipo, icono, nombre, descripcion, clase_dialogo) in enumerate(self.REPORTES):
            tarjeta = self._crear_tarjeta(tipo,  icono, nombre, descripcion, clase_dialogo)
            grid.addWidget(tarjeta, i // 3, i % 3)

        layout.addLayout(grid)
        layout.addStretch()

    def _crear_tarjeta(self, tipo: str, icono: str, nombre: str,
                        descripcion: str, clase_dialogo) -> QFrame:
        card = QFrame()
        card.setObjectName("cardReporte")
        card.setProperty("tipo", tipo)
        card.setMinimumHeight(150)

        v = QVBoxLayout(card)
        v.setContentsMargins(16, 14, 16, 14)
        v.setSpacing(6)


        lbl_titulo = QLabel(f"{icono}  {nombre}")
        lbl_titulo.setObjectName("tituloReporteCard")
        lbl_titulo.setWordWrap(True)

        lbl_descripcion = QLabel(descripcion)
        lbl_descripcion.setObjectName("descripcionReporteCard")
        lbl_descripcion.setWordWrap(True)

        btn_generar = QPushButton("Ver reporte")
        btn_generar.setObjectName("botonGenerar")
        btn_generar.clicked.connect(lambda: self._abrir_reporte(clase_dialogo))

        v.addWidget(lbl_titulo)
        v.addWidget(lbl_descripcion, 1)
        v.addWidget(btn_generar)

        return card

    def _abrir_reporte(self, clase_dialogo):
        dialogo = clase_dialogo(self.usuario_id, self.usuario_nombre, self)
        dialogo.exec()