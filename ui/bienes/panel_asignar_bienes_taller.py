"""
ui/bienes/panel_asignar_bienes_taller.py   ──   Asignación de Bienes a Talleres
═════════════════════════════════════════════════════════════════════════════

RF-31: Lista de bienes ya existe
RF-33: Registrar devolución de bien (estado: Bueno/Regular/Malo)
RF-34: Cambiar estado de bien
RF-35: Alertas visuales de bienes vencidos/dañados
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QLineEdit, QMessageBox,
    QHeaderView, QLabel, QComboBox, QSpinBox, QDialog,
    QTextEdit, QFrame
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont, QBrush

from datetime import date
from services.asignacion_bien_taller_service import AsignacionBienTallerService
from services.taller_service import TallerService


class PanelAsignarBienesTaller(QWidget):
    """
    Panel para asignar bienes a talleres extracurriculares.
    
    FLUJO:
      1. Seleccionar bien disponible
      2. Asignar a taller con plazo de devolución
      3. Registrar devolución cuando se devuelve
      4. Ver alertas de vencidos/dañados
    """

    def __init__(self, sesion_usuario, parent=None):
        super().__init__(parent)
        self.sesion = sesion_usuario
        self.bien_seleccionado_id = None
        self._timer = QTimer(singleShot=True, interval=300)
        self._timer.timeout.connect(self._filtrar_tabla)

        self._configurar_estilos()
        self._construir_ui()
        self._cargar_datos()

    def _configurar_estilos(self):
        """Configura estilos CSS."""
        self.setStyleSheet("""
            QWidget {
                background-color: #f8f7f4;
            }
            QLabel#titulo {
                font-size: 18px;
                font-weight: bold;
                color: #1a1a1a;
            }
            QLineEdit, QComboBox, QSpinBox {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 8px;
                min-height: 32px;
            }
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
                min-height: 32px;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
            QPushButton#btnAsignar {
                background-color: #10b981;
            }
            QPushButton#btnAsignar:hover {
                background-color: #059669;
            }
            QPushButton#btnDevolver {
                background-color: #f59e0b;
            }
            QPushButton#btnDevolver:hover {
                background-color: #d97706;
            }
            QTableWidget {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            QHeaderView::section {
                background-color: #2563eb;
                color: white;
                padding: 8px;
                font-weight: bold;
            }
        """)

    def _construir_ui(self):
        """Construye la interfaz."""
        raiz = QVBoxLayout()
        raiz.setSpacing(15)
        raiz.setContentsMargins(20, 20, 20, 20)

        # ── TÍTULO ───────────────────────────────────────────────
        titulo = QLabel("Asignación de Bienes a Talleres")
        titulo.setObjectName("titulo")
        raiz.addWidget(titulo)

        # ── PANEL DE ALERTAS (RF-35) ────────────────────────────
        self.lbl_alertas = QLabel("")
        self.lbl_alertas.setStyleSheet(
            "background-color: #fee2e2; color: #991b1b; padding: 12px; "
            "border-radius: 4px; font-weight: bold; border: 2px solid #fecaca;"
        )
        self.lbl_alertas.setWordWrap(True)
        self.lbl_alertas.setVisible(False)
        raiz.addWidget(self.lbl_alertas)

        # ── BOTONES ──────────────────────────────────────────────
        botones = QHBoxLayout()

        self.btn_asignar = QPushButton("✚ Asignar a Taller")
        self.btn_asignar.setObjectName("btnAsignar")
        self.btn_asignar.setEnabled(False)
        self.btn_asignar.clicked.connect(self._asignar_bien)
        botones.addWidget(self.btn_asignar)

        self.btn_devolver = QPushButton("📥 Registrar Devolución")
        self.btn_devolver.setObjectName("btnDevolver")
        self.btn_devolver.setEnabled(False)
        self.btn_devolver.clicked.connect(self._devolver_bien)
        botones.addWidget(self.btn_devolver)

        self.btn_refrescar = QPushButton("🔄 Refrescar")
        self.btn_refrescar.clicked.connect(self._cargar_datos)
        botones.addWidget(self.btn_refrescar)

        botones.addStretch()
        raiz.addLayout(botones)

        # ── BÚSQUEDA ─────────────────────────────────────────────
        busqueda = QHBoxLayout()
        busqueda.addWidget(QLabel("🔍 Buscar:"))
        self.inp_buscar = QLineEdit()
        self.inp_buscar.setPlaceholderText("Código o descripción...")
        self.inp_buscar.textChanged.connect(self._timer.start)
        busqueda.addWidget(self.inp_buscar)
        busqueda.addStretch()
        raiz.addLayout(busqueda)

        # ── TABLA DE BIENES ──────────────────────────────────────
        raiz.addWidget(QLabel("Bienes Disponibles:"))
        self.tabla_bienes = QTableWidget()
        self.tabla_bienes.setColumnCount(6)
        self.tabla_bienes.setHorizontalHeaderLabels([
            "Código", "Descripción", "Estado", "Valor", "Disponibilidad", "Acción"
        ])

        header = self.tabla_bienes.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)

        self.tabla_bienes.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla_bienes.setSelectionMode(QTableWidget.SingleSelection)
        self.tabla_bienes.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla_bienes.setAlternatingRowColors(True)
        self.tabla_bienes.verticalHeader().setVisible(False)
        self.tabla_bienes.itemSelectionChanged.connect(self._on_seleccionar_bien)

        raiz.addWidget(self.tabla_bienes, 1)

        # ── INFORMACIÓN DEL BIEN ──────────────────────────────────
        raiz.addWidget(QLabel("Información del Bien:"))
        self.lbl_info_bien = QLabel("Selecciona un bien para ver detalles")
        self.lbl_info_bien.setStyleSheet(
            "background-color: white; border: 1px solid #ddd; padding: 10px; "
            "border-radius: 4px;"
        )
        self.lbl_info_bien.setWordWrap(True)
        raiz.addWidget(self.lbl_info_bien)

        self.setLayout(raiz)

    def _cargar_datos(self):
        """Carga datos."""
        self._cargar_bienes()
        self._mostrar_alertas()

    def _cargar_bienes(self):
        """Carga tabla de bienes."""
        # Obtener bienes disponibles y asignados
        disponibles = AsignacionBienTallerService.obtener_bienes_disponibles()
        asignados = AsignacionBienTallerService.obtener_bienes_asignados()

        bienes = disponibles + asignados

        self.tabla_bienes.setRowCount(len(bienes))

        for row, bien in enumerate(bienes):
            # Código
            item = QTableWidgetItem(bien["codigo"])
            item.setData(Qt.UserRole, bien["id"])
            self.tabla_bienes.setItem(row, 0, item)

            # Descripción
            item = QTableWidgetItem(bien["descripcion"])
            self.tabla_bienes.setItem(row, 1, item)

            # Estado Físico
            item = QTableWidgetItem(bien["estado_bien"])
            item.setTextAlignment(Qt.AlignCenter)
            if bien["estado_bien"] == "Malo":
                item.setForeground(QColor("#991b1b"))
                item.setBackground(QBrush(QColor("#fee2e2")))
            elif bien["estado_bien"] == "Regular":
                item.setForeground(QColor("#92400e"))
                item.setBackground(QBrush(QColor("#fef3c7")))
            else:
                item.setForeground(QColor("#065f46"))
                item.setBackground(QBrush(QColor("#ecfdf5")))
            self.tabla_bienes.setItem(row, 2, item)

            # Valor
            item = QTableWidgetItem(f"${bien['valor']:.2f}")
            item.setTextAlignment(Qt.AlignRight)
            self.tabla_bienes.setItem(row, 3, item)

            # Disponibilidad
            item = QTableWidgetItem(bien["estado_disponibilidad"])
            item.setTextAlignment(Qt.AlignCenter)
            if bien["estado_disponibilidad"] == "Disponible":
                item.setForeground(QColor("#065f46"))
                item.setBackground(QBrush(QColor("#ecfdf5")))
            elif bien["estado_disponibilidad"] == "Asignado":
                item.setForeground(QColor("#dc2626"))
                item.setBackground(QBrush(QColor("#fee2e2")))
            else:
                item.setForeground(QColor("#0369a1"))
                item.setBackground(QBrush(QColor("#cffafe")))
            self.tabla_bienes.setItem(row, 4, item)

            # Acción
            item = QTableWidgetItem("Ver")
            item.setForeground(QColor("#2563eb"))
            self.tabla_bienes.setItem(row, 5, item)

    def _mostrar_alertas(self):
        """Muestra alertas RF-35."""
        alertas = AsignacionBienTallerService.obtener_alertas_bienes()

        if alertas["total_alertas"] > 0:
            mensaje = f"🔴 {alertas['total_alertas']} ALERTA(S):\n\n"

            if alertas["vencidos"]:
                mensaje += f"⏰ {len(alertas['vencidos'])} bien(es) VENCIDO(S):\n"
                for v in alertas["vencidos"][:3]:
                    mensaje += f"   • {v['bien_codigo']}: {v['dias_vencidos']} días vencido\n"
                if len(alertas["vencidos"]) > 3:
                    mensaje += f"   ... y {len(alertas['vencidos'])-3} más\n"
                mensaje += "\n"

            if alertas["dañados"]:
                mensaje += f"💔 {len(alertas['dañados'])} bien(es) DAÑADO(S):\n"
                for d in alertas["dañados"][:3]:
                    mensaje += f"   • {d['bien_codigo']}: {d['bien_descripcion']}\n"
                if len(alertas["dañados"]) > 3:
                    mensaje += f"   ... y {len(alertas['dañados'])-3} más\n"
                mensaje += "\n"

            if alertas["en_mantenimiento"]:
                mensaje += f"🔧 {len(alertas['en_mantenimiento'])} bien(es) EN MANTENIMIENTO:\n"
                for m in alertas["en_mantenimiento"][:2]:
                    mensaje += f"   • {m['bien_codigo']}\n"
                if len(alertas["en_mantenimiento"]) > 2:
                    mensaje += f"   ... y {len(alertas['en_mantenimiento'])-2} más\n"

            self.lbl_alertas.setText(mensaje)
            self.lbl_alertas.setVisible(True)
        else:
            self.lbl_alertas.setVisible(False)

    def _on_seleccionar_bien(self):
        """Cuando selecciona un bien."""
        rows = self.tabla_bienes.selectedIndexes()
        if not rows:
            self.bien_seleccionado_id = None
            self.btn_asignar.setEnabled(False)
            self.btn_devolver.setEnabled(False)
            return

        row = rows[0].row()
        bien_id = self.tabla_bienes.item(row, 0).data(Qt.UserRole)
        self.bien_seleccionado_id = bien_id

        # Obtener bien
        bien = AsignacionBienTallerService.obtener_bien_por_id(bien_id)

        if bien:
            # Habilitar botones según estado
            self.btn_asignar.setEnabled(bien["estado_disponibilidad"] == "Disponible")
            self.btn_devolver.setEnabled(bien["estado_disponibilidad"] == "Asignado")

            # Mostrar información
            info = f"""
            <b>Código:</b> {bien['codigo']}<br>
            <b>Descripción:</b> {bien['descripcion']}<br>
            <b>Estado Físico:</b> {bien['estado_bien']}<br>
            <b>Valor:</b> ${bien['valor']:.2f}<br>
            <b>Disponibilidad:</b> <b style="color: {'#065f46' if bien['estado_disponibilidad'] == 'Disponible' else '#dc2626'};">{bien['estado_disponibilidad']}</b><br>
            <b>Última Actualización:</b> {bien['updated_at']}
            """
            self.lbl_info_bien.setText(info)

    def _filtrar_tabla(self):
        """Filtra tabla."""
        buscar = self.inp_buscar.text().lower()
        for row in range(self.tabla_bienes.rowCount()):
            codigo = self.tabla_bienes.item(row, 0).text().lower()
            descripcion = self.tabla_bienes.item(row, 1).text().lower()
            visible = buscar in codigo or buscar in descripcion
            self.tabla_bienes.setRowHidden(row, not visible)

    def _asignar_bien(self):
        """Abre dialog para asignar bien."""
        if not self.bien_seleccionado_id:
            return

        dialogo = DialogoAsignarBien(
            bien_id=self.bien_seleccionado_id,
            usuario_id=self.sesion.usuario_id,
            parent=self
        )

        if dialogo.exec():
            self._cargar_datos()

    def _devolver_bien(self):
        """Abre dialog para registrar devolución."""
        if not self.bien_seleccionado_id:
            return

        dialogo = DialogoDevolverBien(
            bien_id=self.bien_seleccionado_id,
            usuario_id=self.sesion.usuario_id,
            parent=self
        )

        if dialogo.exec():
            self._cargar_datos()


# ══════════════════════════════════════════════════════════════════════════════
# DIALOGS
# ══════════════════════════════════════════════════════════════════════════════

class DialogoAsignarBien(QDialog):
    """Dialog para asignar bien a taller."""

    def __init__(self, bien_id: int, usuario_id: int, parent=None):
        super().__init__(parent)
        self.bien_id = bien_id
        self.usuario_id = usuario_id

        self.setWindowTitle("Asignar Bien a Taller")
        self.setMinimumSize(450, 300)
        self.setModal(True)

        bien = AsignacionBienTallerService.obtener_bien_por_id(bien_id)

        layout = QVBoxLayout()

        layout.addWidget(QLabel(f"<b>Bien: {bien['codigo']}</b>"))
        layout.addWidget(QLabel(f"Descripción: {bien['descripcion']}"))

        layout.addWidget(QLabel("Selecciona Taller *"))
        self.cmb_taller = QComboBox()

        talleres = TallerService.buscar()
        for taller in talleres:
            self.cmb_taller.addItem(
                f"{taller['nombre']} - {taller['docente']}",
                taller["id"]
            )

        layout.addWidget(self.cmb_taller)

        layout.addWidget(QLabel("Días para Devolver *"))
        self.spn_dias = QSpinBox()
        self.spn_dias.setValue(30)
        self.spn_dias.setMinimum(1)
        self.spn_dias.setMaximum(365)
        layout.addWidget(self.spn_dias)

        layout.addWidget(QLabel("Observaciones"))
        self.txt_obs = QTextEdit()
        self.txt_obs.setMaximumHeight(80)
        layout.addWidget(self.txt_obs)

        layout.addStretch()

        botones = QHBoxLayout()
        botones.addStretch()
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        botones.addWidget(btn_cancelar)

        btn_asignar = QPushButton("✓ Asignar")
        btn_asignar.clicked.connect(self._asignar)
        botones.addWidget(btn_asignar)

        layout.addLayout(botones)
        self.setLayout(layout)

    def _asignar(self):
        """Asigna el bien."""
        taller_id = self.cmb_taller.currentData()
        dias = self.spn_dias.value()
        obs = self.txt_obs.toPlainText().strip()

        resultado = AsignacionBienTallerService.asignar_a_taller(
            bien_id=self.bien_id,
            taller_id=taller_id,
            fecha_limite_dias=dias,
            usuario_id=self.usuario_id,
            observacion=obs
        )

        if resultado.ok:
            QMessageBox.information(self, "Éxito", resultado.mensaje)
            self.accept()
        else:
            QMessageBox.warning(self, "Error", resultado.mensaje)


class DialogoDevolverBien(QDialog):
    """Dialog para registrar devolución (RF-33)."""

    def __init__(self, bien_id: int, usuario_id: int, parent=None):
        super().__init__(parent)
        self.bien_id = bien_id
        self.usuario_id = usuario_id

        self.setWindowTitle("Registrar Devolución")
        self.setMinimumSize(450, 350)
        self.setModal(True)

        bien = AsignacionBienTallerService.obtener_bien_por_id(bien_id)

        layout = QVBoxLayout()

        layout.addWidget(QLabel(f"<b>Bien: {bien['codigo']}</b>"))
        layout.addWidget(QLabel(f"Descripción: {bien['descripcion']}"))
        layout.addWidget(QLabel(f"Estado Actual: {bien['estado_bien']}"))

        layout.addWidget(QLabel("Estado al Retorno * (RF-33)"))
        self.cmb_estado = QComboBox()
        self.cmb_estado.addItems(["Bueno", "Regular", "Malo"])
        layout.addWidget(self.cmb_estado)

        layout.addWidget(QLabel("Observaciones de Devolución"))
        self.txt_obs = QTextEdit()
        self.txt_obs.setMaximumHeight(100)
        self.txt_obs.setPlaceholderText("Ej: Rayones en pantalla, funciona correctamente, etc.")
        layout.addWidget(self.txt_obs)

        layout.addStretch()

        botones = QHBoxLayout()
        botones.addStretch()
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        botones.addWidget(btn_cancelar)

        btn_devolver = QPushButton("✓ Registrar Devolución")
        btn_devolver.clicked.connect(self._devolver)
        botones.addWidget(btn_devolver)

        layout.addLayout(botones)
        self.setLayout(layout)

    def _devolver(self):
        """Registra la devolución."""
        estado = self.cmb_estado.currentText()
        obs = self.txt_obs.toPlainText().strip()

        resultado = AsignacionBienTallerService.registrar_devolucion_taller(
            bien_id=self.bien_id,
            estado_retorno=estado,
            usuario_id=self.usuario_id,
            observacion=obs
        )

        if resultado.ok:
            QMessageBox.information(self, "Éxito", resultado.mensaje)
            self.accept()
        else:
            QMessageBox.warning(self, "Error", resultado.mensaje)
