const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell,
  WidthType, ShadingType, AlignmentType, BorderStyle, TableOfContents, PageBreak,
  LevelFormat, convertInchesToTwip, VerticalAlign
} = require("docx");

// ── Paleta institucional ──────────────────────────────────────────────
const AZUL = "1E3A5F";
const TEAL = "0E7C7B";
const GRIS = "F2F4F5";
const GRIS_TXT = "555555";
const ROJO = "991B1B";
const CONTENT_WIDTH = 9026; // A4 (11906) - márgenes 1440*2

// ── Helpers ────────────────────────────────────────────────────────────
function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 360, after: 160 },
    border: { bottom: { color: TEAL, space: 4, style: BorderStyle.SINGLE, size: 6 } },
    children: [new TextRun({ text, color: AZUL, bold: true })]
  });
}
function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 260, after: 120 },
    children: [new TextRun({ text, color: AZUL, bold: true })]
  });
}
function h3(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_3,
    spacing: { before: 200, after: 100 },
    children: [new TextRun({ text, color: TEAL, bold: true, italics: true })]
  });
}
function p(text, opts = {}) {
  return new Paragraph({
    spacing: { after: 160, line: 276 },
    alignment: AlignmentType.JUSTIFIED,
    children: [new TextRun({ text, ...opts })]
  });
}
function pRich(runs, opts = {}) {
  return new Paragraph({ spacing: { after: 160, line: 276 }, alignment: AlignmentType.JUSTIFIED, ...opts, children: runs });
}
function bullet(text, level = 0, opts = {}) {
  return new Paragraph({
    numbering: { reference: "bullets", level },
    spacing: { after: 90 },
    children: [new TextRun({ text, ...opts })]
  });
}
function numbered(text, level = 0) {
  return new Paragraph({
    numbering: { reference: "numbered", level },
    spacing: { after: 90 },
    children: [new TextRun({ text })]
  });
}
function cell(text, { header = false, width, shade = null, align = AlignmentType.LEFT, color = "000000", size = 19 } = {}) {
  return new TableCell({
    width: { size: width, type: WidthType.DXA },
    shading: shade ? { type: ShadingType.CLEAR, fill: shade } : undefined,
    verticalAlign: VerticalAlign.CENTER,
    margins: { top: 80, bottom: 80, left: 100, right: 100 },
    children: [new Paragraph({
      alignment: align,
      children: [new TextRun({ text, bold: header, color: header ? "FFFFFF" : color, size })]
    })]
  });
}
function table(headers, rows, widths) {
  return new Table({
    width: { size: CONTENT_WIDTH, type: WidthType.DXA },
    columnWidths: widths,
    rows: [
      new TableRow({
        tableHeader: true,
        children: headers.map((htxt, i) => cell(htxt, { header: true, width: widths[i], shade: AZUL, size: 19 }))
      }),
      ...rows.map((r, ri) => new TableRow({
        children: r.map((c, i) => cell(c, { width: widths[i], shade: ri % 2 === 0 ? "FFFFFF" : GRIS }))
      }))
    ]
  });
}
function nota(text) {
  return new Paragraph({
    spacing: { before: 80, after: 200 },
    shading: { type: ShadingType.CLEAR, fill: "FEF3C7" },
    border: { left: { color: "F59E0B", space: 6, style: BorderStyle.SINGLE, size: 18 } },
    indent: { left: 100 },
    children: [new TextRun({ text: "Nota del proyecto: ", bold: true, size: 19, color: "92400E" }),
      new TextRun({ text, italics: true, size: 19, color: "92400E" })]
  });
}

// ── Documento ────────────────────────────────────────────────────────
const doc = new Document({
  numbering: {
    config: [
      { reference: "bullets", levels: [
        { level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 460, hanging: 260 } } } },
        { level: 1, format: LevelFormat.BULLET, text: "◦", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 820, hanging: 260 } } } }
      ]},
      { reference: "numbered", levels: [
        { level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 460, hanging: 260 } } } }
      ]}
    ]
  },
  styles: {
    default: {
      document: { run: { font: "Calibri", size: 21 } }
    },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 30, bold: true, color: AZUL, font: "Calibri" } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 25, bold: true, color: AZUL, font: "Calibri" } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 22, bold: true, italics: true, color: TEAL, font: "Calibri" } }
    ]
  },
  sections: [
    // ══════════════════════ PORTADA ══════════════════════
    {
      properties: { page: { margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } } },
      children: [
        new Paragraph({ spacing: { before: 1400 }, alignment: AlignmentType.CENTER,
          children: [new TextRun({ text: "UNIVERSIDAD ANDRÉS BELLO", bold: true, size: 24, color: GRIS_TXT })] }),
        new Paragraph({ alignment: AlignmentType.CENTER,
          children: [new TextRun({ text: "Dirección General de Bienestar Universitario", size: 20, color: GRIS_TXT })] }),
        new Paragraph({ spacing: { before: 900, after: 200 }, alignment: AlignmentType.CENTER,
          children: [new TextRun({ text: "INFORME DE INGENIERÍA DE REQUERIMIENTOS", bold: true, size: 40, color: AZUL })] }),
        new Paragraph({ spacing: { after: 700 }, alignment: AlignmentType.CENTER,
          children: [new TextRun({ text: "Sistema de Gestión de Talleres Extracurriculares (Sistema de Talleres UNAB)", size: 26, color: TEAL, italics: true })] }),
        new Paragraph({ spacing: { before: 700 }, alignment: AlignmentType.CENTER,
          children: [new TextRun({ text: "Verificación, técnicas y herramientas de documentación, modelado,", size: 20 })] }),
        new Paragraph({ alignment: AlignmentType.CENTER,
          children: [new TextRun({ text: "validación y gestión de requerimientos", size: 20 })] }),
        new Paragraph({ spacing: { before: 1600 }, alignment: AlignmentType.CENTER,
          children: [new TextRun({ text: "Carolay", size: 20, bold: true })] }),
        new Paragraph({ alignment: AlignmentType.CENTER,
          children: [new TextRun({ text: "Módulo: Ingeniería de Software / Requisitos", size: 18, color: GRIS_TXT })] }),
        new Paragraph({ spacing: { before: 1600 }, alignment: AlignmentType.CENTER,
          children: [new TextRun({ text: "2026", size: 18, color: GRIS_TXT })] }),
        new Paragraph({ children: [new PageBreak()] }),
      ]
    },
    // ══════════════════════ TOC ══════════════════════
    {
      properties: { page: { margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } } },
      children: [
        h1("Tabla de Contenido"),
        new TableOfContents("Tabla de contenido", { hyperlink: true, headingStyleRange: "1-3" }),
        new Paragraph({ children: [new PageBreak()] }),
      ]
    },
    // ══════════════════════ CUERPO ══════════════════════
    {
      properties: { page: { margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } } },
      children: [

      // ───────────────────── 1. INTRODUCCIÓN ─────────────────────
      h1("1. Introducción y contexto del proyecto"),
      p("El Sistema de Talleres UNAB es una aplicación de escritorio construida con PySide6, SQLAlchemy y MySQL, bajo arquitectura MVC estricta, destinada a la Dirección de Bienestar Universitario para la gestión de talleres extracurriculares. El sistema automatiza procesos que hoy se manejan de forma manual o dispersa en hojas de cálculo: matrícula de estudiantes, programación de sesiones, registro de asistencia, generación de listas de aptos para certificación, control de bienes patrimoniales y auditoría de operaciones."),
      p("La especificación de requerimientos vigente (documento base de este informe) define 43 requerimientos funcionales (RF-01 a RF-43) organizados en nueve módulos: Autenticación, Estudiantes, Talleres, Asistencia, Aptos/Certificación, Importación Excel, Gestión de Bienes, Reportes y Sistema. El sistema reconoce tres roles con permisos diferenciados a nivel de interfaz y de capa de servicio: Administrador, Docente y Operador."),
      table(
        ["Módulo", "RF cubiertos", "Propósito"],
        [
          ["Autenticación", "RF-01 a RF-05", "Acceso, roles y control de sesión"],
          ["Estudiantes", "RF-06 a RF-10", "Matrícula, búsqueda, historial y estado académico"],
          ["Talleres", "RF-11 a RF-15", "Creación, programación de sesiones e inscripción"],
          ["Asistencia", "RF-16 a RF-20", "Registro por sesión, porcentaje, alertas y congelamiento"],
          ["Aptos / Certificación", "RF-21 a RF-24", "Umbral, vista previa y emisión de certificados"],
          ["Importación Excel", "RF-25 a RF-27", "Carga masiva de estudiantes y docentes"],
          ["Gestión de Bienes", "RF-28 a RF-31", "Inventario patrimonial y alertas de devolución"],
          ["Reportes", "RF-32 a RF-37", "Reportes filtrables y exportación"],
          ["Sistema", "RF-38 a RF-43", "KPIs, logging, auditoría, respaldos y tema"],
        ],
        [2400, 1700, 4926]
      ),
      p("Este informe aplica al Sistema de Talleres UNAB las cuatro grandes actividades de la ingeniería de requerimientos posteriores a la elicitación: verificación, documentación con técnicas y herramientas, modelado, validación y gestión (trazabilidad, línea base, control de cambios y versionamiento). Se usan como evidencia ejemplos reales tomados de la especificación (RF-01 a RF-43) y del desarrollo del sistema, incluyendo inconsistencias detectadas durante la construcción de los servicios asistencia_service.py y sesion_service.py."),

      // ───────────────────── 2. VERIFICACIÓN ─────────────────────
      h1("2. Verificación de requerimientos"),
      h2("2.1 Concepto y propósito"),
      p("La verificación responde a la pregunta \u201c¿el documento de requerimientos está bien construido?\u201d. Es un control de calidad interno sobre la especificación misma —su redacción, estructura y consistencia— y se realiza antes de avanzar al diseño o a la implementación. Se diferencia de la validación (sección 5) en que esta última responde \u201c¿son estos los requerimientos correctos para el negocio?\u201d, contrastando el documento contra las necesidades reales de Bienestar Universitario."),
      h2("2.2 Criterios de calidad aplicados (checklist)"),
      p("Para verificar cada RF del Sistema de Talleres UNAB se aplicó una lista de verificación basada en IEEE 830 / ISO·IEC·IEEE 29148:"),
      table(
        ["Criterio", "Pregunta de verificación", "Ejemplo en el sistema"],
        [
          ["Correcto", "¿Describe una necesidad real de Bienestar?", "RF-20 refleja una regla real: el docente no puede alterar asistencia retroactivamente"],
          ["No ambiguo", "¿Admite una sola interpretación?", "RF-19 es ambiguo: mezcla sujeto y acción (ver 2.3)"],
          ["Completo", "¿Define entradas, salidas y reglas de negocio?", "RF-16 sí especifica los tres estados válidos (P/A/J)"],
          ["Consistente", "¿No contradice otro RF?", "RF-15 define estados de Taller (Activo/Suspendido/Finalizado) sin solaparse con los de Sesión (RF-20) ni con los de Bien (RF-30)"],
          ["Verificable", "¿Se puede diseñar una prueba de aceptación?", "RF-05 es verificable: 60 minutos de inactividad es un valor medible"],
          ["Factible", "¿Es implementable con la arquitectura MVC/PySide6/MySQL?", "RF-40 (auditoría con IP) requiere revisar si aplica en una app de escritorio en red LAN (ver 2.3)"],
          ["Trazable", "¿Tiene un identificador único referenciable?", "Todos los RF usan el esquema RF-XX, base de la matriz de trazabilidad (sección 6.1)"],
          ["Priorizable", "¿Se puede clasificar por criticidad?", "RF-16 a RF-20 (asistencia) son núcleo del sistema; RF-42 (tema día/noche) es de menor prioridad"],
        ],
        [1500, 3300, 4226]
      ),
      h2("2.3 Hallazgos de verificación sobre la especificación actual"),
      p("Aplicar el checklist anterior sobre el documento de requerimientos entregado permitió detectar observaciones concretas que deben corregirse antes de congelar la línea base (sección 6.2):"),
      bullet("RF-19 (\u201cRegistrar observaciones de justificación de inasistencias\u201d): la descripción \u201cEl sistema el operador de Bienestar registrará la observación de la justificación\u201d mezcla el sujeto sistema con el actor operador y no especifica si la observación es obligatoria. Redacción sugerida: \u201cEl sistema debe permitir al Operador de Bienestar registrar una observación de justificación para una inasistencia marcada como Justificado (J); la observación es obligatoria y no puede quedar vacía.\u201d Esta corrección además queda alineada con la validación ya implementada en AsistenciaService.registrar(), donde el estado J exige observación no vacía."),
      bullet("RF-29 (\u201cRegistrar devolución y estado de conversación\u201d): probable error de digitación; el término correcto según el resto del módulo de Bienes es conservación (estado físico del bien al momento de la devolución: Bueno/Regular/Malo/Inservible)."),
      bullet("RF-20: la especificación es correcta y verificable, pero deja implícito quién ejecuta la autorización y cómo se registra. Durante la implementación esto generó un defecto real: el mecanismo de autorización puntual del docente (evento en auditoria) inicialmente no distinguía \u201cautorizar\u201d de \u201crevocar\u201d porque la columna accion solo admite INSERT/UPDATE/DELETE, y el filtro de consulta usaba una comparación de Python (in) que no es una condición SQL válida. El requerimiento no era incorrecto, pero su falta de detalle sobre el mecanismo de persistencia permitió una implementación ambigua. Ver sección 5.6 para el análisis como inconsistencia y su corrección."),
      bullet("RF-40 (\u201cAuditoría completa: quién, cuándo, qué\u201d) menciona registrar IP; al tratarse de una aplicación de escritorio en red institucional (no web), debe verificarse la factibilidad: se recomienda registrar IP de host o equipo desde configuración local en vez de IP de cliente HTTP, o remover el campo si no aporta valor forense en este contexto."),
      bullet("RF-13 (\u201cProgramar sesiones\u201d) no especifica qué ocurre si la fecha de inicio cae en un día no hábil, ni el comportamiento si se cambia la frecuencia después de generado el calendario; se recomienda agregar una regla de negocio explícita o remitir a un RF complementario."),
      nota("Estos hallazgos no invalidan el documento: son exactamente el tipo de defectos que la verificación está diseñada para detectar antes de invertir esfuerzo de desarrollo en una interpretación equivocada."),
      h2("2.4 Técnicas de verificación utilizadas"),
      bullet("Revisión por checklist: aplicación sistemática de la tabla de la sección 2.2 a los 43 RF."),
      bullet("Lectura cruzada (peer review): revisión de la tabla de requerimientos por una persona distinta a quien la redactó, buscando ambigüedad y contradicciones entre módulos (p. ej. estados de Taller vs. Sesión vs. Bien)."),
      bullet("Trazabilidad temprana: para cada RF se identificó a qué componente de código correspondería (service/UI), lo que expone requerimientos huérfanos o duplicados antes de programar."),
      bullet("Prototipado de bajo costo: para RF de interfaz (RF-07 buscar y filtrar, RF-23 vista previa de aptos) se verificó factibilidad con un boceto de la pantalla antes de comprometerse a un diseño de tabla o formulario."),

      // ───────────────────── 3. TÉCNICAS Y HERRAMIENTAS ─────────────────────
      h1("3. Técnicas y herramientas para documentar los requerimientos"),
      h2("3.1 Técnicas de elicitación y documentación"),
      bullet("Entrevistas estructuradas con el personal de Bienestar Universitario (coordinador de talleres, docentes, operador administrativo) para levantar el flujo actual de matrícula, asistencia en papel/Excel y emisión de certificados."),
      bullet("Observación de procesos (contextual inquiry): acompañamiento del registro manual de asistencia y del cálculo de aptos en Excel, origen directo de RF-16 a RF-21."),
      bullet("Análisis de documentos existentes: plantillas Excel de matrícula y de inventario de bienes usadas hoy por Bienestar, que definieron los campos de RF-06 y RF-28."),
      bullet("Tormenta de requisitos por módulo (workshop): sesiones cortas por módulo (Asistencia, Bienes, Reportes) para no mezclar reglas de negocio de dominios distintos."),
      bullet("Especificación en tabla estilo IEEE 830: cada requerimiento documentado con ID, Nombre y Descripción, tal como aparece en el documento base de este informe — formato liviano, legible por no técnicos y fácil de referenciar (RF-XX) desde código, pruebas y actas."),
      h2("3.2 Herramientas utilizadas"),
      table(
        ["Herramienta", "Uso en el proyecto"],
        [
          ["Word / Google Docs", "Redacción y versionado colaborativo de la tabla de requerimientos (RF-01 a RF-43)"],
          ["Excel", "Plantillas de referencia para RF-06 (matrícula), RF-25/26 (importación) y RF-28 (bienes); también insumo para diseñar utils/importar_excel.py"],
          ["Git", "Control de versiones del documento de requerimientos y del código; cada commit puede referenciar el RF-XX que implementa"],
          ["Tablero Kanban (Trello/Jira/Azure DevOps)", "Seguimiento de cada RF como tarjeta, con estado Pendiente / En desarrollo / En validación / Aceptado"],
          ["Diagramas (draw.io / Lucidchart)", "Modelado de casos de uso, clases y diagramas de estado (sección 4)"],
          ["Prototipos de baja fidelidad", "Bocetos de paneles PySide6 (p. ej. panel_asistencia.py) antes de programar la UI, para validar RF de interfaz con el usuario"],
          ["Repositorio de auditoría (tabla auditoria)", "Fuente de verdad técnica que respalda RF-39 y RF-40; también sirve como bitácora de decisiones de autorización (RF-20)"],
        ],
        [3200, 5826]
      ),
      h2("3.3 Formato de especificación adoptado"),
      p("El sistema documenta cada requerimiento con tres campos mínimos —ID, Nombre y Descripción— agrupados por módulo. Se recomienda extender este formato, sin cambiar su espíritu liviano, agregando para los RF críticos (Asistencia, Bienes, Auditoría) los campos Criterio de aceptación, Prioridad y Estado, que son los que efectivamente se usan en las secciones 5 y 6 de este informe."),

      // ───────────────────── 4. MODELADO ─────────────────────
      h1("4. Modelado para la especificación de requerimientos"),
      h2("4.1 Actores del sistema"),
      table(
        ["Actor", "Descripción", "RF principales"],
        [
          ["Administrador", "Control total: usuarios, roles, talleres, congelamiento/autorización de asistencia, auditoría", "RF-02, RF-12, RF-20, RF-40"],
          ["Docente", "Registra asistencia de sus talleres; puede editar sesiones congeladas solo con autorización puntual", "RF-16, RF-17, RF-18, RF-20"],
          ["Operador (Bienestar)", "Matrícula, bienes patrimoniales, observaciones de justificación, reportes", "RF-06, RF-19, RF-28 a RF-31"],
          ["Estudiante (actor pasivo)", "No usa el sistema directamente; es la entidad sobre la que se registra información", "RF-06 a RF-10, RF-21"],
        ],
        [2000, 4826, 2200]
      ),
      h2("4.2 Casos de uso principales por módulo"),
      p("En lugar de un único diagrama monolítico, se agrupan los casos de uso por módulo, siguiendo la misma organización del documento de requerimientos, lo que facilita trazar cada caso de uso a su RF de origen."),
      table(
        ["Caso de uso", "Actor(es)", "RF relacionado", "Flujo resumido"],
        [
          ["Iniciar sesión", "Todos", "RF-01, RF-05", "Ingresar credenciales → validar → conceder acceso según rol → controlar inactividad"],
          ["Matricular estudiante", "Operador, Administrador", "RF-06, RF-14", "Registrar/seleccionar estudiante → asociar a taller → validar cupo"],
          ["Programar sesiones de taller", "Administrador", "RF-11, RF-13", "Crear taller → definir fecha inicio, frecuencia y cantidad → generar calendario"],
          ["Registrar asistencia por sesión", "Docente, Administrador", "RF-16, RF-17, RF-18", "Seleccionar sesión → marcar P/A/J por estudiante → guardar en bloque → recalcular % → generar alerta si aplica"],
          ["Autorizar edición de sesión congelada", "Administrador", "RF-20", "Docente solicita → Administrador autoriza puntualmente → evento queda en auditoría → docente edita esa sesión"],
          ["Generar lista de aptos", "Operador, Administrador", "RF-21 a RF-24", "Definir umbral → calcular aptos → previsualizar → exportar a Excel → registrar emisión"],
          ["Gestionar bien patrimonial", "Operador, Administrador", "RF-28 a RF-31", "Registrar bien → asignar a docente/taller → registrar devolución → alertar si hay daño o demora"],
          ["Generar reporte", "Operador, Administrador", "RF-32 a RF-37", "Elegir tipo de reporte → filtrar → exportar (Excel/PDF/CSV) con formato UNAB"],
        ],
        [2100, 1500, 1500, 3926]
      ),
      h2("4.3 Modelo de dominio (entidades principales)"),
      p("El modelo de dominio refleja directamente las entidades que ya existen en la capa de datos (SQLAlchemy) del sistema:"),
      table(
        ["Entidad", "Atributos clave", "Relaciones"],
        [
          ["Usuario", "id, username, nombre_completo, rol_nombre", "1—N Auditoria (registrado_por); 1—N Sesion (docente asignado)"],
          ["Estudiante", "id, nombres, apellidos, dni, código, carrera, ciclo, estado", "1—N Inscripcion"],
          ["Taller", "id, nombre, categoría, cupo_máximo, umbral_asistencia, estado", "1—N Sesion; 1—N Inscripcion"],
          ["Inscripcion", "id, estudiante_id, taller_id, estado (Activo/Inactivo)", "1—N Asistencia"],
          ["Sesion", "id, taller_id, numero, fecha, hora, estado (Programada/Realizada/Cancelada)", "1—N Asistencia"],
          ["Asistencia", "id, inscripcion_id, sesion_id, estado (P/A/J), observacion, registrado_por", "N—1 Inscripcion, N—1 Sesion"],
          ["Bien", "id, codigo_patrimonial, categoria, estado (Disponible/Asignado/Mantenimiento/DeBaja)", "N—1 Usuario (asignado a docente/taller)"],
          ["Auditoria", "id, usuario_id, tabla_afectada, accion (INSERT/UPDATE/DELETE), registro_id, datos_anteriores, datos_nuevos", "N—1 Usuario"],
        ],
        [1700, 4326, 3000]
      ),
      h2("4.4 Diagramas de estado"),
      p("Tres entidades tienen máquinas de estado explícitas en los requerimientos; documentarlas evita ambigüedad de implementación (ver hallazgo de RF-13 en 2.3):"),
      table(
        ["Entidad", "Estados (RF de origen)", "Transición relevante"],
        [
          ["Taller", "Activo → Suspendido → Finalizado (RF-15)", "Un taller Finalizado no admite nuevas inscripciones (RF-14) ni nuevas sesiones (RF-13)"],
          ["Sesion", "Programada → Realizada → (Cancelada)", "Al guardarse la primera asistencia de la sesión, pasa automáticamente de Programada a Realizada"],
          ["Bien", "Disponible → Asignado → Mantenimiento → (DeBaja) (RF-30)", "Al devolverse en estado Malo/Inservible, no vuelve a Disponible: pasa a Mantenimiento (RF-29, RF-31)"],
        ],
        [1400, 3800, 3826]
      ),
      h2("4.5 Diagrama de secuencia — ejemplo: registrar asistencia (RF-16 a RF-18, RF-20)"),
      p("Se describe en formato textual (equivalente a un diagrama de secuencia UML) el flujo real implementado en AsistenciaService y PanelRegistrarAsistencia, que integra cuatro requerimientos en una sola operación de usuario:"),
      numbered("Docente selecciona una sesión en panel_asistencia.py → PanelRegistrarAsistencia carga inscritos y asistencias existentes."),
      numbered("Docente marca P/A/J por estudiante en la tabla (edición inline) y pulsa \u201cGuardar Asistencia\u201d."),
      numbered("Por cada estudiante, la UI llama a AsistenciaService.registrar(sesion_id, inscripcion_id, estado, usuario_id, observacion, rol_usuario)."),
      numbered("El servicio valida el estado (P/A/J), exige observación si es J (RF-19), y verifica si la sesión está congelada (RF-20) mediante _bloqueada_para()."),
      numbered("Si la sesión no está congelada, o el docente cuenta con autorización puntual vigente, el servicio inserta/actualiza el registro en Asistencia y recalcula el porcentaje (RF-17)."),
      numbered("Se registra el evento en Auditoria (RF-40) y se hace commit."),
      numbered("Si el porcentaje resultante es menor al umbral del taller, el servicio retorna una alerta (RF-18), que la UI acumula y muestra en el resumen final."),
      numbered("Al terminar de procesar todos los estudiantes, si la sesión seguía en estado Programada, el servicio invoca SesionService.cambiar_estado(sesion_id, \"Realizada\", usuario_id), efecto colateral que cierra el ciclo de vida de la sesión sin intervención manual del docente."),
      nota("Este flujo es un ejemplo directo de por qué el modelado de secuencia es útil incluso sin diagrama gráfico: expone que RF-16, RF-17, RF-18, RF-19, RF-20 y la transición de estado de Sesión no son independientes, sino un único caso de uso con múltiples reglas de negocio encadenadas — información que la tabla plana de requerimientos, por sí sola, no deja ver."),

      // ───────────────────── 5. VALIDACIÓN ─────────────────────
      h1("5. Validación de requerimientos"),
      h2("5.1 Contexto de la validación"),
      p("La validación se ejecuta después de tener una versión verificada de la especificación (sección 2) y antes de congelar la línea base (sección 6.2). Su objetivo es confirmar, junto a los interesados reales —coordinador de Bienestar Universitario, un docente representativo y el operador administrativo—, que los 43 RF documentados efectivamente resuelven sus problemas actuales (registro manual de asistencia, cálculo de aptos en Excel, control disperso de bienes) y no omiten ninguna regla de negocio crítica."),
      p("El contexto institucional impone restricciones que la validación debe verificar explícitamente: el sistema es de escritorio (no web), opera dentro de la red de la universidad, y coexiste con procesos administrativos ya establecidos (por ejemplo, el formato oficial UNAB de reportes exigido en RF-36). Validar sin considerar este contexto llevaría a aceptar requerimientos técnicamente correctos pero organizacionalmente inviables."),
      h2("5.2 Calidad de los requerimientos"),
      p("Además de los criterios de verificación (sección 2.2, centrados en la redacción), la validación evalúa calidad desde la perspectiva del negocio:"),
      bullet("Necesidad real: ¿el requerimiento resuelve un problema que Bienestar reportó? RF-18 (alertas por bajo umbral) nace directamente de la queja de que hoy se detectan estudiantes en riesgo demasiado tarde."),
      bullet("Prioridad de negocio: RF-20 (congelar asistencia) fue calificado como crítico por el coordinador, porque hoy existen casos de asistencia \u201cajustada\u201d después de finalizado el taller; de ahí que solo el administrador (o un docente autorizado puntualmente) pueda saltarse el congelamiento."),
      bullet("Impacto si falta: sin RF-21 (lista de aptos en Excel), Bienestar seguiría dependiendo de un cálculo manual propenso a errores — el mismo problema que originó el proyecto."),
      bullet("Consistencia con el rol: RF-19 asigna la observación de justificación al Operador, no al Docente; esto debe confirmarse explícitamente en la reunión de validación (5.5), porque el flujo de RF-16 a RF-18 sugiere que el Docente también participa del ciclo de justificación."),
      h2("5.3 Técnicas de validación de requerimientos: pruebas de aceptación"),
      p("Para los RF críticos se definieron criterios de aceptación en formato Dado / Cuando / Entonces, verificables directamente contra el comportamiento de los servicios ya implementados:"),
      table(
        ["RF", "Criterio de aceptación (Given / When / Then)"],
        [
          ["RF-16", "Dado un docente autenticado en un taller propio, cuando registra P/A/J para un estudiante en una sesión no congelada, entonces el registro se guarda con un único registro por inscripción-sesión (UNIQUE)."],
          ["RF-17", "Dado un estudiante con N sesiones y M marcadas P o J, cuando se guarda una nueva asistencia, entonces el porcentaje mostrado es (M/N)×100, recalculado sin recargar la aplicación."],
          ["RF-18", "Dado un taller con umbral 80%, cuando el porcentaje de un estudiante cae por debajo de 80%, entonces el sistema retorna una alerta visible en el resumen de guardado."],
          ["RF-19", "Dado un estado marcado como Justificado (J), cuando se intenta guardar sin observación, entonces el sistema rechaza el guardado y señala qué estudiantes faltan."],
          ["RF-20", "Dado que la fecha de la sesión ya pasó, cuando un docente sin autorización intenta guardar asistencia, entonces el sistema rechaza la operación; si el administrador lo autorizó puntualmente, el guardado se permite."],
          ["RF-21", "Dado un taller finalizado, cuando se genera la lista de aptos, entonces solo aparecen estudiantes cuyo porcentaje acumulado (P+J)/Total sea ≥ umbral configurado."],
          ["RF-30", "Dado un bien devuelto en estado Malo o Inservible, cuando se registra la devolución, entonces el bien pasa a Mantenimiento y no a Disponible."],
        ],
        [900, 8126]
      ),
      h2("5.4 Enfoques de validación"),
      bullet("Revisiones formales (inspecciones/walkthroughs): lectura guiada del documento de requerimientos junto al coordinador de Bienestar, RF por RF, dejando acta de observaciones."),
      bullet("Prototipado: bocetos o versiones tempranas de panel_asistencia.py y panel_bienes.py mostrados a un docente y a un operador real antes de considerar cerrado el RF de interfaz correspondiente."),
      bullet("Pruebas de aceptación ejecutables: las tablas Given/When/Then de la sección 5.3 se convierten en casos de prueba manuales o automatizados sobre AsistenciaService, BienesService y SesionService."),
      bullet("Trazabilidad cruzada: verificar que cada objetivo de negocio declarado por Bienestar tenga al menos un RF que lo cubra, y que ningún RF quede sin justificación de negocio (evita sobre-ingeniería, p. ej. revisar si RF-42 \u201ctema día/noche\u201d responde a una necesidad real o es un extra)."),
      bullet("Simulación de escenarios límite: sesión con cero inscritos, taller sin umbral configurado, bien devuelto sin haber sido asignado — escenarios que la tabla de requerimientos no cubre explícitamente y que deben acordarse con el usuario antes de codificarlos por defecto."),
      h2("5.5 Reunión de validación con usuarios"),
      p("Se recomienda una reunión formal de validación antes de establecer la línea base, con la siguiente estructura:"),
      table(
        ["Elemento", "Detalle"],
        [
          ["Participantes", "Coordinador de Bienestar Universitario (dueño del proceso), un Docente representativo, el Operador administrativo, y el equipo de desarrollo (moderador + relator)"],
          ["Insumos", "Documento de requerimientos (RF-01 a RF-43), prototipos de panel_asistencia.py y panel_bienes.py, matriz de trazabilidad preliminar (sección 6.1)"],
          ["Agenda sugerida", "1) Contexto y objetivos (10 min) · 2) Revisión módulo por módulo con foco en Asistencia y Bienes (60 min) · 3) Demostración de prototipo (20 min) · 4) Registro de hallazgos y acuerdos (20 min)"],
          ["Roles", "Moderador: guía la sesión sin opinar sobre soluciones técnicas · Relator: registra cada observación con el RF asociado · Usuarios: validan si el RF representa correctamente su necesidad"],
          ["Salidas", "Acta de reunión, lista de hallazgos (inconsistencias, ambigüedades, RF faltantes), acuerdo de prioridad para cada hallazgo"],
        ],
        [2200, 6826]
      ),
      h2("5.6 Corrección de inconsistencias"),
      p("Toda inconsistencia detectada en verificación (sección 2) o validación (secciones 5.1–5.5) sigue un ciclo cerrado antes de tocar código: registrar → priorizar → reformular → re-revisar → aprobar."),
      numbered("Registrar: cada hallazgo se anota con el RF afectado, quién lo detectó y en qué instancia (verificación interna o reunión con usuarios)."),
      numbered("Priorizar: se clasifica como Bloqueante (impide avanzar, ej. RF-20 sin mecanismo claro de autorización), Importante (afecta calidad, ej. redacción ambigua de RF-19) o Menor (cosmético, ej. typo \u201cconversación\u201d en RF-29)."),
      numbered("Reformular: se reescribe el RF y se marca su versión (sección 6.4) sin borrar el historial de la redacción anterior."),
      numbered("Re-revisar: el RF corregido vuelve a pasar el checklist de la sección 2.2 antes de cerrarse."),
      numbered("Aprobar: el interesado que reportó el hallazgo confirma que la nueva redacción resuelve su observación."),
      h3("Caso real: inconsistencia entre RF-20 y su implementación"),
      p("Este ciclo se aplicó efectivamente sobre un caso concreto del sistema. RF-20 exige que un docente solo pueda editar una sesión congelada \u201ccon autorización explícita del administrador\u201d, pero no especifica el mecanismo. En la implementación, esa autorización se registra como un evento en la tabla auditoria (sin crear tablas nuevas, según convención del proyecto). Se detectaron dos inconsistencias entre el requerimiento y el código:"),
      bullet("La consulta que busca la autorización vigente (AsistenciaService._tiene_autorizacion_activa) usaba la expresión Auditoria.datos_nuevos in ([\u2026]) — una comparación de Python, no una condición SQL — que no filtraba nada de forma confiable."),
      bullet("Tanto autorizar_edicion_congelada() como revocar_autorizacion_edicion() escribían accion=\"UPDATE\" (restricción del ENUM de la tabla, que solo admite INSERT/UPDATE/DELETE), por lo que no había forma de distinguir una autorización de una revocación consultando solo esa columna."),
      p("La corrección (aplicada en este mismo proyecto) fue agregar una clave tipo_evento (\"AUTORIZAR_EDICION_ASISTENCIA\" / \"REVOCAR_AUTORIZACION_EDICION_ASISTENCIA\") dentro del JSON datos_nuevos, y reescribir la consulta para filtrar por tabla_afectada, registro_id y accion==\"UPDATE\" a nivel SQL, resolviendo la ambigüedad en Python sobre ese campo. El RF-20 no requirió cambio de redacción — su intención de negocio era correcta — pero sí quedó documentado que el mecanismo de persistencia de la autorización debe registrarse como nota técnica adjunta al RF, para que no vuelva a implementarse de forma ambigua."),
      nota("Este caso ilustra por qué la corrección de inconsistencias no distingue entre \u201cerror de requerimiento\u201d y \u201cerror de implementación\u201d: ambos se resuelven con el mismo ciclo, y ambos deben quedar trazados al mismo RF-20 en la matriz de trazabilidad."),

      // ───────────────────── 6. GESTIÓN ─────────────────────
      h1("6. Gestión de requerimientos"),
      h2("6.1 Trazabilidad"),
      p("Cada RF debe poder rastrearse desde su origen de negocio hasta el artefacto de código y su prueba de aceptación. La siguiente matriz muestra una muestra representativa usando los componentes reales del proyecto:"),
      table(
        ["RF", "Módulo / Servicio", "Componente UI", "Prueba de aceptación"],
        [
          ["RF-16", "asistencia_service.py → registrar()", "panel_asistencia.py", "5.3 — RF-16"],
          ["RF-17", "asistencia_service.py → _calcular_porcentaje_actual()", "panel_asistencia.py (columna %)", "5.3 — RF-17"],
          ["RF-18", "asistencia_service.py → obtener_estudiantes_en_riesgo()", "panel_asistencia.py (resumen de guardado)", "5.3 — RF-18"],
          ["RF-20", "asistencia_service.py → _bloqueada_para(), puede_editar_sesion_congelada()", "panel_asistencia.py (botón Autorizar a un docente)", "5.3 — RF-20"],
          ["—", "sesion_service.py → cambiar_estado()", "(disparado automáticamente, sin UI directa)", "4.5 — paso 8"],
          ["RF-21", "utils/exportar_excel.py + servicio de aptos", "panel de lista de aptos", "5.3 — RF-21"],
          ["RF-25 / RF-26", "utils/importar_excel.py", "diálogo de importación masiva", "—"],
          ["RF-28 a RF-31", "bienes_service.py", "panel_bienes.py", "5.3 — RF-30"],
          ["RF-39 / RF-40", "auditoria_service.py", "panel_auditoria.py, detalle_auditoria_dialog.py", "—"],
          ["RF-42", "utils/themes.py", "main_window.py", "—"],
        ],
        [900, 2900, 2726, 2500]
      ),
      p("Se recomienda mantener esta matriz como documento vivo (hoja de cálculo o campo adicional en el tablero Kanban), actualizándola en cada Pull Request que declare qué RF-XX implementa, siguiendo la misma convención de nombrado ya usada en la especificación."),
      h2("6.2 Línea base"),
      p("La línea base es la versión del documento de requerimientos formalmente aprobada tras la reunión de validación (sección 5.5), que a partir de ese momento solo puede modificarse mediante control de cambios (sección 6.3), no por edición directa."),
      bullet("Línea base 1.0 (propuesta): los 43 RF actuales, con las correcciones de redacción de la sección 2.3 (RF-19, RF-29) ya incorporadas y aprobadas en la reunión de validación."),
      bullet("Criterio de congelamiento: un RF entra a la línea base solo si pasó el checklist de verificación (2.2) y fue confirmado en la reunión de validación (5.5) sin observaciones bloqueantes pendientes."),
      bullet("Alcance de la línea base: define qué se construye en la versión actual del sistema; cualquier funcionalidad fuera de los 43 RF (por ejemplo, notificaciones automáticas por correo) queda fuera de alcance hasta que pase por una solicitud de cambio formal."),
      h2("6.3 Control de cambios"),
      p("Una vez establecida la línea base, toda modificación —agregar, eliminar o alterar un RF— sigue un procedimiento formal de solicitud de cambio (Change Request):"),
      numbered("Solicitud: cualquier interesado (Bienestar, docente, desarrollo) documenta el cambio propuesto y su justificación de negocio."),
      numbered("Análisis de impacto: se evalúa qué otros RF, servicios y pantallas se ven afectados usando la matriz de trazabilidad (6.1). Por ejemplo, cambiar el umbral por defecto de RF-22 (80%) impactaría RF-18, RF-21 y los reportes de RF-32/RF-37."),
      numbered("Evaluación de prioridad y esfuerzo: el equipo estima costo de implementación y urgencia."),
      numbered("Aprobación: el coordinador de Bienestar (dueño del proceso) y el equipo técnico aprueban o rechazan el cambio."),
      numbered("Actualización de la línea base: si se aprueba, se emite una nueva versión del documento (sección 6.4) y se actualiza la matriz de trazabilidad."),
      numbered("Comunicación: se notifica a todos los interesados y se referencia el cambio en el commit o Pull Request correspondiente."),
      h2("6.4 Versionamiento"),
      p("Se recomienda versionar el documento de requerimientos con un esquema semántico simple, independiente del versionamiento del software, pero enlazado a él mediante referencias RF-XX:"),
      table(
        ["Versión", "Contenido", "Estado"],
        [
          ["v1.0", "43 RF originales (RF-01 a RF-43), tal como fueron elicitados", "Verificado (con observaciones, sección 2.3)"],
          ["v1.1 (propuesta)", "Incorpora la redacción corregida de RF-19 y RF-29, y nota técnica sobre el mecanismo de autorización de RF-20", "Pendiente de aprobación en reunión de validación"],
          ["v1.x", "Cambios menores aprobados por control de cambios (ajustes de redacción, aclaraciones)", "Bajo control de cambios"],
          ["v2.0 (futura)", "Incorporación de nuevos RF fuera del alcance actual (ej. notificaciones), tras análisis de impacto completo", "No iniciada"],
        ],
        [1600, 5326, 2100]
      ),
      bullet("El documento de requerimientos se versiona en el mismo repositorio Git del proyecto (o en Google Docs con historial de versiones habilitado), de modo que cada commit de código que implemente un RF pueda referenciar la versión del documento vigente al momento del cambio."),
      bullet("Cada RF conserva su identificador (RF-XX) de forma permanente entre versiones del documento; solo cambia su contenido o se marca como Obsoleto si se reemplaza por otro RF, nunca se reutiliza el mismo ID para un requerimiento distinto."),

      // ───────────────────── 7. CONCLUSIONES ─────────────────────
      h1("7. Conclusiones"),
      p("La especificación de requerimientos del Sistema de Talleres UNAB, con sus 43 RF organizados en nueve módulos, constituye una base sólida y mayormente verificable: la mayoría de los requerimientos cumple los criterios de no ambigüedad, verificabilidad y factibilidad. Sin embargo, el ejercicio de verificación identificó defectos de redacción concretos (RF-19, RF-29) y un caso real de requerimiento correcto pero subespecificado en su mecanismo (RF-20), cuya falta de detalle técnico se tradujo en un defecto de implementación efectivamente corregido en el código del proyecto."),
      p("El modelado por actores, casos de uso, entidades de dominio y diagramas de estado permitió exponer relaciones que la tabla plana de requerimientos no muestra por sí sola —en particular, que el registro de asistencia (RF-16 a RF-20) es un único flujo de negocio con múltiples reglas encadenadas, no cinco funcionalidades independientes—. La validación con criterios Given/When/Then convierte cada RF crítico en un caso de prueba ejecutable contra los servicios ya implementados, cerrando el ciclo entre requerimiento, diseño y código."),
      p("Finalmente, establecer una línea base formal, un procedimiento de control de cambios y un esquema simple de versionamiento del documento de requerimientos —enlazado por el identificador RF-XX a la matriz de trazabilidad, al código y a las pruebas de aceptación— es lo que permitirá que el sistema evolucione (nuevos módulos, ajustes de reglas de negocio) sin perder consistencia entre lo que Bienestar Universitario necesita y lo que el sistema efectivamente hace."),

      // ───────────────────── REFERENCIAS ─────────────────────
      h1("Referencias"),
      p("IEEE Std 830-1998. Recommended Practice for Software Requirements Specifications. Institute of Electrical and Electronics Engineers."),
      p("ISO/IEC/IEEE 29148:2018. Systems and software engineering — Life cycle processes — Requirements engineering."),
      p("Sommerville, I. Ingeniería de Software (10.ª ed.). Pearson."),
      p("Pressman, R. S., & Maxim, B. R. Ingeniería del Software: Un Enfoque Práctico (8.ª ed.). McGraw-Hill."),
      p("Documento base: requerimientos.docx — Especificación de Requerimientos Funcionales del Sistema de Talleres UNAB (RF-01 a RF-43)."),
      ]
    }
  ]
});

Packer.toBuffer(doc).then(buf => {
  require("fs").writeFileSync("/mnt/user-data/outputs/Informe_Ingenieria_Requerimientos_Sistema_Talleres_UNAB.docx", buf);
  console.log("OK: documento generado");
});