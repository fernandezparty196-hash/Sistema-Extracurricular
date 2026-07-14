"""
ui/bienes/dialogo_editar_bien.py
"""

from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QLineEdit,
    QTextEdit,
    QDoubleSpinBox,
    QPushButton,
    QGridLayout,
    QHBoxLayout,
    QVBoxLayout,
    QMessageBox,
)

from services.bienes_service import BienesService


class DialogoEditarBien(QDialog):

    def __init__(self, bien: dict, usuario_id: int, parent=None):
        super().__init__(parent)

        self.bien = bien
        self.usuario_id = usuario_id

        self.setWindowTitle("Editar Bien Patrimonial")
        self.resize(600, 420)

        self._crear_ui()
        self._cargar_datos()


    def _crear_ui(self):

        layout = QVBoxLayout(self)

        grid = QGridLayout()

        fila = 0

        # Código patrimonial (solo lectura)

        grid.addWidget(QLabel("Código Patrimonial"), fila, 0)

        self.txt_codigo = QLineEdit()
        self.txt_codigo.setReadOnly(True)

        grid.addWidget(self.txt_codigo, fila, 1)

        fila += 1

        grid.addWidget(QLabel("Descripción"), fila, 0)

        self.txt_descripcion = QLineEdit()

        grid.addWidget(self.txt_descripcion, fila, 1)

        fila += 1

        grid.addWidget(QLabel("Categoría"), fila, 0)

        self.txt_categoria = QLineEdit()

        grid.addWidget(self.txt_categoria, fila, 1)

        fila += 1

        grid.addWidget(QLabel("Valor adquisición"), fila, 0)

        self.spn_valor = QDoubleSpinBox()
        self.spn_valor.setMaximum(1000000)
        self.spn_valor.setDecimals(2)
        self.spn_valor.setPrefix("S/. ")

        grid.addWidget(self.spn_valor, fila, 1)

        fila += 1

        grid.addWidget(QLabel("Observaciones"), fila, 0)

        self.txt_obs = QTextEdit()
        self.txt_obs.setMaximumHeight(120)

        grid.addWidget(self.txt_obs, fila, 1)

        layout.addLayout(grid)

        botones = QHBoxLayout()

        botones.addStretch()

        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_guardar = QPushButton("Guardar Cambios")

        botones.addWidget(self.btn_cancelar)
        botones.addWidget(self.btn_guardar)

        layout.addLayout(botones)

        self.btn_cancelar.clicked.connect(self.reject)
        self.btn_guardar.clicked.connect(self._guardar)
    
    def _cargar_datos(self):

        self.txt_codigo.setText(
            self.bien["codigo_patrimonial"]
        )

        self.txt_descripcion.setText(
            self.bien["descripcion"]
        )

        self.txt_categoria.setText(
            self.bien["categoria"] or ""
        )

        if self.bien["valor_adquisicion"]:

            self.spn_valor.setValue(
                float(self.bien["valor_adquisicion"])
            )

        self.txt_obs.setPlainText(
            self.bien["observaciones"] or ""
        )

    def _guardar(self):

        descripcion = self.txt_descripcion.text().strip()

        if not descripcion:

            QMessageBox.warning(
                self,
                "Bienes",
                "Debe ingresar una descripción."
            )

            return

        datos = {

            "descripcion":
                descripcion,

            "categoria":
                self.txt_categoria.text().strip(),

            "valor_adquisicion":
                self.spn_valor.value(),

            "observaciones":
                self.txt_obs.toPlainText().strip()

        }

        resultado = BienesService.editar(

            self.bien["id"],

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