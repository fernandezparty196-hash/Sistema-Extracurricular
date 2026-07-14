"""
ui/lista_aptos/lista_aptos_widget.py   ──   EP-05 Lista de Aptos (CON EXPORTACIÓN)
═════════════════════════════════════════════════════════════════

Incluye funcionalidad de exportación a Excel y PDF.
"""

from PySide6.QtCore    import Qt
from PySide6.QtGui     import QColor, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QMessageBox, QComboBox,
    QGroupBox, QHeaderView, QFileDialog
)
from PySide6.QtPrintSupport import QPrinter, QPrintDialog
from PySide6.QtGui import QPageSize

from services.lista_aptos_service import ListaAptosService
from services.auth_service import SesionUsuario
from utils.exportar_aptos import ExportarExcel
from utils.exportar_pdf import ExportarPDF


class ListaAptosWidget(QWidget):
    """Widget principal para lista de aptos CON EXPORTACIÓN."""

    def __init__(self, sesion: SesionUsuario):
        super().__init__()
        self.sesion = sesion
        self.datos_generados = None
        self.taller_seleccionado = None

        self._construir_ui()
        self._cargar_datos()

    # ══════════════════════════════════════════════════════════════
    # CONSTRUCCIÓN DE UI
    # ══════════════════════════════════════════════════════════════

    def _construir_ui(self) -> None:
        """Construye toda la interfaz."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(2)

        # ── Panel de control ──────────────────────────────────────
        layout.addWidget(self._crear_panel_control())

        # ── Tabla de resultados ───────────────────────────────────
        layout.addWidget(self._crear_grupo_resultados())

        # ── Botones de acción ─────────────────────────────────────
        layout.addWidget(self._crear_grupo_acciones())

        layout.addStretch()

    def _crear_panel_control(self) -> QGroupBox:
        """Panel para seleccionar taller y generar lista."""
        grupo = QGroupBox("Seleccionar Taller")
        layout = QHBoxLayout(grupo)

        lbl_taller = QLabel("Taller:")
        self.cmb_taller = QComboBox()
        self.cmb_taller.currentIndexChanged.connect(self._on_taller_cambio)

        self.btn_generar = QPushButton("🔄 Generar Lista")
        self.btn_generar.clicked.connect(self._on_generar_lista)

        layout.addWidget(lbl_taller)
        layout.addWidget(self.cmb_taller, stretch=1)
        layout.addWidget(self.btn_generar)

        return grupo

    def _crear_grupo_resultados(self) -> QGroupBox:
        """Grupo con información de resultados."""
        grupo = QGroupBox("Resultados")
        layout = QVBoxLayout(grupo)

        info_layout = QHBoxLayout()
        self.lbl_info = QLabel("Selecciona un taller para generar la lista")
        self.lbl_info.setStyleSheet("color: #73726c; font-size: 12px;")
        info_layout.addWidget(self.lbl_info)
        info_layout.addStretch()
        layout.addLayout(info_layout)

        self.tabla_aptos = QTableWidget()
        self.tabla_aptos.setColumnCount(7)
        self.tabla_aptos.setHorizontalHeaderLabels([
            "Nombre", "DNI", "Código", "Carrera", "Asistencia", "Umbral", "Estado"
        ])
        self.tabla_aptos.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        layout.addWidget(self.tabla_aptos)

        return grupo

    def _crear_grupo_acciones(self) -> QGroupBox:
        """Botones de acción con exportación funcional."""
        grupo = QGroupBox("Acciones")
        layout = QHBoxLayout(grupo)

        self.btn_exportar_excel = QPushButton("📊 Exportar a Excel")
        self.btn_exportar_excel.clicked.connect(self._on_exportar_excel)

        self.btn_exportar_pdf = QPushButton("📄 Exportar a PDF")
        self.btn_exportar_pdf.clicked.connect(self._on_exportar_pdf)

        self.btn_imprimir = QPushButton("🖨️ Imprimir")
        self.btn_imprimir.clicked.connect(self._on_imprimir)

        self.btn_actualizar = QPushButton("🔄 Actualizar")
        self.btn_actualizar.clicked.connect(self._cargar_datos)

        layout.addWidget(self.btn_exportar_excel)
        layout.addWidget(self.btn_exportar_pdf)
        layout.addWidget(self.btn_imprimir)
        layout.addStretch()
        layout.addWidget(self.btn_actualizar)

        return grupo

    # ══════════════════════════════════════════════════════════════
    # CARGA DE DATOS
    # ══════════════════════════════════════════════════════════════

    def _cargar_datos(self) -> None:
        """Carga lista de talleres activos."""
        talleres = ListaAptosService.listar_talleres_activos()

        self.cmb_taller.blockSignals(True)
        self.cmb_taller.clear()
        self.cmb_taller.addItem("Selecciona un taller...", None)

        if not talleres:
            self.cmb_taller.addItem("No hay talleres activos", None)
            self.cmb_taller.setEnabled(False)
            self.btn_generar.setEnabled(False)
        else:
            for taller in talleres:
                texto = f"{taller['codigo']} - {taller['nombre']}"
                self.cmb_taller.addItem(
                    texto,
                    {
                        "id": taller["id"],
                        "umbral": taller["umbral"],
                        "inscritos": taller["inscritos"],
                    }
                )
            self.cmb_taller.setEnabled(True)
            self.btn_generar.setEnabled(True)

        self.cmb_taller.blockSignals(False)

    # ══════════════════════════════════════════════════════════════
    # EVENTOS
    # ══════════════════════════════════════════════════════════════

    def _on_taller_cambio(self) -> None:
        """Cuando cambia la selección de taller."""
        datos = self.cmb_taller.currentData()
        if datos:
            self.taller_seleccionado = datos
            self.datos_generados = None
            self._limpiar_tabla()
            self.lbl_info.setText(
                f"Umbral: {datos['umbral']}%  |  Inscritos: {datos['inscritos']}"
            )
        else:
            self.lbl_info.setText("Selecciona un taller para generar la lista")

    def _on_generar_lista(self) -> None:
        """Genera la lista de aptos."""

        
        if not self.taller_seleccionado:
            QMessageBox.warning(self, "Error", "Selecciona un taller primero")
            return

        taller_id = self.taller_seleccionado["id"]

        self.btn_generar.setEnabled(False)
        self.btn_generar.setText("⏳ Generando...")

        try:
            resultado = ListaAptosService.generar_lista(
                taller_id,
                self.sesion.usuario_id
            )

            if not resultado.ok:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Error al generar:\n{resultado.mensaje}"
                )
                return

            self.datos_generados = resultado
            self._mostrar_resultados(resultado)

            QMessageBox.information(self, "Éxito", resultado.mensaje)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error: {str(e)}")
        finally:
            self.btn_generar.setEnabled(True)
            self.btn_generar.setText("🔄 Generar Lista")

    def _mostrar_resultados(self, resultado) -> None:
        """Muestra resultados en la tabla."""
        self._limpiar_tabla()

        if not resultado.lista:
            return

        todos = resultado.lista.get("aptos", []) + resultado.lista.get("desaptos", [])
        self.tabla_aptos.setRowCount(len(todos))

        for fila, estudiante in enumerate(todos):
            # Llenar datos
            self.tabla_aptos.setItem(fila, 0, QTableWidgetItem(estudiante["nombre_completo"]))
            self.tabla_aptos.setItem(fila, 1, QTableWidgetItem(estudiante["dni"] or "N/A"))
            self.tabla_aptos.setItem(fila, 2, QTableWidgetItem(estudiante["codigo_estudiantil"] or "N/A"))
            self.tabla_aptos.setItem(fila, 3, QTableWidgetItem(estudiante["carrera"]))

            asistencia_str = f"{estudiante['asistencia_porcentaje']:.1f}%"
            item_asistencia = QTableWidgetItem(asistencia_str)
            item_asistencia.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tabla_aptos.setItem(fila, 4, item_asistencia)

            umbral_str = f"{resultado.datos['umbral']}%"
            item_umbral = QTableWidgetItem(umbral_str)
            item_umbral.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tabla_aptos.setItem(fila, 5, item_umbral)

            estado_texto = "✅ APTO" if estudiante["apto"] else "❌ NO APTO"
            item_estado = QTableWidgetItem(estado_texto)
            item_estado.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            if estudiante["apto"]:
                item_estado.setBackground(QColor("#e8f8f2"))
                item_estado.setForeground(QColor("#1D9E75"))
            else:
                item_estado.setBackground(QColor("#fdf0ee"))
                item_estado.setForeground(QColor("#C0392B"))

            self.tabla_aptos.setItem(fila, 6, item_estado)
            from PySide6.QtWidgets import QHeaderView

            header = self.tabla_aptos.horizontalHeader()
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        self._actualizar_informacion(resultado)

    def _actualizar_informacion(self, resultado) -> None:
        """Actualiza información resumida."""
        datos = resultado.datos
        aptos = datos["aptos_count"]
        desaptos = datos["desaptos_count"]
        total = aptos + desaptos

        pct_aptos = (aptos / total * 100) if total > 0 else 0

        info_texto = (
            f"📊 {aptos} aptos ({pct_aptos:.1f}%)  |  "
            f"❌ {desaptos} desaptos  |  "
            f"Umbral: {datos['umbral']}%"
        )
        self.lbl_info.setText(info_texto)

    def _limpiar_tabla(self) -> None:
        """Limpia la tabla."""
        self.tabla_aptos.setRowCount(0)
        self.lbl_info.setText("Selecciona un taller para generar la lista")

    # ══════════════════════════════════════════════════════════════
    # EXPORTACIÓN
    # ══════════════════════════════════════════════════════════════

    def _on_exportar_excel(self) -> None:
        """Exporta a Excel."""
        if not self.datos_generados:
            QMessageBox.warning(self, "Error", "Genera una lista primero")
            return

        try:
            # Usar diálogo de archivo
            archivo, _ = QFileDialog.getSaveFileName(
                self,
                "Guardar como Excel",
                f"Lista_Aptos_{self.datos_generados.datos['taller_nombre']}.xlsx",
                "Archivos Excel (*.xlsx)"
            )

            if not archivo:
                return

            resultado = ExportarExcel.lista_aptos(
                datos=self.datos_generados.datos,
                estudiantes=self.datos_generados.lista,
                ruta=archivo
            )

            if resultado:
                QMessageBox.information(
                    self,
                    "Éxito",
                    f"Archivo guardado:\n{archivo}"
                )
            else:
                QMessageBox.critical(
                    self,
                    "Error",
                    "No se pudo exportar a Excel"
                )

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error: {str(e)}")

    def _on_exportar_pdf(self) -> None:
        """Exporta a PDF."""
        if not self.datos_generados:
            QMessageBox.warning(self, "Error", "Genera una lista primero")
            return

        try:
            archivo, _ = QFileDialog.getSaveFileName(
                self,
                "Guardar como PDF",
                f"Lista_Aptos_{self.datos_generados.datos['taller_nombre']}.pdf",
                "Archivos PDF (*.pdf)"
            )

            if not archivo:
                return

            resultado = ExportarPDF.lista_aptos(
                datos=self.datos_generados.datos,
                estudiantes=self.datos_generados.lista,
                ruta=archivo
            )

            if resultado:
                QMessageBox.information(
                    self,
                    "Éxito",
                    f"Archivo guardado:\n{archivo}"
                )
            else:
                QMessageBox.critical(
                    self,
                    "Error",
                    "No se pudo exportar a PDF"
                )

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error: {str(e)}")

    def _on_imprimir(self) -> None:
        """Imprime la tabla."""
        if not self.datos_generados:
            QMessageBox.warning(self, "Error", "Genera una lista primero")
            return

        try:
            printer = QPrinter()
            dialog = QPrintDialog(printer, self)

            if dialog.exec() == QFileDialog.Accepted:
                # Aquí irá la lógica de impresión
                QMessageBox.information(self, "Info", "Impresión en desarrollo")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error: {str(e)}")