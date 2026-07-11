
from dataclasses import dataclass, field

from services.taller_service import TallerService
from services.estudiante_service import EstudianteService
from utils.importar_inscritos import leer_plantilla_inscripcion


@dataclass
class FilaValidada:
    fila: int
    dni: str
    nombre: str = ""
    estudiante_id: int | None = None
    valido: bool = False
    motivo: str = ""


@dataclass
class ResultadoValidacion:
    filas: list[FilaValidada] = field(default_factory=list)
    cupo_disponible: int = 0

    @property
    def validas(self) -> list[FilaValidada]:
        return [f for f in self.filas if f.valido]

    @property
    def invalidas(self) -> list[FilaValidada]:
        return [f for f in self.filas if not f.valido]


@dataclass
class ResultadoProceso:
    exitosas: int = 0
    fallidas: int = 0
    detalle: list[tuple[str, str, str]] = field(default_factory=list)
    # cada item: (dni, nombre, mensaje)


class InscripcionMasivaService:

    @staticmethod
    def validar_archivo(taller_id: int, ruta_archivo: str) -> ResultadoValidacion:
        """
        Lee el Excel y valida cada fila contra las reglas de negocio:
          1. DNI con formato válido (8 dígitos numéricos)
          2. Sin DNIs duplicados dentro del mismo archivo
          3. El estudiante existe en el sistema
          4. El estudiante está en estado 'Activo'
          5. El estudiante no está ya inscrito (Activo) en el taller
          6. No se excede el cupo disponible del taller
        """
        registros = leer_plantilla_inscripcion(ruta_archivo)

        taller = TallerService.obtener_por_id(taller_id)
        if not taller:
            raise ValueError("Taller no encontrado.")
        cupo_disponible = taller["cupo_disponible"]

        inscritos_activos = {
            i["dni"] for i in TallerService.listar_inscritos(taller_id, solo_activos=False)
            if i["estado"] == "Activo"
        }

        resultado = ResultadoValidacion(cupo_disponible=cupo_disponible)
        dnis_vistos: dict[str, int] = {}
        cupos_usados = 0

        for reg in registros:
            fv = FilaValidada(fila=reg["fila"], dni=reg["dni"], nombre=reg["nombre_ref"])

            if not reg["dni"] or not reg["dni"].isdigit() or len(reg["dni"]) != 8:
                fv.motivo = "DNI inválido (debe tener 8 dígitos)"
                resultado.filas.append(fv)
                continue

            if reg["dni"] in dnis_vistos:
                fv.motivo = f"DNI duplicado en el archivo (fila {dnis_vistos[reg['dni']]})"
                resultado.filas.append(fv)
                continue
            dnis_vistos[reg["dni"]] = reg["fila"]

            estudiante = EstudianteService.obtener_por_dni(reg["dni"])
            if not estudiante:
                fv.motivo = "Estudiante no encontrado en el sistema"
                resultado.filas.append(fv)
                continue

            fv.nombre = estudiante.get("nombre_completo", fv.nombre)
            fv.estudiante_id = estudiante["id"]

            if estudiante.get("estado") != "Activo":
                fv.motivo = "Estudiante inactivo"
                resultado.filas.append(fv)
                continue

            if reg["dni"] in inscritos_activos:
                fv.motivo = "Ya inscrito en este taller"
                resultado.filas.append(fv)
                continue

            if cupos_usados >= cupo_disponible:
                fv.motivo = "Sin cupo disponible"
                resultado.filas.append(fv)
                continue

            fv.valido = True
            fv.motivo = "Listo para inscribir"
            cupos_usados += 1
            resultado.filas.append(fv)

        return resultado

    @staticmethod
    def procesar_inscripciones(
        taller_id: int, filas_validas: list[FilaValidada], usuario_id: int
    ) -> ResultadoProceso:
        """Ejecuta la inscripción de cada fila previamente validada."""
        resultado = ResultadoProceso()

        for fv in filas_validas:
            res = TallerService.inscribir(taller_id, fv.estudiante_id, usuario_id)
            if res.ok:
                resultado.exitosas += 1
                resultado.detalle.append((fv.dni, fv.nombre, "Inscrito correctamente"))
            else:
                resultado.fallidas += 1
                resultado.detalle.append((fv.dni, fv.nombre, res.mensaje))

        return resultado
