"""
ui/bienes/__init__.py   ──   Módulo de Gestión de Bienes
"""

from .panel_gestion_bienes import PanelBienesPatrimoniales
from .formulario_bien_dialog import FormularioBienDialog
from .dialogo_registrar_bien import DialogoRegistrarBien

__all__ = [
    "PanelBienesPatrimoniales",
    "FormularioBienDialog",
    "DialogoRegistrarBien",
]

