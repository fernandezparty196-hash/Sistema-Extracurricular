"""
ui/bienes/dialogo_registrar_bien.py
"""

from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QLineEdit,
    QTextEdit,
    QDoubleSpinBox,
    QDateEdit,
    QComboBox,
    QPushButton,
    QGridLayout,
    QHBoxLayout,
    QVBoxLayout,
    QMessageBox
)

from services.bienes_service import BienesService


class DialogoRegistrarBien(QDialog):

    def __init__(self, usuario_id, parent=None):
        super().__init__(parent)

        self.usuario_id = usuario_id

        self.setWindowTitle("Registrar Bien Patrimonial")
        self.resize(600, 430)

        self._crear_ui()

    def _crear_ui(self):

        layout = QVBoxLayout(self)
        grid = QGridLayout()
        fila = 0

        grid.addWidget(QLabel("Código Patrimonial *"), fila, 0)
        self.txt_codigo = QLineEdit()
        grid.addWidget(self.txt_codigo, fila, 1)
        fila += 1

        grid.addWidget(QLabel("Descripción *"), fila, 0)
        self.txt_descripcion = QLineEdit()
        grid.addWidget(self.txt_descripcion, fila, 1)
        fila += 1

        grid.addWidget(QLabel("Categoría"), fila, 0)

        self.cmb_categoria = QComboBox()
        self.cmb_categoria.addItems([
            "",
            "Equipos",
            "Mobiliario",
            "Instrumentos",
            "Material Deportivo",
            "Material Artístico",
            "Otros"
        ])

        grid.addWidget(self.cmb_categoria, fila, 1)
        fila += 1

        grid.addWidget(QLabel("Valor de adquisición"), fila, 0)

        self.spn_valor = QDoubleSpinBox()
        self.spn_valor.setMaximum(1000000)
        self.spn_valor.setDecimals(2)
        self.spn_valor.setPrefix("S/. ")

        grid.addWidget(self.spn_valor, fila, 1)
        fila += 1

        grid.addWidget(QLabel("Fecha de adquisición"), fila, 0)

        self.dtp_fecha = QDateEdit()

        self.dtp_fecha.setCalendarPopup(True)
        self.dtp_fecha.setDate(date.today())

        grid.addWidget(self.dtp_fecha, fila, 1)
        fila += 1

        grid.addWidget(QLabel("Observaciones"), fila, 0)

        self.txt_obs = QTextEdit()

        self.txt_obs.setMaximumHeight(120)

        grid.addWidget(self.txt_obs, fila, 1)

        layout.addLayout(grid)

        botones = QHBoxLayout()

        botones.addStretch()

        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_guardar = QPushButton("Guardar")

        botones.addWidget(self.btn_cancelar)
        botones.addWidget(self.btn_guardar)

        layout.addLayout(botones)

        self.btn_cancelar.clicked.connect(self.reject)
        self.btn_guardar.clicked.connect(self._guardar)


    def _guardar(self):

        datos = {

            "codigo_patrimonial":
                self.txt_codigo.text().strip(),

            "descripcion":
                self.txt_descripcion.text().strip(),

            "categoria":
                self.cmb_categoria.currentText(),

            "valor_adquisicion":
                self.spn_valor.value(),

            "fecha_adquisicion":
                self.dtp_fecha.date().toPython(),

            "observaciones":
                self.txt_obs.toPlainText().strip()

        }

        resultado = BienesService.registrar(
            datos,
            self.usuario_id
        )

        if resultado.ok:

            QMessageBox.information(
                self,
                "Bienes",
                resultado.mensaje
            )

            self.accept()

        else:

            QMessageBox.warning(
                self,
                "Bienes",
                resultado.mensaje
            )