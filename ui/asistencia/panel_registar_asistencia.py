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

FLUJO DE EDICIÓN (actualizado):
  La tabla de asistencia ya no se edita por diálogo modal (doble click).
  Cada fila trae un QComboBox (Presente/Ausente/Justificado) y un QLineEdit
  de observación editables directamente en la tabla. Los botones "Marcar
  todos" solo rellenan los combos localmente; nada se persiste hasta que
  se aprieta "Guardar Asistencia", que registra todas las filas en bloque.

NOTA DE ESTILO:
  Este panel NO define QSS propio (setStyleSheet inline). Todos los colores,
  bordes y estados (incluyendo el color de fondo del combo según P/A/J) se
  resuelven vía objectName / propiedad dinámica en utils/themes.py, igual
  que ui/estudiantes/lista_estudiantes.py.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QLineEdit, QMessageBox,
    QHeaderView, QLabel, QComboBox, QDialog, QSpinBox,
    QTextEdit, QFrame, QInputDialog
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
      1. Cabecera con título y botón refrescar
      2. Frame de filtros: taller + búsqueda de sesión
      3. Info del taller (umbral, inscritos, docente)
      4. Tabla de sesiones del taller
      5. Tabla de asistencia de la sesión seleccionada
      6. Pie con acciones en bloque (Presente/Ausente) y edición
    """

    def __init__(self, sesion_usuario, parent=None):
        super().__init__(parent)
        self.sesion = sesion_usuario
        self.taller_seleccionado_id = None
        self.sesion_seleccionada_id = None
        self._sesion_congelada = False
        self.docente_talleres = []  # Si es docente, sus talleres
        self._timer = QTimer(singleShot=True, interval=300)
        self._timer.timeout.connect(self._filtrar_tabla)

        self._construir_ui()
        self._cargar_talleres()

    # ──────────────────────────────────────────────────────────────
    # CONSTRUCCIÓN DE LA INTERFAZ
    # ──────────────────────────────────────────────────────────────
    def _construir_ui(self):
        """Construye la interfaz principal."""
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 12)
        raiz.setSpacing(2)

        # ── Frame de filtros (taller + búsqueda) ─────────────────
        raiz.addWidget(self._barra_filtros())
        raiz.addSpacing(8)

        # ── Info del taller ───────────────────────────────────────
        self.lbl_info_taller = QLabel("")
        self.lbl_info_taller.setObjectName("subtitulo")
        raiz.addWidget(self.lbl_info_taller)
        raiz.addSpacing(12)

        # ── TABLA DE SESIONES ────────────────────────────────────
        lbl_sesiones = QLabel("Sesiones del taller")
        lbl_sesiones.setObjectName("etiqueta_seccion")
        raiz.addWidget(lbl_sesiones)
        raiz.addSpacing(6)

        self.tabla_sesiones = self._construir_tabla_sesiones()
        raiz.addWidget(self.tabla_sesiones, 1)
        raiz.addSpacing(10)

        # ── TABLA DE ASISTENCIA (Sesión seleccionada) ───────────
        lbl_asistencia = QLabel("Asistencia de la sesión seleccionada")
        lbl_asistencia.setObjectName("etiqueta_seccion")
        raiz.addWidget(lbl_asistencia)
        raiz.addSpacing(6)

        self.tabla_asistencia = self._construir_tabla_asistencia()
        raiz.addWidget(self.tabla_asistencia, 1)
        raiz.addSpacing(6)

        # ── PIE: acciones en bloque ───────────────────────────────
        raiz.addLayout(self._pie())

    # ── Barra de filtros ─────────────────────────────────────────
    def _barra_filtros(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("frame_filtros")

        lay = QHBoxLayout(frame)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        lay.addWidget(QLabel("Taller:"))

        self.cmb_taller = QComboBox()
        self.cmb_taller.setObjectName("cmb_taller")
        self.cmb_taller.setMinimumWidth(360)
        self.cmb_taller.currentIndexChanged.connect(self._on_taller_cambio)
        lay.addWidget(self.cmb_taller, 2)

        self.inp_buscar = QLineEdit()
        self.inp_buscar.setObjectName("inp_buscar")
        self.inp_buscar.setPlaceholderText("🔍  Buscar sesión por fecha o número…")
        self.inp_buscar.textChanged.connect(self._timer.start)
        lay.addWidget(self.inp_buscar, 1)

        return frame

    # ── Tabla de sesiones ─────────────────────────────────────────
    def _construir_tabla_sesiones(self) -> QTableWidget:
        """Tabla de sesiones del taller."""
        tabla = QTableWidget()
        tabla.setObjectName("tbl_sesiones")
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
        tabla.verticalHeader().setDefaultSectionSize(36)
        tabla.setShowGrid(False)

        tabla.itemSelectionChanged.connect(self._on_seleccionar_sesion)

        return tabla

    # ── Tabla de asistencia ───────────────────────────────────────
    def _construir_tabla_asistencia(self) -> QTableWidget:
        """Tabla de asistencia para la sesión seleccionada."""
        tabla = QTableWidget()
        tabla.setObjectName("tbl_asistencia")
        tabla.setColumnCount(6)
        tabla.setHorizontalHeaderLabels([
            "Estudiante", "DNI", "Carrera", "Estado", "%", "Observación"
        ])

        header = tabla.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.Stretch)
        tabla.setColumnWidth(3, 150)

        # Estado y Observación se editan inline (combo / lineedit por fila),
        # el resto de celdas es de solo lectura.
        tabla.setSelectionBehavior(QTableWidget.SelectRows)
        tabla.setSelectionMode(QTableWidget.SingleSelection)
        tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        tabla.setAlternatingRowColors(True)
        tabla.verticalHeader().setVisible(False)
        tabla.verticalHeader().setDefaultSectionSize(54)
        tabla.setShowGrid(False)

        return tabla

    # ── Pie ──────────────────────────────────────────────────────
    def _pie(self) -> QHBoxLayout:
        lay = QHBoxLayout()

        self.lbl_conteo = QLabel("")
        self.lbl_conteo.setObjectName("lbl_conteo")
        lay.addWidget(self.lbl_conteo)
        lay.addStretch()

        self.btn_todos_presentes = QPushButton("✓  Marcar todos Presente")
        self.btn_todos_presentes.setObjectName("btn_marcar_presentes")
        self.btn_todos_presentes.setEnabled(False)
        self.btn_todos_presentes.clicked.connect(lambda: self._marcar_todos_bloque("P"))
        lay.addWidget(self.btn_todos_presentes)

        lay.addSpacing(6)

        self.btn_todos_ausentes = QPushButton("✗  Marcar todos Ausente")
        self.btn_todos_ausentes.setObjectName("btn_marcar_ausentes")
        self.btn_todos_ausentes.setEnabled(False)
        self.btn_todos_ausentes.clicked.connect(lambda: self._marcar_todos_bloque("A"))
        lay.addWidget(self.btn_todos_ausentes)

        lay.addSpacing(6)

        self.btn_guardar_asistencia = QPushButton("💾  Guardar Asistencia")
        self.btn_guardar_asistencia.setObjectName("btn_guardar_asistencia")
        self.btn_guardar_asistencia.setEnabled(False)
        self.btn_guardar_asistencia.clicked.connect(self._guardar_asistencia)
        lay.addWidget(self.btn_guardar_asistencia)

        return lay

    # ──────────────────────────────────────────────────────────────
    # CARGA DE DATOS  (sin cambios de lógica)
    # ──────────────────────────────────────────────────────────────
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
            self.lbl_conteo.setText("")
            return

        self.taller_seleccionado_id = taller_id

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
            item = QTableWidgetItem(f"Sesión {sesion['numero']}")
            item.setData(Qt.UserRole, sesion["id"])
            self.tabla_sesiones.setItem(row, 0, item)

            item = QTableWidgetItem(sesion["fecha"])
            self.tabla_sesiones.setItem(row, 1, item)

            item = QTableWidgetItem(sesion["hora"])
            self.tabla_sesiones.setItem(row, 2, item)

            resumen = AsistenciaService.obtener_resumen_sesion(sesion["id"])
            presentes = resumen.get("presentes", 0)
            total = resumen.get("total", 0)
            item = QTableWidgetItem(f"{presentes}/{total}")
            item.setTextAlignment(Qt.AlignCenter)
            self.tabla_sesiones.setItem(row, 3, item)

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
            except Exception:
                pass

        n = len(sesiones)
        sufijo = "" if n == 1 else "es"
        self.lbl_conteo.setText(f"{n} sesión{sufijo}" if n == 1 else f"{n} sesiones")

    def _on_seleccionar_sesion(self):
        """Al seleccionar una sesión, cargar su asistencia."""
        rows = self.tabla_sesiones.selectedIndexes()
        if not rows:
            self.tabla_asistencia.setRowCount(0)
            self.btn_todos_presentes.setEnabled(False)
            self.btn_todos_ausentes.setEnabled(False)
            self.btn_guardar_asistencia.setEnabled(False)
            return

        row = rows[0].row()
        sesion_id = self.tabla_sesiones.item(row, 0).data(Qt.UserRole)
        estado = self.tabla_sesiones.item(row, 4).text()

        self.sesion_seleccionada_id = sesion_id
        self._sesion_congelada = "🔒" in estado

        self.btn_todos_presentes.setEnabled(not self._sesion_congelada)
        self.btn_todos_ausentes.setEnabled(not self._sesion_congelada)
        self.btn_guardar_asistencia.setEnabled(not self._sesion_congelada)

        self._cargar_asistencia_sesion()

    def _cargar_asistencia_sesion(self):
        """Carga asistencia de la sesión seleccionada."""
        if not self.sesion_seleccionada_id:
            return

        inscritos = TallerService.listar_inscritos(
            self.taller_seleccionado_id, solo_activos=True
        )

        asistencias = AsistenciaService.obtener_por_sesion(
            self.sesion_seleccionada_id
        )
        asist_dict = {a["inscripcion_id"]: a for a in asistencias}

        self.tabla_asistencia.setRowCount(len(inscritos))

        for row, inscrito in enumerate(inscritos):
            insc_id = inscrito["inscripcion_id"]
            asist = asist_dict.get(insc_id, {})

            item = QTableWidgetItem(inscrito["nombre_completo"])
            item.setData(Qt.UserRole, insc_id)
            self.tabla_asistencia.setItem(row, 0, item)

            item = QTableWidgetItem(inscrito["dni"])
            self.tabla_asistencia.setItem(row, 1, item)

            item = QTableWidgetItem(inscrito["carrera"])
            self.tabla_asistencia.setItem(row, 2, item)

            # ── Estado: combo editable inline (Presente/Ausente/Justificado) ──
            estado_actual = asist.get("estado")
            combo = QComboBox()
            combo.setObjectName("cmb_estado_asistencia")
            combo.addItem("Presente", "P")
            combo.addItem("Ausente", "A")
            combo.addItem("Justificado", "J")
            idx = combo.findData(estado_actual) if estado_actual else -1
            combo.setCurrentIndex(idx if idx >= 0 else 0)
            combo.setEnabled(not self._sesion_congelada)
            self._actualizar_color_combo(combo, combo.currentData())
            combo.currentIndexChanged.connect(
                lambda _, c=combo: self._actualizar_color_combo(c, c.currentData())
            )
            self.tabla_asistencia.setCellWidget(row, 3, combo)

            # ── Porcentaje ────────────────────────────────────────────────
            pct = self._obtener_porcentaje(insc_id, self.taller_seleccionado_id)
            item = QTableWidgetItem(f"{pct:.1f}%")
            item.setTextAlignment(Qt.AlignCenter)

            taller = TallerService.obtener_por_id(self.taller_seleccionado_id)
            if taller and pct < taller["umbral"]:
                item.setForeground(QColor("#991b1b"))
                item.setBackground(QBrush(QColor("#fee2e2")))

            self.tabla_asistencia.setItem(row, 4, item)

            # ── Observación: editable inline, obligatoria si Justificado ──
            campo_obs = QLineEdit(asist.get("observacion", ""))
            campo_obs.setObjectName("inp_obs_asistencia")
            campo_obs.setPlaceholderText("Obligatoria si Justificado…")
            campo_obs.setEnabled(not self._sesion_congelada)
            self.tabla_asistencia.setCellWidget(row, 5, campo_obs)

    def _actualizar_color_combo(self, combo: QComboBox, estado: str):
        """
        Marca el estado en una propiedad dinámica ('estado') para que
        utils/themes.py pueda pintar el combo (verde/rojo/ámbar) vía QSS,
        sin usar setStyleSheet aquí.
        """
        combo.setProperty("estado", estado)
        combo.style().unpolish(combo)
        combo.style().polish(combo)

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
        except Exception:
            return 0.0

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
        ✅ RF-17: Pone el mismo estado en TODOS los combos de la sesión.

        Esto es solo un ajuste local en la tabla — nada se persiste en BD
        hasta que se aprieta "Guardar Asistencia". Así se puede marcar
        a todos como Presente y luego corregir persona por persona antes
        de guardar.

        PARÁMETRO:
          estado: "P" (Presente) | "A" (Ausente)
        """
        filas = self.tabla_asistencia.rowCount()
        if filas == 0:
            QMessageBox.warning(self, "Error", "No hay estudiantes cargados en esta sesión.")
            return

        for row in range(filas):
            combo = self.tabla_asistencia.cellWidget(row, 3)
            if combo is None:
                continue
            idx = combo.findData(estado)
            if idx >= 0:
                combo.setCurrentIndex(idx)

    def _guardar_asistencia(self):
        """
        Guarda en bloque el estado (P/A/J) y observación de cada estudiante,
        leyendo directamente los combos y campos de texto de la tabla.
        """
        if not self.sesion_seleccionada_id:
            QMessageBox.warning(self, "Error", "Selecciona una sesión primero.")
            return

        filas = self.tabla_asistencia.rowCount()
        if filas == 0:
            QMessageBox.warning(self, "Error", "No hay estudiantes para registrar.")
            return

        # ── Validar observación obligatoria en filas Justificado ──────────
        pendientes = []
        sin_observacion = []

        for row in range(filas):
            item_estudiante = self.tabla_asistencia.item(row, 0)
            combo = self.tabla_asistencia.cellWidget(row, 3)
            campo_obs = self.tabla_asistencia.cellWidget(row, 5)

            insc_id = item_estudiante.data(Qt.UserRole)
            nombre = item_estudiante.text()
            estado = combo.currentData()
            observacion = campo_obs.text().strip()

            if estado == "J" and not observacion:
                sin_observacion.append(nombre)
                continue

            pendientes.append((insc_id, estado, observacion, nombre))

        if sin_observacion:
            QMessageBox.warning(
                self, "Falta observación",
                "Los siguientes estudiantes están marcados como Justificado "
                "pero no tienen observación:\n\n"
                + "\n".join(f"• {n}" for n in sin_observacion)
            )
            return

        resultado = QMessageBox.question(
            self, "Guardar asistencia",
            f"¿Guardar la asistencia de {len(pendientes)} estudiante(s) "
            f"para esta sesión?",
            QMessageBox.Yes | QMessageBox.No
        )
        if resultado != QMessageBox.Yes:
            return

        registrados = 0
        errores = 0
        alertas = []

        for insc_id, estado, observacion, nombre in pendientes:
            res = AsistenciaService.registrar(
                sesion_id=self.sesion_seleccionada_id,
                inscripcion_id=insc_id,
                estado=estado,
                usuario_id=self.sesion.usuario_id,
                observacion=observacion
            )

            if res.ok:
                registrados += 1

                if res.datos and "porcentaje" in res.datos:
                    pct = res.datos["porcentaje"]
                    taller = TallerService.obtener_por_id(self.taller_seleccionado_id)
                    if taller and pct < taller["umbral"]:
                        alertas.append({
                            "nombre": nombre,
                            "porcentaje": pct,
                            "umbral": taller["umbral"]
                        })
            else:
                errores += 1

        mensaje = f"✅ Asistencia guardada para {registrados} estudiante(s)"

        if alertas:
            mensaje += f"\n\n⚠️ {len(alertas)} estudiante(s) bajo umbral:"
            for alerta in alertas[:5]:
                mensaje += f"\n   • {alerta['nombre']}: {alerta['porcentaje']:.1f}% < {alerta['umbral']}%"
            if len(alertas) > 5:
                mensaje += f"\n   ... y {len(alertas)-5} más"

        if errores > 0:
            mensaje += f"\n\n❌ Errores: {errores} estudiante(s)"

        QMessageBox.information(self, "Resultado", mensaje)

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

        self.setObjectName("dialogo_editar_asistencia")
        self.setWindowTitle("Editar Asistencia")
        self.setMinimumSize(480, 380)
        self.setModal(True)

        self._construir_ui()
        self._cargar_datos()

    def _construir_ui(self):
        """Construye la interfaz del dialog."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)

        titulo = QLabel("Editar Asistencia")
        titulo.setObjectName("titulo_dialogo")
        layout.addWidget(titulo)

        self.lbl_estudiante = QLabel("")
        self.lbl_estudiante.setObjectName("subtitulo")
        layout.addWidget(self.lbl_estudiante)
        layout.addSpacing(6)

        layout.addWidget(QLabel("Estado:"))
        estado_layout = QHBoxLayout()
        estado_layout.setSpacing(8)

        self.btn_presente = QPushButton("✓ Presente")
        self.btn_presente.setObjectName("btn_estado_presente")
        self.btn_presente.setCheckable(True)
        self.btn_presente.setFixedHeight(34)
        self.btn_presente.clicked.connect(lambda: self._cambiar_estado("P"))
        estado_layout.addWidget(self.btn_presente)

        self.btn_ausente = QPushButton("✗ Ausente")
        self.btn_ausente.setObjectName("btn_estado_ausente")
        self.btn_ausente.setCheckable(True)
        self.btn_ausente.setFixedHeight(34)
        self.btn_ausente.clicked.connect(lambda: self._cambiar_estado("A"))
        estado_layout.addWidget(self.btn_ausente)

        self.btn_justificado = QPushButton("⚠ Justificado")
        self.btn_justificado.setObjectName("btn_estado_justificado")
        self.btn_justificado.setCheckable(True)
        self.btn_justificado.setFixedHeight(34)
        self.btn_justificado.clicked.connect(lambda: self._cambiar_estado("J"))
        estado_layout.addWidget(self.btn_justificado)

        layout.addLayout(estado_layout)
        layout.addSpacing(6)

        layout.addWidget(QLabel("Observación (obligatoria si Justificado):"))
        self.txt_observacion = QTextEdit()
        self.txt_observacion.setObjectName("txt_observacion")
        self.txt_observacion.setMaximumHeight(100)
        layout.addWidget(self.txt_observacion)
        layout.addSpacing(6)

        self.lbl_porcentaje = QLabel("")
        self.lbl_porcentaje.setObjectName("subtitulo")
        layout.addWidget(self.lbl_porcentaje)
        layout.addStretch()

        botones = QHBoxLayout()
        botones.addStretch()

        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setObjectName("btn_cancelar")
        btn_cancelar.setFixedHeight(34)
        btn_cancelar.clicked.connect(self.reject)
        botones.addWidget(btn_cancelar)

        btn_guardar = QPushButton("✓ Guardar")
        btn_guardar.setObjectName("btn_guardar")
        btn_guardar.setFixedHeight(34)
        btn_guardar.clicked.connect(self._guardar)
        botones.addWidget(btn_guardar)

        layout.addLayout(botones)

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
                    if asist.estado == "P":
                        self.btn_presente.setChecked(True)
                    elif asist.estado == "A":
                        self.btn_ausente.setChecked(True)
                    elif asist.estado == "J":
                        self.btn_justificado.setChecked(True)

                    if asist.observacion:
                        self.txt_observacion.setPlainText(asist.observacion)

                pct = self._calcular_porcentaje()
                self.lbl_porcentaje.setText(f"<b>Porcentaje actual:</b> {pct:.1f}%")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al cargar: {str(e)}")

    def _cambiar_estado(self, estado: str):
        """Cambia el estado seleccionado."""
        self.btn_presente.setChecked(estado == "P")
        self.btn_ausente.setChecked(estado == "A")
        self.btn_justificado.setChecked(estado == "J")

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
        except Exception:
            return 0.0

    def _guardar(self):
        """Guarda los cambios."""
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

        observacion = self.txt_observacion.toPlainText().strip()
        if estado == "J" and not observacion:
            QMessageBox.warning(self, "Error",
                "La observación es obligatoria para justificadas.")
            return

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