from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont

from services.inscripcion_masiva_service import InscripcionMasivaService
from utils.importar_inscritos import generar_plantilla_inscripcion


class InscripcionMasivaDialog(QDialog):
    """
    Diálogo para inscribir estudiantes de forma masiva a un taller
    a partir de un archivo Excel, con validación previa fila por fila.

    USO:
        dlg = InscripcionMasivaDialog(taller_id=5, sesion=sesion_usuario, parent=self)
        if dlg.exec():
            ...  # refrescar la lista de inscritos (hubo al menos 1 inscripción)
    """

    COLUMNAS = [
        (0, "Fila",     50),
        (1, "DNI",     100),
        (2, "Nombre",  220),
        (3, "Estado",   90),
        (4, "Detalle", 260),
    ]

    def __init__(self, taller_id: int, sesion, parent=None):
        super().__init__(parent)
        self.taller_id = taller_id
        self.sesion = sesion
        self._resultado_validacion = None
        self._se_inscribio_alguno = False

        self.setModal(True)
        self.setMinimumSize(760, 540)
        self.setWindowTitle("Inscripción masiva desde Excel")
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint
        )
        self._construir_ui()

    # ──────────────────────────────────────────────────────────
    def _construir_ui(self):
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(22, 18, 22, 18)

        lbl_titulo = QLabel("Inscripción masiva de estudiantes")
        f = QFont(); f.setPointSize(15); f.setWeight(QFont.Weight.Medium)
        lbl_titulo.setFont(f)
        raiz.addWidget(lbl_titulo)
        raiz.addSpacing(4)

        lbl_ayuda = QLabel(
            "Selecciona un archivo Excel (.xlsx) con una columna 'DNI'. "
            "¿No tienes el formato? Descarga la plantilla."
        )
        lbl_ayuda.setWordWrap(True)
        lbl_ayuda.setObjectName("lbl_ayuda_masiva")
        raiz.addWidget(lbl_ayuda)
        raiz.addSpacing(10)

        # Barra de acciones de archivo
        fila_archivo = QHBoxLayout()

        self.btn_plantilla = QPushButton("⬇ Descargar plantilla")
        self.btn_plantilla.setFixedHeight(32)
        self.btn_plantilla.clicked.connect(self._descargar_plantilla)
        fila_archivo.addWidget(self.btn_plantilla)

        fila_archivo.addSpacing(6)

        self.btn_seleccionar = QPushButton("📂 Seleccionar archivo Excel...")
        self.btn_seleccionar.setFixedHeight(32)
        self.btn_seleccionar.clicked.connect(self._seleccionar_archivo)
        fila_archivo.addWidget(self.btn_seleccionar)

        fila_archivo.addStretch()
        raiz.addLayout(fila_archivo)
        raiz.addSpacing(10)

        self.lbl_ruta = QLabel("Ningún archivo seleccionado.")
        self.lbl_ruta.setObjectName("lbl_ruta_archivo")
        raiz.addWidget(self.lbl_ruta)
        raiz.addSpacing(10)

        # Tabla de previsualización
        self.tbl_preview = QTableWidget()
        self.tbl_preview.setColumnCount(len(self.COLUMNAS))
        self.tbl_preview.setHorizontalHeaderLabels([c[1] for c in self.COLUMNAS])
        self.tbl_preview.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_preview.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.tbl_preview.setAlternatingRowColors(True)
        self.tbl_preview.setShowGrid(False)
        self.tbl_preview.verticalHeader().setVisible(False)
        for idx, _, ancho in self.COLUMNAS:
            self.tbl_preview.setColumnWidth(idx, ancho)
        self.tbl_preview.horizontalHeader().setSectionResizeMode(
            4, QHeaderView.ResizeMode.Stretch)
        raiz.addWidget(self.tbl_preview, 1)

        raiz.addSpacing(8)
        self.lbl_resumen = QLabel("")
        self.lbl_resumen.setObjectName("lbl_resumen_masiva")
        raiz.addWidget(self.lbl_resumen)
        raiz.addSpacing(10)

        # Pie
        pie = QHBoxLayout()
        pie.addStretch()

        self.btn_cancelar = QPushButton("Cerrar")
        self.btn_cancelar.setFixedSize(100, 34)
        self.btn_cancelar.clicked.connect(self._cerrar)
        pie.addWidget(self.btn_cancelar)

        pie.addSpacing(8)

        self.btn_procesar = QPushButton("Inscribir válidos")
        self.btn_procesar.setObjectName("btn_procesar_masiva")
        self.btn_procesar.setFixedSize(150, 34)
        self.btn_procesar.setEnabled(False)
        self.btn_procesar.clicked.connect(self._procesar)
        pie.addWidget(self.btn_procesar)

        raiz.addLayout(pie)

    # ──────────────────────────────────────────────────────────
    def _descargar_plantilla(self):
        ruta, _ = QFileDialog.getSaveFileName(
            self, "Guardar plantilla", "plantilla_inscripcion.xlsx",
            "Excel (*.xlsx)"
        )
        if not ruta:
            return
        try:
            generar_plantilla_inscripcion(ruta)
            QMessageBox.information(self, "Éxito", "Plantilla descargada correctamente.")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo generar la plantilla:\n{e}")

    def _seleccionar_archivo(self):
        ruta, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar archivo de inscripción masiva",
            "", "Excel (*.xlsx)"
        )
        if not ruta:
            return

        self.lbl_ruta.setText(ruta)

        try:
            self._resultado_validacion = InscripcionMasivaService.validar_archivo(
                self.taller_id, ruta
            )
        except ValueError as e:
            QMessageBox.warning(self, "Archivo inválido", str(e))
            self._resultado_validacion = None
            self.btn_procesar.setEnabled(False)
            self.tbl_preview.setRowCount(0)
            self.lbl_resumen.setText("")
            return
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Error inesperado al leer el archivo:\n{e}"
            )
            return

        self._poblar_preview()

    def _poblar_preview(self):
        r = self._resultado_validacion
        self.tbl_preview.setRowCount(len(r.filas))

        for fila_idx, fv in enumerate(r.filas):
            valores = [
                str(fv.fila), fv.dni, fv.nombre,
                "✓ Válido" if fv.valido else "✗ Error", fv.motivo
            ]

            for col, val in enumerate(valores):
                item = QTableWidgetItem(val)
                if col in (0, 3):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                if fv.valido:
                    item.setForeground(QColor("#1D9E75"))
                    item.setBackground(QColor("#E8F8F2"))
                else:
                    item.setForeground(QColor("#B3261E"))
                    item.setBackground(QColor("#FBE9E7"))

                self.tbl_preview.setItem(fila_idx, col, item)

        n_validas = len(r.validas)
        n_invalidas = len(r.invalidas)
        self.lbl_resumen.setText(
            f"<b>{n_validas}</b> lista(s) para inscribir &nbsp;|&nbsp; "
            f"<b>{n_invalidas}</b> con errores &nbsp;|&nbsp; "
            f"Cupo disponible en el taller: <b>{r.cupo_disponible}</b>"
        )

        self.btn_procesar.setEnabled(n_validas > 0)

    # ──────────────────────────────────────────────────────────
    def _procesar(self):
        if not self._resultado_validacion:
            return

        validas = self._resultado_validacion.validas
        if not validas:
            return

        r = QMessageBox.question(
            self, "Confirmar inscripción masiva",
            f"Se inscribirán {len(validas)} estudiante(s) al taller.\n"
            f"¿Deseas continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if r != QMessageBox.StandardButton.Yes:
            return

        self.btn_procesar.setEnabled(False)
        self.btn_seleccionar.setEnabled(False)
        self.setCursor(Qt.CursorShape.WaitCursor)

        resultado = InscripcionMasivaService.procesar_inscripciones(
            self.taller_id, validas, self.sesion.usuario_id
        )

        self.unsetCursor()
        self._se_inscribio_alguno = resultado.exitosas > 0

        mensaje = (
            f"Inscripciones exitosas: {resultado.exitosas}\n"
            f"Inscripciones fallidas: {resultado.fallidas}"
        )
        if resultado.fallidas:
            detalle_fallidas = "\n".join(
                f"• {dni} ({nombre}): {msg}"
                for dni, nombre, msg in resultado.detalle
                if msg != "Inscrito correctamente"
            )
            mensaje += f"\n\nDetalle de fallos:\n{detalle_fallidas}"

        QMessageBox.information(self, "Proceso finalizado", mensaje)
        self.accept()

    def _cerrar(self):
        if self._se_inscribio_alguno:
            self.accept()
        else:
            self.reject()
