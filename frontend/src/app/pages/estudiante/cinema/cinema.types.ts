export type TemaEscena =
  | 'tribunal_comite'
  | 'laboratorio_autoridad'
  | 'hospital_urgencias'
  | 'entrevista_clinica'
  | 'proteccion_riesgo'
  | 'red_ciudad';

export type PlanoCamara = 'general' | 'medio' | 'primer_plano' | 'decision';

export type ModoCamara = 'auto' | 'general' | 'medio' | 'primer_plano';

export type SubEscena =
  | 'VOTACION_MAYORIA_4_1'
  | 'INSISTENCIA_DECANO'
  | 'ORDEN_LABORATORIO'
  | 'CRISIS_URGENCIAS'
  | 'ENTREVISTA_CLINICA'
  | 'RESGUARDO_RIESGO'
  | 'MESA_INTERINSTITUCIONAL';

export type ExpresionFacial =
  | 'neutro'
  | 'preocupacion'
  | 'desacuerdo'
  | 'autoridad'
  | 'inseguridad'
  | 'tension'
  | 'convencimiento'
  | 'calma';

export type PosturaCorporal =
  | 'sentado_firme'
  | 'inclinado_adelante'
  | 'brazo_levantado'
  | 'senalar_orden'
  | 'retroceso_tension'
  | 'defensa_abierta'
  | 'escucha_empatica'
  | 'decidido';

export type VestuarioActor =
  | 'protagonista'
  | 'ejecutivo'
  | 'decano'
  | 'bata'
  | 'clinico'
  | 'casual';

export type EstiloCabello =
  | 'ejecutivo_corto'
  | 'melena_lacia'
  | 'mono_alto'
  | 'canoso_peinado'
  | 'ondulado_medio'
  | 'clinico_recogido';

export type DireccionMirada = 'izquierda' | 'centro' | 'derecha' | 'abajo';

export type HeroeId =
  | 'cobalto'
  | 'dinamo'
  | 'astral'
  | 'prisma'
  | 'bastion'
  | 'eco'
  | 'vigia'
  | 'solar'
  | 'aurora'
  | 'pulso'
  | 'jade'
  | 'vector';

export type EfectoPoderHeroe = 'escudo' | 'pulso' | 'destello';

export interface PerfilHeroe {
  id: HeroeId;
  nombre: string;
  arquetipo: string;
  valorPsicosocial: string;
  colorTraje: string;
  colorTrajeSombra: string;
  colorAcento: string;
  colorEnergia: string;
  efectoPoder: EfectoPoderHeroe;
}

export interface ConfiguracionActor {
  id: string;
  nombre: string;
  rol: string;
  pielClara: string;
  pielSombra: string;
  cabelloColor: string;
  cabelloBrillo: string;
  estiloCabello: EstiloCabello;
  vestuario: VestuarioActor;
  colorTraje: string;
  colorTrajeSombra: string;
  colorCamisa: string;
  colorCorbata?: string;
  lentes?: boolean;
  maduro?: boolean;
  esProtagonista?: boolean;
  heroe?: PerfilHeroe;
  expresion: ExpresionFacial;
  postura: PosturaCorporal;
  mirada: DireccionMirada;
  hablando?: boolean;
  destacado?: boolean;
  atenuado?: boolean;
  retrasoRespiracionMs?: number;
  retrasoParpadeoMs?: number;
  retrasoGestoMs?: number;
  posicion: {
    xPct: number;
    zIndex: number;
  };
}
