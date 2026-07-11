
import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QFileDialog, QProgressBar, QHeaderView, QAbstractItemView,
    QFrame,
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui  import QColor, QFont

try:
    import openpyxl
    OPENPYXL_OK = True
except ImportError:
    OPENPYXL_OK = False

from services.estudiante_service import EstudianteService


# ══════════════════════════════════════════════════════════════════
# HILO DE IMPORTACIÓN (para no congelar la UI)
# ══════════════════════════════════════════════════════════════════

class ImportWorker(QThread):
    
    progreso        = Signal(int)
    fila_procesada  = Signal(int, str, str)   # fila, "ok"/"error", mensaje
    terminado       = Signal(int, int)

    def __init__(self, filas: list[dict], carreras_map: dict,
                 usuario_id: int):
        super().__init__()
        self.filas       = filas
        self.carreras    = carreras_map   # nombre_lower → id
        self.usuario_id  = usuario_id

    def run(self):
        insertados = 0
        errores    = 0
        total      = len(self.filas)

        for i, fila in enumerate(self.filas):
            # Resolver carrera
            carrera_nombre = str(fila.get("carrera", "")).strip().lower()
            carrera_id = self.carreras.get(carrera_nombre)
            if not carrera_id:
                errores += 1
                self.fila_procesada.emit(
                    i, "error",
                    f"Carrera '{fila.get('carrera')}' no encontrada."
                )
                self.progreso.emit(int((i + 1) * 100 / total))
                continue

            datos = {
                "dni":                str(fila.get("dni", "")).strip(),
                "codigo_estudiantil": str(fila.get("codigo", "")).strip(),
                "apellidos":          str(fila.get("apellidos", "")).strip(),
                "nombres":            str(fila.get("nombres", "")).strip(),
                "carrera_id":         carrera_id,
                "ciclo_actual":       fila.get("ciclo"),
                "email":              str(fila.get("email", "")).strip(),
                "telefono":           str(fila.get("telefono", "")).strip(),
            }

            resultado = EstudianteService.registrar(datos, self.usuario_id)
            if resultado.ok:
                insertados += 1
                self.fila_procesada.emit(i, "ok", resultado.mensaje)
            else:
                errores += 1
                self.fila_procesada.emit(i, "error", resultado.mensaje)

            self.progreso.emit(int((i + 1) * 100 / total))

        self.terminado.emit(insertados, errores)


# ══════════════════════════════════════════════════════════════════
# DIÁLOGO DE IMPORTACIÓN
# ══════════════════════════════════════════════════════════════════

class ExcelImportDialog(QDialog):

    COLS_PREVIEW = [
        (0, "Fila",      40),
        (1, "DNI",       90),
        (2, "Código",   110),
        (3, "Apellidos",140),
        (4, "Nombres",  130),
        (5, "Carrera",  160),
        (6, "Ciclo",     50),
        (7, "Email",    160),
        (8, "Estado",    80),
        (9, "Mensaje",  200),
    ]

    def __init__(self, sesion, parent=None):
        super().__init__(parent)
        self.sesion     = sesion
        self._ruta      = None
        self._filas     = []       # filas parseadas del Excel
        self._worker    = None

        self.setModal(True)
        self.setMinimumSize(860, 560)
        self.setWindowTitle("Importar estudiantes desde Excel")
        self.setWindowFlags(self.windowFlags() &
                            ~Qt.WindowType.WindowContextHelpButtonHint)

        if not OPENPYXL_OK:
            self._construir_ui_sin_openpyxl()
        else:
            self._construir_ui()

    # ── UI sin openpyxl ───────────────────────────────────────────
    def _construir_ui_sin_openpyxl(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(32, 32, 32, 32)
        msg = QLabel(
            "❌  La librería 'openpyxl' no está instalada.\n\n"
            "Instálala con:\n\n    pip install openpyxl\n\n"
            "Luego reinicia la aplicación."
        )
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(msg)
        btn = QPushButton("Cerrar")
        btn.setObjectName("btn_cancelar")
        btn.clicked.connect(self.reject)
        lay.addWidget(btn, alignment=Qt.AlignmentFlag.AlignRight)

    # ── UI principal ──────────────────────────────────────────────
    def _construir_ui(self):
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(24, 20, 24, 20)
        raiz.setSpacing(0)

        # Título
        lbl_titulo = QLabel("Importar estudiantes desde Excel")
        lbl_titulo.setObjectName("lbl_titulo_dialogo")
        f = QFont(); f.setPointSize(16); f.setWeight(QFont.Weight.Medium)
        lbl_titulo.setFont(f)
        raiz.addWidget(lbl_titulo)

        raiz.addSpacing(6)

        # Instrucción
        self.lbl_instruccion = QLabel(
            "Selecciona un archivo .xlsx con las columnas: "
            "DNI · Código · Apellidos · Nombres · Carrera · Ciclo · Email · Teléfono"
        )
        self.lbl_instruccion.setObjectName("lbl_instruccion")
        self.lbl_instruccion.setWordWrap(True)
        raiz.addWidget(self.lbl_instruccion)

        raiz.addSpacing(14)

        # Selector de archivo
        fila_archivo = QHBoxLayout()

        self.btn_seleccionar = QPushButton("📂  Seleccionar archivo…")
        self.btn_seleccionar.setObjectName("btn_seleccionar")
        self.btn_seleccionar.setFixedHeight(36)
        self.btn_seleccionar.clicked.connect(self._seleccionar_archivo)
        fila_archivo.addWidget(self.btn_seleccionar)

        self.lbl_archivo = QLabel("Ningún archivo seleccionado")
        self.lbl_archivo.setObjectName("lbl_archivo")
        fila_archivo.addWidget(self.lbl_archivo, 1)
        raiz.addLayout(fila_archivo)

        raiz.addSpacing(12)

        # Tabla de previsualización
        self.tbl_preview = self._construir_tabla_preview()
        self.tbl_preview.setObjectName("tbl_preview")
        raiz.addWidget(self.tbl_preview, 1)

        raiz.addSpacing(8)

        # Conteo de filas
        self.lbl_conteo_preview = QLabel("")
        self.lbl_conteo_preview.setObjectName("lbl_conteo_preview")
        raiz.addWidget(self.lbl_conteo_preview)

        raiz.addSpacing(8)

        # Barra de progreso (oculta inicialmente)
        self.barra_progreso = QProgressBar()
        self.barra_progreso.setObjectName("barra_progreso")
        self.barra_progreso.setRange(0, 100)
        self.barra_progreso.setFixedHeight(8)
        self.barra_progreso.setVisible(False)
        raiz.addWidget(self.barra_progreso)

        # Resultado
        self.lbl_resultado = QLabel("")
        self.lbl_resultado.setObjectName("lbl_resultado")
        self.lbl_resultado.setVisible(False)
        self.lbl_resultado.setWordWrap(True)
        raiz.addWidget(self.lbl_resultado)

        raiz.addSpacing(12)

        # Botones
        pie = QHBoxLayout()
        pie.addStretch()

        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_cancelar.setObjectName("btn_cancelar")
        self.btn_cancelar.setFixedSize(100, 36)
        self.btn_cancelar.clicked.connect(self.reject)
        pie.addWidget(self.btn_cancelar)

        pie.addSpacing(8)

        self.btn_importar = QPushButton("↑  Importar filas válidas")
        self.btn_importar.setObjectName("btn_importar")
        self.btn_importar.setFixedSize(180, 36)
        self.btn_importar.setEnabled(False)
        self.btn_importar.clicked.connect(self._iniciar_importacion)
        pie.addWidget(self.btn_importar)

        raiz.addLayout(pie)

    def _construir_tabla_preview(self) -> QTableWidget:
        tbl = QTableWidget()
        tbl.setColumnCount(len(self.COLS_PREVIEW))
        tbl.setHorizontalHeaderLabels([c[1] for c in self.COLS_PREVIEW])
        tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tbl.setAlternatingRowColors(True)
        tbl.setShowGrid(False)
        tbl.verticalHeader().setVisible(False)
        for idx, _, ancho in self.COLS_PREVIEW:
            tbl.setColumnWidth(idx, ancho)
        tbl.horizontalHeader().setSectionResizeMode(
            9, QHeaderView.ResizeMode.Stretch
        )
        tbl.verticalHeader().setDefaultSectionSize(32)
        return tbl

    # ──────────────────────────────────────────────────────────────
    # FLUJO DE IMPORTACIÓN
    # ──────────────────────────────────────────────────────────────
    def _seleccionar_archivo(self):
        ruta, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar Excel", "",
            "Excel (*.xlsx *.xls)"
        )
        if not ruta:
            return

        self._ruta = ruta
        self.lbl_archivo.setText(os.path.basename(ruta))
        self._parsear_excel(ruta)

    def _parsear_excel(self, ruta: str):
        """Lee el archivo Excel y muestra la previsualización."""
        try:
            wb = openpyxl.load_workbook(ruta, read_only=True, data_only=True)
            ws = wb.active
            filas_raw = list(ws.iter_rows(min_row=2, values_only=True))
            wb.close()
        except Exception as e:
            self.lbl_conteo_preview.setText(f"❌ Error al leer el archivo: {e}")
            return

        self._filas = []
        self.tbl_preview.setRowCount(len(filas_raw))

        errores = 0
        for idx, fila in enumerate(filas_raw):
            # Mapear columnas A-H
            dni       = str(fila[0] or "").strip()
            codigo    = str(fila[1] or "").strip()
            apellidos = str(fila[2] or "").strip()
            nombres   = str(fila[3] or "").strip()
            carrera   = str(fila[4] or "").strip()
            ciclo_raw = fila[5]
            email     = str(fila[6] or "").strip()
            telefono  = str(fila[7] or "").strip()

            try:
                ciclo = int(ciclo_raw) if ciclo_raw else None
            except (ValueError, TypeError):
                ciclo = None

            # Validación básica
            estado, mensaje = "ok", "OK"
            if not dni or len(dni) != 8 or not dni.isdigit():
                estado, mensaje = "error", "DNI inválido (debe ser 8 dígitos)"
                errores += 1
            elif not codigo:
                estado, mensaje = "error", "Código vacío"
                errores += 1
            elif not apellidos or not nombres:
                estado, mensaje = "error", "Nombre o apellidos vacíos"
                errores += 1
            elif not carrera:
                estado, mensaje = "error", "Carrera vacía"
                errores += 1

            self._filas.append({
                "dni": dni, "codigo": codigo,
                "apellidos": apellidos, "nombres": nombres,
                "carrera": carrera, "ciclo": ciclo,
                "email": email, "telefono": telefono,
                "_estado": estado, "_mensaje": mensaje,
            })

            # Rellenar tabla
            vals = [str(idx + 2), dni, codigo, apellidos,
                    nombres, carrera, str(ciclo or ""), email,
                    "✅ OK" if estado == "ok" else "❌ Error", mensaje]

            for col, val in enumerate(vals):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter |
                                      Qt.AlignmentFlag.AlignLeft)
                if col == 8:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    item.setForeground(
                        QColor("#1D9E75") if estado == "ok"
                        else QColor("#C0392B")
                    )
                self.tbl_preview.setItem(idx, col, item)

        validas = len(self._filas) - errores
        self.lbl_conteo_preview.setText(
            f"{len(self._filas)} filas encontradas  ·  "
            f"✅ {validas} válidas  ·  ❌ {errores} con errores"
        )
        self.btn_importar.setEnabled(validas > 0)

    def _iniciar_importacion(self):
        """Crea el ImportWorker y lanza la importación en segundo plano."""
        filas_validas = [f for f in self._filas if f["_estado"] == "ok"]
        if not filas_validas:
            return

        # Mapa carrera_nombre_lower → id
        carreras_map = {
            c["nombre"].lower(): c["id"]
            for c in EstudianteService.listar_carreras()
        }

        self.btn_importar.setEnabled(False)
        self.btn_seleccionar.setEnabled(False)
        self.barra_progreso.setValue(0)
        self.barra_progreso.setVisible(True)

        self._worker = ImportWorker(
            filas_validas, carreras_map, self.sesion.usuario_id
        )
        self._worker.progreso.connect(self.barra_progreso.setValue)
        self._worker.fila_procesada.connect(self._on_fila_procesada)
        self._worker.terminado.connect(self._on_importacion_terminada)
        self._worker.start()

    def _on_fila_procesada(self, indice: int, estado: str, mensaje: str):
        """Actualiza la fila en la tabla de previsualización."""
        col_estado  = 8
        col_mensaje = 9
        filas_validas_indices = [
            i for i, f in enumerate(self._filas) if f["_estado"] == "ok"
        ]
        if indice < len(filas_validas_indices):
            fila_tabla = filas_validas_indices[indice]
            item_est = QTableWidgetItem(
                "✅ Insertado" if estado == "ok" else "❌ Error"
            )
            item_est.setForeground(
                QColor("#1D9E75") if estado == "ok" else QColor("#C0392B")
            )
            item_est.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tbl_preview.setItem(fila_tabla, col_estado, item_est)
            self.tbl_preview.setItem(
                fila_tabla, col_mensaje, QTableWidgetItem(mensaje)
            )

    def _on_importacion_terminada(self, insertados: int, errores: int):
        self.barra_progreso.setValue(100)
        self.lbl_resultado.setText(
            f"✅ Importación completada: {insertados} estudiante(s) insertado(s), "
            f"{errores} fila(s) con error."
        )
        self.lbl_resultado.setStyleSheet(
            "background:#e8f8f2; color:#1D9E75; border:1px solid #a8e6cf;"
            "border-radius:7px; padding:8px 12px;"
        )
        self.lbl_resultado.setVisible(True)
        self.btn_cancelar.setText("Cerrar")
        if insertados > 0:
            # Cerrar automáticamente al hacer clic en Cerrar
            self.btn_cancelar.clicked.disconnect()
            self.btn_cancelar.clicked.connect(self.accept)
