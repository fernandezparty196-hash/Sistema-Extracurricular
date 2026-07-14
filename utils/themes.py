import os

from dotenv import load_dotenv, set_key, find_dotenv
from PySide6.QtWidgets import QApplication

load_dotenv()


class ThemeManager:
    """Gestor centralizado de temas de la aplicación."""

    # Ruta al archivo .env usada para persistir la preferencia de tema.
    # find_dotenv() localiza el .env real del proyecto; si no existe,
    # se crea uno vacío en el directorio actual para no romper set_key().
    _env_file = find_dotenv() or ".env"
    if not os.path.exists(_env_file):
        try:
            open(_env_file, "a").close()
        except Exception:
            pass

    # ═══════════════════════════════════════════════════════════
    # PALETA INSTITUCIONAL (azules / grises / blanco + acentos)
    # ═══════════════════════════════════════════════════════════
    LIGHT = {
        "bg_principal":   "#f4f6f9",
        "bg_sidebar":     "#0f2440",   # azul institucional profundo
        "bg_sidebar_alt": "#16324f",
        "bg_topbar":      "#ffffff",
        "bg_card":        "#ffffff",
        "bg_card_alt":    "#f8fafc",
        "bg_input":       "#ffffff",
        "bg_hover":       "#eef2f7",

        "text_primary":   "#1a2233",
        "text_secondary": "#5b6472",
        "text_light":     "#9aa3b1",
        "text_on_dark":   "#e7ecf5",
        "text_on_dark_muted": "#94a3c4",

        "border":         "#e0e4ea",
        "border_strong":  "#c7ccd6",

        "primary":        "#1d4ed8",
        "primary_hover":  "#1739ab",
        "primary_soft":   "#e8eefc",

        "accent":         "#0ea5a5",   # teal institucional
        "accent_hover":   "#0b8686",

        "success":        "#15803d",
        "success_soft":   "#e7f6ec",
        "danger":         "#dc2626",
        "danger_soft":    "#fdecec",
        "warning":        "#b45309",
        "warning_soft":   "#fdf3e2",
        "info":           "#1d4ed8",
        "info_soft":      "#e8eefc",

        "shadow":         "rgba(15, 36, 64, 0.10)",
        "icono_tema":     "🌙",
    }

    DARK = {
        "bg_principal":   "#0b1220",
        "bg_sidebar":     "#0a1424",
        "bg_sidebar_alt": "#101d33",
        "bg_topbar":      "#111a2c",
        "bg_card":        "#141e33",
        "bg_card_alt":    "#101a2c",
        "bg_input":       "#0f1a2c",
        "bg_hover":       "#18243b",

        "text_primary":   "#eef2f9",
        "text_secondary": "#a9b3c6",
        "text_light":     "#7987a1",
        "text_on_dark":   "#eef2f9",
        "text_on_dark_muted": "#8896b3",

        "border":         "#26324a",
        "border_strong":  "#37455f",

        "primary":        "#3b82f6",
        "primary_hover":  "#2563eb",
        "primary_soft":   "#152743",

        "accent":         "#2dd4bf",
        "accent_hover":   "#14b8a6",

        "success":        "#22c55e",
        "success_soft":   "#123322",
        "danger":         "#f87171",
        "danger_soft":    "#3a1a1a",
        "warning":        "#fbbf24",
        "warning_soft":   "#3a2c10",
        "info":           "#60a5fa",
        "info_soft":      "#152743",

        "shadow":         "rgba(0, 0, 0, 0.35)",
        "icono_tema":     "☀️",
    }

    _tema_actual = "claro"

    # ─────────────────────────────────────────────────────────
    @staticmethod
    def _paleta(tema: str) -> dict:
        return ThemeManager.DARK if tema == "oscuro" else ThemeManager.LIGHT

    @staticmethod
    def aplicar(app: QApplication, tema: str = "claro") -> None:
        colores = ThemeManager._paleta(tema)
        stylesheet = ThemeManager._generar_stylesheet(colores)

        app.setStyleSheet(stylesheet)
        app.tema_actual = tema
        ThemeManager._tema_actual = tema

        try:
            set_key(ThemeManager._env_file, "APP_TEMA", tema)
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
        if tema not in ("claro", "oscuro"):
            raise ValueError(f"Tema desconocido: {tema}")
        paleta = ThemeManager._paleta(tema)
        if clave not in paleta:
            raise ValueError(f"Color desconocido: {clave}")
        return paleta[clave]

    @staticmethod
    def obtener_tema_actual(app: QApplication) -> str:
        """Obtiene el tema aplicado actualmente."""
        return getattr(app, "tema_actual", "claro")

    @staticmethod
    def toggle(app: QApplication) -> str:
        nuevo_tema = "oscuro" if ThemeManager._tema_actual == "claro" else "claro"
        ThemeManager.aplicar(app, nuevo_tema)
        return nuevo_tema

    @staticmethod
    def cargar_preferencia(app: QApplication) -> None:
        tema = os.getenv("APP_TEMA", "claro")
        ThemeManager.aplicar(app, tema)

    @staticmethod
    def tema_actual() -> str:
        return ThemeManager._tema_actual

    @staticmethod
    def icono_boton() -> str:
        paleta = ThemeManager._paleta(ThemeManager._tema_actual)
        return paleta["icono_tema"]

    # ═══════════════════════════════════════════════════════════
    # GENERACIÓN DEL STYLESHEET
    # ═══════════════════════════════════════════════════════════
    @staticmethod
    def _generar_stylesheet(colores: dict) -> str:
        c = colores
        return f"""
        /* ═══════════════════════════════════════════════════════ */
        /* BASE                                                     */
        /* ═══════════════════════════════════════════════════════ */

        * {{
            font-family: "Segoe UI", "Inter", "Helvetica Neue", Arial, sans-serif;
            outline: none;
        }}

        QMainWindow, QDialog {{
            background-color: {c['bg_principal']};
            color: {c['text_primary']};
        }}

        QWidget {{
            background-color: {c['bg_principal']};
            color: {c['text_primary']};
            font-size: 13px;
        }}

        QLabel {{
            background: transparent;
            color: {c['text_primary']};
        }}

        QLabel:disabled {{
            color: {c['text_light']};
        }}

        QToolTip {{
            background-color: {c['text_primary']};
            color: {c['bg_card']};
            border: none;
            padding: 6px 10px;
            border-radius: 4px;
            font-size: 12px;
        }}

        /* ═══════════════════════════════════════════════════════ */
        /* SIDEBAR                                                  */
        /* ═══════════════════════════════════════════════════════ */

        QWidget#sidebar {{
            background-color: {c['bg_sidebar']};
            min-width: 240px;
            max-width: 240px;
            border: none;
        }}

        QLabel#sidebar_logo {{
            color: {c['text_on_dark']};
            font-size: 16px;
            font-weight: 700;
            padding: 0 20px;
            letter-spacing: 0.5px;
        }}

        QLabel#sidebar_logo_sub {{
            color: {c['text_on_dark_muted']};
            font-size: 10px;
            font-weight: 600;
            padding: 0 20px;
            letter-spacing: 1.5px;
        }}

        QLabel#sidebar_titulo {{
            color: {c['text_on_dark']};
            font-size: 13px;
            font-weight: 600;
            padding: 0 20px;
        }}

        QLabel#sidebar_rol {{
            color: {c['text_on_dark_muted']};
            font-size: 10px;
            font-weight: 600;
            padding: 0 20px;
            letter-spacing: 0.8px;
        }}

        QFrame#sidebar_separator {{
            background-color: {c['border_strong']};
            max-height: 1px;
            min-height: 1px;
            margin: 0 20px;
        }}

        QPushButton#btn_modulo {{
            text-align: left;
            padding: 10px 20px;
            border: none;
            border-left: 3px solid transparent;
            background: transparent;
            color: {c['text_on_dark_muted']};
            font-size: 13px;
            border-radius: 0;
        }}

        QPushButton#btn_modulo:hover {{
            background-color: {c['bg_sidebar_alt']};
            color: {c['text_on_dark']};
        }}

        QPushButton#btn_modulo[activo="true"] {{
            background-color: {c['bg_sidebar_alt']};
            border-left: 3px solid {c['accent']};
            color: {c['text_on_dark']};
            font-weight: 600;
        }}

        QPushButton#btn_logout {{
            text-align: left;
            padding: 12px 20px;
            border: none;
            background: transparent;
            color: #f2a9a9;
            font-size: 13px;
            font-weight: 600;
        }}

        QPushButton#btn_logout:hover {{
            background-color: {c['bg_sidebar_alt']};
            color: #ffffff;
        }}

        /* ═══════════════════════════════════════════════════════ */
        /* TOPBAR                                                   */
        /* ═══════════════════════════════════════════════════════ */

        QWidget#topbar {{
            background-color: {c['bg_topbar']};
            border-bottom: 1px solid {c['border']};
            min-height: 56px;
            max-height: 56px;
        }}

        QLabel#topbar_titulo {{
            color: {c['text_primary']};
            font-size: 16px;
            font-weight: 700;
            padding-left: 24px;
        }}

        QLabel#topbar_usuario {{
            color: {c['text_secondary']};
            font-size: 12px;
            font-weight: 600;
        }}

        QLabel#topbar_reloj {{
            color: {c['text_light']};
            font-size: 12px;
            padding-right: 24px;
        }}

        /* ═══════════════════════════════════════════════════════ */
        /* ÁREA CENTRAL / CARDS                                     */
        /* ═══════════════════════════════════════════════════════ */

        QWidget#area_central {{
            background-color: {c['bg_principal']};
        }}

        QFrame#card, QWidget#card {{
            background-color: {c['bg_card']};
            border: 1px solid {c['border']};
            border-radius: 10px;
        }}

        QFrame#kpi_card {{
            background-color: {c['bg_card']};
            border: 1px solid {c['border']};
            border-radius: 10px;
        }}

        QLabel#kpi_valor {{
            font-size: 26px;
            font-weight: 700;
            color: {c['text_primary']};
        }}

        QLabel#kpi_etiqueta {{
            font-size: 11px;
            font-weight: 600;
            color: {c['text_secondary']};
            letter-spacing: 0.5px;
        }}

        QLabel#titulo {{
            font-size: 19px;
            font-weight: 700;
            color: {c['text_primary']};
        }}

        QLabel#subtitulo {{
            font-size: 13px;
            font-weight: 600;
            color: {c['text_secondary']};
        }}

        QFrame#separator {{
            background-color: {c['border']};
            min-height: 1px;
            max-height: 1px;
        }}

        /* ═══════════════════════════════════════════════════════ */
        /* BOTONES                                                  */
        /* ═══════════════════════════════════════════════════════ */

        QPushButton {{
            background-color: {c['primary']};
            color: white;
            border: none;
            border-radius: 6px;
            padding: 9px 18px;
            font-weight: 600;
            font-size: 13px;
            min-height: 30px;
        }}

        QPushButton:hover {{
            background-color: {c['primary_hover']};
        }}

        QPushButton:pressed {{
            padding-top: 11px;
            padding-bottom: 7px;
        }}

        QPushButton:disabled {{
            background-color: {c['border_strong']};
            color: {c['text_light']};
        }}

        QPushButton#btn_secondary {{
            background-color: transparent;
            color: {c['primary']};
            border: 1.5px solid {c['primary']};
        }}

        QPushButton#btn_secondary:hover {{
            background-color: {c['primary_soft']};
        }}

        QPushButton#btn_ghost {{
            background-color: transparent;
            color: {c['text_secondary']};
            border: 1px solid {c['border_strong']};
            font-weight: 500;
        }}

        QPushButton#btn_ghost:hover {{
            background-color: {c['bg_hover']};
            color: {c['text_primary']};
        }}

        QPushButton#btn_danger {{
            background-color: {c['danger']};
        }}
        QPushButton#btn_danger:hover {{ background-color: #b91c1c; }}

        QPushButton#btn_success {{
            background-color: {c['success']};
        }}
        QPushButton#btn_success:hover {{ background-color: #15803d; }}

        QPushButton#btn_warning {{
            background-color: {c['warning']};
        }}
        QPushButton#btn_warning:hover {{ background-color: #92400e; }}

        /* ═══════════════════════════════════════════════════════ */
        /* INPUTS                                                   */
        /* ═══════════════════════════════════════════════════════ */

        QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
            background-color: {c['bg_input']};
            color: {c['text_primary']};
            border: 1.5px solid {c['border']};
            border-radius: 6px;
            padding: 8px 12px;
            font-size: 13px;
            selection-background-color: {c['primary']};
            selection-color: white;
        }}

        QLineEdit:focus, QTextEdit:focus, QComboBox:focus,
        QSpinBox:focus, QDoubleSpinBox:focus {{
            border: 1.5px solid {c['primary']};
        }}

        QLineEdit:disabled, QComboBox:disabled {{
            background-color: {c['bg_card_alt']};
            color: {c['text_light']};
        }}

        /* Estados de validación (property "estado") */
        QLineEdit[estado="error"] {{
            border: 1.5px solid {c['danger']};
            background-color: {c['danger_soft']};
        }}
        QLineEdit[estado="valido"] {{
            border: 1.5px solid {c['success']};
        }}
        QLabel#lbl_error {{
            color: {c['danger']};
            font-size: 11px;
            font-weight: 600;
            padding-left: 2px;
        }}

        /* Badges de estado / acción (usados p.ej. en Auditoría) */
        QLabel#badge_insert {{
            background-color: {c['success_soft']};
            color: {c['success']};
            border-radius: 4px;
            padding: 3px 10px;
            font-size: 11px;
            font-weight: 700;
        }}
        QLabel#badge_update {{
            background-color: {c['info_soft']};
            color: {c['info']};
            border-radius: 4px;
            padding: 3px 10px;
            font-size: 11px;
            font-weight: 700;
        }}
        QLabel#badge_delete {{
            background-color: {c['danger_soft']};
            color: {c['danger']};
            border-radius: 4px;
            padding: 3px 10px;
            font-size: 11px;
            font-weight: 700;
        }}

        QComboBox::drop-down {{
            border: none;
            width: 24px;
        }}
        QComboBox::down-arrow {{
            image: none;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 5px solid {c['text_secondary']};
            margin-right: 8px;
        }}

        QListView {{
            background-color: {c['bg_card']};
            color: {c['text_primary']};
            border: 1px solid {c['border']};
            border-radius: 6px;
            selection-background-color: {c['primary']};
            selection-color: white;
            padding: 4px;
            outline: none;
        }}

        QCheckBox, QRadioButton {{
            color: {c['text_primary']};
            spacing: 8px;
            background: transparent;
        }}

        QCheckBox::indicator, QRadioButton::indicator {{
            width: 16px;
            height: 16px;
            border-radius: 4px;
            border: 1.5px solid {c['border_strong']};
            background-color: {c['bg_input']};
        }}

        QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
            background-color: {c['primary']};
            border: 1.5px solid {c['primary']};
        }}

        /* ═══════════════════════════════════════════════════════ */
        /* TABLAS                                                   */
        /* ═══════════════════════════════════════════════════════ */

        QTableWidget, QTableView {{
            background-color: {c['bg_card']};
            alternate-background-color: {c['bg_card_alt']};
            color: {c['text_primary']};
            border: 1px solid {c['border']};
            border-radius: 8px;
            gridline-color: {c['border']};
            selection-background-color: {c['primary_soft']};
            selection-color: {c['text_primary']};
        }}

        QTableWidget::item, QTableView::item {{
            padding: 8px;
            border: none;
        }}

        QTableWidget::item:selected, QTableView::item:selected {{
            background-color: {c['primary_soft']};
            color: {c['text_primary']};
        }}

        QHeaderView::section {{
            background-color: {c['bg_card_alt']};
            color: {c['text_secondary']};
            padding: 8px;
            border: none;
            border-bottom: 1.5px solid {c['border_strong']};
            font-weight: 700;
            font-size: 11px;
            letter-spacing: 0.4px;
            text-transform: uppercase;
        }}

        QTableCornerButton::section {{
            background-color: {c['bg_card_alt']};
            border: none;
        }}

        /* ═══════════════════════════════════════════════════════ */
        /* SCROLLBARS                                               */
        /* ═══════════════════════════════════════════════════════ */

        QScrollBar:vertical {{
            width: 10px;
            background: transparent;
            margin: 2px;
        }}
        QScrollBar::handle:vertical {{
            background-color: {c['border_strong']};
            border-radius: 5px;
            min-height: 24px;
        }}
        QScrollBar::handle:vertical:hover {{ background-color: {c['primary']}; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

        QScrollBar:horizontal {{
            height: 10px;
            background: transparent;
            margin: 2px;
        }}
        QScrollBar::handle:horizontal {{
            background-color: {c['border_strong']};
            border-radius: 5px;
            min-width: 24px;
        }}
        QScrollBar::handle:horizontal:hover {{ background-color: {c['primary']}; }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

        /* ═══════════════════════════════════════════════════════ */
        /* MENÚS                                                    */
        /* ═══════════════════════════════════════════════════════ */

        QMenuBar {{
            background-color: {c['bg_topbar']};
            color: {c['text_primary']};
            border-bottom: 1px solid {c['border']};
            padding: 2px 4px;
        }}
        QMenuBar::item {{
            padding: 6px 14px;
            margin: 2px;
            border-radius: 4px;
            background: transparent;
        }}
        QMenuBar::item:selected {{
            background-color: {c['bg_hover']};
        }}

        QMenu {{
            background-color: {c['bg_card']};
            color: {c['text_primary']};
            border: 1px solid {c['border']};
            border-radius: 6px;
            padding: 4px;
        }}
        QMenu::item {{
            padding: 8px 24px;
            border-radius: 4px;
        }}
        QMenu::item:selected {{
            background-color: {c['primary_soft']};
            color: {c['text_primary']};
        }}
        QMenu::separator {{
            height: 1px;
            background: {c['border']};
            margin: 4px 8px;
        }}

        /* ═══════════════════════════════════════════════════════ */
        /* DIÁLOGOS Y MESSAGEBOX                                    */
        /* ═══════════════════════════════════════════════════════ */

        QDialog {{
            background-color: {c['bg_principal']};
            border-radius: 10px;
        }}

        QDialogButtonBox {{
            background-color: transparent;
        }}

        QMessageBox {{
            background-color: {c['bg_card']};
        }}
        QMessageBox QLabel {{
            color: {c['text_primary']};
            font-size: 13px;
        }}

        /* ═══════════════════════════════════════════════════════ */
        /* STATUS BAR                                               */
        /* ═══════════════════════════════════════════════════════ */

        QStatusBar {{
            background-color: {c['bg_topbar']};
            color: {c['text_secondary']};
            border-top: 1px solid {c['border']};
            font-size: 11px;
        }}
        QStatusBar QLabel {{
            color: {c['text_secondary']};
        }}
        #titulo_panel {{ font-size: 18px; font-weight: bold; }}
        #etiqueta_seccion {{ font-size: 12px; font-weight: bold; }}
        #frame_filtros {{ border: 1px solid #ddd; border-radius: 6px; padding: 10px; }}

        #btn_marcar_presentes {{ background-color: #10b981; color: white; }}
        #btn_marcar_presentes:hover:!disabled {{ background-color: #059669; }}
        #btn_marcar_presentes:disabled {{ background-color: #ccc; }}

        #btn_marcar_ausentes {{ background-color: #ef4444; color: white; }}
        #btn_marcar_ausentes:hover:!disabled {{ background-color: #dc2626; }}
        #btn_marcar_ausentes:disabled {{ background-color: #ccc; }}

        #btn_estado_presente:checked {{ background-color: #10b981; color: white; }}
        #btn_estado_ausente:checked {{ background-color: #ef4444; color: white; }}
        #btn_estado_justificado:checked {{ background-color: #f59e0b; color: white; }}

        """