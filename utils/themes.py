import os

from dotenv import load_dotenv, set_key
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QColor

load_dotenv()

class ThemeManager:
    """Gestor centralizado de temas de la aplicación."""

    # COLORES POR TEMA
    LIGHT = {
        "bg_principal": "#F5F7FA",
        "bg_sidebar": "#FFFFFF",
        "bg_card": "#FFFFFF",

        "text_primary": "#1F2937",
        "text_secondary": "#6B7280",
        "text_light": "#9CA3AF",

        "border": "#D1D5DB",

        # Azul institucional
        "primary": "#1E3A5F",
        "primary_hover": "#274C77",

        "success": "#15803D",
        "danger": "#B91C1C",
        "warning": "#B45309",
        "info": "#0369A1",

        "TEMA_ICONO": "🌙"
    }


    DARK = {
        "bg_principal": "#111827",
        "bg_sidebar": "#172033",
        "bg_card": "#1F2937",

        "text_primary": "#F9FAFB",
        "text_secondary": "#D1D5DB",
        "text_light": "#9CA3AF",

        "border": "#374151",

        "primary": "#60A5FA",
        "primary_hover": "#3B82F6",

        "success": "#22C55E",
        "danger": "#EF4444",
        "warning": "#F59E0B",
        "info": "#38BDF8",

        "TEMA_ICONO": "☀️"
    }
    _tema_actual = "claro"

    @staticmethod
    def aplicar(app: QApplication, tema: str = "claro") -> None:

        colores = ThemeManager.DARK if tema == "oscuro" else ThemeManager.LIGHT

        stylesheet = ThemeManager._generar_stylesheet(colores)

        app.setStyleSheet(stylesheet)

        app.tema_actual = tema
        ThemeManager._tema_actual = tema

        try:
            set_key(
                ThemeManager._env_file,
                "APP_TEMA",
                tema
            )
        except Exception:
            pass
        
    @staticmethod
    def obtener_color(tema: str, clave: str) -> str:
        """
        Obtiene el código hex de un color.

        EJEMPLO:
          color_primary = ThemeManager.obtener_color("oscuro", "primary")
          # retorna: "#3b82f6"
        """
        if tema not in ThemeManager.TEMAS:
            raise ValueError(f"Tema desconocido: {tema}")
        if clave not in ThemeManager.TEMAS[tema]:
            raise ValueError(f"Color desconocido: {clave}")

        return ThemeManager.TEMAS[tema][clave]

    @staticmethod
    def obtener_tema_actual(app: QApplication) -> str:
        """Obtiene el tema aplicado actualmente."""
        return getattr(app, "tema_actual", "claro")

    @staticmethod
    def toggle(app: QApplication) -> str:

        nuevo_tema = (
            "oscuro"
            if ThemeManager._tema_actual == "claro"
            else "claro"
        )

        ThemeManager.aplicar(app, nuevo_tema)

        return nuevo_tema


    @staticmethod
    def cargar_preferencia(app: QApplication) -> None:

        tema = os.getenv(
            "APP_TEMA",
            "claro"
        )

        ThemeManager.aplicar(
            app,
            tema
        )


    @staticmethod
    def tema_actual() -> str:
        return ThemeManager._tema_actual


    @staticmethod
    def icono_boton() -> str:

        paleta = (
            ThemeManager.DARK
            if ThemeManager._tema_actual == "oscuro"
            else ThemeManager.LIGHT
        )

        return paleta["TEMA_ICONO"]
    @staticmethod
    def _generar_stylesheet(colores: dict) -> str:
        """
        Genera el stylesheet CSS para PySide6 basado en los colores.
        """
        return f"""
        /* ═══════════════════════════════════════════════════════════ */
        /* COLORES BASE                                                */
        /* ═══════════════════════════════════════════════════════════ */

        QMainWindow, QDialog {{
            background-color: {colores['bg_principal']};
            color: {colores['text_primary']};
        }}

        QWidget {{
            background-color: {colores['bg_principal']};
            color: {colores['text_primary']};
        }}

        /* ═══════════════════════════════════════════════════════════ */
        /* TEXTO                                                        */
        /* ═══════════════════════════════════════════════════════════ */

        QLabel {{
            color: {colores['text_primary']};
        }}

        QLabel:disabled {{
            color: {colores['text_light']};
        }}

        /* ═══════════════════════════════════════════════════════════ */
        /* BOTONES                                                      */
        /* ═══════════════════════════════════════════════════════════ */

        QPushButton {{
            background-color: {colores['primary']};
            color:white;
            border-radius:5px;
            padding:9px 18px;
            font-size:13px;
            font-weight:600;
            border:none;
        }}


        QPushButton:hover {{
            background-color:{colores['primary_hover']};
        }}


        QPushButton:pressed {{
            background-color:#142B45;
        }}

        QPushButton:disabled {{
            background-color: {colores['text_light']};
            color: {colores['text_primary']};
        }}

        /* Botón secundario (outline) */
        QPushButton#btn_secondary {{
            background-color: transparent;
            color: {colores['primary']};
            border: 2px solid {colores['primary']};
        }}

        QPushButton#btn_secondary:hover {{
            background-color: {colores['primary']};
            color: white;
        }}

        /* ═══════════════════════════════════════════════════════════ */
        /* INPUTS                                                       */
        /* ═══════════════════════════════════════════════════════════ */

        QLineEdit, QTextEdit, QPlainTextEdit, QComboBox {{
            background-color: {colores['bg_card']};
            color: {colores['text_primary']};
            border: 1px solid {colores['border']};
            border-radius: 4px;
            padding: 8px 12px;
            font-size: 12px;
            selection-background-color: {colores['primary']};
        }}

        QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
            border: 2px solid {colores['primary']};
        }}

        QLineEdit:disabled, QComboBox:disabled {{
            background-color: {colores['bg_principal']};
            color: {colores['text_light']};
        }}

        /* ═══════════════════════════════════════════════════════════ */
        /* TABLAS                                                       */
        /* ═══════════════════════════════════════════════════════════ */

        QTableWidget, QTableView {{
            background-color: {colores['bg_card']};
            color: {colores['text_primary']};
            border: 1px solid {colores['border']};
            gridline-color: {colores['border']};
        }}

        QTableWidget::item {{
            padding: 5px;
            border: none;
        }}

        QTableWidget::item:selected {{
            background-color: {colores['primary']};
            color: white;
        }}

        QHeaderView::section {{
            background-color: {colores['bg_sidebar']};
            color: {colores['text_primary']};
            padding: 5px;
            border: 1px solid {colores['border']};
            font-weight: bold;
        }}

        /* ═══════════════════════════════════════════════════════════ */
        /* DROPDOWNS / COMBOBOX                                         */
        /* ═══════════════════════════════════════════════════════════ */

        QComboBox {{
            background:white;
            border:1px solid {colores['border']};
            border-radius:6px;
            padding:9px;
            font-size:13px;
        }}

        QComboBox::drop-down {{
            border: none;
            width: 20px;
        }}

        QComboBox::down-arrow {{
            image: none;
            width: 0px;
        }}

        QComboBox:focus {{
            border:2px solid {colores['primary']};
        }}

        QListView {{
            background-color: {colores['bg_card']};
            color: {colores['text_primary']};
            border: 1px solid {colores['border']};
            selection-background-color: {colores['primary']};
        }}

        /* ═══════════════════════════════════════════════════════════ */
        /* SPINBOX / SLIDERS                                            */
        /* ═══════════════════════════════════════════════════════════ */

        QSpinBox, QDoubleSpinBox {{
            background-color: {colores['bg_card']};
            color: {colores['text_primary']};
            border: 1px solid {colores['border']};
            border-radius: 4px;
            padding: 6px;
        }}

        QSlider::groove:horizontal {{
            background-color: {colores['border']};
            height: 4px;
            border-radius: 2px;
        }}

        QSlider::handle:horizontal {{
            background-color: {colores['primary']};
            width: 14px;
            margin: -5px 0;
            border-radius: 7px;
        }}

        QSlider::handle:horizontal:hover {{
            background-color: {colores['primary_hover']};
        }}

        /* ═══════════════════════════════════════════════════════════ */
        /* CHECKBOXES / RADIO BUTTONS                                   */
        /* ═══════════════════════════════════════════════════════════ */

        QCheckBox, QRadioButton {{
            color: {colores['text_primary']};
            spacing: 8px;
        }}

        QCheckBox::indicator, QRadioButton::indicator {{
            width: 16px;
            height: 16px;
            border-radius: 3px;
            border: 2px solid {colores['border']};
            background-color: {colores['bg_card']};
        }}

        QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
            background-color: {colores['primary']};
            border: 2px solid {colores['primary']};
        }}

        /* ═══════════════════════════════════════════════════════════ */
        /* SCROLLBARS                                                   */
        /* ═══════════════════════════════════════════════════════════ */

        QScrollBar:vertical {{
            width: 12px;
            background-color: {colores['bg_principal']};
            border: none;
        }}

        QScrollBar::handle:vertical {{
            background-color: {colores['border']};
            border-radius: 6px;
            min-height: 20px;
        }}

        QScrollBar::handle:vertical:hover {{
            background-color: {colores['primary']};
        }}

        QScrollBar:horizontal {{
            height: 12px;
            background-color: {colores['bg_principal']};
            border: none;
        }}

        QScrollBar::handle:horizontal {{
            background-color: {colores['border']};
            border-radius: 6px;
            min-width: 20px;
        }}

        QScrollBar::handle:horizontal:hover {{
            background-color: {colores['primary']};
        }}

        /* ═══════════════════════════════════════════════════════════ */
        /* MENÚS                                                        */
        /* ═══════════════════════════════════════════════════════════ */

        QMenuBar {{
            background-color: {colores['bg_sidebar']};
            color: {colores['text_primary']};
            padding: 2px 4px;
        }}

        QMenuBar::item:selected {{
            background-color: {colores['primary']};
            color: white;
        }}

        QMenu {{
            background-color: {colores['bg_card']};
            color: {colores['text_primary']};
        }}

        QMenu::item:selected {{
            background-color: {colores['primary']};
            color: white;
        }}

        QMenu::separator {{
            height: 1px;
            background: {colores['border']};
            margin: 4px 8px;
        }}

        /* ═══════════════════════════════════════════════════════════ */
        /* DIÁLOGOS                                                     */
        /* ═══════════════════════════════════════════════════════════ */

        QDialog {{
            background-color: {colores['bg_principal']};
        }}

        QDialogButtonBox {{
            background-color: transparent;
        }}

        /* ═══════════════════════════════════════════════════════════ */
        /* STATUS BAR                                                   */
        /* ═══════════════════════════════════════════════════════════ */

        QStatusBar {{
            background-color: {colores['bg_sidebar']};
            color: {colores['text_secondary']};
            border-top: 1px solid {colores['border']};
        }}

        /* ═══════════════════════════════════════════════════════════ */
        /* CUSTOM ROLES (opcionales)                                    */
        /* ═══════════════════════════════════════════════════════════ */

        QPushButton#btn_danger {{
            background-color: {colores['danger']};
        }}

        QPushButton#btn_danger:hover {{
            background-color: #dc2626;
        }}

        QPushButton#btn_success {{
            background-color: {colores['success']};
        }}

        QPushButton#btn_success:hover {{
            background-color: #059669;
        }}

        QPushButton#btn_warning {{
            background-color: {colores['warning']};
        }}

        QPushButton#btn_warning:hover {{
            background-color: #d97706;
        }}

        QPushButton#btn_modulo {{
            color: {colores['text_primary']};
            background-color: transparent;
        }}


        QLabel#titulo {{
            font-size: 18px;
            font-weight: bold;
            color: {colores['text_primary']};
        }}

        QLabel#subtitulo {{
            font-size: 14px;
            font-weight: 600;
            color: {colores['text_secondary']};
        }}

        QFrame#card {{
            background-color: {colores['bg_card']};
            border: 1px solid {colores['border']};
            border-radius: 8px;
        }}

        QFrame#separator {{
            background-color: {colores['border']};
            min-height: 1px;
            max-height: 1px;
        }}
        """
