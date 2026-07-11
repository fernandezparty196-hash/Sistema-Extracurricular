"""
ui/asistencia/panel_asistencia.py   ──   PANEL COMPLETO RF-16 a RF-20
═══════════════════════════════════════════════════════════════════════════════

¿QUÉ HACE?
  QWidget que muestra:
  • Historial de asistencia por CADA SESIÓN
  • Docente ve solo sus talleres
  • Admin puede ver/editar todas las asistencias
  • Doble click para editar + agregar observación si justificado
  • Dialog emergente para observaciones
  • Sesiones congeladas protegidas
  • Alertas de bajo umbral en rojo

ROLES:
  • Docente: Ve sus talleres, registra asistencia sesiones futuras
  • Admin: Ve todos talleres, puede editar/modificar cualquier asistencia
  • Operador: Puede cambiar A→J con observación

USO:
  from ui.asistencia.panel_asistencia import PanelAsistencia
  
  panel = PanelAsistencia(sesion_usuario=self.sesion, parent=self)
  self.setCentralWidget(panel)
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QLineEdit, QMessageBox,
    QHeaderView, QLabel, QComboBox, QDialog, QSpinBox,
    QTextEdit, QFrame
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont, QBrush

from datetime import date
from services.asistencia_service import AsistenciaService
from services.taller_service import TallerService
from database.connection import get_session
from models import Sesion


class PanelRegistrarAsistencia(QWidget):
    """
    Panel completo de asistencia mostrando historial por sesión.
    
    ESTRUCTURA:
      1. Seleccionar Taller (filtrado por rol)
      2. Tabla con TODAS las sesiones del taller
      3. Clic en sesión → muestra asistencias de esa sesión
      4. Doble clic en fila → editar asistencia (si es admin)
      5. Observaciones obligatorias si estado == "J"
    """

    def __init__(self, sesion_usuario, parent=None):
        super().__init__(parent)
        self.sesion = sesion_usuario
        self.taller_seleccionado_id = None
        self.sesion_seleccionada_id = None
        self.docente_talleres = []  # Si es docente, sus talleres
        self._timer = QTimer(singleShot=True, interval=300)
        self._timer.timeout.connect(self._filtrar_tabla)

        self._configurar_estilos()
        self._construir_ui()
        self._cargar_talleres()

    def _configurar_estilos(self):
        """Configura estilos CSS."""
        self.setStyleSheet("""
            QLabel#titulo {
                font-size: 18px;
                font-weight: bold;
            }
            QLabel#subtitulo {
                font-size: 11px;
            }
            QLineEdit, QComboBox {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 8px;
                min-height: 32px;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 2px solid #2563eb;
            }
            QPushButton {
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
                min-height: 32px;
            }

            QTableWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            QHeaderView::section {
                padding: 8px;
                font-weight: bold;
            }
        """)

    def _construir_ui(self):
        """Construye la interfaz principal."""
        raiz = QVBoxLayout()
        raiz.setSpacing(15)
        raiz.setContentsMargins(20, 20, 20, 20)

        # ── TÍTULO ───────────────────────────────────────────────
        titulo = QLabel("Historial de Asistencia")
        titulo.setObjectName("titulo")
        raiz.addWidget(titulo)

        # ── SELECCIÓN DE TALLER ──────────────────────────────────
        sel = QHBoxLayout()
        sel.addWidget(QLabel("Taller:"))
        self.cmb_taller = QComboBox()
        self.cmb_taller.setMinimumWidth(400)
        self.cmb_taller.currentIndexChanged.connect(self._on_taller_cambio)
        sel.addWidget(self.cmb_taller)
        sel.addStretch()
        raiz.addLayout(sel)

        # ── INFO DEL TALLER ──────────────────────────────────────
        self.lbl_info_taller = QLabel("")
        self.lbl_info_taller.setObjectName("subtitulo")
        raiz.addWidget(self.lbl_info_taller)

        # ── BÚSQUEDA EN SESIONES ─────────────────────────────────
        busqueda = QHBoxLayout()
        busqueda.addWidget(QLabel("Buscar sesión:"))
        self.inp_buscar = QLineEdit()
        self.inp_buscar.setPlaceholderText("Búsqueda por fecha o número...")
        self.inp_buscar.setMaximumWidth(300)
        self.inp_buscar.textChanged.connect(self._timer.start)
        busqueda.addWidget(self.inp_buscar)
        busqueda.addStretch()
        raiz.addLayout(busqueda)

        # ── TABLA DE SESIONES ────────────────────────────────────
        raiz.addWidget(QLabel("Sesiones del Taller:"))
        self.tabla_sesiones = self._construir_tabla_sesiones()
        raiz.addWidget(self.tabla_sesiones, 1)

        # ── TABLA DE ASISTENCIA (Sesión seleccionada) ───────────
        raiz.addWidget(QLabel("Asistencia de la Sesión Seleccionada:"))
        self.tabla_asistencia = self._construir_tabla_asistencia()
        raiz.addWidget(self.tabla_asistencia, 1)

        # ── BOTONES DE ACCIÓN ────────────────────────────────────
        acciones = QHBoxLayout()

        self.btn_refrescar = QPushButton("🔄 Refrescar")
        self.btn_refrescar.clicked.connect(self._cargar_talleres)
        acciones.addWidget(self.btn_refrescar)

        self.btn_todos_presentes = QPushButton("✓ Marcar Todos Presente")
        self.btn_todos_presentes.setEnabled(False)
        self.btn_todos_presentes.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
            }
            QPushButton:hover:!disabled {
                background-color: #059669;
            }
            QPushButton:disabled {
                background-color: #ccc;
            }
        """)
        self.btn_todos_presentes.clicked.connect(lambda: self._marcar_todos_bloque("P"))
        acciones.addWidget(self.btn_todos_presentes)

        self.btn_todos_ausentes = QPushButton("✗ Marcar Todos Ausente")
        self.btn_todos_ausentes.setEnabled(False)
        self.btn_todos_ausentes.setStyleSheet("""
            QPushButton {
                background-color: #ef4444;
            }
            QPushButton:hover:!disabled {
                background-color: #dc2626;
            }
            QPushButton:disabled {
                background-color: #ccc;
            }
        """)
        self.btn_todos_ausentes.clicked.connect(lambda: self._marcar_todos_bloque("A"))
        acciones.addWidget(self.btn_todos_ausentes)

        self.btn_editar = QPushButton("✎ Editar Seleccionado")
        self.btn_editar.setEnabled(False)
        self.btn_editar.clicked.connect(self._editar_asistencia)
        self.btn_editar.setVisible(self.sesion.es_administrador)
        acciones.addWidget(self.btn_editar)

        acciones.addStretch()
        raiz.addLayout(acciones)

        self.setLayout(raiz)

    def _construir_tabla_sesiones(self) -> QTableWidget:
        """Tabla de sesiones del taller."""
        tabla = QTableWidget()
        tabla.setColumnCount(5)
        tabla.setHorizontalHeaderLabels([
            "Sesión", "Fecha", "Hora", "Presentes", "Estado"
        ])

        header = tabla.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)

        tabla.setSelectionBehavior(QTableWidget.SelectRows)
        tabla.setSelectionMode(QTableWidget.SingleSelection)
        tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        tabla.setAlternatingRowColors(True)
        tabla.verticalHeader().setVisible(False)
        tabla.setShowGrid(False)

        tabla.itemSelectionChanged.connect(self._on_seleccionar_sesion)

        return tabla

    def _construir_tabla_asistencia(self) -> QTableWidget:
        """Tabla de asistencia para la sesión seleccionada."""
        tabla = QTableWidget()
        tabla.setColumnCount(7)
        tabla.setHorizontalHeaderLabels([
            "Estudiante", "DNI", "Carrera", "Estado", "%", "Obs.", "Acción"
        ])

        header = tabla.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.Stretch)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)

        tabla.setSelectionBehavior(QTableWidget.SelectRows)
        tabla.setSelectionMode(QTableWidget.SingleSelection)
        tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        tabla.setAlternatingRowColors(True)
        tabla.verticalHeader().setVisible(False)
        tabla.setShowGrid(False)

        tabla.cellDoubleClicked.connect(self._on_doble_clic_asistencia)

        return tabla

    def _cargar_talleres(self):
        """Carga talleres según rol."""
        self.cmb_taller.blockSignals(True)
        self.cmb_taller.clear()
        self.cmb_taller.blockSignals(False)

        talleres = TallerService.listar_para_asistencia(
            usuario_id=self.sesion.usuario_id,
            rol_nombre=self.sesion.rol_nombre,
            estado="Activo"
        )

        if not talleres:
            self.cmb_taller.addItem("No hay talleres disponibles", None)
            return

        for taller in talleres:
            self.cmb_taller.addItem(
                f"{taller['nombre']} - {taller['docente']}",
                taller["id"]
            )

    def _on_taller_cambio(self):
        """Al cambiar taller, cargar sesiones."""
        taller_id = self.cmb_taller.currentData()
        if not taller_id:
            self.tabla_sesiones.setRowCount(0)
            self.tabla_asistencia.setRowCount(0)
            return

        self.taller_seleccionado_id = taller_id

        # Obtener información del taller
        taller = TallerService.obtener_por_id(taller_id)
        if taller:
            self.lbl_info_taller.setText(
                f"<b>Docente:</b> {taller['docente']} | "
                f"<b>Umbral:</b> {taller['umbral']}% | "
                f"<b>Inscritos:</b> {taller['total_inscritos']}"
            )

        self._cargar_sesiones()

    def _cargar_sesiones(self):
        """Carga sesiones del taller seleccionado."""
        if not self.taller_seleccionado_id:
            return

        sesiones = TallerService.listar_sesiones(self.taller_seleccionado_id)

        self.tabla_sesiones.setRowCount(len(sesiones))

        for row, sesion in enumerate(sesiones):
            # Sesión
            item = QTableWidgetItem(f"Sesión {sesion['numero']}")
            item.setData(Qt.UserRole, sesion["id"])
            self.tabla_sesiones.setItem(row, 0, item)

            # Fecha
            item = QTableWidgetItem(sesion["fecha"])
            self.tabla_sesiones.setItem(row, 1, item)

            # Hora
            item = QTableWidgetItem(sesion["hora"])
            self.tabla_sesiones.setItem(row, 2, item)

            # Presentes
            resumen = AsistenciaService.obtener_resumen_sesion(sesion["id"])
            presentes = resumen.get("presentes", 0)
            total = resumen.get("total", 0)
            item = QTableWidgetItem(f"{presentes}/{total}")
            item.setTextAlignment(Qt.AlignCenter)
            self.tabla_sesiones.setItem(row, 3, item)

            # Estado (Congelada o Activa)
            try:
                with get_session() as session:
                    s = session.get(Sesion, sesion["id"])
                    hoy = date.today()
                    congelada = hoy > s.fecha

                    if congelada:
                        item = QTableWidgetItem("🔒 Congelada")
                        item.setForeground(QColor("#991b1b"))
                        item.setBackground(QBrush(QColor("#fee2e2")))
                    else:
                        item = QTableWidgetItem("✓ Activa")
                        item.setForeground(QColor("#065f46"))
                        item.setBackground(QBrush(QColor("#ecfdf5")))

                    self.tabla_sesiones.setItem(row, 4, item)
            except:
                pass

    def _on_seleccionar_sesion(self):
        """Al seleccionar una sesión, cargar su asistencia."""
        rows = self.tabla_sesiones.selectedIndexes()
        if not rows:
            self.tabla_asistencia.setRowCount(0)
            self.btn_todos_presentes.setEnabled(False)
            self.btn_todos_ausentes.setEnabled(False)
            return

        row = rows[0].row()
        sesion_id = self.tabla_sesiones.item(row, 0).data(Qt.UserRole)
        estado = self.tabla_sesiones.item(row, 4).text()

        self.sesion_seleccionada_id = sesion_id
        
        # Habilitar botones solo si sesión no está congelada
        congelada = "🔒" in estado
        self.btn_todos_presentes.setEnabled(not congelada)
        self.btn_todos_ausentes.setEnabled(not congelada)
        
        self._cargar_asistencia_sesion()

    def _cargar_asistencia_sesion(self):
        """Carga asistencia de la sesión seleccionada."""
        if not self.sesion_seleccionada_id:
            return

        # Obtener inscritos
        inscritos = TallerService.listar_inscritos(
            self.taller_seleccionado_id, solo_activos=True
        )

        # Obtener asistencias
        asistencias = AsistenciaService.obtener_por_sesion(
            self.sesion_seleccionada_id
        )
        asist_dict = {a["inscripcion_id"]: a for a in asistencias}

        self.tabla_asistencia.setRowCount(len(inscritos))

        for row, inscrito in enumerate(inscritos):
            insc_id = inscrito["inscripcion_id"]
            asist = asist_dict.get(insc_id, {})

            # Estudiante
            item = QTableWidgetItem(inscrito["nombre_completo"])
            item.setData(Qt.UserRole, insc_id)
            self.tabla_asistencia.setItem(row, 0, item)

            # DNI
            item = QTableWidgetItem(inscrito["dni"])
            self.tabla_asistencia.setItem(row, 1, item)

            # Carrera
            item = QTableWidgetItem(inscrito["carrera"])
            self.tabla_asistencia.setItem(row, 2, item)

            # Estado (P/A/J con color)
            estado = asist.get("estado", "-")
            etiqueta = {"P": "Presente", "A": "Ausente", "J": "Justificado"}.get(
                estado, "-"
            )
            item = QTableWidgetItem(f"{etiqueta}")
            item.setTextAlignment(Qt.AlignCenter)

            if estado == "P":
                item.setForeground(QColor("#065f46"))
                item.setBackground(QBrush(QColor("#ecfdf5")))
            elif estado == "A":
                item.setForeground(QColor("#991b1b"))
                item.setBackground(QBrush(QColor("#fee2e2")))
            elif estado == "J":
                item.setForeground(QColor("#92400e"))
                item.setBackground(QBrush(QColor("#fef3c7")))

            self.tabla_asistencia.setItem(row, 3, item)

            # Porcentaje
            pct = self._obtener_porcentaje(insc_id, self.taller_seleccionado_id)
            item = QTableWidgetItem(f"{pct:.1f}%")
            item.setTextAlignment(Qt.AlignCenter)

            taller = TallerService.obtener_por_id(self.taller_seleccionado_id)
            if taller and pct < taller["umbral"]:
                item.setForeground(QColor("#991b1b"))
                item.setBackground(QBrush(QColor("#fee2e2")))

            self.tabla_asistencia.setItem(row, 4, item)

            # Observación
            obs = asist.get("observacion", "")
            item = QTableWidgetItem(obs)
            self.tabla_asistencia.setItem(row, 5, item)

            # Acción (solo si es admin)
            if self.sesion.es_administrador:
                item = QTableWidgetItem("✎ Editar")
                item.setForeground(QColor("#2563eb"))
                self.tabla_asistencia.setItem(row, 6, item)

    def _obtener_porcentaje(self, inscripcion_id: int, taller_id: int) -> float:
        """Calcula porcentaje de asistencia."""
        from database.connection import get_session
        from models import Asistencia, Sesion
        from sqlalchemy import func

        try:
            with get_session() as session:
                total = session.query(func.count(Sesion.id)).filter(
                    Sesion.taller_id == taller_id
                ).scalar() or 0

                if total == 0:
                    return 0.0

                cuentan = session.query(func.count(Asistencia.id)).filter(
                    Asistencia.inscripcion_id == inscripcion_id,
                    Asistencia.estado.in_(["P", "J"])
                ).scalar() or 0

                return (cuentan / total) * 100
        except:
            return 0.0

    def _on_doble_clic_asistencia(self, row: int, col: int):
        """Abre dialog para editar asistencia (solo admin)."""
        if not self.sesion.es_administrador:
            QMessageBox.information(self, "Información",
                "Solo administrador puede editar asistencia.")
            return

        inscripcion_id = self.tabla_asistencia.item(row, 0).data(Qt.UserRole)

        dialogo = DialogoEditarAsistencia(
            inscripcion_id=inscripcion_id,
            sesion_id=self.sesion_seleccionada_id,
            usuario_id=self.sesion.usuario_id,
            parent=self
        )

        if dialogo.exec():
            self._cargar_asistencia_sesion()

    def _editar_asistencia(self):
        """Edita la fila seleccionada en tabla_asistencia."""
        rows = self.tabla_asistencia.selectedIndexes()
        if not rows:
            QMessageBox.warning(self, "Error", "Selecciona una asistencia.")
            return

        row = rows[0].row()
        self._on_doble_clic_asistencia(row, 0)

    def _filtrar_tabla(self):
        """Filtra tabla de sesiones."""
        buscar = self.inp_buscar.text().lower()
        for row in range(self.tabla_sesiones.rowCount()):
            fecha = self.tabla_sesiones.item(row, 1).text().lower()
            sesion = self.tabla_sesiones.item(row, 0).text().lower()
            visible = buscar in fecha or buscar in sesion
            self.tabla_sesiones.setRowHidden(row, not visible)

    def _marcar_todos_bloque(self, estado: str):
        """
        ✅ RF-17: Marca TODOS los estudiantes de la sesión con el mismo estado.
        
        PARÁMETRO:
          estado: "P" (Presente) | "A" (Ausente)
        """
        if not self.sesion_seleccionada_id:
            QMessageBox.warning(self, "Error", "Selecciona una sesión primero.")
            return

        # Obtener inscritos
        inscritos = TallerService.listar_inscritos(
            self.taller_seleccionado_id, solo_activos=True
        )

        if not inscritos:
            QMessageBox.warning(self, "Error", "No hay inscritos en este taller.")
            return

        # Confirmar acción
        etiqueta = "Presente" if estado == "P" else "Ausente"
        resultado = QMessageBox.question(
            self,
            "Marcar en Bloque",
            f"¿Marcar a todos los {len(inscritos)} estudiantes como {etiqueta}?\n\n"
            f"Esta acción afectará la asistencia de toda la sesión.",
            QMessageBox.Yes | QMessageBox.No
        )

        if resultado != QMessageBox.Yes:
            return

        # Marcar todos
        registrados = 0
        errores = 0
        alertas = []

        for inscrito in inscritos:
            insc_id = inscrito["inscripcion_id"]

            # Registrar asistencia
            res = AsistenciaService.registrar(
                sesion_id=self.sesion_seleccionada_id,
                inscripcion_id=insc_id,
                estado=estado,
                usuario_id=self.sesion.usuario_id,
                observacion=""
            )

            if res.ok:
                registrados += 1

                # Detectar alertas (RF-18)
                if res.datos and "porcentaje" in res.datos:
                    pct = res.datos["porcentaje"]
                    taller = TallerService.obtener_por_id(self.taller_seleccionado_id)
                    if taller and pct < taller["umbral"]:
                        alertas.append({
                            "nombre": inscrito["nombre_completo"],
                            "porcentaje": pct,
                            "umbral": taller["umbral"]
                        })
            else:
                errores += 1

        # Mostrar resumen
        mensaje = f"✅ Se marcaron {registrados} estudiantes como {etiqueta}"

        if alertas:
            mensaje += f"\n\n⚠️ {len(alertas)} estudiante(s) bajo umbral:"
            for alerta in alertas[:5]:
                mensaje += f"\n   • {alerta['nombre']}: {alerta['porcentaje']:.1f}% < {alerta['umbral']}%"
            if len(alertas) > 5:
                mensaje += f"\n   ... y {len(alertas)-5} más"

        if errores > 0:
            mensaje += f"\n\n❌ Errores: {errores} estudiantes"

        QMessageBox.information(self, "Resultado", mensaje)

        # Recargar tabla
        self._cargar_asistencia_sesion()


# ══════════════════════════════════════════════════════════════════════════════
# DIALOG PARA EDITAR ASISTENCIA
# ══════════════════════════════════════════════════════════════════════════════

class DialogoEditarAsistencia(QDialog):
    """Dialog para editar asistencia con observaciones."""

    def __init__(self, inscripcion_id: int, sesion_id: int,
                 usuario_id: int, parent=None):
        super().__init__(parent)
        self.inscripcion_id = inscripcion_id
        self.sesion_id = sesion_id
        self.usuario_id = usuario_id

        self.setWindowTitle("Editar Asistencia")
        self.setMinimumSize(500, 350)
        self.setModal(True)

        self._construir_ui()
        self._cargar_datos()

    def _construir_ui(self):
        """Construye la interfaz del dialog."""
        layout = QVBoxLayout()

        # Título
        titulo = QLabel("Editar Asistencia")
        f = QFont()
        f.setPointSize(14)
        f.setWeight(QFont.Weight.Bold)
        titulo.setFont(f)
        layout.addWidget(titulo)

        # Info estudiante
        self.lbl_estudiante = QLabel("")
        layout.addWidget(self.lbl_estudiante)

        # Estado (P/A/J)
        layout.addWidget(QLabel("Estado:"))
        estado_layout = QHBoxLayout()
        self.btn_presente = QPushButton("✓ Presente")
        self.btn_presente.setCheckable(True)
        self.btn_presente.clicked.connect(lambda: self._cambiar_estado("P"))
        estado_layout.addWidget(self.btn_presente)

        self.btn_ausente = QPushButton("✗ Ausente")
        self.btn_ausente.setCheckable(True)
        self.btn_ausente.clicked.connect(lambda: self._cambiar_estado("A"))
        estado_layout.addWidget(self.btn_ausente)

        self.btn_justificado = QPushButton("⚠️ Justificado")
        self.btn_justificado.setCheckable(True)
        self.btn_justificado.clicked.connect(lambda: self._cambiar_estado("J"))
        estado_layout.addWidget(self.btn_justificado)

        layout.addLayout(estado_layout)

        # Observación (para justificadas)
        layout.addWidget(QLabel("Observación (obligatoria si Justificado):"))
        self.txt_observacion = QTextEdit()
        self.txt_observacion.setMaximumHeight(100)
        layout.addWidget(self.txt_observacion)

        # Info porcentaje
        self.lbl_porcentaje = QLabel("")
        layout.addWidget(self.lbl_porcentaje)

        # Botones
        botones = QHBoxLayout()
        botones.addStretch()

        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        botones.addWidget(btn_cancelar)

        btn_guardar = QPushButton("✓ Guardar")
        btn_guardar.clicked.connect(self._guardar)
        botones.addWidget(btn_guardar)

        layout.addLayout(botones)
        self.setLayout(layout)

    def _cargar_datos(self):
        """Carga datos de asistencia actual."""
        from database.connection import get_session
        from models import Inscripcion, Asistencia

        try:
            with get_session() as session:
                insc = session.get(Inscripcion, self.inscripcion_id)
                if insc:
                    self.lbl_estudiante.setText(
                        f"<b>{insc.estudiante.nombre_completo}</b> "
                        f"(DNI: {insc.estudiante.dni})"
                    )

                asist = session.query(Asistencia).filter(
                    Asistencia.inscripcion_id == self.inscripcion_id,
                    Asistencia.sesion_id == self.sesion_id
                ).first()

                if asist:
                    # Cargar estado actual
                    if asist.estado == "P":
                        self.btn_presente.setChecked(True)
                    elif asist.estado == "A":
                        self.btn_ausente.setChecked(True)
                    elif asist.estado == "J":
                        self.btn_justificado.setChecked(True)

                    # Cargar observación
                    if asist.observacion:
                        self.txt_observacion.setPlainText(asist.observacion)

                # Cargar porcentaje
                pct = self._calcular_porcentaje()
                self.lbl_porcentaje.setText(f"<b>Porcentaje actual:</b> {pct:.1f}%")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al cargar: {str(e)}")

    def _cambiar_estado(self, estado: str):
        """Cambia el estado seleccionado."""
        self.btn_presente.setChecked(estado == "P")
        self.btn_ausente.setChecked(estado == "A")
        self.btn_justificado.setChecked(estado == "J")

        # Si es justificado, foco en observación
        if estado == "J":
            self.txt_observacion.setFocus()

    def _calcular_porcentaje(self) -> float:
        """Calcula porcentaje actual del estudiante."""
        from database.connection import get_session
        from models import Inscripcion, Asistencia, Sesion
        from sqlalchemy import func

        try:
            with get_session() as session:
                insc = session.get(Inscripcion, self.inscripcion_id)
                if not insc:
                    return 0.0

                total = session.query(func.count(Sesion.id)).filter(
                    Sesion.taller_id == insc.taller_id
                ).scalar() or 0

                if total == 0:
                    return 0.0

                cuentan = session.query(func.count(Asistencia.id)).filter(
                    Asistencia.inscripcion_id == self.inscripcion_id,
                    Asistencia.estado.in_(["P", "J"])
                ).scalar() or 0

                return (cuentan / total) * 100
        except:
            return 0.0

    def _guardar(self):
        """Guarda los cambios."""
        # Determinar estado
        estado = None
        if self.btn_presente.isChecked():
            estado = "P"
        elif self.btn_ausente.isChecked():
            estado = "A"
        elif self.btn_justificado.isChecked():
            estado = "J"

        if not estado:
            QMessageBox.warning(self, "Error", "Selecciona un estado.")
            return

        # Validar observación si justificado
        observacion = self.txt_observacion.toPlainText().strip()
        if estado == "J" and not observacion:
            QMessageBox.warning(self, "Error",
                "La observación es obligatoria para justificadas.")
            return

        # Guardar
        resultado = AsistenciaService.registrar(
            sesion_id=self.sesion_id,
            inscripcion_id=self.inscripcion_id,
            estado=estado,
            usuario_id=self.usuario_id,
            observacion=observacion
        )

        if resultado.ok:
            QMessageBox.information(self, "Éxito", resultado.mensaje)
            self.accept()
        else:
            QMessageBox.warning(self, "Error", resultado.mensaje)