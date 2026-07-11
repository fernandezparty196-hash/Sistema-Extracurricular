"""
services/configuracion_service.py

Service para gestionar la configuración global del sistema
usando un archivo JSON (sin base de datos).

Archivo guardado en: config/configuracion.json
"""

import json
from pathlib import Path
from dataclasses import dataclass


@dataclass
class Configuracion:
    """Resultado de operación de configuración"""
    ok: bool
    mensaje: str
    datos: dict = None


class ConfiguracionService:
    """
    Gestiona la configuración global del sistema usando JSON.
    
    Uso:
        resultado = ConfiguracionService.obtener()
        resultado = ConfiguracionService.actualizar(
            nombre_institucion="UNAB",
            logo_ruta="assets/logos/unab_logo.png"
        )
    """

    # Ruta del archivo de configuración
    CARPETA_CONFIG = Path(__file__).parent.parent / "config"
    ARCHIVO_CONFIG = CARPETA_CONFIG / "configuracion.json"
    
    # Carpeta donde se guardan los logos
    CARPETA_LOGOS = Path(__file__).parent.parent / "assets" / "logos"

    # Configuración por defecto
    CONFIG_DEFECTO = {
        "nombre_institucion": "Universidad Nacional de Barranca",
        "logo_ruta": None
    }

    @classmethod
    def _asegurar_archivos(cls) -> None:
        """Crea las carpetas necesarias si no existen"""
        cls.CARPETA_CONFIG.mkdir(parents=True, exist_ok=True)
        cls.CARPETA_LOGOS.mkdir(parents=True, exist_ok=True)

    @classmethod
    def _cargar_json(cls) -> dict:
        """Carga el archivo JSON de configuración"""
        cls._asegurar_archivos()
        
        if cls.ARCHIVO_CONFIG.exists():
            try:
                with open(cls.ARCHIVO_CONFIG, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error al leer config: {e}")
                return cls.CONFIG_DEFECTO.copy()
        else:
            # Crear archivo con valores por defecto
            cls._guardar_json(cls.CONFIG_DEFECTO.copy())
            return cls.CONFIG_DEFECTO.copy()

    @classmethod
    def _guardar_json(cls, datos: dict) -> bool:
        """Guarda los datos en el archivo JSON"""
        try:
            cls._asegurar_archivos()
            
            with open(cls.ARCHIVO_CONFIG, 'w', encoding='utf-8') as f:
                json.dump(datos, f, indent=4, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"Error al guardar config: {e}")
            return False

    @classmethod
    def obtener(cls) -> Configuracion:
        """
        Obtiene la configuración actual del sistema.
        
        Returns:
            Configuracion con ok=True y datos={'nombre_institucion', 'logo_ruta'}
        """
        try:
            datos = cls._cargar_json()
            
            return Configuracion(
                ok=True,
                mensaje="Configuración obtenida",
                datos=datos
            )
        except Exception as e:
            return Configuracion(
                ok=False,
                mensaje=f"Error al obtener configuración: {str(e)}",
                datos=cls.CONFIG_DEFECTO.copy()
            )

    @classmethod
    def actualizar(cls, 
                   nombre_institucion: str = None,
                   logo_ruta: str = None) -> Configuracion:
        """
        Actualiza la configuración del sistema.
        
        Args:
            nombre_institucion: Nuevo nombre de la institución
            logo_ruta: Nueva ruta del logo
            
        Returns:
            Configuracion con ok=True si fue exitoso
        """
        try:
            # Cargar configuración actual
            datos = cls._cargar_json()

            # Actualizar campos
            if nombre_institucion is not None:
                datos["nombre_institucion"] = nombre_institucion
            if logo_ruta is not None:
                datos["logo_ruta"] = logo_ruta

            # Guardar
            if cls._guardar_json(datos):
                return Configuracion(
                    ok=True,
                    mensaje="Configuración actualizada correctamente",
                    datos=datos
                )
            else:
                return Configuracion(
                    ok=False,
                    mensaje="Error al guardar en archivo",
                    datos=None
                )
        except Exception as e:
            return Configuracion(
                ok=False,
                mensaje=f"Error al actualizar configuración: {str(e)}",
                datos=None
            )

    @classmethod
    def guardar_logo(cls, archivo_path: str, nombre_archivo: str = None) -> Configuracion:
        """
        Guarda un archivo de logo en la carpeta de assets.
        
        Args:
            archivo_path: Ruta del archivo original
            nombre_archivo: Nombre del archivo guardado (default: nombre_archivo)
            
        Returns:
            Configuracion con la ruta relativa del logo guardado
        """
        try:
            # Crear carpeta si no existe
            cls.CARPETA_LOGOS.mkdir(parents=True, exist_ok=True)

            # Usar nombre original o generar uno
            if nombre_archivo is None:
                nombre_archivo = Path(archivo_path).name

            # Ruta destino
            ruta_destino = cls.CARPETA_LOGOS / nombre_archivo
            ruta_relativa = f"assets/logos/{nombre_archivo}"

            # Copiar archivo
            with open(archivo_path, 'rb') as src:
                with open(ruta_destino, 'wb') as dst:
                    dst.write(src.read())

            return Configuracion(
                ok=True,
                mensaje=f"Logo guardado: {nombre_archivo}",
                datos={"ruta_relativa": ruta_relativa}
            )
        except Exception as e:
            return Configuracion(
                ok=False,
                mensaje=f"Error al guardar logo: {str(e)}",
                datos=None
            )

    @classmethod
    def obtener_ruta_logo_absoluta(cls, ruta_relativa: str) -> str:
        """
        Convierte una ruta relativa a absoluta.
        
        Args:
            ruta_relativa: Ruta relativa (ej: "assets/logos/unab.png")
            
        Returns:
            Ruta absoluta completa
        """
        if not ruta_relativa:
            return None
        
        ruta_base = Path(__file__).parent.parent
        return str(ruta_base / ruta_relativa)

    @classmethod
    def resetear_a_defecto(cls) -> Configuracion:
        """Restaura la configuración a los valores por defecto"""
        try:
            if cls._guardar_json(cls.CONFIG_DEFECTO.copy()):
                return Configuracion(
                    ok=True,
                    mensaje="Configuración restaurada a valores por defecto",
                    datos=cls.CONFIG_DEFECTO.copy()
                )
            else:
                return Configuracion(
                    ok=False,
                    mensaje="Error al restaurar",
                    datos=None
                )
        except Exception as e:
            return Configuracion(
                ok=False,
                mensaje=f"Error: {str(e)}",
                datos=None
            )