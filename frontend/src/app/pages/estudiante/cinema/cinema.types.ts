export type TemaEscena =
  | 'tribunal_comite'
  | 'laboratorio_autoridad'
  | 'hospital_urgencias'
  | 'entrevista_clinica'
  | 'proteccion_riesgo'
  | 'red_ciudad';

export type PlanoCamara = 'general' | 'medio' | 'primer_plano' | 'decision';

export type ModoCamara = 'auto' | 'general' | 'medio' | 'primer_plano';

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

export type UniversoHeroe = 'MARVEL' | 'DC';

export type HeroeId =
  | 'captain_america'
  | 'iron_man'
  | 'doctor_strange'
  | 'spider_man'
  | 'black_panther'
  | 'daredevil'
  | 'batman'
  | 'superman'
  | 'wonder_woman'
  | 'flash'
  | 'green_lantern'
  | 'cyborg';

export type TipoEmblemaHeroe =
  | 'escudo_estrella'
  | 'reactor_arc'
  | 'mandala'
  | 'aracnido'
  | 'pantera'
  | 'radar'
  | 'murcielago'
  | 'diamante_s'
  | 'lazo_estrella'
  | 'relampago'
  | 'anillo_linterna'
  | 'bionico';

export type TipoMascaraHeroe =
  | 'ninguna'
  | 'capucha_aletas'
  | 'visor_tech'
  | 'antifaz_tactico'
  | 'capucha_murcielago'
  | 'diadema_dorada'
  | 'capucha_aracnida';

export type EfectoPoderHeroe =
  | 'escudo_vibranium'
  | 'hud_repulsor'
  | 'runas_arcanas'
  | 'sentido_aracnido'
  | 'ondas_vibranium'
  | 'sonar_justicia'
  | 'batarang_tactico'
  | 'emblema_solar'
  | 'lazo_verdad'
  | 'estela_speedforce'
  | 'constructo_esmeralda'
  | 'escaneo_cibernetico';

export interface PerfilHeroe {
  id: HeroeId;
  universo: UniversoHeroe;
  nombre: string;
  arquetipo: string;
  valorPsicosocial: string;
  colorTraje: string;
  colorTrajeSombra: string;
  colorAcento: string;
  colorEnergia: string;
  llevaCapa: boolean;
  colorCapa?: string;
  tipoEmblema: TipoEmblemaHeroe;
  tipoMascara: TipoMascaraHeroe;
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
    bottomPx: number;
    escala: number;
    zIndex: number;
    invertido?: boolean;
  };
}
