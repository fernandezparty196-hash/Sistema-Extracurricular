"""
services/usuario_service.py   ──   Gestión de Usuarios
════════════════════════════════════════════════════════════
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import and_
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from database.connection import get_session
from models import Usuario, Rol, Auditoria


# ══════════════════════════════════════════════════════════════════
# RESULTADO ESTÁNDAR
# ══════════════════════════════════════════════════════════════════

@dataclass
class ResultadoUsuario:
    """
    Estructura de respuesta estándar.
    Mismo patrón que ResultadoAuth en auth_service.py.
    """
    ok: bool
    mensaje: str
    usuario: Optional[Usuario] = None
    lista: Optional[List[Dict[str, Any]]] = None
    datos: Optional[Dict[str, Any]] = None


# ══════════════════════════════════════════════════════════════════
# SERVICIO DE USUARIOS
# ══════════════════════════════════════════════════════════════════

class UsuarioService:
    """
    Todas las funciones son @staticmethod.
    No necesitas instanciar la clase:
        UsuarioService.crear(...) ✓
        servicio = UsuarioService() ✗
    """

    # ══════════════════════════════════════════════════════════════
    # CREAR USUARIO
    # ══════════════════════════════════════════════════════════════

    @staticmethod
    def crear(
        nombres: str,
        apellidos: str,
        username: str,
        email: str,
        password: str,
        rol_id: int,
        usuario_creador_id: int = None
    ) -> ResultadoUsuario:
        """
        Crea un nuevo usuario en el sistema.

        VALIDACIONES:
          ✓ Nombres y apellidos: no vacíos, 2-100 caracteres
          ✓ Username: 3-50 caracteres, único, sin espacios
          ✓ Email: formato válido, único
          ✓ Password: mínimo 8 caracteres
          ✓ Rol: debe existir en tabla roles

        PARÁMETROS:
          usuario_creador_id: ID del admin que está creando (para auditoría)

        RETORNA:
          ResultadoUsuario con ok=True y datos del usuario creado
          O ResultadoUsuario con ok=False y mensaje de error
        """

        # ── Validaciones ─────────────────────────────────────────
        error = UsuarioService._validar_datos(
            nombres, apellidos, username, email, password
        )
        if error:
            return ResultadoUsuario(ok=False, mensaje=error)

        try:
            with get_session() as session:
                # Verificar que el rol existe
                rol = session.query(Rol).filter_by(id=rol_id).first()
                if not rol:
                    return ResultadoUsuario(
                        ok=False,
                        mensaje=f"El rol con ID {rol_id} no existe."
                    )

                # Crear usuario
                usuario = Usuario(
                    nombres=nombres.strip(),
                    apellidos=apellidos.strip(),
                    username=username.strip().lower(),
                    email=email.strip().lower(),
                    rol_id=rol_id,
                    activo=True
                )
                usuario.set_password(password)

                session.add(usuario)
                session.flush()  # Para obtener el ID
                usuario_id = usuario.id

                # Auditoría - mismo patrón que auth_service.py
                UsuarioService._auditar(
                    session,
                    usuario_id=usuario_creador_id or usuario_id,
                    tabla_afectada="usuarios",
                    accion="INSERT",
                    registro_id=usuario_id,
                    datos_nuevos={
                        "username": usuario.username,
                        "email": usuario.email,
                        "rol_id": rol_id,
                        "nombres": nombres,
                        "apellidos": apellidos,
                        "accion": "usuario_creado"
                    }
                )

                session.commit()

                return ResultadoUsuario(
                    ok=True,
                    mensaje=f"Usuario '{usuario.username}' creado correctamente.",
                    usuario=usuario,
                    datos={
                        "id": usuario.id,
                        "username": usuario.username,
                        "nombre_completo": usuario.nombre_completo,
                        "email": usuario.email,
                        "rol": rol.nombre
                    }
                )

        except IntegrityError as e:
            if "username" in str(e).lower():
                return ResultadoUsuario(
                    ok=False,
                    mensaje="El nombre de usuario ya existe."
                )
            elif "email" in str(e).lower():
                return ResultadoUsuario(
                    ok=False,
                    mensaje="El email ya está registrado."
                )
            else:
                return ResultadoUsuario(
                    ok=False,
                    mensaje=f"Error de integridad: {str(e)}"
                )

        except SQLAlchemyError as e:
            return ResultadoUsuario(
                ok=False,
                mensaje=f"Error al crear usuario: {str(e)}"
            )

    # ══════════════════════════════════════════════════════════════
    # OBTENER USUARIO
    # ══════════════════════════════════════════════════════════════

    @staticmethod
    def obtener_por_id(usuario_id: int) -> ResultadoUsuario:
        """Obtiene un usuario por su ID."""
        try:
            with get_session() as session:
                usuario = session.query(Usuario).filter_by(id=usuario_id).first()

                if not usuario:
                    return ResultadoUsuario(
                        ok=False,
                        mensaje=f"Usuario con ID {usuario_id} no encontrado."
                    )

                return ResultadoUsuario(
                    ok=True,
                    mensaje="Usuario obtenido correctamente.",
                    usuario=usuario,
                    datos={
                        "id": usuario.id,
                        "username": usuario.username,
                        "nombres": usuario.nombres,
                        "apellidos": usuario.apellidos,
                        "nombre_completo": usuario.nombre_completo,
                        "email": usuario.email,
                        "rol_id": usuario.rol_id,
                        "rol_nombre": usuario.rol.nombre,
                        "activo": usuario.activo,
                        "ultimo_acceso": usuario.ultimo_acceso.strftime("%d/%m/%Y %H:%M") if usuario.ultimo_acceso else "Nunca",
                        "bloqueado_hasta": usuario.bloqueado_hasta.strftime("%d/%m/%Y %H:%M") if usuario.bloqueado_hasta else None,
                        "esta_bloqueado": usuario.esta_bloqueado,
                        "intentos_fallidos": usuario.intentos_fallidos
                    }
                )

        except SQLAlchemyError as e:
            return ResultadoUsuario(
                ok=False,
                mensaje=f"Error al obtener usuario: {str(e)}"
            )

    @staticmethod
    def obtener_por_username(username: str) -> ResultadoUsuario:
        """Obtiene un usuario por username."""
        try:
            with get_session() as session:
                usuario = session.query(Usuario).filter_by(
                    username=username.strip().lower()
                ).first()

                if not usuario:
                    return ResultadoUsuario(
                        ok=False,
                        mensaje=f"Usuario '{username}' no encontrado."
                    )

                return ResultadoUsuario(
                    ok=True,
                    mensaje="Usuario obtenido correctamente.",
                    usuario=usuario
                )

        except SQLAlchemyError as e:
            return ResultadoUsuario(
                ok=False,
                mensaje=f"Error al obtener usuario: {str(e)}"
            )

    # ══════════════════════════════════════════════════════════════
    # LISTAR USUARIOS
    # ══════════════════════════════════════════════════════════════

    @staticmethod
    def listar(
        rol_id: int = None,
        activos_solo: bool = True,
        limite: int = None
    ) -> ResultadoUsuario:
        """
        Lista usuarios con filtros opcionales.

        PARÁMETROS:
          rol_id: filtrar por rol (None = todos)
          activos_solo: True = solo usuarios activos
          limite: máximo número de resultados

        RETORNA:
          Lista de dicts con: id, username, nombre, email, rol, activo, etc.
        """
        try:
            with get_session() as session:
                query = session.query(Usuario)

                if activos_solo:
                    query = query.filter_by(activo=True)

                if rol_id:
                    query = query.filter_by(rol_id=rol_id)

                if limite:
                    query = query.limit(limite)

                usuarios = query.order_by(Usuario.nombres).all()

                lista = [
                    {
                        "id": u.id,
                        "username": u.username,
                        "nombre": u.nombre_completo,
                        "email": u.email,
                        "rol": u.rol.nombre,
                        "activo": u.activo,
                        "ultimo_acceso": u.ultimo_acceso.strftime("%d/%m/%Y %H:%M") if u.ultimo_acceso else "Nunca",
                        "esta_bloqueado": u.esta_bloqueado
                    }
                    for u in usuarios
                ]

                return ResultadoUsuario(
                    ok=True,
                    mensaje=f"Se encontraron {len(lista)} usuario(s).",
                    lista=lista
                )

        except SQLAlchemyError as e:
            return ResultadoUsuario(
                ok=False,
                mensaje=f"Error al listar usuarios: {str(e)}"
            )

    # ══════════════════════════════════════════════════════════════
    # ACTUALIZAR USUARIO
    # ══════════════════════════════════════════════════════════════

    @staticmethod
    def actualizar(
        usuario_id: int,
        nombres: str = None,
        apellidos: str = None,
        email: str = None,
        rol_id: int = None,
        activo: bool = None,
        usuario_editor_id: int = None
    ) -> ResultadoUsuario:
        """
        Actualiza datos del usuario.

        NOTA: Para cambiar password, usar AuthService.cambiar_password()
              No se puede cambiar username (campo único, identificador).

        PARÁMETROS:
          usuario_id: ID del usuario a actualizar
          nombres, apellidos, email, rol_id, activo: campos a cambiar (None = no cambiar)
          usuario_editor_id: ID de quién está haciendo el cambio (para auditoría)
        """
        try:
            with get_session() as session:
                usuario = session.query(Usuario).filter_by(id=usuario_id).first()

                if not usuario:
                    return ResultadoUsuario(
                        ok=False,
                        mensaje=f"Usuario con ID {usuario_id} no encontrado."
                    )

                # Guardar valores antiguos para auditoría
                datos_anteriores = {
                    "nombres": usuario.nombres,
                    "apellidos": usuario.apellidos,
                    "email": usuario.email,
                    "rol_id": usuario.rol_id,
                    "activo": usuario.activo
                }

                cambios = {}

                # Actualizar nombres
                if nombres is not None:
                    nombres_limpio = nombres.strip()
                    if len(nombres_limpio) < 2 or len(nombres_limpio) > 100:
                        return ResultadoUsuario(
                            ok=False,
                            mensaje="El nombre debe tener entre 2 y 100 caracteres."
                        )
                    usuario.nombres = nombres_limpio
                    cambios["nombres"] = nombres_limpio

                # Actualizar apellidos
                if apellidos is not None:
                    apellidos_limpio = apellidos.strip()
                    if len(apellidos_limpio) < 2 or len(apellidos_limpio) > 100:
                        return ResultadoUsuario(
                            ok=False,
                            mensaje="El apellido debe tener entre 2 y 100 caracteres."
                        )
                    usuario.apellidos = apellidos_limpio
                    cambios["apellidos"] = apellidos_limpio

                # Actualizar email
                if email is not None:
                    email_limpio = email.strip().lower()
                    if "@" not in email_limpio or "." not in email_limpio.split("@")[-1]:
                        return ResultadoUsuario(
                            ok=False,
                            mensaje="El email no tiene un formato válido."
                        )
                    # Verificar unicidad
                    existe = session.query(Usuario).filter(
                        and_(
                            Usuario.email == email_limpio,
                            Usuario.id != usuario_id
                        )
                    ).first()
                    if existe:
                        return ResultadoUsuario(
                            ok=False,
                            mensaje="El email ya está en uso por otro usuario."
                        )
                    usuario.email = email_limpio
                    cambios["email"] = email_limpio

                # Actualizar rol
                if rol_id is not None:
                    rol = session.query(Rol).filter_by(id=rol_id).first()
                    if not rol:
                        return ResultadoUsuario(
                            ok=False,
                            mensaje=f"El rol con ID {rol_id} no existe."
                        )
                    usuario.rol_id = rol_id
                    cambios["rol_id"] = rol_id

                # Actualizar activo
                if activo is not None:
                    usuario.activo = activo
                    cambios["activo"] = activo

                usuario.updated_at = datetime.now()

                # Auditoría
                if cambios:
                    UsuarioService._auditar(
                        session,
                        usuario_id=usuario_editor_id or usuario_id,
                        tabla_afectada="usuarios",
                        accion="UPDATE",
                        registro_id=usuario_id,
                        datos_anteriores=datos_anteriores,
                        datos_nuevos=cambios
                    )

                session.commit()

                return ResultadoUsuario(
                    ok=True,
                    mensaje="Usuario actualizado correctamente.",
                    usuario=usuario
                )

        except IntegrityError as e:
            if "email" in str(e).lower():
                return ResultadoUsuario(
                    ok=False,
                    mensaje="El email ya está en uso."
                )
            else:
                return ResultadoUsuario(
                    ok=False,
                    mensaje=f"Error de integridad: {str(e)}"
                )

        except SQLAlchemyError as e:
            return ResultadoUsuario(
                ok=False,
                mensaje=f"Error al actualizar usuario: {str(e)}"
            )

    # ══════════════════════════════════════════════════════════════
    # ACTIVAR / DESACTIVAR
    # ══════════════════════════════════════════════════════════════

    @staticmethod
    def desactivar(usuario_id: int, usuario_editor_id: int = None) -> ResultadoUsuario:
        """Desactiva un usuario (no lo elimina, mantiene histórico)."""
        return UsuarioService.actualizar(
            usuario_id=usuario_id,
            activo=False,
            usuario_editor_id=usuario_editor_id
        )

    @staticmethod
    def activar(usuario_id: int, usuario_editor_id: int = None) -> ResultadoUsuario:
        """Reactiva un usuario inactivo."""
        return UsuarioService.actualizar(
            usuario_id=usuario_id,
            activo=True,
            usuario_editor_id=usuario_editor_id
        )

    # ══════════════════════════════════════════════════════════════
    # DESBLOQUEAR USUARIO
    # ══════════════════════════════════════════════════════════════

    @staticmethod
    def desbloquear(usuario_id: int, usuario_editor_id: int = None) -> ResultadoUsuario:
        """
        Desbloquea un usuario que fue bloqueado por intentos fallidos.
        Llamar desde panel admin cuando un usuario está bloqueado.
        """
        try:
            with get_session() as session:
                usuario = session.query(Usuario).filter_by(id=usuario_id).first()

                if not usuario:
                    return ResultadoUsuario(
                        ok=False,
                        mensaje=f"Usuario con ID {usuario_id} no encontrado."
                    )

                usuario.intentos_fallidos = 0
                usuario.bloqueado_hasta = None

                UsuarioService._auditar(
                    session,
                    usuario_id=usuario_editor_id or usuario_id,
                    tabla_afectada="usuarios",
                    accion="UPDATE",
                    registro_id=usuario_id,
                    datos_nuevos={"accion": "usuario_desbloqueado"}
                )

                session.commit()

                return ResultadoUsuario(
                    ok=True,
                    mensaje=f"Usuario '{usuario.username}' desbloqueado."
                )

        except SQLAlchemyError as e:
            return ResultadoUsuario(
                ok=False,
                mensaje=f"Error al desbloquear usuario: {str(e)}"
            )

    # ══════════════════════════════════════════════════════════════
    # ELIMINAR USUARIO (con precaución)
    # ══════════════════════════════════════════════════════════════

    @staticmethod
    def eliminar(usuario_id: int, usuario_editor_id: int = None) -> ResultadoUsuario:
        """
        Elimina un usuario de la BD (CUIDADO).

        RECOMENDACIÓN:
          Usar desactivar() en lugar de eliminar().
          Desactivar mantiene el histórico en auditoría.
          Eliminar borra todos los datos.

        VERIFICACIONES:
          • Se audita antes de eliminar
        """
        try:
            with get_session() as session:
                usuario = session.query(Usuario).filter_by(id=usuario_id).first()

                if not usuario:
                    return ResultadoUsuario(
                        ok=False,
                        mensaje=f"Usuario con ID {usuario_id} no encontrado."
                    )

                username = usuario.username

                UsuarioService._auditar(
                    session,
                    usuario_id=usuario_editor_id or usuario_id,
                    tabla_afectada="usuarios",
                    accion="DELETE",
                    registro_id=usuario_id,
                    datos_anteriores={
                        "username": usuario.username,
                        "email": usuario.email,
                        "nombre_completo": usuario.nombre_completo
                    }
                )

                session.delete(usuario)
                session.commit()

                return ResultadoUsuario(
                    ok=True,
                    mensaje=f"Usuario '{username}' eliminado correctamente."
                )

        except SQLAlchemyError as e:
            return ResultadoUsuario(
                ok=False,
                mensaje=f"Error al eliminar usuario: {str(e)}"
            )

    # ══════════════════════════════════════════════════════════════
    # MÉTODOS PRIVADOS
    # ══════════════════════════════════════════════════════════════

    @staticmethod
    def _validar_datos(
        nombres: str,
        apellidos: str,
        username: str,
        email: str,
        password: str
    ) -> Optional[str]:
        """
        Valida los datos del usuario.
        Retorna None si todo es válido, o mensaje de error.
        """

        # Nombres
        if not nombres or not nombres.strip():
            return "El nombre es obligatorio."
        if len(nombres.strip()) < 2:
            return "El nombre debe tener al menos 2 caracteres."
        if len(nombres.strip()) > 100:
            return "El nombre no puede exceder 100 caracteres."

        # Apellidos
        if not apellidos or not apellidos.strip():
            return "El apellido es obligatorio."
        if len(apellidos.strip()) < 2:
            return "El apellido debe tener al menos 2 caracteres."
        if len(apellidos.strip()) > 100:
            return "El apellido no puede exceder 100 caracteres."

        # Username
        if not username or not username.strip():
            return "El nombre de usuario es obligatorio."
        username = username.strip().lower()
        if len(username) < 3:
            return "El nombre de usuario debe tener al menos 3 caracteres."
        if len(username) > 50:
            return "El nombre de usuario no puede exceder 50 caracteres."
        if " " in username:
            return "El nombre de usuario no puede contener espacios."
        if not username.replace("_", "").replace(".", "").isalnum():
            return "El nombre de usuario solo puede contener letras, números, guiones y puntos."

        # Email
        if not email or not email.strip():
            return "El email es obligatorio."
        email = email.strip().lower()
        if "@" not in email or "." not in email.split("@")[-1]:
            return "El email no tiene un formato válido."
        if len(email) > 150:
            return "El email no puede exceder 150 caracteres."

        # Password
        if not password:
            return "La contraseña es obligatoria."
        if len(password) < 8:
            return "La contraseña debe tener al menos 8 caracteres."
        if len(password) > 255:
            return "La contraseña es demasiado larga."

        return None

    @staticmethod
    def _auditar(
        session,
        usuario_id: int,
        tabla_afectada: str,
        accion: str,
        registro_id: int = None,
        datos_anteriores: dict = None,
        datos_nuevos: dict = None
    ) -> None:
        """
        Inserta un registro en la tabla auditoria.
        Mismo patrón que auth_service.py
        """
        registro = Auditoria(
            usuario_id=usuario_id,
            tabla_afectada=tabla_afectada,
            accion=accion,
            registro_id=registro_id,
            datos_anteriores=datos_anteriores,
            datos_nuevos=datos_nuevos
        )
        session.add(registro)
