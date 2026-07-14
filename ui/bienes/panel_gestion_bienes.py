"""
ui/panel_bienes.py   ──   EP-06 Gestión de Bienes Patrimoniales
═════════════════════════════════════════════════════════════

Panel principal para RF-31 a RF-35 + CRUD de bienes.

  RF-31: Lista de bienes con filtros (código, descripción, categoría, estado).
  CRUD:  Crear bien nuevo y editar datos generales (usa registrar()/editar()
         del servicio). No existe "eliminar" físico: la baja de un bien es
         un estado del dominio (DeBaja), manejado por RF-34.
  RF-33: Registrar devolución indicando estado de conservación
         (Excelente/Bueno/Regular/Malo/Inservible).
  RF-34: Cambiar estado manualmente (Disponible ↔ Mantenimiento, o baja
         de emergencia a DeBaja). "Asignado" solo se alcanza vía el
         flujo de asignación real.
  RF-35: Alertas visuales por fila:
         ⏰ Vencido       → asignación activa con fecha de devolución superada
         💔 Dañado        → última devolución con conservación Regular/Malo/Inservible
         🔧 Mantenimiento → bien actualmente en Mantenimiento

REGLAS DE ARQUITECTURA (proyecto):
  • Este widget NUNCA accede a la base de datos ni al ORM directamente.
  • Toda operación pasa por BienesService, que retorna ResultadoBien.
  • Los diálogos heredan de QDialog (no QWidget) para que exec() funcione.
  • No se usa QSS inline "duro": los colores de alerta son datos de
    estado (como el preview verde/rojo de la importación de Excel), no
    tema visual, así que se aplican vía QColor sobre el QTableWidgetItem.
    El resto de widgets usa objectName() para engancharse a main.qss.
"""

from datetime import datetime, date

from PySide6.QtCore import Qt, Signal, QDate
from PySide6.QtGui import QColor, QBrush
from PySide6.QtWidgets import (
    QWidget, QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout,
    QLabel, QLineEdit, QComboBox, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QTextEdit, QMessageBox, QCheckBox,
    QDialogButtonBox, QAbstractItemView, QSizePolicy, QToolButton, QFrame,
    QDateEdit, QDoubleSpinBox
)

from services.bienes_service import BienesService


# ────────────────────────────────────────────────────────────────
# Colores de estado (datos, no tema) para resaltar filas con alertas
# ────────────────────────────────────────────────────────────────
COLOR_VENCIDO       = QColor(255, 205, 210)   # rojo suave
COLOR_DANIADO       = QColor(255, 224, 178)   # naranja suave
COLOR_MANTENIMIENTO = QColor(255, 249, 196)   # amarillo suave
COLOR_NORMAL        = QColor(255, 255, 255)

ESTADOS_BADGE = {
    "Disponible":    "🟢 Disponible",
    "Asignado":      "🔵 Asignado",
    "Mantenimiento": "🟠 Mantenimiento",
    "DeBaja":        "⚫ De Baja",
}


COLOR_KPI = {
    "total":          "#4f46e5",   # índigo
    "disponibles":    "#16a34a",   # verde
    "asignados":      "#2563eb",   # azul
    "mantenimiento":  "#d97706",   # ámbar
    "vencidos":       "#dc2626",   # rojo
    "daniados":       "#ea580c",   # naranja
}

ESTADOS_CONSERVACION = ["Excelente", "Bueno", "Regular", "Malo", "Inservible"]


def _alerta_texto(fila: dict) -> str:
    iconos = []
    if fila.get("alerta_vencido"):
        iconos.append("⏰")
    if fila.get("alerta_daniado"):
        iconos.append("💔")
    if fila.get("alerta_mantenimiento"):
        iconos.append("🔧")
    return " ".join(iconos) if iconos else "—"


def _color_fila(fila: dict) -> QColor:
    # Prioridad visual: vencido > dañado > mantenimiento
    if fila.get("alerta_vencido"):
        return COLOR_VENCIDO
    if fila.get("alerta_daniado"):
        return COLOR_DANIADO
    if fila.get("alerta_mantenimiento"):
        return COLOR_MANTENIMIENTO
    return COLOR_NORMAL


CATEGORIAS_SUGERIDAS = [
    "Equipos", "Mobiliario", "Instrumentos musicales", "Material deportivo",
    "Herramientas", "Tecnología", "Vestuario", "Otros"
]

def _cargar_docentes() -> list:
    """
    Carga docentes activos para el combo de asignación.

    Usa services.docente_service.DocenteService.listar(activos_solo=True),
    que retorna ResultadoDocente(ok, mensaje, lista=[{id, dni, nombre,
    apellidos, especialidad, email, usuario, activo}, ...]).
    Nota: la clave del nombre completo es 'nombre' (no 'nombre_completo').
    """
    try:
        from services.docente_service import DocenteService
        resultado = DocenteService.listar(activos_solo=True)
        if resultado.ok:
            return resultado.lista or []
    except Exception:
        pass
    return []


def _cargar_talleres() -> list:
    """
    Carga talleres activos para el combo de asignación.

    Usa services.taller_service.TallerService.listar_activos(), que
    retorna directamente una lista (sin envoltorio ResultadoTaller) de
    dicts {id, codigo, nombre, docente}.
    """
    try:
        from services.taller_service import TallerService
        return TallerService.listar_activos() or []
    except Exception:
        return []


class _FormularioBien:
    """Mixin con el formulario compartido entre Crear y Editar bien."""

    def _construir_formulario(self, incluir_codigo: bool):
        form = QFormLayout()

        if incluir_codigo:
            self.input_codigo = QLineEdit()
            self.input_codigo.setPlaceholderText("Ej. BP-2025-001")
            form.addRow("Código patrimonial *:", self.input_codigo)
        else:
            self.input_codigo = None

        self.input_descripcion = QLineEdit()
        self.input_descripcion.setPlaceholderText("Ej. Proyector Epson PowerLite")
        form.addRow("Descripción *:", self.input_descripcion)

        self.combo_categoria = QComboBox()
        self.combo_categoria.setEditable(True)
        self.combo_categoria.addItems(CATEGORIAS_SUGERIDAS)
        self.combo_categoria.setCurrentText("")
        form.addRow("Categoría:", self.combo_categoria)

        self.spin_valor = QDoubleSpinBox()
        self.spin_valor.setRange(0.0, 9_999_999.99)
        self.spin_valor.setDecimals(2)
        self.spin_valor.setPrefix("S/. ")
        form.addRow("Valor de adquisición:", self.spin_valor)

        if incluir_codigo:
            self.date_adquisicion = QDateEdit()
            self.date_adquisicion.setCalendarPopup(True)
            self.date_adquisicion.setDisplayFormat("dd/MM/yyyy")
            self.date_adquisicion.setDate(QDate.currentDate())
            self.date_adquisicion.setMaximumDate(QDate.currentDate())
            form.addRow("Fecha de adquisición:", self.date_adquisicion)
        else:
            self.date_adquisicion = None

        self.texto_observaciones = QTextEdit()
        self.texto_observaciones.setFixedHeight(70)
        self.texto_observaciones.setPlaceholderText("Observaciones (opcional)")
        form.addRow("Observaciones:", self.texto_observaciones)

        return form

    def _leer_formulario(self) -> dict:
        datos = {
            "descripcion": self.input_descripcion.text().strip(),
            "categoria": self.combo_categoria.currentText().strip(),
            "valor_adquisicion": self.spin_valor.value() or None,
            "observaciones": self.texto_observaciones.toPlainText().strip(),
        }
        if self.input_codigo is not None:
            datos["codigo_patrimonial"] = self.input_codigo.text().strip()
        if self.date_adquisicion is not None:
            datos["fecha_adquisicion"] = self.date_adquisicion.date().toPython()
        return datos


# ════════════════════════════════════════════════════════════════
# Diálogo: Registrar nuevo bien (CRUD - Crear)
# ════════════════════════════════════════════════════════════════
class DialogoRegistrarBien(_FormularioBien, QDialog):
    """Crea un bien patrimonial nuevo vía BienesService.registrar()."""

    def __init__(self, usuario_id: int, parent=None):
        super().__init__(parent)
        self.usuario_id = usuario_id
        self.setWindowTitle("Registrar nuevo bien")
        self.setObjectName("dialogoRegistrarBien")
        self.setMinimumWidth(420)
        self._armar_ui()

    def _armar_ui(self):
        layout = QVBoxLayout(self)
        layout.addLayout(self._construir_formulario(incluir_codigo=True))

        botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botones.button(QDialogButtonBox.Ok).setText("Registrar bien")
        botones.accepted.connect(self._confirmar)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)

    def _confirmar(self):
        datos = self._leer_formulario()

        if not datos["codigo_patrimonial"] or not datos["descripcion"]:
            QMessageBox.warning(self, "Datos incompletos",
                                 "El código patrimonial y la descripción son obligatorios.")
            return

        resultado = BienesService.registrar(datos, self.usuario_id)

        if resultado.ok:
            QMessageBox.information(self, "Bien registrado", resultado.mensaje)
            self.accept()
        else:
            QMessageBox.warning(self, "No se pudo registrar el bien", resultado.mensaje)


# ════════════════════════════════════════════════════════════════
# Diálogo: Editar bien existente (CRUD - Actualizar)
# ════════════════════════════════════════════════════════════════
class DialogoEditarBien(_FormularioBien, QDialog):
    """Edita los datos generales de un bien vía BienesService.editar().

    El código patrimonial no es editable aquí (es la llave de negocio del
    bien); el estado tampoco se toca desde este diálogo, para eso está
    DialogoCambiarEstado (RF-34).
    """

    def __init__(self, bien_id: int, usuario_id: int, parent=None):
        super().__init__(parent)
        self.bien_id = bien_id
        self.usuario_id = usuario_id
        self.setWindowTitle("Editar bien")
        self.setObjectName("dialogoEditarBien")
        self.setMinimumWidth(420)
        self._armar_ui()
        self._cargar_datos()

    def _armar_ui(self):
        layout = QVBoxLayout(self)

        self.label_codigo = QLabel()
        self.label_codigo.setObjectName("labelCodigoReadOnly")
        layout.addWidget(self.label_codigo)

        layout.addLayout(self._construir_formulario(incluir_codigo=False))

        botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botones.button(QDialogButtonBox.Ok).setText("Guardar cambios")
        botones.accepted.connect(self._confirmar)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)

    def _cargar_datos(self):
        resultado = BienesService.obtener_por_id(self.bien_id)
        if not resultado.ok:
            QMessageBox.warning(self, "Error", resultado.mensaje)
            self.reject()
            return

        datos = resultado.datos
        self.label_codigo.setText(f"<b>Código patrimonial:</b> {datos['codigo_patrimonial']}")
        self.input_descripcion.setText(datos.get("descripcion") or "")
        self.combo_categoria.setCurrentText(datos.get("categoria") or "")
        self.spin_valor.setValue(datos.get("valor_adquisicion") or 0.0)
        self.texto_observaciones.setPlainText(datos.get("observaciones") or "")

    def _confirmar(self):
        datos = self._leer_formulario()

        if not datos["descripcion"]:
            QMessageBox.warning(self, "Datos incompletos", "La descripción es obligatoria.")
            return

        resultado = BienesService.editar(self.bien_id, datos, self.usuario_id)

        if resultado.ok:
            QMessageBox.information(self, "Bien actualizado", resultado.mensaje)
            self.accept()
        else:
            QMessageBox.warning(self, "No se pudo actualizar el bien", resultado.mensaje)


# ════════════════════════════════════════════════════════════════
# Diálogo: Asignar bien a docente y/o taller
# ════════════════════════════════════════════════════════════════
class DialogoAsignarBien(QDialog):
    """Asigna un bien Disponible a un docente y/o taller vía BienesService.asignar()."""

    def __init__(self, bien: dict, usuario_id: int, parent=None):
        super().__init__(parent)
        self.bien = bien
        self.usuario_id = usuario_id
        self.setWindowTitle(f"Asignar bien — {bien['codigo_patrimonial']}")
        self.setObjectName("dialogoAsignarBien")
        self.setMinimumWidth(420)
        self._armar_ui()
        self._cargar_combos()

    def _armar_ui(self):
        layout = QVBoxLayout(self)

        info = QLabel(f"<b>{self.bien['codigo_patrimonial']}</b> — {self.bien['descripcion']}")
        info.setWordWrap(True)
        layout.addWidget(info)

        form = QFormLayout()

        self.combo_docente = QComboBox()
        form.addRow("Docente:", self.combo_docente)

        self.combo_taller = QComboBox()
        form.addRow("Taller:", self.combo_taller)

        self.date_devolucion = QDateEdit()
        self.date_devolucion.setCalendarPopup(True)
        self.date_devolucion.setDisplayFormat("dd/MM/yyyy")
        self.date_devolucion.setDate(QDate.currentDate().addDays(7))
        self.date_devolucion.setMinimumDate(QDate.currentDate())
        form.addRow("Devolución esperada:", self.date_devolucion)

        self.texto_observaciones = QTextEdit()
        self.texto_observaciones.setFixedHeight(70)
        self.texto_observaciones.setPlaceholderText("Observaciones de la asignación (opcional)")
        form.addRow("Observaciones:", self.texto_observaciones)

        layout.addLayout(form)

        self.aviso = QLabel("Seleccione al menos un docente o un taller.")
        self.aviso.setObjectName("avisoAdvertencia")
        self.aviso.setWordWrap(True)
        layout.addWidget(self.aviso)

        botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botones.button(QDialogButtonBox.Ok).setText("Asignar bien")
        botones.accepted.connect(self._confirmar)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)

    def _cargar_combos(self):
        self.combo_docente.addItem("— Ninguno —", None)
        for d in _cargar_docentes():
            texto = d.get("nombre") or f"Docente {d.get('id')}"
            if d.get("especialidad") and d["especialidad"] != "—":
                texto = f"{texto} ({d['especialidad']})"
            self.combo_docente.addItem(texto, d.get("id"))

        self.combo_taller.addItem("— Ninguno —", None)
        for t in _cargar_talleres():
            texto = t.get("nombre") or f"Taller {t.get('id')}"
            if t.get("docente"):
                texto = f"{texto} — {t['docente']}"
            self.combo_taller.addItem(texto, t.get("id"))

        if self.combo_docente.count() == 1 and self.combo_taller.count() == 1:
            self.aviso.setText(
                "⚠️ No se pudieron cargar docentes ni talleres. Verifique que "
                "DocenteService y TallerService estén disponibles."
            )

    def _confirmar(self):
        docente_id = self.combo_docente.currentData()
        taller_id = self.combo_taller.currentData()

        if docente_id is None and taller_id is None:
            QMessageBox.warning(self, "Datos incompletos",
                                 "Debe seleccionar al menos un docente o un taller.")
            return

        resultado = BienesService.asignar(
            bien_id=self.bien["id"],
            docente_id=docente_id,
            taller_id=taller_id,
            fecha_devolucion=self.date_devolucion.date().toPython(),
            observaciones=self.texto_observaciones.toPlainText().strip() or None,
            usuario_id=self.usuario_id,
        )

        if resultado.ok:
            QMessageBox.information(self, "Bien asignado", resultado.mensaje)
            self.accept()
        else:
            QMessageBox.warning(self, "No se pudo asignar el bien", resultado.mensaje)


# ════════════════════════════════════════════════════════════════
# Diálogo: Registrar devolución (RF-33)
# ════════════════════════════════════════════════════════════════
class DialogoDevolucion(QDialog):
    """Registra la devolución de un bien asignado, con su estado de conservación."""

    def __init__(self, bien: dict, usuario_id: int, parent=None):
        super().__init__(parent)
        self.bien = bien
        self.usuario_id = usuario_id
        self.setWindowTitle(f"Registrar devolución — {bien['codigo_patrimonial']}")
        self.setObjectName("dialogoDevolucion")
        self.setMinimumWidth(420)
        self._armar_ui()

    def _armar_ui(self):
        layout = QVBoxLayout(self)

        info = QLabel(
            f"<b>{self.bien['codigo_patrimonial']}</b> — {self.bien['descripcion']}<br>"
            f"Asignado a: {self.bien.get('asignado_a') or 'N/A'}"
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        form = QFormLayout()

        self.combo_conservacion = QComboBox()
        self.combo_conservacion.addItems(ESTADOS_CONSERVACION)
        self.combo_conservacion.setCurrentText("Bueno")
        form.addRow("Estado de conservación:", self.combo_conservacion)

        self.texto_observaciones = QTextEdit()
        self.texto_observaciones.setPlaceholderText("Observaciones de la devolución (opcional)")
        self.texto_observaciones.setFixedHeight(80)
        form.addRow("Observaciones:", self.texto_observaciones)

        layout.addLayout(form)

        self.aviso = QLabel("")
        self.aviso.setObjectName("avisoAdvertencia")
        self.aviso.setWordWrap(True)
        layout.addWidget(self.aviso)
        self.combo_conservacion.currentTextChanged.connect(self._actualizar_aviso)
        self._actualizar_aviso(self.combo_conservacion.currentText())

        botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botones.button(QDialogButtonBox.Ok).setText("Registrar devolución")
        botones.accepted.connect(self._confirmar)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)

    def _actualizar_aviso(self, estado: str):
        if estado in ("Malo", "Inservible"):
            self.aviso.setText("⚠️ El bien pasará automáticamente a estado Mantenimiento.")
        else:
            self.aviso.setText("El bien pasará automáticamente a estado Disponible.")

    def _confirmar(self):
        asignacion_id = self.bien.get("asignacion_activa_id")
        if not asignacion_id:
            QMessageBox.warning(self, "Sin asignación activa",
                                 "Este bien no tiene una asignación activa para devolver.")
            self.reject()
            return

        resultado = BienesService.devolver(
            asignacion_id=asignacion_id,
            estado_conservacion=self.combo_conservacion.currentText(),
            observaciones_devolucion=self.texto_observaciones.toPlainText().strip() or None,
            usuario_id=self.usuario_id,
        )

        if resultado.ok:
            QMessageBox.information(self, "Devolución registrada", resultado.mensaje)
            self.accept()
        else:
            QMessageBox.warning(self, "No se pudo registrar la devolución", resultado.mensaje)


# ════════════════════════════════════════════════════════════════
# Diálogo: Cambiar estado (RF-34)
# ════════════════════════════════════════════════════════════════
class DialogoCambiarEstado(QDialog):
    """Cambia el estado de un bien respetando las transiciones válidas del servicio."""

    # Debe reflejar TRANSICIONES_MANUALES de bienes_service.py
    TRANSICIONES = {
        "Disponible":    ["Mantenimiento", "DeBaja"],
        "Mantenimiento": ["Disponible", "DeBaja"],
        "Asignado":      ["DeBaja"],
        "DeBaja":        [],
    }

    def __init__(self, bien: dict, usuario_id: int, parent=None):
        super().__init__(parent)
        self.bien = bien
        self.usuario_id = usuario_id
        self.setWindowTitle(f"Cambiar estado — {bien['codigo_patrimonial']}")
        self.setObjectName("dialogoCambiarEstado")
        self.setMinimumWidth(380)
        self._armar_ui()

    def _armar_ui(self):
        layout = QVBoxLayout(self)

        estado_actual = self.bien["estado"]
        opciones = self.TRANSICIONES.get(estado_actual, [])

        layout.addWidget(QLabel(
            f"<b>{self.bien['codigo_patrimonial']}</b> — {self.bien['descripcion']}<br>"
            f"Estado actual: {ESTADOS_BADGE.get(estado_actual, estado_actual)}"
        ))

        if not opciones:
            aviso = QLabel(
                "⚫ Este bien está De Baja y no admite cambios de estado."
                if estado_actual == "DeBaja"
                else "No hay transiciones manuales disponibles para este estado."
            )
            aviso.setWordWrap(True)
            layout.addWidget(aviso)
            botones = QDialogButtonBox(QDialogButtonBox.Close)
            botones.rejected.connect(self.reject)
            botones.accepted.connect(self.reject)
            layout.addWidget(botones)
            self.combo_nuevo_estado = None
            return

        form = QFormLayout()
        self.combo_nuevo_estado = QComboBox()
        self.combo_nuevo_estado.addItems(opciones)
        form.addRow("Nuevo estado:", self.combo_nuevo_estado)
        layout.addLayout(form)

        if estado_actual == "Asignado":
            aviso = QLabel(
                "⚠️ El bien está actualmente asignado. Dar de baja aquí es una "
                "acción de emergencia; lo normal es registrar la devolución primero."
            )
            aviso.setWordWrap(True)
            layout.addWidget(aviso)

        botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botones.button(QDialogButtonBox.Ok).setText("Cambiar estado")
        botones.accepted.connect(self._confirmar)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)

    def _confirmar(self):
        nuevo_estado = self.combo_nuevo_estado.currentText()

        if nuevo_estado == "DeBaja":
            confirmacion = QMessageBox.question(
                self, "Confirmar baja definitiva",
                f"¿Confirma dar de baja el bien {self.bien['codigo_patrimonial']}? "
                "Esta acción es definitiva.",
                QMessageBox.Yes | QMessageBox.No
            )
            if confirmacion != QMessageBox.Yes:
                return

        resultado = BienesService.cambiar_estado(
            bien_id=self.bien["id"],
            nuevo_estado=nuevo_estado,
            usuario_id=self.usuario_id,
        )

        if resultado.ok:
            QMessageBox.information(self, "Estado actualizado", resultado.mensaje)
            self.accept()
        else:
            QMessageBox.warning(self, "No se pudo cambiar el estado", resultado.mensaje)


# ════════════════════════════════════════════════════════════════
# Diálogo: Historial de asignaciones (apoyo para RF-35 / trazabilidad)
# ════════════════════════════════════════════════════════════════
class DialogoHistorial(QDialog):
    def __init__(self, bien: dict, parent=None):
        super().__init__(parent)
        self.bien = bien
        self.setWindowTitle(f"Historial — {bien['codigo_patrimonial']}")
        self.setObjectName("dialogoHistorial")
        self.resize(720, 380)
        self._armar_ui()
        self._cargar()

    def _armar_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"<b>{self.bien['codigo_patrimonial']}</b> — {self.bien['descripcion']}"))

        self.tabla = QTableWidget(0, 6)
        self.tabla.setHorizontalHeaderLabels(
            ["Docente", "Taller", "F. Asignación", "F. Dev. Esperada", "F. Dev. Real", "Conservación"]
        )
        self.tabla.horizontalHeader().setStretchLastSection(True)
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        layout.addWidget(self.tabla)

        cerrar = QDialogButtonBox(QDialogButtonBox.Close)
        cerrar.rejected.connect(self.reject)
        cerrar.accepted.connect(self.reject)
        layout.addWidget(cerrar)

    def _cargar(self):
        resultado = BienesService.obtener_asignaciones(self.bien["id"])
        if not resultado.ok:
            QMessageBox.warning(self, "Error", resultado.mensaje)
            return

        filas = resultado.lista or []
        self.tabla.setRowCount(len(filas))
        for i, a in enumerate(filas):
            valores = [
                a["docente"], a["taller"], a["fecha_asignacion"],
                a["fecha_devolucion_esperada"], a["fecha_devolucion_real"], a["conservacion"]
            ]
            for j, v in enumerate(valores):
                self.tabla.setItem(i, j, QTableWidgetItem(str(v)))


# ════════════════════════════════════════════════════════════════
# Panel principal
# ════════════════════════════════════════════════════════════════
class PanelBienesPatrimoniales(QWidget):
    """
    Panel de gestión de bienes patrimoniales.

    usuario_id: id del usuario en sesión, requerido por el servicio para
                auditoría en cada operación de escritura.
    """

    bien_actualizado = Signal()

    COLUMNAS = ["Código", "Descripción", "Categoría", "Estado", "Asignado a",
                "Vence", "Alertas", "Acciones"]


    def __init__(self, usuario_id, parent=None):
        super().__init__(parent)
        self.usuario_id = getattr(usuario_id, "usuario_id", usuario_id)
        self._datos_actuales = [] 
        self._datos_filtrados = []
        self.setObjectName("panelBienes")
        self._armar_ui()
        self.refrescar()
        self.setStyleSheet("""
            QFrame#kpiBienesContainer {
                background: transparent;
                border: none;
            }
            QFrame#kpiCard {
                background: #ffffff;
                border: 1px solid #e5e7eb;
                border: #4f46e5;
                border-radius: 10px;
            }
            QLabel#kpiValor {
                font-size: 18px;
                font-weight: 700;
                color: #1e293b;
            }
            QLabel#kpiNombre {
                font-size: 10px;
                color: #64748b;
            }
        """)


    # ── Construcción de UI ──────────────────────────────────────
    def _armar_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(2)

        layout.addWidget(self._armar_kpis())
        layout.addLayout(self._armar_filtros())

        self.tabla = QTableWidget(0, len(self.COLUMNAS))
        self.tabla.setObjectName("tablaBienes")
        self.tabla.setHorizontalHeaderLabels(self.COLUMNAS) 
        self.tabla.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)  
        self.tabla.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tabla.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)            
        self.tabla.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tabla.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeToContents)
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla.setAlternatingRowColors(False)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tabla.verticalHeader().setDefaultSectionSize(40)  
        layout.addWidget(self.tabla)

        leyenda = QLabel("⏰ Vencidos; 💔 Dañados; 🔧 En mantenimiento")
        leyenda.setObjectName("leyendaAlertas")
        layout.addWidget(leyenda)

    def _armar_kpis(self) -> QWidget:
        card = QFrame()
        card.setObjectName("kpiBienesContainer")
        grid = QGridLayout(card)
        grid.setSpacing(8)

        self.kpi_labels = {}
        etiquetas = [
            ("total", "Total"),
            ("disponibles", "Disponibles"),
            ("asignados", "Asignados"),
            ("mantenimiento", "Mantenimiento"),
            ("vencidos", "⏰ Vencidos"),
            ("daniados", "💔 Dañados"),
        ]
        for i, (clave, texto) in enumerate(etiquetas):
            caja = QFrame()
            caja.setObjectName("kpiCard")
            v = QVBoxLayout(caja)
            v.setContentsMargins(10, 8, 10, 8)
            valor = QLabel("0")
            valor.setObjectName("kpiValor")
            nombre = QLabel(texto)
            nombre.setObjectName("kpiNombre")
            v.addWidget(valor)
            v.addWidget(nombre)
            grid.addWidget(caja, 0, i)
            self.kpi_labels[clave] = valor

        return card

    def _armar_filtros(self) -> QHBoxLayout:
        fila = QHBoxLayout()

        self.input_busqueda = QLineEdit()
        self.input_busqueda.setObjectName("inputBusquedaBienes")
        self.input_busqueda.setPlaceholderText("Buscar por código o descripción…")
        self.input_busqueda.textChanged.connect(self._aplicar_filtros_locales)

        self.combo_estado = QComboBox()
        self.combo_estado.addItems(["Todos", "Disponible", "Asignado", "Mantenimiento", "DeBaja"])
        self.combo_estado.currentIndexChanged.connect(self.refrescar)

        self.check_solo_alertas = QCheckBox("Solo con alertas")
        self.check_solo_alertas.stateChanged.connect(self._aplicar_filtros_locales)

        boton_editar = QPushButton("Editar")
        boton_editar.setObjectName("botonEditar")
        boton_editar.clicked.connect(self._abrir_editar)

        boton_nuevo = QPushButton("+ Nuevo bien")
        boton_nuevo.setObjectName("botonNuevoBien")
        boton_nuevo.clicked.connect(self._abrir_registrar)

        fila.addWidget(self.input_busqueda, 2)
        fila.addWidget(QLabel("Estado:"))
        fila.addWidget(self.combo_estado, 1)
        fila.addWidget(self.check_solo_alertas)
        fila.addStretch()
        fila.addWidget(boton_editar)
        fila.addWidget(boton_nuevo)
        return fila

    # ── Carga de datos ──────────────────────────────────────────
    def refrescar(self):
        filtro = {}
        estado = self.combo_estado.currentText()
        if estado != "Todos":
            filtro["estado"] = estado

        resultado = BienesService.listar(filtro or None)
        if not resultado.ok:
            QMessageBox.warning(self, "Error al cargar bienes", resultado.mensaje)
            self._datos_actuales = []
        else:
            self._datos_actuales = resultado.lista or []

        self._actualizar_kpis()
        self._aplicar_filtros_locales()

    def _actualizar_kpis(self):
        datos = self._datos_actuales
        self.kpi_labels["total"].setText(str(len(datos)))
        self.kpi_labels["disponibles"].setText(str(sum(1 for b in datos if b["estado"] == "Disponible")))
        self.kpi_labels["asignados"].setText(str(sum(1 for b in datos if b["estado"] == "Asignado")))
        self.kpi_labels["mantenimiento"].setText(str(sum(1 for b in datos if b["estado"] == "Mantenimiento")))
        self.kpi_labels["vencidos"].setText(str(sum(1 for b in datos if b["alerta_vencido"])))
        self.kpi_labels["daniados"].setText(str(sum(1 for b in datos if b["alerta_daniado"])))

    def _aplicar_filtros_locales(self):
        texto = self.input_busqueda.text().strip().lower()
        solo_alertas = self.check_solo_alertas.isChecked()

        filas = self._datos_actuales
        if texto:
            filas = [
                b for b in filas
                if texto in b["codigo_patrimonial"].lower() or texto in b["descripcion"].lower()
            ]
        if solo_alertas:
            filas = [
                b for b in filas
                if b["alerta_vencido"] or b["alerta_daniado"] or b["alerta_mantenimiento"]
            ]

        self._datos_filtrados = filas
        self._poblar_tabla(filas)

    # ── Render de tabla ─────────────────────────────────────────
    def _poblar_tabla(self, filas: list):
        self.tabla.setRowCount(len(filas))

        for fila_idx, bien in enumerate(filas):
            color = _color_fila(bien)

            valores = [
                bien["codigo_patrimonial"],
                bien["descripcion"],
                bien["categoria"],
                ESTADOS_BADGE.get(bien["estado"], bien["estado"]),
                bien.get("asignado_a") or "—",
                bien.get("fecha_devolucion_esperada") or "—",
                _alerta_texto(bien),
            ]
            for col, valor in enumerate(valores):
                item = QTableWidgetItem(str(valor))
                item.setBackground(QBrush(color))
                self.tabla.setItem(fila_idx, col, item)

            self.tabla.setCellWidget(fila_idx, 7, self._armar_acciones(bien))

    def _armar_acciones(self, bien: dict) -> QWidget:
        contenedor = QWidget()
        layout = QHBoxLayout(contenedor)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)

        boton_asignar = QToolButton()
        boton_asignar.setText("🤝 Asignar")
        boton_asignar.setEnabled(bien["estado"] == "Disponible")
        boton_asignar.setToolTip(
            "Asignar a docente o taller" if bien["estado"] == "Disponible"
            else f"Solo se puede asignar un bien Disponible (estado actual: {bien['estado']})"
        )
        boton_asignar.clicked.connect(lambda: self._abrir_asignar(bien))

        boton_devolver = QToolButton()
        boton_devolver.setText("↩ Devolver")
        boton_devolver.setEnabled(bien.get("asignacion_activa_id") is not None)
        boton_devolver.setToolTip(
            "Registrar devolución" if bien.get("asignacion_activa_id")
            else "El bien no tiene una asignación activa"
        )
        boton_devolver.clicked.connect(lambda: self._abrir_devolucion(bien))

        boton_estado = QToolButton()
        boton_estado.setText("⚙ Estado")
        boton_estado.setToolTip("Cambiar estado")
        boton_estado.clicked.connect(lambda: self._abrir_cambiar_estado(bien))

        boton_historial = QToolButton()
        boton_historial.setText("🕘")
        boton_historial.setToolTip("Ver historial de asignaciones")
        boton_historial.clicked.connect(lambda: self._abrir_historial(bien))

        layout.addWidget(boton_asignar)
        layout.addWidget(boton_devolver)
        layout.addWidget(boton_estado)
        layout.addWidget(boton_historial)
        return contenedor

    # ── Acciones ────────────────────────────────────────────────
    def _abrir_registrar(self):
        dialogo = DialogoRegistrarBien(self.usuario_id, self)
        if dialogo.exec() == QDialog.Accepted:
            self.refrescar()
            self.bien_actualizado.emit()

    def _abrir_editar(self):
        fila = self.tabla.currentRow()

        if fila < 0:
            QMessageBox.information(
                self,
                "Editar bien",
                "Seleccione un bien de la tabla."
            )
            return

        if fila >= len(self._datos_filtrados):
            return

        bien = self._datos_filtrados[fila]

        dialogo = DialogoEditarBien(
            bien["id"],
            self.usuario_id,
            self
        )

        if dialogo.exec() == QDialog.Accepted:
            self.refrescar()
            self.bien_actualizado.emit()

    def _abrir_asignar(self, bien: dict):
        dialogo = DialogoAsignarBien(bien, self.usuario_id, self)
        if dialogo.exec() == QDialog.Accepted:
            self.refrescar()
            self.bien_actualizado.emit()

    def _abrir_devolucion(self, bien: dict):
        dialogo = DialogoDevolucion(bien, self.usuario_id, self)
        if dialogo.exec() == QDialog.Accepted:
            self.refrescar()
            self.bien_actualizado.emit()

    def _abrir_cambiar_estado(self, bien: dict):
        dialogo = DialogoCambiarEstado(bien, self.usuario_id, self)
        if dialogo.exec() == QDialog.Accepted:
            self.refrescar()
            self.bien_actualizado.emit()

    def _abrir_historial(self, bien: dict):
        dialogo = DialogoHistorial(bien, self)
        dialogo.exec()