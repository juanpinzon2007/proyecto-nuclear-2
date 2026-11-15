/**
 * Tipos del contrato HTTP del backend SPS.
 * Generados a mano a partir del OpenAPI de `develop` (app.main). No modificar el backend:
 * si el contrato cambia, actualizar estos tipos.
 */

export type Uuid = string;
export type Rol = 'ADMINISTRADOR' | 'DOCENTE' | 'ESTUDIANTE';

// ---------- Errores ----------
export interface DetalleErrorHTTP { codigo: string; mensaje: string; campos?: string[] | null; }
export interface ErrorHTTP { detail: DetalleErrorHTTP; }

// ---------- Identity ----------
export interface SolicitudLogin { correo: string; codigo_convocatoria: string; }
export interface SolicitudLoginPersonal { correo: string; clave: string; }
export interface RespuestaToken { access_token: string; token_type?: string; }
export interface UsuarioPublico { id_usuario: string; correo: string; roles: Rol[]; permisos: string[]; }

export interface CuentaDocenteRespuesta { id_usuario: string; nombre: string; correo: string; activo: boolean; }
export interface PaginaDocentesRespuesta { docentes: CuentaDocenteRespuesta[]; total: number; limite: number; desplazamiento: number; }
export interface CrearDocente { roles?: Rol[]; permisos?: string[]; correo: string; nombre?: string | null; clave?: string | null; }
export interface AutorizacionesDocente { roles?: Rol[]; permisos?: string[]; }
export interface PerfilPermisosDocentesRespuesta {
  id_rol: number; rol: string; permisos: string[]; permisos_disponibles: string[]; docentes_afectados: number; alcance: string;
}
export interface SolicitudRepeticion { id_sesion: string; id_estudiante: string; }
export interface AutorizacionRepeticion {
  id_sesion: string; id_estudiante: string; id_docente_autorizador: string; fecha_autorizacion: string; id_permiso_extra?: number | null;
}

export interface DocumentoRespuesta {
  id_version_documento: number; referencia: string; documento_id: string; version: string; texto: string; huella: string;
}
export interface AceptarConsentimiento { id_version_documento: number; referencia: string; huella: string; acepta: boolean; }
export interface AceptacionRespuesta {
  aceptado: boolean; id_version_documento: number; referencia: string; huella: string;
  id_consentimiento: number | null; fecha_aceptacion: string | null;
}

// Seguimiento docente
export interface ResumenCaso { id_caso: string; nombre: string; version_caso_id?: string | null; }
export interface ResumenParticipacion {
  id_participacion: string; id_estudiante: string; id_caso: string; version_caso_id: string;
  id_convocatoria: string; id_sesion: string; estado: string;
}
export interface RespuestaSeguimiento {
  id_pregunta: string; id_opcion: string | null; retroalimentacion: string | null;
  id_intento?: string | null; numero_paso?: number | null; reflexion_estudiante?: string | null;
}
export interface IntentoSeguimiento {
  id_intento: string; numero_intento: number; estado: string; inicio: string; fin: string | null; respondidas: number;
}
export interface DetalleParticipacion {
  id_participacion: string; id_estudiante: string; id_caso: string; respuestas: RespuestaSeguimiento[];
  feedback_docente: string | null; intentos?: IntentoSeguimiento[]; version_caso_id?: string | null;
  id_convocatoria?: string | null; id_sesion?: string | null; estado?: string | null;
}
export interface FeedbackDocente { id_participacion: string; id_docente: string; texto: string; fecha: string; }
export interface ReporteFiltros {
  formato?: 'xlsx' | 'pdf'; version_publicacion?: number | null; id_grupo?: number | null;
  id_estudiante?: number[] | null; estado?: 'COMPLETA' | 'PARCIAL' | 'AUSENTE' | null; agrupar_por?: 'grupo' | 'estudiante';
}

// ---------- Cases ----------
export type EstadoCaso = 'BORRADOR' | 'PUBLICADO' | 'ARCHIVADO';

export interface OpcionSchema { orden: number; texto: string; esCorrecta: boolean; justificacion: string; valoraciones?: Record<string, number | string>; }
export interface PreguntaSchema { orden: number; enunciado: string; options?: OpcionSchema[]; }
export interface EscenarioSchema { orden: number; contextoSituacional: string; questions?: PreguntaSchema[]; }
export interface NivelSchema { nombre: string; puntaje: number | string; descriptor: string; }
export interface CriterioSchema { nombre: string; peso: number | string; niveles?: NivelSchema[]; }
export interface RubricaSchema { nombre: string; versionRegla: string; criterios?: CriterioSchema[]; }
export interface DatosCasoSchema { nombre: string; desarrolloSituacional: string; contextoHistoria: string; tiempoEstimadoMin: number; }
export interface CasoPayload { case: DatosCasoSchema; scenarios?: EscenarioSchema[]; rubric?: RubricaSchema | null; }

export interface CasoResumenResponse {
  version_id: Uuid; caso_id: Uuid; numero: number; nombre: string; tiempo_estimado_min: number; estado: EstadoCaso; creado_en: string;
}
export interface VersionResponse { caso_id: Uuid; version_id: Uuid; estado: EstadoCaso; }
export interface OpcionResponse { id: Uuid; orden: number; texto: string; es_correcta: boolean; justificacion: string; valoraciones: Record<string, string>; }
export interface PreguntaResponse { id: Uuid; orden: number; enunciado: string; opciones: OpcionResponse[]; }
export interface EscenarioResponse { id: Uuid; orden: number; contexto_situacional: string; preguntas: PreguntaResponse[]; }
export interface NivelResponse { id: Uuid; nombre: string; puntaje: string; descriptor: string; }
export interface CriterioResponse { id: Uuid; nombre: string; peso: string; niveles: NivelResponse[]; }
export interface RubricaResponse { id: Uuid; nombre: string; version_regla: string; criterios: CriterioResponse[]; }
export interface CasoDetalleResponse {
  id: Uuid; caso_id: Uuid; numero: number; nombre: string; desarrollo_situacional: string; contexto_historia: string;
  tiempo_estimado_min: number; estado: EstadoCaso; escenarios: EscenarioResponse[]; rubrica: RubricaResponse | null;
}
export interface TransicionResponse { opcion_id: Uuid; tipo: string | null; destino_id: Uuid | null; texto: string; }
export interface PreguntaGrafoResponse { id: Uuid; enunciado: string; opciones: TransicionResponse[]; }
export interface EscenaGrafoResponse { id: Uuid; inicial: boolean; contexto: string; preguntas: PreguntaGrafoResponse[]; }
export interface GrafoResponse { version_id: Uuid; escenas: EscenaGrafoResponse[]; }
export interface TransicionSolicitud { opcion_id: Uuid; tipo: 'ESCENA' | 'FIN'; destino_id?: Uuid | null; }
export interface GrafoSolicitud { escenario_inicial_id: Uuid; transiciones: TransicionSolicitud[]; }

// ---------- Scheduling ----------
export interface EspacioAcademicoResponse { id: Uuid; nombre: string; }
export interface SesionResponse {
  id: Uuid; espacio_academico_id: Uuid; version_caso_id: Uuid; docente_id: Uuid; fecha_inicio: string; fecha_fin: string;
  tiempo_maximo_minutos: number; lugar: string | null; mensaje_personalizado: string | null; estado: string; finalizado_en: string | null;
}
export interface ConvocatoriaAsignadaResponse { convocatoria_id: Uuid; codigo_acceso: string; estudiante_id: Uuid; }
export interface SesionConAsignacionResponse extends SesionResponse { id_asignacion: number; convocatorias: ConvocatoriaAsignadaResponse[]; }
export interface ProgramarSesionRequest {
  espacio_academico_id: Uuid; version_caso_id: Uuid; fecha_inicio: string; fecha_fin: string; tiempo_maximo_minutos: number;
  lugar?: string | null; mensaje_personalizado?: string | null; grupo_id?: number | null; estudiantes_ids?: Uuid[] | null;
  fecha_limite_ingreso?: string | null;
}
export interface ConvocatoriaDetalleResponse { id: Uuid; sesion_id: Uuid; estudiante_id: Uuid; estado: string; }
export interface ConvocatoriaResponse { convocatoria_id: Uuid; codigo_acceso: string; }
export interface NotificacionResponse {
  id: Uuid; convocatoria_id: Uuid | null; destinatario_id: Uuid; tipo: string; canal: string; mensaje: string; estado: string; creada_en: string;
}
export interface ComprobanteAdmision {
  convocatoria_id: Uuid; sesion_id: Uuid; version_caso_id: Uuid; solicitada: boolean; admitida: boolean; estado_sesion: string;
}
export interface IntentoPreparacionRespuesta { id_intento: number; numero: number; estado: EstadoIntento; resultado_tecnico_disponible: boolean; }
export interface ConvocatoriaPreparacionRespuesta {
  id_convocatoria: Uuid; id_estudiante: number; estado: 'ACTIVA' | 'RETIRADA'; id_participacion: number | null;
  intentos: IntentoPreparacionRespuesta[]; pendientes: string[];
}
export interface PreparacionSesionRespuesta {
  id_sesion: Uuid; version_caso_id: Uuid; estado_sesion: 'SIN_INICIAR' | 'EN_CURSO' | 'FINALIZADO';
  convocatorias: ConvocatoriaPreparacionRespuesta[]; pendientes: string[]; publicable: boolean;
}
export interface ConsolidacionSesion {
  id_sesion: string; publicable: boolean; pendientes: string[]; revision_sha256: string; filas?: unknown[]; retiradas?: unknown[];
  [k: string]: unknown;
}
export interface PreguntaTecnicaRespuesta { pregunta_id: Uuid; opcion_id: Uuid; puntaje: string; numero_paso: number; }
export interface CriterioTecnicoRespuesta {
  criterio_id: Uuid; suma_puntajes?: string | null; preguntas_evaluables?: number | null; numerador?: string | null;
  denominador?: string | null; nivel_id?: Uuid | null; puntaje_obtenido?: string | null;
}
export interface ResultadoTecnicoRespuesta {
  id_sesion: Uuid; id_convocatoria: Uuid; id_participacion: number; id_intento: number; id_resultado: number;
  version_caso_id: Uuid; rubrica_id: Uuid; version_regla: string; modalidad: 'COMPLETA' | 'PARCIAL';
  ambito: 'TECNICO' | 'LABORATORIO'; oficial: boolean; fecha_calculo: string; nota_final: string; procedencia_sha256: string;
  preguntas_exigidas?: number | null; preguntas_respondidas?: number | null; pendientes_con_cero?: number | null;
  suma_puntajes?: string | null; preguntas: PreguntaTecnicaRespuesta[]; criterios: CriterioTecnicoRespuesta[];
}

// ---------- Participation ----------
export type EstadoIntento = 'EN_CURSO' | 'FINALIZADO' | 'VENCIDO';
export interface InicioConvocatoriaSolicitud { id_asignacion: number; codigo_acceso: string; id_consentimiento: number; id_permiso_extra?: number | null; }
export interface IntentoRespuesta {
  id_intento: number; id_participacion: number; numero_intento: number; estado: EstadoIntento; inicio: string; fin: string | null; vence_en: string;
}
export interface OpcionActualRespuesta { id: Uuid; texto: string; }
export interface PreguntaActualRespuesta { id: Uuid; enunciado: string; opciones: OpcionActualRespuesta[]; }
export interface EscenarioActualRespuesta {
  id_escenario: Uuid | null; contexto: string | null; pregunta: PreguntaActualRespuesta | null; recorrido_finalizado: boolean; respondidas: number;
}
export interface SeleccionSolicitud { id_opcion: Uuid | number; reflexion_estudiante?: string | null; }
export interface SeleccionRespuesta { id_decision: Uuid | number; id_opcion: Uuid | number; }
export interface ProgresoRespuesta {
  intento: IntentoRespuesta; decisiones_aplicables: (Uuid | number)[] | null; selecciones: SeleccionRespuesta[];
  pendientes: (Uuid | number)[] | null; total_aplicable: number | null; respondidas: number;
}

