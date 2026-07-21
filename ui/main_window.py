from datetime import datetime

from PySide6.QtCore    import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui     import QAction
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QStackedWidget, QFrame,
    QStatusBar, QMessageBox, QApplication,
    QGraphicsOpacityEffect
)

from ui.configuracion_sistema_dialog import ConfiguracionSistemaDialog
from services.auth_service import AuthService, SesionUsuario
from utils.themes import ThemeManager
from ui.estudiantes import ListaEstudiantesWidget
from ui.talleres import ListaTalleresWidget
from ui.asistencia import PanelRegistrarAsistencia
from ui.reportes import DashboardWidget
from ui.reportes.reporte_sesion_dialog import ReporteAsistenciaDialog
from ui.reportes.reportes_principal_dialog import PanelReportes
from ui.lista_aptos.lista_aptos_widget import ListaAptosWidget
from ui.usuarios.panel_gestionar_usuarios import PanelGestionarUsuarios
from ui.docentes.panel_gestionar_docentes import PanelGestionarDocentes
from ui.bienes.panel_gestion_bienes import PanelBienesPatrimoniales
from ui.auditoria import PanelAuditoria


# ══════════════════════════════════════════════════════════════════
# DEFINICIÓN DE MÓDULOS POR ROL
# ══════════════════════════════════════════════════════════════════
# Cada entrada: (nombre_visible, icono, roles_permitidos, widget_class)

MODULOS = [
    ("Inicio",         "🏠", ["Administrador", "Docente", "Operador"], DashboardWidget),
    ("Usuarios",       "👥", ["Administrador"],                        PanelGestionarUsuarios),
    ("Estudiantes",    "🎓", ["Administrador"],                        ListaEstudiantesWidget),
    ("Docentes",       "🧑‍🏫", ["Administrador"],                       PanelGestionarDocentes),
    ("Talleres",       "🎯", ["Administrador", "Docente"],             ListaTalleresWidget),
    ("Asistencia",     "📋", ["Administrador", "Docente"],             PanelRegistrarAsistencia),
    ("Lista de Aptos", "✅", ["Administrador"],                        ListaAptosWidget),
    ("Bienes",         "📦", ["Administrador", "Operador"],            PanelBienesPatrimoniales),
    ("Reportes",       "📊", ["Administrador"],                        PanelReportes),
    ("Auditoría",      "🕵️", ["Administrador"],                        PanelAuditoria),
]


class MainWindow(QMainWindow):

    def __init__(self, sesion: SesionUsuario):
        super().__init__()
        self.sesion = sesion
        self.botones_menu: list[QPushButton] = []
        self._modulo_actual = "Inicio"

        self._configurar_ventana()
        self._construir_barra_menu()
        self._construir_ui_central()
        self._construir_barra_estado()
        self._iniciar_timer_sesion()
        self._iniciar_reloj()

    # ══════════════════════════════════════════════════════════════
    # CONFIGURACIÓN
    # ══════════════════════════════════════════════════════════════

    def _configurar_ventana(self) -> None:
        self.setWindowTitle(f"Sistema de Talleres UNAB — {self.sesion.nombre_completo}")
        self.setMinimumSize(1000, 550)
        self.resize(1280, 760)

        pantalla = QApplication.primaryScreen().geometry()
        x = (pantalla.width() - self.width()) // 2
        y = (pantalla.height() - self.height()) // 2
        self.move(x, y)
        # NOTA: los estilos visuales ya NO se definen aquí.
        # Todo el look & feel (sidebar, topbar, botones, tablas, etc.)
        # se controla centralizadamente desde utils/themes.py (ThemeManager),
        # usando los objectName asignados a cada widget en este archivo.

    # ══════════════════════════════════════════════════════════════
    # BARRA DE MENÚ SUPERIOR (menú clásico, oculto visualmente por la topbar)
    # ══════════════════════════════════════════════════════════════

    def _construir_barra_menu(self) -> None:
        barra = self.menuBar()

        menu_archivo = barra.addMenu("Archivo")

        act_cerrar_sesion = QAction("🔒 Cerrar sesión", self)
        act_cerrar_sesion.setShortcut("Ctrl+L")
        act_cerrar_sesion.triggered.connect(self._cerrar_sesion)

        act_salir = QAction("Salir", self)
        act_salir.setShortcut("Ctrl+Q")
        act_salir.triggered.connect(self.close)

        menu_archivo.addAction(act_cerrar_sesion)
        menu_archivo.addSeparator()
        menu_archivo.addAction(act_salir)

        menu_cuenta = barra.addMenu("Mi cuenta")
        act_cambiar_pass = QAction("🔑 Cambiar contraseña", self)
        act_cambiar_pass.triggered.connect(self._abrir_cambio_password)
        menu_cuenta.addAction(act_cambiar_pass)

        menu_apariencia = barra.addMenu("Apariencia")
        self.act_tema = QAction("🌙  Cambiar tema", self)
        self.act_tema.triggered.connect(self._toggle_tema)
        menu_apariencia.addAction(self.act_tema)
        self._actualizar_texto_tema()

        menu_config = barra.addMenu("Configuración")
        act_cambiar_logo = QAction("Cambiar Logo", self)
        act_cambiar_logo.triggered.connect(self._config_logo)
        menu_config.addAction(act_cambiar_logo)

    # ══════════════════════════════════════════════════════════════
    # UI CENTRAL (sidebar + topbar + contenido)
    # ══════════════════════════════════════════════════════════════

    def _construir_ui_central(self) -> None:
        contenedor = QWidget()
        self.setCentralWidget(contenedor)
        layout_raiz = QHBoxLayout(contenedor)
        layout_raiz.setContentsMargins(0, 0, 0, 0)
        layout_raiz.setSpacing(0)

        sidebar = self._construir_sidebar()
        columna_derecha = self._construir_columna_derecha()

        layout_raiz.addWidget(sidebar)
        layout_raiz.addWidget(columna_derecha, stretch=1)

    # ── Sidebar ──────────────────────────────────────────────────
    def _construir_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 24, 0, 16)
        layout.setSpacing(2)

        # ── Logo / marca del sistema ─────────────────────────────
        lbl_logo = QLabel("SISTEMA DE TALLERES")
        lbl_logo.setObjectName("sidebar_logo")
        lbl_logo.setWordWrap(True)

        lbl_logo_sub = QLabel("UNAB · BIENESTAR UNIVERSITARIO")
        lbl_logo_sub.setObjectName("sidebar_logo_sub")
        lbl_logo_sub.setWordWrap(True)

        layout.addWidget(lbl_logo)
        layout.addSpacing(2)
        layout.addWidget(lbl_logo_sub)
        layout.addSpacing(20)

        sep = QFrame()
        sep.setObjectName("sidebar_separator")
        sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)
        layout.addSpacing(16)

        # ── Botones de módulos (filtrados por rol) ───────────────
        self._construir_menu_por_rol(layout)

        layout.addStretch()

        sep2 = QFrame()
        sep2.setObjectName("sidebar_separator")
        sep2.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep2)
        layout.addSpacing(10)


        btn_logout = QPushButton("🔒  Cerrar sesión")
        btn_logout.setObjectName("btn_logout")
        btn_logout.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_logout.clicked.connect(self._cerrar_sesion)
        layout.addWidget(btn_logout)

        return sidebar

    def _construir_menu_por_rol(self, layout: QVBoxLayout) -> None:
        for nombre, icono, roles_permitidos, _ in MODULOS:
            if self.sesion.rol_nombre not in roles_permitidos:
                continue

            btn = QPushButton(f"  {icono}   {nombre}")
            btn.setObjectName("btn_modulo")
            btn.setProperty("activo", "false")
            btn.setProperty("modulo", nombre)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, n=nombre: self._navegar_a(n))

            self.botones_menu.append(btn)
            layout.addWidget(btn)

        if self.botones_menu:
            self._marcar_activo(self.botones_menu[0])

    # ── Columna derecha: topbar + área central ──────────────────
    def _construir_columna_derecha(self) -> QWidget:
        columna = QWidget()
        layout = QVBoxLayout(columna)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._construir_topbar())
        layout.addWidget(self._construir_area_central(), stretch=1)
        return columna

    def _construir_topbar(self) -> QWidget:
        topbar = QWidget()
        topbar.setObjectName("topbar")
        layout = QHBoxLayout(topbar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.lbl_topbar_titulo = QLabel("Inicio")
        self.lbl_topbar_titulo.setObjectName("topbar_titulo")
        layout.addWidget(self.lbl_topbar_titulo)

        layout.addStretch()

        lbl_usuario = QLabel(f"{self.sesion.nombre_completo}  ·  {self.sesion.rol_nombre}")
        lbl_usuario.setObjectName("topbar_usuario")
        layout.addWidget(lbl_usuario)

        layout.addSpacing(20)

        self.lbl_topbar_reloj = QLabel()
        self.lbl_topbar_reloj.setObjectName("topbar_reloj")
        layout.addWidget(self.lbl_topbar_reloj)

        return topbar

    def _construir_area_central(self) -> QWidget:
        area = QWidget()
        area.setObjectName("area_central")
        layout = QVBoxLayout(area)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(0)

        self.stack = QStackedWidget()

        self.stack.addWidget(DashboardWidget(self.sesion))
        self._stack_indices = {"Inicio": 0}

        for nombre, _icono, _roles, widget_class in MODULOS:
            if widget_class is not None and nombre not in self._stack_indices:
                widget = widget_class(self.sesion)
                idx = self.stack.addWidget(widget)
                self._stack_indices[nombre] = idx

        layout.addWidget(self.stack)
        return area

    # ══════════════════════════════════════════════════════════════
    # BARRA DE ESTADO INFERIOR
    # ══════════════════════════════════════════════════════════════

    def _construir_barra_estado(self) -> None:
        barra = QStatusBar()
        self.setStatusBar(barra)

        self.lbl_estado_usuario = QLabel(
            f"  👤 {self.sesion.nombre_completo}  |  🔑 {self.sesion.rol_nombre}"
        )
        self.lbl_estado_tiempo = QLabel()

        barra.addWidget(self.lbl_estado_usuario)
        barra.addPermanentWidget(self.lbl_estado_tiempo)

        self._actualizar_barra_estado()

    def _actualizar_barra_estado(self) -> None:
        minutos = self.sesion.minutos_restantes
        self.lbl_estado_tiempo.setText(f"⏱ Sesión expira en {minutos} min  ")

    # ══════════════════════════════════════════════════════════════
    # RELOJ EN TOPBAR
    # ══════════════════════════════════════════════════════════════

    def _iniciar_reloj(self) -> None:
        self.timer_reloj = QTimer(self)
        self.timer_reloj.setInterval(1_000)
        self.timer_reloj.timeout.connect(self._actualizar_reloj)
        self.timer_reloj.start()
        self._actualizar_reloj()

    def _actualizar_reloj(self) -> None:
        ahora = datetime.now().strftime("%A, %d %b %Y  ·  %H:%M:%S")
        self.lbl_topbar_reloj.setText(ahora)

    # ══════════════════════════════════════════════════════════════
    # TIMER DE SESIÓN (verifica cada 60 segundos)
    # ══════════════════════════════════════════════════════════════

    def _iniciar_timer_sesion(self) -> None:
        self.timer_sesion = QTimer(self)
        self.timer_sesion.setInterval(60_000)
        self.timer_sesion.timeout.connect(self._verificar_sesion)
        self.timer_sesion.start()

    def _verificar_sesion(self) -> None:
        self._actualizar_barra_estado()
        if not AuthService.verificar_sesion(self.sesion):
            QMessageBox.warning(
                self,
                "Sesión expirada",
                "Tu sesión cerró automáticamente por 60 minutos de inactividad."
            )
            self._cerrar_sesion()

    # ══════════════════════════════════════════════════════════════
    # NAVEGACIÓN (con transición de opacidad)
    # ══════════════════════════════════════════════════════════════

    def _navegar_a(self, nombre_modulo: str) -> None:
        if nombre_modulo == self._modulo_actual:
            return

        self.sesion.registrar_actividad()

        for btn in self.botones_menu:
            if btn.property("modulo") == nombre_modulo:
                self._marcar_activo(btn)

        idx = self._stack_indices.get(nombre_modulo, 0)
        self.stack.setCurrentIndex(idx)
        self._modulo_actual = nombre_modulo
        self.lbl_topbar_titulo.setText(nombre_modulo)

        self._animar_entrada_pagina()

    def _animar_entrada_pagina(self) -> None:
        """Fade-in suave al cambiar de módulo."""
        widget_actual = self.stack.currentWidget()
        efecto = QGraphicsOpacityEffect(widget_actual)
        widget_actual.setGraphicsEffect(efecto)

        animacion = QPropertyAnimation(efecto, b"opacity", widget_actual)
        animacion.setDuration(220)
        animacion.setStartValue(0.0)
        animacion.setEndValue(1.0)
        animacion.setEasingCurve(QEasingCurve.Type.OutCubic)
        animacion.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

        # Mantener referencia viva hasta que termine, evita garbage collection prematuro
        self._animacion_actual = animacion

    def _marcar_activo(self, btn_activo: QPushButton) -> None:
        for btn in self.botones_menu:
            activo = btn == btn_activo
            btn.setProperty("activo", "true" if activo else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    # ══════════════════════════════════════════════════════════════
    # CIERRE DE SESIÓN Y CAMBIO DE CONTRASEÑA
    # ══════════════════════════════════════════════════════════════

    def _cerrar_sesion(self) -> None:
        confirmacion = QMessageBox.question(
            self,
            "Cerrar sesión",
            "¿Seguro que deseas cerrar la sesión?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if confirmacion != QMessageBox.StandardButton.Yes:
            return

        self.timer_sesion.stop()
        if hasattr(self, "timer_reloj"):
            self.timer_reloj.stop()
        AuthService.logout(self.sesion)
        self.sesion = None
        self.close()

    def _toggle_tema(self) -> None:
        ThemeManager.toggle(QApplication.instance())
        self._actualizar_texto_tema()

    def _actualizar_texto_tema(self) -> None:
        if hasattr(self, "act_tema"):
            icono = ThemeManager.icono_boton()
            self.act_tema.setText(f"{icono}  Cambiar tema")

    def _abrir_cambio_password(self) -> None:
        from ui.cambio_password_dialog import CambioPasswordDialog
        dialogo = CambioPasswordDialog(self.sesion, self)
        dialogo.exec()

    def _config_logo(self) -> None:
        dlg = ConfiguracionSistemaDialog(self.sesion, self)
        dlg.exec()

    def closeEvent(self, event) -> None:
        if self.sesion:
            AuthService.logout(self.sesion)
        self.timer_sesion.stop()
        if hasattr(self, "timer_reloj"):
            self.timer_reloj.stop()
        event.accept()