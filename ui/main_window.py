from PySide6.QtCore    import Qt, QTimer
from PySide6.QtGui     import QFont, QAction
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QStackedWidget, QFrame,
    QMenuBar, QMenu, QStatusBar, QMessageBox,
    QApplication, QSizePolicy, QDialog
)

from ui.configuracion_sistema_dialog import ConfiguracionSistemaDialog
from services.auth_service import AuthService, SesionUsuario
from utils.themes import ThemeManager
from ui.estudiantes import ListaEstudiantesWidget
from ui.talleres import ListaTalleresWidget
from ui.asistencia import PanelRegistrarAsistencia
from ui.reportes import DashboardWidget
from ui.reportes.reporte_sesion_dialog import ReporteAsistenciaDialog
from ui.reportes.reportes_principal_dialog import ReportesPrincipalDialog
from ui.lista_aptos.lista_aptos_widget import ListaAptosWidget
from ui.usuarios.panel_gestionar_usuarios import PanelGestionarUsuarios
from ui.docentes.panel_gestionar_docentes import PanelGestionarDocentes
from ui.bienes.lista_bienes_widget import ListaBienesWidget


# ══════════════════════════════════════════════════════════════════
# DEFINICIÓN DE MÓDULOS POR ROL
# ══════════════════════════════════════════════════════════════════
# Cada entrada: (nombre_visible, icono, roles_permitidos, widget_class)
# widget_class = None hasta que se implemente en su sprint

MODULOS = [
    ("Inicio",          "🏠", ["Administrador", "Docente", "Operador"],DashboardWidget),
    ("Estudiantes",     "👨‍🎓", ["Administrador"],            ListaEstudiantesWidget),  # Sprint 2
    ("Docentes",        "👩‍🏫", ["Administrador"],            PanelGestionarDocentes),  # Sprint 2 (extra)
    ("Talleres",        "🎯", ["Administrador", "Docente"],    ListaTalleresWidget),  # Sprint 3
    ("Asistencia",      "📋", ["Administrador", "Docente"],PanelRegistrarAsistencia),  # Sprint 4
    ("Lista de Aptos",  "✅", ["Administrador"],                   ListaAptosWidget),  # Sprint 5
    ("Bienes",          "📦", ["Administrador", "Operador"],      ListaBienesWidget),  # Sprint 6
    ("Reportes",        "📊", ["Administrador"],               ReportesPrincipalDialog),  # Sprint 7
    ("Usuarios",        "👥", ["Administrador"],                PanelGestionarUsuarios),  # Sprint 1 (extra)
]


class MainWindow(QMainWindow):

    def __init__(self, sesion: SesionUsuario):
        super().__init__()
        self.sesion = sesion       # objeto con info del usuario logueado
        self.botones_menu: list[QPushButton] = []

        self._configurar_ventana()
        self._construir_barra_menu()
        self._construir_ui_central()
        self._construir_barra_estado()
        self._iniciar_timer_sesion()

    # ══════════════════════════════════════════════════════════════
    # CONFIGURACIÓN
    # ══════════════════════════════════════════════════════════════

    def _configurar_ventana(self) -> None:
        self.setWindowTitle(f"Sistema de Talleres UNAB — {self.sesion.nombre_completo}")
        self.setMinimumSize(1024, 640)
        self.resize(1024, 740)
        # Centrar en pantalla
        pantalla = QApplication.primaryScreen().geometry()
        x = (pantalla.width()  - self.width())  // 2
        y = (pantalla.height() - self.height()) // 2
        self.move(x, y)

        self.setStyleSheet("""
            QMainWindow { background-color: #f8f7f4; }

            /* ── Sidebar ─────────────────────────────────── */
            QWidget#sidebar {
                min-width: 220px;
                max-width: 220px;
            }
            QLabel#sidebar_titulo {
                color: #534AB7;
                font-size: 14px;
                font-weight: 600;
                padding: 0 16px;
            }
            QLabel#sidebar_rol {
                font-size: 11px;
                padding: 0 16px;
            }
            QMenuBar {
                border: none; 
            }
            QMenuBar::item {
                padding: 6px 18px;   
                margin: 2px;
                border: none;        
            }
            QMenu {
                border: 1px solid #ccc;
            }
            QMenu::item {
                padding: 6px 22px;  
                border: none;
            }
                
            QPushButton#btn_modulo {
                text-align: left;
                padding: 11px 20px;
                border: none;
                background: transparent;
                font-size: 13px;
                border-radius: 0;
            }
            QPushButton#btn_modulo:hover {
                background-color: #534AB7;
                color: #ffffff;
            }
            QPushButton#btn_modulo[activo="true"] {
                background-color: #534AB7;
                color: #ffffff;
                font-weight: 500;
            }
            QPushButton#btn_logout {
                text-align: left;
                padding: 10px 20px;
                border: none;
                background: transparent;
                color: #ff8a80;
                font-size: 13px;
            }
            QPushButton#btn_logout:hover {
                background-color: #2d2b45; }

        """)

    # ══════════════════════════════════════════════════════════════
    # BARRA DE MENÚ SUPERIOR
    # ══════════════════════════════════════════════════════════════

    def _construir_barra_menu(self) -> None:
        barra = self.menuBar()

        # ── Menú: Archivo ────────────────────────────────────────
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

        # ── Menú: Mi cuenta ──────────────────────────────────────
        menu_cuenta = barra.addMenu("Mi cuenta")

        act_cambiar_pass = QAction("🔑 Cambiar contraseña", self)
        act_cambiar_pass.triggered.connect(self._abrir_cambio_password)
        menu_cuenta.addAction(act_cambiar_pass)

        # ── Menú: Apariencia ─────────────────────────────────────
        menu_apariencia = barra.addMenu("Apariencia")
        act_tema = QAction("🌙 Cambiar tema", self)
        act_tema.triggered.connect(self._toggle_tema)
        self._actualizar_texto_tema()

        menu_apariencia.addAction(act_tema)

        # ── Menú: Configuracion ─────────────────────────────────────
        menu_config = barra.addMenu("Configuración")
        act_cambiar_logo = QAction ("Cambiar Logo",self)
        act_cambiar_logo.triggered.connect(self._config_logo)
        menu_config.addAction(act_cambiar_logo)

    # ══════════════════════════════════════════════════════════════
    # UI CENTRAL (sidebar + área de contenido)
    # ══════════════════════════════════════════════════════════════

    def _construir_ui_central(self) -> None:
        # Contenedor raíz con layout horizontal: [sidebar | contenido]
        contenedor = QWidget()
        self.setCentralWidget(contenedor)
        layout_raiz = QHBoxLayout(contenedor)
        layout_raiz.setContentsMargins(0, 0, 0, 0)
        layout_raiz.setSpacing(0)

        # Construir cada parte
        sidebar = self._construir_sidebar()
        area    = self._construir_area_central()

        layout_raiz.addWidget(sidebar)
        layout_raiz.addWidget(area, stretch=1)  

    def _construir_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        layout  = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 24, 0, 16)
        layout.setSpacing(2)

        # ── Cabecera: nombre y rol ───────────────────────────────
        lbl_nombre = QLabel(f"👤  {self.sesion.nombre_completo}")
        lbl_nombre.setObjectName("sidebar_titulo")
        lbl_nombre.setWordWrap(True)

        lbl_rol = QLabel(self.sesion.rol_nombre.upper())
        lbl_rol.setObjectName("sidebar_rol")

        layout.addWidget(lbl_nombre)
        layout.addWidget(lbl_rol)
        layout.addSpacing(20)

        # Separador
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #2d2b45; margin: 0 16px;")
        layout.addWidget(sep)
        layout.addSpacing(8)

        # ── Botones de módulos (filtrados por rol) ───────────────
        self._construir_menu_por_rol(layout)

        layout.addStretch()   # empuja el botón logout al fondo

        # ── Botón Cerrar sesión ──────────────────────────────────
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet("color: #2d2b45; margin: 0 16px;")
        layout.addWidget(sep2)

        btn_logout = QPushButton("🔒  Cerrar sesión")
        btn_logout.setObjectName("btn_logout")
        btn_logout.clicked.connect(self._cerrar_sesion)
        layout.addWidget(btn_logout)

        return sidebar

    def _construir_menu_por_rol(self, layout: QVBoxLayout) -> None:
        for nombre, icono, roles_permitidos, _ in MODULOS:
            if self.sesion.rol_nombre not in roles_permitidos:
                continue   # este módulo no es para este rol

            btn = QPushButton(f"  {icono}  {nombre}")
            btn.setObjectName("btn_modulo")
            btn.setProperty("activo", "false")
            btn.setProperty("modulo", nombre)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, n=nombre: self._navegar_a(n))

            self.botones_menu.append(btn)
            layout.addWidget(btn)

        # Activar el primer módulo por defecto
        if self.botones_menu:
            self._marcar_activo(self.botones_menu[0])

    def _construir_area_central(self) -> QWidget:
        """
        Cada página del stack es un módulo del sistema.
        Sprint a sprint se irán agregando las páginas reales.
        """
        area = QWidget()
        area.setObjectName("area_central")
        layout = QVBoxLayout(area)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.stack = QStackedWidget()

        # Índice 0 → Inicio (bienvenida)
        self.stack.addWidget(DashboardWidget(self.sesion))  # Página de bienvenida

        # Mapa nombre_módulo → índice en el stack
        self._stack_indices = {"Inicio": 0}

        # Agregar páginas de módulos implementados
        for nombre, _icono, _roles, widget_class in MODULOS:
            if widget_class is not None and nombre not in self._stack_indices:
                widget = widget_class(self.sesion)         
                idx = self.stack.addWidget(widget)
                self._stack_indices[nombre] = idx

        layout.addWidget(self.stack)
        return area

    def _pagina_bienvenida(self) -> QWidget:
        """Página inicial que se ve al abrir el sistema."""
        pagina = QWidget()
        layout = QVBoxLayout(pagina)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_titulo = QLabel(f"Bienvenido, {self.sesion.nombres_solo() if hasattr(self.sesion,'nombres_solo') else self.sesion.nombre_completo.split()[0]} 👋")
        lbl_titulo.setObjectName("bienvenida_titulo")
        lbl_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_sub = QLabel(
            f"Rol: {self.sesion.rol_nombre}  ·  "
            f"Sesión activa por {self.sesion.minutos_restantes} min más"
        )
        lbl_sub.setObjectName("bienvenida_sub")
        lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_bienvenida_sub = lbl_sub   # guardar referencia para actualizar

        layout.addWidget(lbl_titulo)
        layout.addSpacing(8)
        layout.addWidget(lbl_sub)
        return pagina

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
        barra.addPermanentWidget(self.lbl_estado_tiempo)   # addPermanent → alinea a la derecha

        self._actualizar_barra_estado()

    def _actualizar_barra_estado(self) -> None:
        """Actualiza el tiempo restante de sesión en la barra inferior."""
        minutos = self.sesion.minutos_restantes
        self.lbl_estado_tiempo.setText(f"⏱ Sesión expira en {minutos} min  ")
        if hasattr(self, 'lbl_bienvenida_sub'):
            self.lbl_bienvenida_sub.setText(
                f"Rol: {self.sesion.rol_nombre}  ·  "
                f"Sesión activa por {minutos} min más"
            )

    # ══════════════════════════════════════════════════════════════
    # TIMER DE SESIÓN (verifica cada 60 segundos)
    # ══════════════════════════════════════════════════════════════

    def _iniciar_timer_sesion(self) -> None:

        self.timer_sesion = QTimer(self)
        self.timer_sesion.setInterval(60_000)       # cada 60 000 ms = 1 minuto
        self.timer_sesion.timeout.connect(self._verificar_sesion)
        self.timer_sesion.start()

    def _verificar_sesion(self) -> None:
        """
        Ejecutada por el QTimer cada minuto.
        Si la sesión expiró → cierra sesión automáticamente.
        """
        self._actualizar_barra_estado()
        if not AuthService.verificar_sesion(self.sesion):
            QMessageBox.warning(
                self,
                "Sesión expirada",
                "Tu sesión cerró automáticamente por 60 minutos de inactividad."
            )
            self._cerrar_sesion()

    # ══════════════════════════════════════════════════════════════
    # NAVEGACIÓN
    # ══════════════════════════════════════════════════════════════

    def _navegar_a(self, nombre_modulo: str) -> None:

        self.sesion.registrar_actividad()   # reinicia el contador de 60 min

        # Marcar el botón activo en el sidebar
        for btn in self.botones_menu:
            if btn.property("modulo") == nombre_modulo:
                self._marcar_activo(btn)

        idx = self._stack_indices.get(nombre_modulo, 0)
        self.stack.setCurrentIndex(idx)
        
    def _marcar_activo(self, btn_activo: QPushButton) -> None:
        """Resalta el botón del módulo actual en el sidebar."""
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
        AuthService.logout(self.sesion)
        self.sesion = None
        self.close()     # cierra MainWindow → el main.py mostrará login de nuevo

    def _toggle_tema(self) -> None:
        from PySide6.QtWidgets import QApplication
        ThemeManager.toggle(QApplication.instance())
        self._actualizar_texto_tema()

    def _actualizar_texto_tema(self) -> None:
        if hasattr(self, 'act_tema'):
            if ThemeManager.tema_actual() == "claro":
                self.act_tema.setText("🌙  Cambiar tema ")
            else:
                self.act_tema.setText("☀️  Cambiar tema")

    def _abrir_cambio_password(self) -> None:
        from ui.cambio_password_dialog import CambioPasswordDialog
        dialogo = CambioPasswordDialog(self.sesion, self)
        dialogo.exec()

    def _config_logo(self) -> None:
        """Abre el diálogo de configuración del sistema"""
        dlg = ConfiguracionSistemaDialog(self.sesion, self)
        dlg.exec()

    def closeEvent(self, event) -> None:
        if self.sesion:
            AuthService.logout(self.sesion)
        self.timer_sesion.stop()
        event.accept()
