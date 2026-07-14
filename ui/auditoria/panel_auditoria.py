from datetime import date, timedelta

from PySide6.QtCore    import Qt, QDate
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QComboBox, QDateEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QAbstractItemView, QSizePolicy
)

from services.auditoria_service import (
    AuditoriaService, ResultadoAuditoria, RegistroAuditoria,
    ACCIONES_DISPONIBLES, POR_PAGINA_DEFAULT
)
from services.auth_service import SesionUsuario
from ui.auditoria.detalle_auditoria_dialog import DetalleAuditoriaDialog


ETIQUETAS_ACCION = {
    "INSERT": ("Creación",     "badge_insert"),
    "UPDATE": ("Modificación", "badge_update"),
    "DELETE": ("Eliminación",  "badge_delete"),
}

COLUMNAS = ["Fecha y hora", "Usuario", "Tabla", "Acción", "ID Registro", "IP", ""]


class PanelAuditoria(QWidget):

    def __init__(self, sesion: SesionUsuario, parent=None):
        super().__init__(parent)
        self.sesion = sesion
        self._pagina_actual = 1
        self._ultimo_resultado: ResultadoAuditoria | None = None

        self._construir_ui()

        if self.sesion.es_administrador:
            self._buscar()

    # ══════════════════════════════════════════════════════════════
    # CONSTRUCCIÓN DE UI
    # ══════════════════════════════════════════════════════════════

    def _construir_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        if not self.sesion.es_administrador:
            layout.addWidget(self._construir_sin_permiso())
            return

        layout.addWidget(self._construir_encabezado())
        layout.addSpacing(8)
        layout.addWidget(self._construir_filtros())
        layout.addSpacing(12)

        lbl_registros = QLabel("Registros de auditoría")
        lbl_registros.setObjectName("etiqueta_seccion")
        layout.addWidget(lbl_registros)
        layout.addSpacing(6)

        layout.addWidget(self._construir_tabla(), stretch=1)
        layout.addLayout(self._construir_paginacion())

    def _construir_sin_permiso(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 24, 24, 24)

        lbl = QLabel("🔒  No tienes permisos para ver la auditoría del sistema.")
        lbl.setObjectName("subtitulo")
        layout.addWidget(lbl)
        return card

    def _construir_encabezado(self) -> QWidget:
        """Solo subtítulo — este panel es exclusivo de Administrador."""
        contenedor = QWidget()
        layout = QVBoxLayout(contenedor)
        layout.setContentsMargins(0, 0, 0, 0)

        subtitulo = QLabel("Historial de cambios realizados por los usuarios del sistema.")
        subtitulo.setObjectName("subtitulo")

        layout.addWidget(subtitulo)
        return contenedor

    def _construir_filtros(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        layout = QGridLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(8)

        # ── Tabla afectada ────────────────────────────────────────
        self.combo_tabla = QComboBox()
        self.combo_tabla.addItem("Todas las tablas", None)
        for nombre_tabla in AuditoriaService.listar_tablas_disponibles():
            self.combo_tabla.addItem(nombre_tabla, nombre_tabla)

        # ── Acción ───────────────────────────────────────────────
        self.combo_accion = QComboBox()
        self.combo_accion.addItem("Todas las acciones", None)
        for accion in ACCIONES_DISPONIBLES:
            etiqueta, _ = ETIQUETAS_ACCION.get(accion, (accion, None))
            self.combo_accion.addItem(etiqueta, accion)

        # ── Rango de fechas (por defecto: últimos 30 días) ─────────
        self.date_desde = QDateEdit(calendarPopup=True)
        self.date_desde.setDisplayFormat("dd/MM/yyyy")
        self.date_desde.setDate(QDate.currentDate().addDays(-30))

        self.date_hasta = QDateEdit(calendarPopup=True)
        self.date_hasta.setDisplayFormat("dd/MM/yyyy")
        self.date_hasta.setDate(QDate.currentDate())

        # ── Texto libre ──────────────────────────────────────────
        self.input_busqueda = QLineEdit()
        self.input_busqueda.setPlaceholderText("Buscar por usuario o tabla…")
        self.input_busqueda.returnPressed.connect(self._buscar)

        # ── Botones ──────────────────────────────────────────────
        btn_buscar = QPushButton("Buscar")
        btn_buscar.clicked.connect(self._buscar)

        btn_limpiar = QPushButton("Limpiar filtros")
        btn_limpiar.setObjectName("btn_ghost")
        btn_limpiar.clicked.connect(self._limpiar_filtros)

        # ── Layout en grilla ─────────────────────────────────────
        layout.addWidget(self._campo("Tabla", self.combo_tabla),        0, 0)
        layout.addWidget(self._campo("Acción", self.combo_accion),      0, 1)
        layout.addWidget(self._campo("Desde", self.date_desde),         0, 2)
        layout.addWidget(self._campo("Hasta", self.date_hasta),         0, 3)
        layout.addWidget(self._campo("Búsqueda", self.input_busqueda),  0, 4)

        fila_botones = QHBoxLayout()
        fila_botones.addStretch()
        fila_botones.addWidget(btn_limpiar)
        fila_botones.addWidget(btn_buscar)
        layout.addLayout(fila_botones, 1, 0, 1, 5)

        for col in range(5):
            layout.setColumnStretch(col, 1)

        return card

    def _campo(self, etiqueta: str, widget: QWidget) -> QWidget:
        contenedor = QWidget()
        layout = QVBoxLayout(contenedor)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        lbl = QLabel(etiqueta.upper())
        lbl.setObjectName("subtitulo")
        layout.addWidget(lbl)
        layout.addWidget(widget)
        return contenedor

    def _construir_tabla(self) -> QTableWidget:
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(len(COLUMNAS))
        self.tabla.setHorizontalHeaderLabels(COLUMNAS)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setShowGrid(False)
        self.tabla.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        header = self.tabla.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)

        self.tabla.doubleClicked.connect(self._abrir_detalle_de_fila_actual)
        return self.tabla

    def _construir_paginacion(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 6, 0, 0)

        self.lbl_resumen = QLabel("")
        self.lbl_resumen.setObjectName("subtitulo")

        self.btn_anterior = QPushButton("‹ Anterior")
        self.btn_anterior.setObjectName("btn_ghost")
        self.btn_anterior.clicked.connect(self._pagina_anterior)

        self.lbl_pagina = QLabel("")
        self.lbl_pagina.setObjectName("subtitulo")

        self.btn_siguiente = QPushButton("Siguiente ›")
        self.btn_siguiente.setObjectName("btn_ghost")
        self.btn_siguiente.clicked.connect(self._pagina_siguiente)

        layout.addWidget(self.lbl_resumen)
        layout.addStretch()
        layout.addWidget(self.btn_anterior)
        layout.addWidget(self.lbl_pagina)
        layout.addWidget(self.btn_siguiente)
        return layout

    # ══════════════════════════════════════════════════════════════
    # BÚSQUEDA / FILTROS
    # ══════════════════════════════════════════════════════════════

    def _buscar(self) -> None:
        self._pagina_actual = 1
        self._ejecutar_consulta()

    def _limpiar_filtros(self) -> None:
        self.combo_tabla.setCurrentIndex(0)
        self.combo_accion.setCurrentIndex(0)
        self.date_desde.setDate(QDate.currentDate().addDays(-30))
        self.date_hasta.setDate(QDate.currentDate())
        self.input_busqueda.clear()
        self._buscar()

    def _ejecutar_consulta(self) -> None:
        resultado = AuditoriaService.listar(
            tabla_afectada = self.combo_tabla.currentData(),
            accion         = self.combo_accion.currentData(),
            fecha_desde    = self.date_desde.date().toPython(),
            fecha_hasta    = self.date_hasta.date().toPython(),
            texto_libre    = self.input_busqueda.text(),
            pagina         = self._pagina_actual,
            por_pagina     = POR_PAGINA_DEFAULT,
        )
        self._cargar_resultado(resultado)

    # ══════════════════════════════════════════════════════════════
    # RENDER DE RESULTADOS
    # ══════════════════════════════════════════════════════════════

    def _cargar_resultado(self, resultado: ResultadoAuditoria) -> None:
        self._ultimo_resultado = resultado

        if not resultado.ok:
            self.tabla.setRowCount(0)
            self.lbl_resumen.setText(resultado.mensaje)
            self.lbl_pagina.setText("")
            self.btn_anterior.setEnabled(False)
            self.btn_siguiente.setEnabled(False)
            return

        self._pagina_actual = resultado.pagina
        registros = resultado.registros

        self.tabla.setRowCount(len(registros))
        for fila, registro in enumerate(registros):
            self._llenar_fila(fila, registro)

        inicio = 0 if resultado.total == 0 else (resultado.pagina - 1) * POR_PAGINA_DEFAULT + 1
        fin = min(resultado.pagina * POR_PAGINA_DEFAULT, resultado.total)
        self.lbl_resumen.setText(f"Mostrando {inicio}–{fin} de {resultado.total} registros")
        self.lbl_pagina.setText(f"Página {resultado.pagina} de {resultado.total_paginas}")

        self.btn_anterior.setEnabled(resultado.pagina > 1)
        self.btn_siguiente.setEnabled(resultado.pagina < resultado.total_paginas)

    def _llenar_fila(self, fila: int, registro: RegistroAuditoria) -> None:
        self.tabla.setItem(fila, 0, QTableWidgetItem(registro.created_at.strftime("%d/%m/%Y  %H:%M:%S")))
        self.tabla.setItem(fila, 1, QTableWidgetItem(registro.usuario_nombre))
        self.tabla.setItem(fila, 2, QTableWidgetItem(registro.tabla_afectada))

        self.tabla.setCellWidget(fila, 3, self._crear_badge(registro.accion))

        item_registro_id = QTableWidgetItem(str(registro.registro_id) if registro.registro_id is not None else "—")
        item_registro_id.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tabla.setItem(fila, 4, item_registro_id)

        self.tabla.setItem(fila, 5, QTableWidgetItem(registro.ip_address or "—"))

        btn_detalle = QPushButton("Ver detalle")
        btn_detalle.setObjectName("btnLink")
        btn_detalle.setCursor(Qt.PointingHandCursor)
        btn_detalle.clicked.connect(lambda checked, r=registro: self._abrir_detalle(r))
        self.tabla.setCellWidget(fila, 6, btn_detalle)
        self.setStyleSheet("""
                    QPushButton#btnLink{
                        background:transparent;
                        border:none;
                        color:#2563EB;
                        font-weight:600;
                    }

                    QPushButton#btnLink:hover{
                        color:#1D4ED8;
                        text-decoration: underline;
                    }""")

        self.tabla.setRowHeight(fila, 44)

    def _crear_badge(self, accion: str) -> QLabel:
        etiqueta, object_name = ETIQUETAS_ACCION.get(accion, (accion, "badge_update"))
        badge = QLabel(etiqueta)
        badge.setObjectName(object_name)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return badge

    # ══════════════════════════════════════════════════════════════
    # DETALLE / PAGINACIÓN
    # ══════════════════════════════════════════════════════════════

    def _abrir_detalle(self, registro: RegistroAuditoria) -> None:
        dialogo = DetalleAuditoriaDialog(registro, self)
        dialogo.exec()

    def _abrir_detalle_de_fila_actual(self) -> None:
        if not self._ultimo_resultado or not self._ultimo_resultado.ok:
            return
        fila = self.tabla.currentRow()
        if 0 <= fila < len(self._ultimo_resultado.registros):
            self._abrir_detalle(self._ultimo_resultado.registros[fila])

    def _pagina_anterior(self) -> None:
        if self._pagina_actual > 1:
            self._pagina_actual -= 1
            self._ejecutar_consulta()

    def _pagina_siguiente(self) -> None:
        if self._ultimo_resultado and self._pagina_actual < self._ultimo_resultado.total_paginas:
            self._pagina_actual += 1
            self._ejecutar_consulta()