"""
ui/dashboard.py   ──   HU-12 Dashboard (CORREGIDO)
═════════════════════════════════════════════════════════════

CORRECCIONES:
  ✅ Usa ReporteServiceMejorado en lugar de ReporteService
  ✅ CSS compatible con Qt (sin box-shadow)
  ✅ Manejo correcto de errores
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,QHeaderView,QAbstractItemView,
    QTableWidget, QTableWidgetItem, QMessageBox, QGridLayout,QSizePolicy
)

from services.reporte_service import ReporteService


class DashboardWidget(QWidget):
    """Widget principal con dashboard de la aplicación."""

    def __init__(self, sesion_usuario=None):
        super().__init__()
        self.sesion_usuario = sesion_usuario
        self.reporte_service = ReporteService()
        self.datos_dashboard = None

        self._configurar_widget()
        self._construir_ui()
        self._cargar_datos()

    def _configurar_widget(self) -> None:
        """Configura el widget del dashboard."""
        self.setStyleSheet("""
            QLabel#titulo {
                font-size: 20px;
                font-weight: bold;
            }      
            QLabel#bienvenida {
                font-size: 14px;
            }
            QFrame#tarjeta {
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 15px;
            }
            QFrame#tarjeta_numero {
                border: 2px solid #2563eb;
                border-radius: 8px;
                padding: 20px;
            }
            QLabel#numero_grande {
                font-size: 28px;
                font-weight: bold;
            }
            QLabel#label_tarjeta {
                font-size: 12px;
            }
            QTableWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            QHeaderView::section {
                padding: 5px;
                font-weight: bold;
            }
        """)

    def _construir_ui(self) -> None:
        """Construye la interfaz del dashboard."""
        layout = QVBoxLayout()
        layout.setContentsMargins(25, 25, 25, 25)

        # ── ENCABEZADO ─────────────────────────────────────────────
        header_layout = QHBoxLayout()

        self.label_bienvenida = QLabel()
        self.label_bienvenida.setObjectName("bienvenida")
        header_layout.addStretch()
        header_layout.addWidget(self.label_bienvenida)

        layout.addLayout(header_layout)

        # ── TARJETAS DE RESUMEN ────────────────────────────────────
        grid_layout = QGridLayout()
        grid_layout.setSpacing(15)

        # Tarjeta 1: Total Talleres
        self.tarjeta_talleres = self._crear_tarjeta_numero(
            "0", "Total de Talleres", "#3b82f6"
        )
        grid_layout.addWidget(self.tarjeta_talleres, 0, 0)

        # Tarjeta 2: Total Estudiantes
        self.tarjeta_estudiantes = self._crear_tarjeta_numero(
            "0", "Total de Estudiantes", "#10b981"
        )
        grid_layout.addWidget(self.tarjeta_estudiantes, 0, 1)

        # Tarjeta 3: Sesiones Hoy
        self.tarjeta_sesiones = self._crear_tarjeta_numero(
            "0", "Sesiones Hoy", "#f59e0b"
        )
        grid_layout.addWidget(self.tarjeta_sesiones, 0, 2)

        # Tarjeta 4: En Riesgo
        self.tarjeta_riesgo = self._crear_tarjeta_numero(
            "0", "Estudiantes en Riesgo", "#ef4444"
        )
        grid_layout.addWidget(self.tarjeta_riesgo, 0, 3)

        layout.addLayout(grid_layout)

        # ── PRÓXIMA SESIÓN ─────────────────────────────────────────
        label_proxima = QLabel("Próxima Sesión Programada:")
        label_proxima.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(label_proxima)

        self.frame_proxima = QFrame()
        self.frame_proxima.setObjectName("tarjeta")
        proxima_layout = QVBoxLayout()

        self.label_proxima_taller = QLabel("No hay sesiones próximas")
        self.label_proxima_taller.setFont(QFont("Arial", 13, QFont.Bold))
        proxima_layout.addWidget(self.label_proxima_taller)

        self.label_proxima_datos = QLabel()
        self.label_proxima_datos.setStyleSheet("color: #666; font-size: 11px;")
        proxima_layout.addWidget(self.label_proxima_datos)

        self.frame_proxima.setLayout(proxima_layout)
        layout.addWidget(self.frame_proxima)

        # ── TABLA DE PRÓXIMAS SESIONES ─────────────────────────────
        label_sesiones = QLabel("Próximas Sesiones:")
        label_sesiones.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(label_sesiones)

        self.tabla_sesiones = QTableWidget()
        self.tabla_sesiones.setColumnCount(4)
        self.tabla_sesiones.setHorizontalHeaderLabels([
            "Taller", "Sesión", "Fecha/Hora", "Ubicación"
        ])
        self.tabla_sesiones.setColumnWidth(0, 300)
        self.tabla_sesiones.setColumnWidth(1, 80)
        self.tabla_sesiones.setColumnWidth(2, 200)
        self.tabla_sesiones.setColumnWidth(3, 200)
        self.tabla_sesiones.setMaximumHeight(250)
        self.tabla_sesiones.setSelectionBehavior(QTableWidget.SelectRows)

        header = self.tabla_sesiones.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        self.tabla_sesiones.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla_sesiones.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tabla_sesiones.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla_sesiones.setAlternatingRowColors(True)
        self.tabla_sesiones.verticalHeader().setVisible(False)
        self.tabla_sesiones.setShowGrid(False)
        self.tabla_sesiones.setSortingEnabled(True)
        self.tabla_sesiones.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    
        layout.addWidget(self.tabla_sesiones)

        # ── SPACER FINAL ───────────────────────────────────────────
        layout.addStretch()

        self.setLayout(layout)

    def _crear_tarjeta_numero(self, numero: str, label: str, color: str) -> QFrame:
        """Crea una tarjeta con número grande."""
        frame = QFrame()
        frame.setObjectName("tarjeta_numero")

        # Cambiar color del borde
        frame.setStyleSheet(f"""
            QFrame#tarjeta_numero {{
                border: 2px solid {color};
                border-radius: 8px;
                padding: 20px;
            }}
        """)

        layout = QVBoxLayout()

        numero_label = QLabel(numero)
        numero_label.setObjectName("numero_grande")
        numero_label.setStyleSheet(f"color: {color};")
        layout.addWidget(numero_label)

        label_widget = QLabel(label)
        label_widget.setObjectName("label_tarjeta")
        layout.addWidget(label_widget)

        frame.setLayout(layout)
        frame.numero_label = numero_label  # Guardar referencia
        return frame

    def _cargar_datos(self) -> None:
        """Carga los datos del dashboard."""
        try:
            # ✅ Usar ReporteServiceMejorado
            resultado = self.reporte_service.obtener_datos_dashboard()

            if not resultado.ok:
                # No mostrar error, solo mostrar mensaje en tarjetas
                print(f"⚠️ {resultado.mensaje}")
                self._mostrar_sin_datos()
                return

            self.datos_dashboard = resultado.datos
            self._mostrar_datos()

        except Exception as e:
            print(f"❌ Error al cargar dashboard: {str(e)}")
            self._mostrar_sin_datos()

    def _mostrar_sin_datos(self) -> None:
        """Muestra el dashboard sin datos."""
        self.tarjeta_talleres.numero_label.setText("0")
        self.tarjeta_estudiantes.numero_label.setText("0")
        self.tarjeta_sesiones.numero_label.setText("0")
        self.tarjeta_riesgo.numero_label.setText("0")
        self.label_proxima_taller.setText("No hay sesiones próximas")
        self.label_proxima_datos.setText("")

    def _mostrar_datos(self) -> None:
        """Muestra los datos en la UI."""
        if not self.datos_dashboard:
            return

        try:
            resumen = self.datos_dashboard.get("resumen", {})
            sesiones = self.datos_dashboard.get("proximas_sesiones", [])

            # Actualizar bienvenida
            if self.sesion_usuario:
                nombre = self.sesion_usuario.nombre_completo
                self.label_bienvenida.setText(f"Bienvenido, {nombre}")

            # Actualizar tarjetas de resumen
            self.tarjeta_talleres.numero_label.setText(
                str(resumen.get("total_talleres", 0))
            )
            self.tarjeta_estudiantes.numero_label.setText(
                str(resumen.get("total_estudiantes", 0))
            )
            self.tarjeta_sesiones.numero_label.setText(
                str(resumen.get("sesiones_hoy", 0))
            )
            self.tarjeta_riesgo.numero_label.setText(
                str(resumen.get("estudiantes_en_riesgo", 0))
            )

            # Próxima sesión
            proxima = resumen.get("proxima_sesion")
            if isinstance(proxima, dict):
                self.label_proxima_taller.setText(
                    proxima.get("taller", "No disponible")
                )
                self.label_proxima_datos.setText(
                    f"Sesión {proxima.get('sesion', '')} - "
                    f"{proxima.get('fecha', '')} - "
                    f"Ubicación: {proxima.get('ubicacion', '')}"
                )
            else:
                self.label_proxima_taller.setText("No hay sesiones próximas")
                self.label_proxima_datos.setText("")

            # Tabla de sesiones
            self.tabla_sesiones.setRowCount(len(sesiones))

            for row, sesion in enumerate(sesiones):
                # Taller
                item_taller = QTableWidgetItem(sesion.get("taller", ""))
                item_taller.setFlags(item_taller.flags() & ~Qt.ItemIsEditable)
                self.tabla_sesiones.setItem(row, 0, item_taller)

                # Sesión
                item_sesion = QTableWidgetItem(str(sesion.get("sesion", "")))
                item_sesion.setFlags(item_sesion.flags() & ~Qt.ItemIsEditable)
                item_sesion.setTextAlignment(Qt.AlignCenter)
                self.tabla_sesiones.setItem(row, 1, item_sesion)

                # Fecha/Hora
                item_fecha = QTableWidgetItem(sesion.get("fecha", ""))
                item_fecha.setFlags(item_fecha.flags() & ~Qt.ItemIsEditable)
                self.tabla_sesiones.setItem(row, 2, item_fecha)

                # Ubicación
                item_ubicacion = QTableWidgetItem(sesion.get("ubicacion", ""))
                item_ubicacion.setFlags(item_ubicacion.flags() & ~Qt.ItemIsEditable)
                self.tabla_sesiones.setItem(row, 3, item_ubicacion)

        except Exception as e:
            print(f"❌ Error al mostrar datos: {str(e)}")

    def actualizar(self) -> None:
        """Actualiza los datos del dashboard."""
        self._cargar_datos()