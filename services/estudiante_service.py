

from datetime import datetime
from typing   import Optional

from sqlalchemy import or_, func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from database.connection import get_session
from models import (
    Estudiante, Carrera, Facultad,
    Inscripcion, Asistencia, Sesion,
    ListaAptoDetalle, Auditoria, Usuario
)


# ── Resultado estándar (igual que en auth_service) ────────────────
class ResultadoEstudiante:
    def __init__(self, ok: bool, mensaje: str,
                 datos=None, lista=None):
        self.ok      = ok
        self.mensaje = mensaje
        self.datos   = datos    # un objeto Estudiante o dict
        self.lista   = lista    # lista de resultados


class EstudianteService:

    # ══════════════════════════════════════════════════════════════
    # HU-02 · REGISTRAR ESTUDIANTE INDIVIDUAL
    # ══════════════════════════════════════════════════════════════
    @staticmethod
    def registrar(datos: dict, usuario_id: int) -> ResultadoEstudiante:

        # ── Validaciones de campos obligatorios ──────────────────
        obligatorios = ["dni", "codigo_estudiantil", "nombres",
                        "apellidos", "carrera_id"]
        for campo in obligatorios:
            if not datos.get(campo):
                return ResultadoEstudiante(
                    ok=False,
                    mensaje=f"El campo '{campo}' es obligatorio."
                )

        # ── Validar formato de email ──────────────────────────────
        email = datos.get("email", "")
        advertencia_email = ""
        if email:
            if "@" not in email:
                return ResultadoEstudiante(
                    ok=False,
                    mensaje="El correo no tiene un formato válido."
                )
            if not email.endswith("@unab.edu.pe"):
                advertencia_email = (
                    " (Advertencia: el correo no es institucional @unab.edu.pe)"
                )

        try:
            with get_session() as session:
                # ── Verificar duplicados ──────────────────────────
                dni_existe = session.query(Estudiante).filter(
                    Estudiante.dni == datos["dni"].strip()
                ).first()
                if dni_existe:
                    return ResultadoEstudiante(
                        ok=False,
                        mensaje=f"Ya existe un estudiante con DNI {datos['dni']}."
                    )

                codigo_existe = session.query(Estudiante).filter(
                    Estudiante.codigo_estudiantil == datos["codigo_estudiantil"].strip()
                ).first()
                if codigo_existe:
                    return ResultadoEstudiante(
                        ok=False,
                        mensaje=f"Ya existe un estudiante con código {datos['codigo_estudiantil']}."
                    )

                # ── Crear el objeto ───────────────────────────────
                nuevo = Estudiante(
                    dni                = datos["dni"].strip(),
                    codigo_estudiantil = datos["codigo_estudiantil"].strip(),
                    nombres            = datos["nombres"].strip().title(),
                    apellidos          = datos["apellidos"].strip().title(),
                    carrera_id         = datos["carrera_id"],
                    ciclo_actual       = datos.get("ciclo_actual"),
                    email              = datos.get("email", "").strip() or None,
                    telefono           = datos.get("telefono", "").strip() or None,
                    foto_ruta          = datos.get("foto_ruta"),
                    estado             = "Activo",
                    created_by         = usuario_id,
                )
                session.add(nuevo)
                session.flush()   # obtiene el ID antes del commit

                # ── Auditoría ─────────────────────────────────────
                session.add(Auditoria(
                    usuario_id     = usuario_id,
                    tabla_afectada = "estudiantes",
                    accion         = "INSERT",
                    registro_id    = nuevo.id,
                    datos_nuevos   = {
                        "dni": nuevo.dni,
                        "codigo": nuevo.codigo_estudiantil,
                        "nombre": nuevo.nombre_completo,
                    }
                ))

            mensaje = f"Estudiante '{datos['nombres']}' registrado correctamente."
            return ResultadoEstudiante(
                ok=True,
                mensaje=mensaje + advertencia_email,
                datos={"id": nuevo.id}
            )

        except SQLAlchemyError as e:
            return ResultadoEstudiante(
                ok=False,
                mensaje=f"Error al guardar en la base de datos: {e}"
            )

    # ══════════════════════════════════════════════════════════════
    # HU-04 · BUSCAR Y FILTRAR (resultados en tiempo real)
    # ══════════════════════════════════════════════════════════════
    @staticmethod
    def buscar(texto: str = "", carrera_id: int = None,
               ciclo: int = None, estado: str = None,
               limite: int = 200) -> list[dict]:
        """
        Búsqueda combinada de estudiantes.
        Retorna lista de dicts (no objetos SQLAlchemy) para usar
        directamente en QTableWidget sin problemas de sesión cerrada.

        PARÁMETROS:
          texto:      busca en nombres, apellidos, DNI, código
          carrera_id: filtra por carrera (None = todas)
          ciclo:      filtra por ciclo (None = todos)
          estado:     "Activo", "Inactivo", "Egresado" (None = todos)
          limite:     máximo de resultados (por defecto 200)

        RETORNA lista de dicts:
          [{
            "id", "dni", "codigo_estudiantil",
            "nombre_completo", "carrera", "facultad",
            "ciclo_actual", "email", "telefono",
            "estado", "foto_ruta"
          }, ...]
        """
        try:
            with get_session() as session:
                query = (
                    session.query(Estudiante)
                    .join(Carrera,  Estudiante.carrera_id == Carrera.id)
                    .join(Facultad, Carrera.facultad_id   == Facultad.id)
                )

                # Filtro de texto (OR entre campos)
                if texto and texto.strip():
                    t = f"%{texto.strip()}%"
                    query = query.filter(
                        or_(
                            Estudiante.nombres.ilike(t),
                            Estudiante.apellidos.ilike(t),
                            Estudiante.dni.ilike(t),
                            Estudiante.codigo_estudiantil.ilike(t),
                        )
                    )

                if carrera_id:
                    query = query.filter(Estudiante.carrera_id == carrera_id)

                if ciclo:
                    query = query.filter(Estudiante.ciclo_actual == ciclo)

                if estado:
                    query = query.filter(Estudiante.estado == estado)

                # Ordenar por apellidos
                query = query.order_by(
                    Estudiante.apellidos, Estudiante.nombres
                ).limit(limite)

                estudiantes = query.all()

                # Serializar a dicts (independiente de la sesión)
                return [
                    {
                        "id":                 e.id,
                        "dni":                e.dni,
                        "codigo_estudiantil": e.codigo_estudiantil,
                        "nombre_completo":    e.nombre_completo,
                        "nombres":            e.nombres,
                        "apellidos":          e.apellidos,
                        "carrera":            e.carrera.nombre,
                        "carrera_id":         e.carrera_id,
                        "facultad":           e.carrera.facultad.nombre,
                        "ciclo_actual":       e.ciclo_actual,
                        "email":              e.email or "",
                        "telefono":           e.telefono or "",
                        "estado":             e.estado,
                        "foto_ruta":          e.foto_ruta,
                    }
                    for e in estudiantes
                ]
        except SQLAlchemyError:
            return []

    # ══════════════════════════════════════════════════════════════
    # OBTENER UN ESTUDIANTE POR ID
    # ══════════════════════════════════════════════════════════════
    @staticmethod
    def obtener_por_id(estudiante_id: int) -> Optional[dict]:
        """
        Retorna todos los datos de un estudiante.
        Usado para poblar el formulario de edición.
        """
        try:
            with get_session() as session:
                e = session.get(Estudiante, estudiante_id)
                if not e:
                    return None
                return {
                    "id":                 e.id,
                    "dni":                e.dni,
                    "codigo_estudiantil": e.codigo_estudiantil,
                    "nombres":            e.nombres,
                    "apellidos":          e.apellidos,
                    "nombre_completo":    e.nombre_completo,
                    "carrera_id":         e.carrera_id,
                    "carrera":            e.carrera.nombre,
                    "facultad":           e.carrera.facultad.nombre,
                    "ciclo_actual":       e.ciclo_actual,
                    "fecha_nacimiento":   str(e.fecha_nacimiento) if e.fecha_nacimiento else "",
                    "email":              e.email or "",
                    "telefono":           e.telefono or "",
                    "foto_ruta":          e.foto_ruta or "",
                    "estado":             e.estado,
                    "created_at":         str(e.created_at),
                }
        except SQLAlchemyError:
            return None

    # ══════════════════════════════════════════════════════════════
    # RF-02.4 · EDITAR DATOS (con auditoría)
    # ══════════════════════════════════════════════════════════════
    @staticmethod
    def editar(estudiante_id: int, datos: dict,
               usuario_id: int) -> ResultadoEstudiante:
        """
        Actualiza datos del estudiante.
        Guarda snapshot antes/después en la tabla auditoria.
        """
        try:
            with get_session() as session:
                e = session.get(Estudiante, estudiante_id)
                if not e:
                    return ResultadoEstudiante(
                        ok=False, mensaje="Estudiante no encontrado."
                    )

                # Snapshot antes del cambio (para auditoría)
                antes = {
                    "nombres":   e.nombres,
                    "apellidos": e.apellidos,
                    "email":     e.email,
                    "ciclo":     e.ciclo_actual,
                    "estado":    e.estado,
                }

                # Aplicar cambios
                campos_editables = [
                    "nombres", "apellidos", "carrera_id",
                    "ciclo_actual", "email", "telefono", "foto_ruta"
                ]
                for campo in campos_editables:
                    if campo in datos:
                        val = datos[campo]
                        if isinstance(val, str):
                            val = val.strip() or None
                        setattr(e, campo, val)

                e.updated_at = datetime.now()

                # Auditoría
                session.add(Auditoria(
                    usuario_id     = usuario_id,
                    tabla_afectada = "estudiantes",
                    accion         = "UPDATE",
                    registro_id    = estudiante_id,
                    datos_anteriores = antes,
                    datos_nuevos     = {k: datos[k] for k in datos
                                        if k in campos_editables},
                ))

            return ResultadoEstudiante(
                ok=True,
                mensaje="Datos actualizados correctamente."
            )
        except SQLAlchemyError as e:
            return ResultadoEstudiante(
                ok=False, mensaje=f"Error al actualizar: {e}"
            )

    # ══════════════════════════════════════════════════════════════
    # RF-02.5 · DESACTIVAR (sin borrar historial)
    # ══════════════════════════════════════════════════════════════
    @staticmethod
    def cambiar_estado(estudiante_id: int,
                       nuevo_estado: str,
                       usuario_id: int) -> ResultadoEstudiante:
        """
        Cambia el estado a Inactivo o Egresado.
        NUNCA elimina el registro ni su historial.
        nuevo_estado: "Inactivo" o "Egresado"
        """
        estados_validos = ("Activo", "Inactivo", "Egresado")
        if nuevo_estado not in estados_validos:
            return ResultadoEstudiante(
                ok=False,
                mensaje=f"Estado inválido. Use: {estados_validos}"
            )
        try:
            with get_session() as session:
                e = session.get(Estudiante, estudiante_id)
                if not e:
                    return ResultadoEstudiante(
                        ok=False, mensaje="Estudiante no encontrado."
                    )

                estado_anterior = e.estado
                e.estado     = nuevo_estado
                e.updated_at = datetime.now()

                session.add(Auditoria(
                    usuario_id       = usuario_id,
                    tabla_afectada   = "estudiantes",
                    accion           = "UPDATE",
                    registro_id      = estudiante_id,
                    datos_anteriores = {"estado": estado_anterior},
                    datos_nuevos     = {"estado": nuevo_estado},
                ))

            return ResultadoEstudiante(
                ok=True,
                mensaje=f"Estado cambiado a '{nuevo_estado}' correctamente."
            )
        except SQLAlchemyError as e:
            return ResultadoEstudiante(
                ok=False, mensaje=f"Error al cambiar estado: {e}"
            )

    # ══════════════════════════════════════════════════════════════
    # HU-05 · HISTORIAL ACADÉMICO
    # ══════════════════════════════════════════════════════════════
    @staticmethod
    def obtener_historial(estudiante_id: int) -> dict:
        """
        Retorna el historial completo del estudiante:
          - Talleres cursados con % de asistencia
          - Si aparece en lista de aptos de cada taller
          - Estadísticas generales

        Usado en la pestaña "Historial" del formulario de estudiante.
        """
        try:
            with get_session() as session:
                inscripciones = (
                    session.query(Inscripcion)
                    .filter(Inscripcion.estudiante_id == estudiante_id)
                    .all()
                )

                talleres_cursados = []
                total_sesiones_global = 0
                total_asistidas_global = 0

                for insc in inscripciones:
                    taller = insc.taller

                    # Contar sesiones realizadas
                    sesiones_realizadas = sum(
                        1 for s in taller.sesiones
                        if s.estado == "Realizada"
                    )

                    # Contar asistencias válidas (P y J)
                    asistidas = sum(
                        1 for a in insc.asistencias
                        if a.estado in ("P", "J")
                    )

                    porcentaje = (
                        round(asistidas * 100 / sesiones_realizadas, 1)
                        if sesiones_realizadas > 0 else 0.0
                    )

                    # ¿Aparece en lista de aptos?
                    detalle_lista = (
                        session.query(ListaAptoDetalle)
                        .filter(
                            ListaAptoDetalle.estudiante_id == estudiante_id,
                            ListaAptoDetalle.lista.has(
                                taller_id=taller.id
                            )
                        )
                        .first()
                    )

                    apto_str = "—"
                    if detalle_lista:
                        if detalle_lista.excluido_manual:
                            apto_str = "Excluido"
                        elif detalle_lista.es_apto:
                            apto_str = "✅ Apto"
                        else:
                            apto_str = "❌ No apto"

                    talleres_cursados.append({
                        "taller_id":          taller.id,
                        "taller_nombre":      taller.nombre,
                        "ciclo":              taller.ciclo_academico.nombre,
                        "docente":            taller.docente.nombre_completo,
                        "sesiones_asistidas": asistidas,
                        "sesiones_totales":   sesiones_realizadas,
                        "porcentaje":         porcentaje,
                        "estado_taller":      taller.estado,
                        "inscripcion_estado": insc.estado,
                        "apto":               apto_str,
                    })

                    total_sesiones_global  += sesiones_realizadas
                    total_asistidas_global += asistidas

                asistencia_global = (
                    round(total_asistidas_global * 100 / total_sesiones_global, 1)
                    if total_sesiones_global > 0 else 0.0
                )

                return {
                    "talleres":           talleres_cursados,
                    "total_talleres":     len(talleres_cursados),
                    "asistencia_global":  asistencia_global,
                    "total_sesiones":     total_sesiones_global,
                    "total_asistidas":    total_asistidas_global,
                }

        except SQLAlchemyError:
            return {"talleres": [], "total_talleres": 0,
                    "asistencia_global": 0.0}
        
    # ══════════════════════════════════════════════════════════════
    # LISTAR ESTUDIANTES PARA COMBOS
    # ══════════════════════════════════════════════════════════════
    @staticmethod
    def listar() -> ResultadoEstudiante:
        """
        Lista estudiantes activos para ComboBox.

        Retorna:
        [
            {
                "id": 1,
                "codigo": "2024001",
                "nombre": "Juan Pérez"
            }
        ]
        """
        try:
            with get_session() as session:
                estudiantes = (
                    session.query(Estudiante)
                    .filter(Estudiante.estado == "Activo")
                    .order_by(
                        Estudiante.apellidos,
                        Estudiante.nombres
                    )
                    .all()
                )

                lista = [
                    {
                        "id": e.id,
                        "codigo": e.codigo_estudiantil,
                        "nombre": e.nombre_completo
                    }
                    for e in estudiantes
                ]

                return ResultadoEstudiante(
                    ok=True,
                    mensaje="Estudiantes cargados correctamente",
                    lista=lista
                )

        except SQLAlchemyError as e:
            return ResultadoEstudiante(
                ok=False,
                mensaje=f"Error al obtener estudiantes: {e}",
                lista=[]
            )

    # ══════════════════════════════════════════════════════════════
    # DATOS AUXILIARES PARA COMBOS DE LA UI
    # ══════════════════════════════════════════════════════════════
    @staticmethod
    def listar_carreras() -> list[dict]:
        """
        Lista carreras activas agrupadas por facultad.
        Usada para poblar el QComboBox de carrera en el formulario.

        Retorna: [{"id": 1, "nombre": "Ing. Sistemas",
                   "facultad": "Facultad de Ingeniería"}, ...]
        """
        try:
            with get_session() as session:
                carreras = (
                    session.query(Carrera)
                    .join(Facultad)
                    .filter(Carrera.activo == True)
                    .order_by(Facultad.nombre, Carrera.nombre)
                    .all()
                )
                return [
                    {
                        "id":       c.id,
                        "nombre":   c.nombre,
                        "codigo":   c.codigo,
                        "facultad": c.facultad.nombre,
                    }
                    for c in carreras
                ]
        except SQLAlchemyError:
            return []

    @staticmethod
    def contar_por_estado() -> dict:
        """
        Estadísticas rápidas para el panel de inicio.
        Retorna: {"Activo": 120, "Inactivo": 5, "Egresado": 18}
        """
        try:
            with get_session() as session:
                resultados = (
                    session.query(
                        Estudiante.estado,
                        func.count(Estudiante.id)
                    )
                    .group_by(Estudiante.estado)
                    .all()
                )
                return {estado: total for estado, total in resultados}
        except SQLAlchemyError:
            return {}
        
    @staticmethod
    def obtener_por_dni(dni: str) -> dict | None:
        with get_session() as session:
            est = session.query(Estudiante).filter(Estudiante.dni == dni).first()
            if not est:
                return None
            return {
                "id": est.id,
                "nombre_completo": est.nombre_completo,
                "dni": est.dni,
                "carrera": est.carrera,
                "estado": est.estado,
            }