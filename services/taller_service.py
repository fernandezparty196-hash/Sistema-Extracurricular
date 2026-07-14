from datetime import date, datetime, timedelta
from typing   import Optional

from sqlalchemy import or_, func
from sqlalchemy.exc import SQLAlchemyError

from database.connection import get_session
from models import (
    Taller, Sesion, Inscripcion,
    CicloAcademico, Docente, Estudiante, Auditoria, Usuario
)


class ResultadoTaller:
    def __init__(self, ok: bool, mensaje: str, datos=None):
        self.ok      = ok
        self.mensaje = mensaje
        self.datos   = datos


class TallerService:

    # ══════════════════════════════════════════════════════════════
    # HU-06 · REGISTRAR TALLER
    # ══════════════════════════════════════════════════════════════
    @staticmethod
    def registrar(datos: dict, usuario_id: int) -> ResultadoTaller:
        """
        Crea un nuevo taller.

        PARÁMETRO datos (dict):
          {
            "codigo":             "TAL-2025-001",
            "nombre":             "Danzas Folklóricas",
            "ciclo_academico_id": 1,
            "docente_id":         2,
            "categoria":          "Arte y Cultura",
            "sede":               "Pabellón A - Sala 203",
            "cupo_maximo":        30,
            "umbral_asistencia":  80,    # % mínimo para ser apto
            "descripcion":        "...",
          }
        """
        obligatorios = ["codigo", "nombre", "ciclo_academico_id",
                        "docente_id", "cupo_maximo", "umbral_asistencia"]
        for campo in obligatorios:
            if not datos.get(campo):
                return ResultadoTaller(False,
                    f"El campo '{campo}' es obligatorio.")

        umbral = datos["umbral_asistencia"]
        if not (50 <= int(umbral) <= 100):
            return ResultadoTaller(False,
                "El umbral de asistencia debe estar entre 50 y 100.")

        try:
            with get_session() as session:
                # Código único
                if session.query(Taller).filter(
                    Taller.codigo == datos["codigo"].strip().upper()
                ).first():
                    return ResultadoTaller(False,
                        f"Ya existe un taller con código '{datos['codigo']}'.")

                nuevo = Taller(
                    codigo             = datos["codigo"].strip().upper(),
                    nombre             = datos["nombre"].strip(),
                    ciclo_academico_id = datos["ciclo_academico_id"],
                    docente_id         = datos["docente_id"],
                    categoria          = datos.get("categoria", "").strip() or None,
                    sede               = datos.get("sede", "").strip() or None,
                    cupo_maximo        = int(datos["cupo_maximo"]),
                    umbral_asistencia  = int(datos["umbral_asistencia"]),
                    descripcion        = datos.get("descripcion", "").strip() or None,
                    estado             = "Activo",
                    created_by         = usuario_id,
                )
                session.add(nuevo)
                session.flush()

                session.add(Auditoria(
                    usuario_id     = usuario_id,
                    tabla_afectada = "talleres",
                    accion         = "INSERT",
                    registro_id    = nuevo.id,
                    datos_nuevos   = {"codigo": nuevo.codigo,
                                      "nombre": nuevo.nombre},
                ))

            return ResultadoTaller(True,
                f"Taller '{datos['nombre']}' registrado correctamente.",
                datos={"id": nuevo.id})

        except SQLAlchemyError as e:
            return ResultadoTaller(False, f"Error al guardar: {e}")

    # ══════════════════════════════════════════════════════════════
    # EDITAR TALLER
    # ══════════════════════════════════════════════════════════════
    @staticmethod
    def editar(taller_id: int, datos: dict,
               usuario_id: int) -> ResultadoTaller:
        try:
            with get_session() as session:
                # Obtener taller
                t = session.get(Taller, taller_id)
                if not t:
                    return ResultadoTaller(False, "Taller no encontrado.")
 
                # Guardar valores anteriores para auditoría
                antes = {
                    "nombre": t.nombre,
                    "umbral": t.umbral_asistencia,
                    "estado": t.estado
                }
 
                # Campos que se pueden editar
                campos = [
                    "nombre", "docente_id", "categoria", "sede",
                    "cupo_maximo", "umbral_asistencia", "descripcion"
                ]
                
                # Aplicar cambios
                for c in campos:
                    if c in datos:
                        val = datos[c]
                        if isinstance(val, str):
                            val = val.strip() or None
                        setattr(t, c, val)
                
                # Actualizar timestamp
                t.updated_at = datetime.now()
 
                # Registrar en auditoría
                session.add(Auditoria(
                    usuario_id       = usuario_id,
                    tabla_afectada   = "talleres",
                    accion           = "UPDATE",
                    registro_id      = taller_id,
                    datos_anteriores = antes,
                    datos_nuevos     = {k: datos[k] for k in datos
                                        if k in campos},
                ))                
                session.commit()
 
            return ResultadoTaller(True, "Taller actualizado correctamente.")
            
        except SQLAlchemyError as e:
            return ResultadoTaller(False, f"Error al actualizar: {e}")
 

    # ══════════════════════════════════════════════════════════════
    # CAMBIAR ESTADO
    # ══════════════════════════════════════════════════════════════
    @staticmethod
    def cambiar_estado(taller_id: int, nuevo_estado: str,
                       usuario_id: int) -> ResultadoTaller:
        estados = ("Activo", "Suspendido", "Finalizado")
        if nuevo_estado not in estados:
            return ResultadoTaller(False,
                f"Estado inválido. Use: {estados}")
        try:
            with get_session() as session:
                t = session.get(Taller, taller_id)
                if not t:
                    return ResultadoTaller(False, "Taller no encontrado.")
                anterior   = t.estado
                t.estado   = nuevo_estado
                t.updated_at = datetime.now()
                session.add(Auditoria(
                    usuario_id       = usuario_id,
                    tabla_afectada   = "talleres",
                    accion           = "UPDATE",
                    registro_id      = taller_id,
                    datos_anteriores = {"estado": anterior},
                    datos_nuevos     = {"estado": nuevo_estado},
                ))
            return ResultadoTaller(True,
                f"Estado cambiado a '{nuevo_estado}'.")
        except SQLAlchemyError as e:
            return ResultadoTaller(False, f"Error: {e}")

    # ══════════════════════════════════════════════════════════════
    # BUSCAR TALLERES (tabla principal)
    # ══════════════════════════════════════════════════════════════
    @staticmethod
    def buscar(texto: str = "", ciclo_id: int = None,
               docente_id: int = None, estado: str = None,
               limite: int = 200) -> list[dict]:
        """
        Búsqueda combinada. Retorna dicts listos para QTableWidget.
        """
        try:
            with get_session() as session:
                q = (session.query(Taller)
                     .join(CicloAcademico)
                     .join(Docente))

                if texto and texto.strip():
                    t = f"%{texto.strip()}%"
                    q = q.filter(or_(
                        Taller.nombre.ilike(t),
                        Taller.codigo.ilike(t),
                        Taller.categoria.ilike(t),
                    ))
                if ciclo_id:
                    q = q.filter(Taller.ciclo_academico_id == ciclo_id)
                if docente_id:
                    q = q.filter(Taller.docente_id == docente_id)
                if estado:
                    q = q.filter(Taller.estado == estado)

                talleres = (q.order_by(Taller.nombre)
                             .limit(limite).all())

                return [
                    {
                        "id":               t.id,
                        "codigo":           t.codigo,
                        "nombre":           t.nombre,
                        "ciclo":            t.ciclo_academico.nombre,
                        "ciclo_id":         t.ciclo_academico_id,
                        "docente":          t.docente.nombre_completo,
                        "docente_id":       t.docente_id,
                        "categoria":        t.categoria or "",
                        "sede":             t.sede or "",
                        "cupo_maximo":      t.cupo_maximo,
                        "total_inscritos":  t.total_inscritos,
                        "cupo_disponible":  t.cupo_disponible,
                        "umbral":           t.umbral_asistencia,
                        "total_sesiones":   t.total_sesiones,
                        "sesiones_realizadas": t.sesiones_realizadas,
                        "estado":           t.estado,
                    }
                    for t in talleres
                ]
        except SQLAlchemyError:
            return []

    # ══════════════════════════════════════════════════════════════
    # OBTENER POR ID
    # ══════════════════════════════════════════════════════════════
    @staticmethod
    def obtener_por_id(taller_id: int) -> Optional[dict]:
        try:
            with get_session() as session:
                t = session.get(Taller, taller_id)
                if not t:
                    return None
                return {
                    "id":               t.id,
                    "codigo":           t.codigo,
                    "nombre":           t.nombre,
                    "ciclo_id":         t.ciclo_academico_id,
                    "ciclo":            t.ciclo_academico.nombre,
                    "docente_id":       t.docente_id,
                    "docente":          t.docente.nombre_completo,
                    "categoria":        t.categoria or "",
                    "sede":             t.sede or "",
                    "cupo_maximo":      t.cupo_maximo,
                    "cupo_disponible":  t.cupo_disponible,
                    "umbral":           t.umbral_asistencia,
                    "descripcion":      t.descripcion or "",
                    "estado":           t.estado,
                    "total_inscritos":  t.total_inscritos,
                    "total_sesiones":   t.total_sesiones,
                    "sesiones_realizadas": t.sesiones_realizadas,
                }
        except SQLAlchemyError:
            return None

    # ══════════════════════════════════════════════════════════════
    # HU-07 · GENERAR SESIONES AUTOMÁTICAMENTE
    # ══════════════════════════════════════════════════════════════
    @staticmethod
    def generar_sesiones(taller_id: int,
                         fecha_inicio: date,
                         fecha_fin:    date,
                         dias_semana:  list[int],   # [0=Lun .. 6=Dom]
                         hora_inicio:  str,          # "HH:MM"
                         hora_fin:     str,          # "HH:MM"
                         sede:         str,          # opcional, para actualizar sede del taller
                         usuario_id:   int) -> ResultadoTaller:
        """
        Genera todas las sesiones de un taller entre fecha_inicio
        y fecha_fin, en los días de la semana indicados.

        EJEMPLO:
          dias_semana = [1, 3]  → Martes y Jueves
          hora_inicio = "14:00"
          hora_fin    = "16:00"

        El sistema calcula automáticamente cuántas sesiones habrá
        y las numera del 1 en adelante.
        """
        if not dias_semana:
            return ResultadoTaller(False,
                "Selecciona al menos un día de la semana.")
        if fecha_inicio >= fecha_fin:
            return ResultadoTaller(False,
                "La fecha de inicio debe ser anterior a la de fin.")

        # Parsear horas
        try:
            from datetime import time as dtime
            hi = dtime(*map(int, hora_inicio.split(":")))
            hf = dtime(*map(int, hora_fin.split(":")))
        except ValueError:
            return ResultadoTaller(False,
                "Formato de hora inválido. Use HH:MM.")

        if hi >= hf:
            return ResultadoTaller(False,
                "La hora de fin debe ser posterior a la de inicio.")

        try:
            with get_session() as session:
                taller = session.get(Taller, taller_id)
                if not taller:
                    return ResultadoTaller(False, "Taller no encontrado.")

                # Eliminar sesiones previas sin asistencia registrada
                sesiones_con_asistencia = {
                    s.id for s in taller.sesiones
                    if s.asistencias
                }
                for s in list(taller.sesiones):
                    if s.id not in sesiones_con_asistencia:
                        session.delete(s)
                session.flush()

                # Generar nuevas fechas
                fechas = []
                cursor = fecha_inicio
                while cursor <= fecha_fin:
                    if cursor.weekday() in dias_semana:
                        fechas.append(cursor)
                    cursor += timedelta(days=1)

                if not fechas:
                    return ResultadoTaller(False,
                        "No hay fechas válidas en el rango con los días seleccionados.")

                for num, fecha in enumerate(fechas, 1):
                    session.add(Sesion(
                        taller_id     = taller_id,
                        numero_sesion = num,
                        fecha         = fecha,
                        hora_inicio   = hi,
                        hora_fin      = hf,
                        estado        = "Programada",
                    ))

            return ResultadoTaller(True,
                f"Se generaron {len(fechas)} sesiones correctamente.",
                datos={"total": len(fechas)})

        except SQLAlchemyError as e:
            return ResultadoTaller(False, f"Error al generar sesiones: {e}")

    # ══════════════════════════════════════════════════════════════
    # HU-08 · INSCRIBIR ESTUDIANTE
    # ══════════════════════════════════════════════════════════════
    @staticmethod
    def inscribir(taller_id: int, estudiante_id: int,
                  usuario_id: int) -> ResultadoTaller:
        """
        Inscribe un estudiante en un taller.
        Validaciones:
          - Taller activo y con cupo disponible
          - Estudiante activo
          - No inscrito ya en el mismo taller
        """
        try:
            with get_session() as session:
                taller = session.get(Taller, taller_id)
                if not taller:
                    return ResultadoTaller(False, "Taller no encontrado.")
                if taller.estado != "Activo":
                    return ResultadoTaller(False,
                        f"El taller está {taller.estado}. No acepta inscripciones.")
                if taller.cupo_disponible <= 0:
                    return ResultadoTaller(False,
                        f"El taller no tiene cupo disponible "
                        f"({taller.cupo_maximo}/{taller.cupo_maximo} inscritos).")

                estudiante = session.get(Estudiante, estudiante_id)
                if not estudiante:
                    return ResultadoTaller(False, "Estudiante no encontrado.")
                if estudiante.estado != "Activo":
                    return ResultadoTaller(False,
                        f"El estudiante está {estudiante.estado}.")

                # ¿Ya inscrito?
                ya = session.query(Inscripcion).filter(
                    Inscripcion.taller_id    == taller_id,
                    Inscripcion.estudiante_id == estudiante_id,
                ).first()

                if ya:
                    if ya.estado == "Activo":
                        return ResultadoTaller(False,
                            "El estudiante ya está inscrito en este taller.")
                    else:
                        # Re-activar inscripción retirada
                        ya.estado     = "Activo"
                        ya.created_by = usuario_id
                        return ResultadoTaller(True,
                            f"Inscripción de '{estudiante.nombre_completo}' "
                            f"reactivada correctamente.")

                session.add(Inscripcion(
                    taller_id     = taller_id,
                    estudiante_id = estudiante_id,
                    estado        = "Activo",
                    created_by    = usuario_id,
                ))

            return ResultadoTaller(True,
                f"'{estudiante.nombre_completo}' inscrito correctamente.")
        except SQLAlchemyError as e:
            return ResultadoTaller(False, f"Error al inscribir: {e}")

    # ══════════════════════════════════════════════════════════════
    # RETIRAR ESTUDIANTE
    # ══════════════════════════════════════════════════════════════
    @staticmethod
    def retirar(taller_id: int, estudiante_id: int,
                usuario_id: int) -> ResultadoTaller:
        """Cambia la inscripción a 'Retirado'. No borra historial."""
        try:
            with get_session() as session:
                insc = session.query(Inscripcion).filter(
                    Inscripcion.taller_id    == taller_id,
                    Inscripcion.estudiante_id == estudiante_id,
                    Inscripcion.estado        == "Activo",
                ).first()

                if not insc:
                    return ResultadoTaller(False,
                        "Inscripción activa no encontrada.")

                insc.estado = "Retirado"
                session.add(Auditoria(
                    usuario_id       = usuario_id,
                    tabla_afectada   = "inscripciones",
                    accion           = "UPDATE",
                    registro_id      = insc.id,
                    datos_anteriores = {"estado": "Activo"},
                    datos_nuevos     = {"estado": "Retirado"},
                ))

            return ResultadoTaller(True, "Estudiante retirado correctamente.")
        except SQLAlchemyError as e:
            return ResultadoTaller(False, f"Error al retirar: {e}")

    # ══════════════════════════════════════════════════════════════
    # LISTAR INSCRITOS DE UN TALLER
    # ══════════════════════════════════════════════════════════════
    @staticmethod
    def listar_inscritos(taller_id: int,
                         solo_activos: bool = True) -> list[dict]:
        """Lista de estudiantes inscritos para el diálogo."""
        try:
            with get_session() as session:
                q = (session.query(Inscripcion)
                     .filter(Inscripcion.taller_id == taller_id)
                     .join(Estudiante))
                if solo_activos:
                    q = q.filter(Inscripcion.estado == "Activo")

                return [
                    {
                        "taller_id":       i.taller_id,
                        "inscripcion_id":  i.id,
                        "estudiante_id":   i.estudiante_id,
                        "nombre_completo": i.estudiante.nombre_completo,
                        "dni":             i.estudiante.dni,
                        "codigo":          i.estudiante.codigo_estudiantil,
                        "carrera":         i.estudiante.carrera.nombre,
                        "ciclo":           i.estudiante.ciclo_actual,
                        "telefono":        i.estudiante.telefono,
                        "estado":          i.estado,
                        "fecha":           str(i.fecha_inscripcion),
                    }
                    for i in q.order_by(
                        Estudiante.apellidos, Estudiante.nombres,
                    ).all()
                ]
        except SQLAlchemyError:
            return []

    # ══════════════════════════════════════════════════════════════
    # LISTAR SESIONES DE UN TALLER
    # ══════════════════════════════════════════════════════════════
    # ══════════════════════════════════════════════════════════════
    @staticmethod
    def listar_sesiones(taller_id: int) -> list[dict]:
        """
        Retorna todas las sesiones de un taller.
        """
        try:
            with get_session() as session:
                taller = session.get(Taller, taller_id)

                if not taller:
                    return []

                sesiones = sorted(
                    taller.sesiones,
                    key=lambda s: (s.numero_sesion, s.fecha)
                )

                resultado = []

                for s in sesiones:
                    hora_inicio = (
                        s.hora_inicio.strftime("%H:%M")
                        if s.hora_inicio else "--:--"
                    )

                    hora_fin = (
                        s.hora_fin.strftime("%H:%M")
                        if s.hora_fin else "--:--"
                    )

                    resultado.append({
                        "id": s.id,
                        "numero": s.numero_sesion,
                        "fecha": s.fecha.strftime("%d/%m/%Y"),
                        "hora": f"{hora_inicio} - {hora_fin}",   # ← lo usa el Panel
                        "hora_inicio": hora_inicio,
                        "hora_fin": hora_fin,
                        "estado": s.estado,
                        "observaciones": s.observaciones or "",
                        "asistencias": len(s.asistencias),
                    })

                return resultado

        except SQLAlchemyError as e:
            print(f"Error al listar sesiones: {e}")
            return []

    # ══════════════════════════════════════════════════════════════
    # DATOS AUXILIARES PARA COMBOS
    # ══════════════════════════════════════════════════════════════
    @staticmethod
    def listar_ciclos() -> list[dict]:
        try:
            with get_session() as session:
                return [
                    {"id": c.id, "nombre": c.nombre, "activo": c.activo}
                    for c in session.query(CicloAcademico)
                               .order_by(CicloAcademico.fecha_inicio.desc())
                               .all()
                ]
        except SQLAlchemyError:
            return []

    @staticmethod
    def listar_docentes() -> list[dict]:
        try:
            with get_session() as session:
                return [
                    {"id": d.id, "nombre": d.nombre_completo,
                     "especialidad": d.especialidad or ""}
                    for d in session.query(Docente)
                               .filter(Docente.activo == True)
                               .order_by(Docente.apellidos)
                               .all()
                ]
        except SQLAlchemyError:
            return []

    # Filtro para listar talleres por rol

    @staticmethod
    def listar_para_asistencia(usuario_id: int, rol_nombre: str, 
                            estado: str = "Activo") -> list[dict]:
        """
        RETORNA:
            list[dict] con talleres disponibles para registrar asistencia
        """
        try:
            with get_session() as session:
                query = session.query(Taller)
                
                # Filtro por estado (siempre aplica)
                if estado:
                    query = query.filter(Taller.estado == estado)
                
                # Filtro por rol
                if rol_nombre == "Docente":
                    # Necesito obtener el docente asociado al usuario
                    usuario = session.get(Usuario, usuario_id)
                    if not usuario or not usuario.docente:
                        return []  # Usuario docente sin relación docente → sin acceso
                    
                    # Filtrar solo los talleres de este docente
                    query = query.filter(Taller.docente_id == usuario.docente.id)
                # Si es Administrador, no hay filtro adicional
                
                talleres = query.order_by(Taller.nombre).all()
                
                return [
                    {
                        "id": t.id,
                        "codigo": t.codigo,
                        "nombre": t.nombre,
                        "docente": t.docente.nombre_completo if t.docente else "N/A",
                        "ciclo": t.ciclo_academico.nombre if t.ciclo_academico else "N/A",
                        "cupo_maximo": t.cupo_maximo,
                        "total_inscritos": t.total_inscritos,
                        "umbral": t.umbral_asistencia,
                        "total_sesiones": t.total_sesiones,
                        "sesiones_realizadas": t.sesiones_realizadas,
                        "estado": t.estado,
                    }
                    for t in talleres
                ]

        
        except SQLAlchemyError:
            return []
            
    @staticmethod
    def listar_por_rol(usuario_id: int, rol_nombre: str,
                    texto: str = "", ciclo_id: int = None,
                    estado: str = None) -> list[dict]:
        """
        Devuelve talleres filtrados según el rol:
        - Administrador: todos
        - Docente: solo los suyos
        """
        try:
            with get_session() as session:
                q = session.query(Taller).join(CicloAcademico).join(Docente)

                if texto and texto.strip():
                    t = f"%{texto.strip()}%"
                    q = q.filter(or_(
                        Taller.nombre.ilike(t),
                        Taller.codigo.ilike(t),
                    ))
                if ciclo_id:
                    q = q.filter(Taller.ciclo_academico_id == ciclo_id)
                if estado:
                    q = q.filter(Taller.estado == estado)

                if rol_nombre == "Docente":
                    usuario = session.get(Usuario, usuario_id)
                    if not usuario or not usuario.docente:
                        return []
                    q = q.filter(Taller.docente_id == usuario.docente.id)

                talleres = q.order_by(Taller.nombre).all()
                return [
                    {
                        "id": t.id,
                        "codigo": t.codigo,
                        "nombre": t.nombre,
                        "docente": t.docente.nombre_completo,
                        "ciclo": t.ciclo_academico.nombre,
                        "estado": t.estado,
                        "umbral": t.umbral_asistencia,
                        "total_inscritos": t.total_inscritos,
                        "total_sesiones": t.total_sesiones,
                    }
                    for t in talleres
                ]
        except SQLAlchemyError:
            return []

    @staticmethod
    def listar_activos() -> list[dict]:
        try:
            with get_session() as session:

                talleres = (session.query(Taller).filter(Taller.estado == "Activo").order_by(Taller.nombre).all())
                return [
                    {
                        "id": t.id,
                        "codigo": t.codigo,
                        "nombre": t.nombre,
                        "docente": t.docente.nombre_completo if t.docente else "",
                    }
                    for t in talleres
                ]

        except SQLAlchemyError:
            return []