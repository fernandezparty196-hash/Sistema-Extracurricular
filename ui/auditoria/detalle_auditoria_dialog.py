import json

from PySide6.QtCore    import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QTextEdit, QPushButton, QFrame, QDialogButtonBox
)

from services.auditoria_service import RegistroAuditoria


ETIQUETAS_ACCION = {
    "INSERT": ("Creación",     "badge_insert"),
    "UPDATE": ("Modificación", "badge_update"),
    "DELETE": ("Eliminación",  "badge_delete"),
}


def _formatear_json(datos: dict | None) -> str:
    if not datos:
        return "— Sin datos —"
    try:
        return json.dumps(datos, indent=2, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return str(datos)


class DetalleAuditoriaDialog(QDialog):

    def __init__(self, registro: RegistroAuditoria, parent=None):
        super().__init__(parent)
        self.registro = registro
        self.setWindowTitle("Detalle de auditoría")
        self.setMinimumSize(720, 480)
        self._construir_ui()

    def _construir_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 20)
        layout.setSpacing(16)

        layout.addWidget(self._construir_encabezado())
        layout.addWidget(self._construir_metadatos())
        layout.addWidget(self._construir_comparacion(), stretch=1)

        botones = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        botones.rejected.connect(self.reject)
        botones.accepted.connect(self.accept)
        botones.button(QDialogButtonBox.StandardButton.Close).clicked.connect(self.accept)
        layout.addWidget(botones)

    def _construir_encabezado(self) -> QLabel:
        etiqueta, _ = ETIQUETAS_ACCION.get(self.registro.accion, (self.registro.accion, "badge_update"))
        titulo = QLabel(f"{etiqueta} · {self.registro.tabla_afectada}")
        titulo.setObjectName("titulo")
        return titulo

    def _construir_metadatos(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        grid = QGridLayout(card)
        grid.setContentsMargins(16, 14, 16, 14)
        grid.setHorizontalSpacing(28)
        grid.setVerticalSpacing(6)

        r = self.registro
        pares = [
            ("Fecha y hora",     r.created_at.strftime("%d/%m/%Y  %H:%M:%S")),
            ("Usuario",          r.usuario_nombre),
            ("Tabla afectada",   r.tabla_afectada),
            ("ID de registro",   str(r.registro_id) if r.registro_id is not None else "—"),
            ("Dirección IP",     r.ip_address or "—"),
        ]

        for i, (etiqueta, valor) in enumerate(pares):
            fila, col = divmod(i, 2)
            lbl_etq = QLabel(etiqueta.upper())
            lbl_etq.setObjectName("subtitulo")
            lbl_val = QLabel(valor)
            bloque = QVBoxLayout()
            bloque.setSpacing(2)
            bloque.addWidget(lbl_etq)
            bloque.addWidget(lbl_val)
            contenedor = QFrame()
            contenedor.setLayout(bloque)
            grid.addWidget(contenedor, fila, col)

        return card

    def _construir_comparacion(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        lbl = QLabel("COMPARACIÓN DE DATOS")
        lbl.setObjectName("subtitulo")
        layout.addWidget(lbl)

        fila = QHBoxLayout()
        fila.setSpacing(16)

        fila.addLayout(self._panel_json("Antes", self.registro.datos_anteriores))
        fila.addLayout(self._panel_json("Después", self.registro.datos_nuevos))

        layout.addLayout(fila)
        return card

    def _panel_json(self, titulo: str, datos: dict | None) -> QVBoxLayout:
        col = QVBoxLayout()
        col.setSpacing(6)

        lbl = QLabel(titulo)
        lbl.setStyleSheet("font-weight: 600;")
        col.addWidget(lbl)

        texto = QTextEdit()
        texto.setReadOnly(True)
        texto.setPlainText(_formatear_json(datos))
        texto.setStyleSheet("font-family: Consolas, 'Courier New', monospace; font-size: 12px;")
        col.addWidget(texto)

        return col
