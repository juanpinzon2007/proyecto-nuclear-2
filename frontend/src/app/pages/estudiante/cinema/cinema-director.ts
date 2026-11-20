import { ConfiguracionActor, DireccionMirada, PerfilHeroe, PlanoCamara, TemaEscena } from './cinema.types';

export interface ContextoNarrativoEscena {
  tema: TemaEscena;
  escenaOrden: number;
  contextoTexto: string;
  preguntaTexto: string;
  opcionArmada: boolean;
  opcionLanzada: boolean;
  yaRespondida: boolean;
  faseNarrativa: number; // 0 = intro/general, 1 = tension/dialogo, 2 = observacion
  heroe?: PerfilHeroe;
}

export interface ResultadoDireccionEscena {
  actores: ConfiguracionActor[];
  subEscena: string;
  subtituloNarrativo: string;
  planoSugerido: PlanoCamara;
  focoX: number; // -12..+12 porcentaje X para paneo de cámara
  focoY: number; // -8..+8 porcentaje Y
  zoomMedio: number;
  zoomPrimerPlano: number;
}

function esConfrontacionDecano(texto: string): boolean {
  const norm = texto
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase();
  return /(decano|retras|desist|encarecid|insisten)/.test(norm);
}

function crearProtagonista(
  heroe: PerfilHeroe | undefined,
  overrides: Partial<ConfiguracionActor> & { posicion: ConfiguracionActor['posicion'] },
): ConfiguracionActor {
  return {
    id: 'protagonista',
    nombre: heroe ? `Tú · ${heroe.nombre}` : 'Tú (Psicólogo/a)',
    rol: heroe ? `${heroe.universo} · ${heroe.arquetipo}` : 'Protagonista',
    pielClara: '#e5b899',
    pielSombra: '#bf8966',
    cabelloColor: '#1f2430',
    cabelloBrillo: '#434c63',
    estiloCabello: 'ejecutivo_corto',
    vestuario: 'protagonista',
    colorTraje: heroe?.colorTraje ?? '#153a4d',
    colorTrajeSombra: heroe?.colorTrajeSombra ?? '#0b1e29',
    colorCamisa: '#ecfeff',
    colorCorbata: heroe?.colorAcento ?? '#00bcd4',
    esProtagonista: true,
    heroe,
    expresion: 'tension',
    postura: 'sentado_firme',
    mirada: 'centro',
    retrasoRespiracionMs: 120,
    retrasoParpadeoMs: 350,
    retrasoGestoMs: 0,
    ...overrides,
  };
}

function dirigirTribunalComite(ctx: ContextoNarrativoEscena): ResultadoDireccionEscena {
  const armada = ctx.opcionArmada;
  const lanzada = ctx.opcionLanzada;
  const texto = `${ctx.contextoTexto} ${ctx.preguntaTexto}`;
  const esDecano = esConfrontacionDecano(texto);

  if (esDecano) {
    const miradaProtag: DireccionMirada = lanzada ? 'izquierda' : armada ? 'izquierda' : 'izquierda';
    const actores: ConfiguracionActor[] = [
      {
        id: 'consejero-fondo-1',
        nombre: 'Dra. Salgado',
        rol: 'Secretaría',
        pielClara: '#dca98a',
        pielSombra: '#b27a5b',
        cabelloColor: '#3a261e',
        cabelloBrillo: '#664538',
        estiloCabello: 'mono_alto',
        vestuario: 'ejecutivo',
        colorTraje: '#3b1d2a',
        colorTrajeSombra: '#220f18',
        colorCamisa: '#f1f5f9',
        expresion: 'tension',
        postura: 'sentado_firme',
        mirada: 'derecha',
        atenuado: true,
        retrasoRespiracionMs: 500,
        retrasoParpadeoMs: 1400,
        posicion: { xPct: 12, bottomPx: 66, escala: 0.82, zIndex: 2 },
      },
      {
        id: 'decano-autoridad',
        nombre: 'Dr. Montalvo (Decano)',
        rol: 'Decano',
        pielClara: '#d9ae94',
        pielSombra: '#ac7d62',
        cabelloColor: '#94a3b8',
        cabelloBrillo: '#e2e8f0',
        estiloCabello: 'canoso_peinado',
        vestuario: 'decano',
        colorTraje: '#4a1d28',
        colorTrajeSombra: '#2a0f16',
        colorCamisa: '#f8fafc',
        colorCorbata: '#d97706',
        lentes: true,
        maduro: true,
        expresion: lanzada ? 'preocupacion' : 'autoridad',
        postura: lanzada ? 'sentado_firme' : 'inclinado_adelante',
        mirada: 'derecha',
        hablando: !armada && !lanzada,
        destacado: !armada && !lanzada,
        retrasoRespiracionMs: 0,
        retrasoParpadeoMs: 900,
        posicion: { xPct: 33, bottomPx: 42, escala: 1.04, zIndex: 6 },
      },
      crearProtagonista(ctx.heroe, {
        expresion: lanzada || armada ? 'convencimiento' : 'tension',
        postura: lanzada ? 'defensa_abierta' : armada ? 'decidido' : 'retroceso_tension',
        mirada: miradaProtag,
        hablando: lanzada,
        destacado: armada || lanzada,
        posicion: { xPct: 67, bottomPx: 34, escala: 1.08, zIndex: 8 },
      }),
      {
        id: 'consejero-fondo-2',
        nombre: 'Prof. Ibáñez',
        rol: 'Vocal',
        pielClara: '#c78c68',
        pielSombra: '#956143',
        cabelloColor: '#1b1d24',
        cabelloBrillo: '#373b4a',
        estiloCabello: 'ejecutivo_corto',
        vestuario: 'ejecutivo',
        colorTraje: '#1f2937',
        colorTrajeSombra: '#0f172a',
        colorCamisa: '#e2e8f0',
        colorCorbata: '#64748b',
        expresion: 'preocupacion',
        postura: 'sentado_firme',
        mirada: 'izquierda',
        atenuado: true,
        retrasoRespiracionMs: 850,
        retrasoParpadeoMs: 2100,
        posicion: { xPct: 88, bottomPx: 66, escala: 0.82, zIndex: 2 },
      },
    ];

    return {
      actores,
      subEscena: 'INSISTENCIA_DECANO',
      subtituloNarrativo: lanzada
        ? 'Sostienes tu postura ética ante la insistencia del Decano y los miembros de la sala observan.'
        : armada
          ? 'Mantienes la mirada firme frente a la presión institucional; decisión lista para registrar.'
          : 'El Decano insiste directamente en acelerar el trámite sin citar testigos.',
      planoSugerido: lanzada ? 'decision' : armada ? 'primer_plano' : ctx.faseNarrativa === 0 ? 'general' : 'medio',
      focoX: armada || lanzada ? -10 : 7,
      focoY: armada || lanzada ? 3 : 1,
      zoomMedio: 1.15,
      zoomPrimerPlano: 1.28,
    };
  }

  // Escena de referencia: Votación unánime 4:1 bajo presión grupal (Asch)
  const miradaObservacion: DireccionMirada =
    ctx.faseNarrativa === 1 ? 'izquierda' : ctx.faseNarrativa === 2 ? 'derecha' : 'centro';
  const miradaProtagonista: DireccionMirada = lanzada || armada ? 'centro' : miradaObservacion;

  const actores: ConfiguracionActor[] = [
    {
      id: 'comite-presidencia',
      nombre: 'Dr. Navarro',
      rol: 'Presidente',
      pielClara: '#deae90',
      pielSombra: '#b58062',
      cabelloColor: '#94a3b8',
      cabelloBrillo: '#e2e8f0',
      estiloCabello: 'canoso_peinado',
      vestuario: 'decano',
      colorTraje: '#1e293b',
      colorTrajeSombra: '#0f172a',
      colorCamisa: '#f8fafc',
      colorCorbata: '#991b1b',
      lentes: true,
      maduro: true,
      expresion: lanzada ? 'preocupacion' : 'autoridad',
      postura: lanzada ? 'inclinado_adelante' : 'brazo_levantado',
      mirada: 'derecha',
      hablando: !armada && !lanzada,
      retrasoRespiracionMs: 0,
      retrasoParpadeoMs: 700,
      retrasoGestoMs: 0,
      posicion: { xPct: 14, bottomPx: 54, escala: 0.9, zIndex: 4 },
    },
    {
      id: 'comite-juridica',
      nombre: 'Dra. Salgado',
      rol: 'Jurídica',
      pielClara: '#d59a78',
      pielSombra: '#a76e4f',
      cabelloColor: '#2d1f1d',
      cabelloBrillo: '#523a36',
      estiloCabello: 'mono_alto',
      vestuario: 'ejecutivo',
      colorTraje: '#451a2b',
      colorTrajeSombra: '#280d18',
      colorCamisa: '#f1f5f9',
      expresion: lanzada ? 'tension' : 'desacuerdo',
      postura: lanzada ? 'sentado_firme' : 'brazo_levantado',
      mirada: 'derecha',
      retrasoRespiracionMs: 420,
      retrasoParpadeoMs: 1650,
      retrasoGestoMs: 360,
      posicion: { xPct: 31, bottomPx: 50, escala: 0.95, zIndex: 5 },
    },
    crearProtagonista(ctx.heroe, {
      expresion: lanzada
        ? 'convencimiento'
        : armada
          ? 'convencimiento'
          : ctx.yaRespondida
            ? 'tension'
            : 'preocupacion',
      postura: lanzada
        ? 'defensa_abierta'
        : armada
          ? 'decidido'
          : 'retroceso_tension',
      mirada: miradaProtagonista,
      hablando: lanzada,
      destacado: armada || lanzada,
      posicion: { xPct: 50, bottomPx: 30, escala: 1.07, zIndex: 8 },
    }),
    {
      id: 'comite-senior',
      nombre: 'Prof. Ibáñez',
      rol: 'Consejero',
      pielClara: '#c58761',
      pielSombra: '#915b3b',
      cabelloColor: '#181a22',
      cabelloBrillo: '#343a4c',
      estiloCabello: 'ejecutivo_corto',
      vestuario: 'ejecutivo',
      colorTraje: '#1e2433',
      colorTrajeSombra: '#0d111a',
      colorCamisa: '#e2e8f0',
      colorCorbata: '#d97706',
      expresion: lanzada ? 'preocupacion' : 'tension',
      postura: lanzada ? 'inclinado_adelante' : 'brazo_levantado',
      mirada: 'izquierda',
      retrasoRespiracionMs: 740,
      retrasoParpadeoMs: 1120,
      retrasoGestoMs: 720,
      posicion: { xPct: 69, bottomPx: 50, escala: 0.95, zIndex: 5 },
    },
    {
      id: 'comite-vocal',
      nombre: 'Lic. Vera',
      rol: 'Vocal',
      pielClara: '#ebbea1',
      pielSombra: '#c59071',
      cabelloColor: '#482d20',
      cabelloBrillo: '#784e39',
      estiloCabello: 'melena_lacia',
      vestuario: 'ejecutivo',
      colorTraje: '#253247',
      colorTrajeSombra: '#131b29',
      colorCamisa: '#f8fafc',
      expresion: lanzada ? 'inseguridad' : 'desacuerdo',
      postura: lanzada ? 'sentado_firme' : 'brazo_levantado',
      mirada: 'izquierda',
      retrasoRespiracionMs: 1080,
      retrasoParpadeoMs: 2200,
      retrasoGestoMs: 1050,
      posicion: { xPct: 86, bottomPx: 54, escala: 0.9, zIndex: 4 },
    },
  ];

  return {
    actores,
    subEscena: 'VOTACION_MAYORIA_4_1',
    subtituloNarrativo: lanzada
      ? 'Has emitido tu postura frente al pleno; la comisión detiene el voto para escuchar tu decisión.'
      : armada
        ? 'Tu postura está definida frente al voto mayoritario. Observa el consenso y confirma cuando estés listo.'
        : 'Cuatro integrantes alzan la mano en consenso unánime y dirigen su mirada esperando tu voto.',
    planoSugerido: lanzada ? 'decision' : armada ? 'primer_plano' : ctx.faseNarrativa === 0 ? 'general' : 'medio',
    focoX: 0,
    focoY: armada || lanzada ? 4 : 0,
    zoomMedio: 1.13,
    zoomPrimerPlano: 1.32,
  };
}

function dirigirLaboratorioAutoridad(ctx: ContextoNarrativoEscena): ResultadoDireccionEscena {
  const armada = ctx.opcionArmada;
  const lanzada = ctx.opcionLanzada;

  const actores: ConfiguracionActor[] = [
    {
      id: 'sujeto-lab',
      nombre: 'Participante B',
      rol: 'Sujeto Experimental',
      pielClara: '#dcb195',
      pielSombra: '#b28265',
      cabelloColor: '#3a2b24',
      cabelloBrillo: '#5c463c',
      estiloCabello: 'ejecutivo_corto',
      vestuario: 'casual',
      colorTraje: '#334155',
      colorTrajeSombra: '#1e293b',
      colorCamisa: '#cbd5e1',
      expresion: lanzada && !armada ? 'calma' : 'preocupacion',
      postura: 'retroceso_tension',
      mirada: 'derecha',
      atenuado: true,
      retrasoRespiracionMs: 300,
      retrasoParpadeoMs: 900,
      posicion: { xPct: 16, bottomPx: 66, escala: 0.84, zIndex: 2 },
    },
    crearProtagonista(ctx.heroe, {
      expresion: lanzada || armada ? 'convencimiento' : 'inseguridad',
      postura: lanzada ? 'defensa_abierta' : armada ? 'decidido' : 'retroceso_tension',
      mirada: armada || lanzada ? 'derecha' : ctx.faseNarrativa === 1 ? 'izquierda' : 'derecha',
      hablando: lanzada,
      destacado: armada || lanzada,
      posicion: { xPct: 48, bottomPx: 32, escala: 1.06, zIndex: 7 },
    }),
    {
      id: 'investigador-bata',
      nombre: 'Dr. Milgram / Director',
      rol: 'Experimentador',
      pielClara: '#e6be9f',
      pielSombra: '#ba8969',
      cabelloColor: '#525b6c',
      cabelloBrillo: '#94a3b8',
      estiloCabello: 'canoso_peinado',
      vestuario: 'bata',
      colorTraje: '#e2e8f0',
      colorTrajeSombra: '#cbd5e1',
      colorCamisa: '#0f172a',
      lentes: true,
      maduro: true,
      expresion: lanzada ? 'tension' : 'autoridad',
      postura: lanzada ? 'sentado_firme' : 'senalar_orden',
      mirada: 'izquierda',
      hablando: !armada && !lanzada,
      destacado: !armada && !lanzada,
      retrasoRespiracionMs: 650,
      retrasoParpadeoMs: 1700,
      posicion: { xPct: 79, bottomPx: 38, escala: 1.05, zIndex: 6 },
    },
  ];

  return {
    actores,
    subEscena: 'ORDEN_LABORATORIO',
    subtituloNarrativo: lanzada
      ? 'Respondes a la orden directa del investigador manteniendo tu criterio frente al bienestar del sujeto.'
      : armada
        ? 'Tu decisión ética está preparada frente al panel de control y la presión de la autoridad.'
        : 'El experimentador con bata blanca ordena continuar tras el cristal mientras el sujeto muestra malestar.',
    planoSugerido: lanzada ? 'decision' : armada ? 'primer_plano' : ctx.faseNarrativa === 0 ? 'general' : 'medio',
    focoX: armada || lanzada ? 2 : -10,
    focoY: armada || lanzada ? 3 : 0,
    zoomMedio: 1.14,
    zoomPrimerPlano: 1.28,
  };
}

function dirigirHospitalUrgencias(ctx: ContextoNarrativoEscena): ResultadoDireccionEscena {
  const armada = ctx.opcionArmada;
  const lanzada = ctx.opcionLanzada;

  const actores: ConfiguracionActor[] = [
    {
      id: 'medica-urgencias',
      nombre: 'Dra. Morales',
      rol: 'Urgencias',
      pielClara: '#d7a180',
      pielSombra: '#ab7454',
      cabelloColor: '#221c20',
      cabelloBrillo: '#4b3d46',
      estiloCabello: 'clinico_recogido',
      vestuario: 'bata',
      colorTraje: '#e2e8f0',
      colorTrajeSombra: '#bfdbfe',
      colorCamisa: '#0e7490',
      expresion: 'tension',
      postura: 'inclinado_adelante',
      mirada: 'derecha',
      hablando: !armada && !lanzada,
      destacado: !armada && !lanzada,
      retrasoRespiracionMs: 180,
      retrasoParpadeoMs: 1200,
      posicion: { xPct: 24, bottomPx: 40, escala: 1.0, zIndex: 5 },
    },
    crearProtagonista(ctx.heroe, {
      expresion: lanzada || armada ? 'convencimiento' : 'preocupacion',
      postura: lanzada ? 'defensa_abierta' : armada ? 'decidido' : 'escucha_empatica',
      mirada: ctx.faseNarrativa === 2 ? 'derecha' : 'izquierda',
      hablando: lanzada,
      destacado: armada || lanzada,
      posicion: { xPct: 52, bottomPx: 30, escala: 1.07, zIndex: 8 },
    }),
    {
      id: 'acompanante-urgencias',
      nombre: 'Familiar / Paciente',
      rol: 'Afectado',
      pielClara: '#e7bca1',
      pielSombra: '#be8c6e',
      cabelloColor: '#4a3127',
      cabelloBrillo: '#734f40',
      estiloCabello: 'ondulado_medio',
      vestuario: 'casual',
      colorTraje: '#374151',
      colorTrajeSombra: '#1f2937',
      colorCamisa: '#e5e7eb',
      expresion: lanzada ? 'calma' : 'preocupacion',
      postura: 'retroceso_tension',
      mirada: 'izquierda',
      retrasoRespiracionMs: 700,
      retrasoParpadeoMs: 2100,
      posicion: { xPct: 80, bottomPx: 44, escala: 0.96, zIndex: 5 },
    },
  ];

  return {
    actores,
    subEscena: 'CRISIS_URGENCIAS',
    subtituloNarrativo: lanzada
      ? 'Comunicas tu prioridad de intervención clínica coordinando al equipo de urgencias.'
      : 'En sala de urgencias 24H, el equipo clínico requiere una decisión inmediata y ética.',
    planoSugerido: lanzada ? 'decision' : armada ? 'primer_plano' : ctx.faseNarrativa === 0 ? 'general' : 'medio',
    focoX: 0,
    focoY: 3,
    zoomMedio: 1.14,
    zoomPrimerPlano: 1.28,
  };
}

function dirigirEntrevistaClinica(ctx: ContextoNarrativoEscena): ResultadoDireccionEscena {
  const armada = ctx.opcionArmada;
  const lanzada = ctx.opcionLanzada;

  const actores: ConfiguracionActor[] = [
    crearProtagonista(ctx.heroe, {
      expresion: lanzada ? 'calma' : armada ? 'convencimiento' : 'preocupacion',
      postura: lanzada ? 'escucha_empatica' : armada ? 'decidido' : 'escucha_empatica',
      mirada: 'derecha',
      hablando: lanzada,
      destacado: armada || lanzada,
      posicion: { xPct: 26, bottomPx: 32, escala: 1.07, zIndex: 8 },
    }),
    {
      id: 'familiar-clinico-1',
      nombre: 'Madre / Consultante',
      rol: 'Familia',
      pielClara: '#d9a483',
      pielSombra: '#ac7655',
      cabelloColor: '#36231d',
      cabelloBrillo: '#5c3d34',
      estiloCabello: 'ondulado_medio',
      vestuario: 'casual',
      colorTraje: '#3f3d56',
      colorTrajeSombra: '#232233',
      colorCamisa: '#fde68a',
      expresion: lanzada ? 'calma' : 'preocupacion',
      postura: 'inclinado_adelante',
      mirada: 'izquierda',
      hablando: !armada && !lanzada,
      destacado: !armada && !lanzada,
      retrasoRespiracionMs: 420,
      retrasoParpadeoMs: 1300,
      posicion: { xPct: 62, bottomPx: 38, escala: 1.0, zIndex: 6 },
    },
    {
      id: 'paciente-clinico-2',
      nombre: 'Joven Paciente',
      rol: 'Consultante',
      pielClara: '#e1ae8e',
      pielSombra: '#b78161',
      cabelloColor: '#231f24',
      cabelloBrillo: '#453e47',
      estiloCabello: 'melena_lacia',
      vestuario: 'casual',
      colorTraje: '#1f3a44',
      colorTrajeSombra: '#102127',
      colorCamisa: '#e2e8f0',
      expresion: lanzada ? 'calma' : 'inseguridad',
      postura: 'retroceso_tension',
      mirada: 'abajo',
      retrasoRespiracionMs: 880,
      retrasoParpadeoMs: 1950,
      posicion: { xPct: 83, bottomPx: 46, escala: 0.92, zIndex: 4 },
    },
  ];

  return {
    actores,
    subEscena: 'ENTREVISTA_CLINICA',
    subtituloNarrativo: lanzada
      ? 'Aplicas la estrategia de contención y escucha terapéutica frente a la familia.'
      : 'En consulta clínica, observas la dinámica emocional entre los consultantes mientras preparas tu intervención.',
    planoSugerido: lanzada ? 'decision' : armada ? 'primer_plano' : ctx.faseNarrativa === 0 ? 'general' : 'medio',
    focoX: armada || lanzada ? 12 : -6,
    focoY: 3,
    zoomMedio: 1.14,
    zoomPrimerPlano: 1.28,
  };
}

function dirigirProteccionRiesgo(ctx: ContextoNarrativoEscena): ResultadoDireccionEscena {
  const armada = ctx.opcionArmada;
  const lanzada = ctx.opcionLanzada;

  const actores: ConfiguracionActor[] = [
    {
      id: 'persona-protegida',
      nombre: 'Persona Protegida',
      rol: 'Usuario',
      pielClara: '#dfb093',
      pielSombra: '#b58366',
      cabelloColor: '#2d2320',
      cabelloBrillo: '#4d3d38',
      estiloCabello: 'melena_lacia',
      vestuario: 'casual',
      colorTraje: '#2b394a',
      colorTrajeSombra: '#18212d',
      colorCamisa: '#e2e8f0',
      expresion: lanzada || armada ? 'calma' : 'inseguridad',
      postura: 'retroceso_tension',
      mirada: 'derecha',
      retrasoRespiracionMs: 360,
      retrasoParpadeoMs: 800,
      posicion: { xPct: 23, bottomPx: 44, escala: 0.96, zIndex: 5 },
    },
    crearProtagonista(ctx.heroe, {
      expresion: 'convencimiento',
      postura: lanzada || armada ? 'defensa_abierta' : 'decidido',
      mirada: ctx.faseNarrativa === 1 ? 'izquierda' : 'derecha',
      hablando: lanzada,
      destacado: true,
      posicion: { xPct: 50, bottomPx: 30, escala: 1.07, zIndex: 8 },
    }),
    {
      id: 'especialista-ruta',
      nombre: 'Coord. Protección',
      rol: 'Equipo',
      pielClara: '#c88c68',
      pielSombra: '#976142',
      cabelloColor: '#1f232c',
      cabelloBrillo: '#3d4557',
      estiloCabello: 'ejecutivo_corto',
      vestuario: 'clinico',
      colorTraje: '#134e4a',
      colorTrajeSombra: '#0b2d2a',
      colorCamisa: '#f0fdfa',
      expresion: 'tension',
      postura: 'inclinado_adelante',
      mirada: 'izquierda',
      hablando: !armada && !lanzada,
      retrasoRespiracionMs: 740,
      retrasoParpadeoMs: 1750,
      posicion: { xPct: 79, bottomPx: 40, escala: 1.0, zIndex: 6 },
    },
  ];

  return {
    actores,
    subEscena: 'RESGUARDO_RIESGO',
    subtituloNarrativo: lanzada
      ? 'Activas el protocolo de resguardo priorizando integridad y confidencialidad.'
      : 'Evalúas el nivel de riesgo junto al equipo de protección para definir medidas de resguardo inmediatas.',
    planoSugerido: lanzada ? 'decision' : armada ? 'primer_plano' : ctx.faseNarrativa === 0 ? 'general' : 'medio',
    focoX: 0,
    focoY: 3,
    zoomMedio: 1.14,
    zoomPrimerPlano: 1.28,
  };
}

function dirigirRedCiudad(ctx: ContextoNarrativoEscena): ResultadoDireccionEscena {
  const armada = ctx.opcionArmada;
  const lanzada = ctx.opcionLanzada;

  const actores: ConfiguracionActor[] = [
    {
      id: 'red-derechos',
      nombre: 'Rep. Derechos',
      rol: 'Comité Territorial',
      pielClara: '#dca787',
      pielSombra: '#b17b5b',
      cabelloColor: '#2f2428',
      cabelloBrillo: '#57434a',
      estiloCabello: 'mono_alto',
      vestuario: 'ejecutivo',
      colorTraje: '#312e81',
      colorTrajeSombra: '#1e1b4b',
      colorCamisa: '#eef2ff',
      expresion: 'preocupacion',
      postura: 'inclinado_adelante',
      mirada: 'derecha',
      hablando: !armada && !lanzada,
      retrasoRespiracionMs: 250,
      retrasoParpadeoMs: 1100,
      posicion: { xPct: 21, bottomPx: 46, escala: 0.94, zIndex: 5 },
    },
    crearProtagonista(ctx.heroe, {
      expresion: lanzada || armada ? 'convencimiento' : 'neutro',
      postura: lanzada ? 'defensa_abierta' : armada ? 'decidido' : 'escucha_empatica',
      mirada: 'centro',
      hablando: lanzada,
      destacado: armada || lanzada,
      posicion: { xPct: 50, bottomPx: 30, escala: 1.07, zIndex: 8 },
    }),
    {
      id: 'red-salud',
      nombre: 'Dir. Red Salud',
      rol: 'Intersectorial',
      pielClara: '#e6bfa4',
      pielSombra: '#be8f70',
      cabelloColor: '#6b7280',
      cabelloBrillo: '#d1d5db',
      estiloCabello: 'canoso_peinado',
      vestuario: 'clinico',
      colorTraje: '#1f2937',
      colorTrajeSombra: '#0f172a',
      colorCamisa: '#f8fafc',
      lentes: true,
      maduro: true,
      expresion: lanzada ? 'convencimiento' : 'tension',
      postura: 'sentado_firme',
      mirada: 'izquierda',
      retrasoRespiracionMs: 680,
      retrasoParpadeoMs: 1900,
      posicion: { xPct: 79, bottomPx: 46, escala: 0.94, zIndex: 5 },
    },
  ];

  return {
    actores,
    subEscena: 'MESA_INTERINSTITUCIONAL',
    subtituloNarrativo: lanzada
      ? 'Articulas la ruta interinstitucional integrando criterios éticos y psicosociales.'
      : 'En mesa de articulación territorial, coordinas la respuesta institucional del caso.',
    planoSugerido: lanzada ? 'decision' : armada ? 'primer_plano' : ctx.faseNarrativa === 0 ? 'general' : 'medio',
    focoX: 0,
    focoY: 3,
    zoomMedio: 1.12,
    zoomPrimerPlano: 1.26,
  };
}

export function resolverDireccionEscena(ctx: ContextoNarrativoEscena): ResultadoDireccionEscena {
  switch (ctx.tema) {
    case 'tribunal_comite':
      return dirigirTribunalComite(ctx);
    case 'laboratorio_autoridad':
      return dirigirLaboratorioAutoridad(ctx);
    case 'hospital_urgencias':
      return dirigirHospitalUrgencias(ctx);
    case 'entrevista_clinica':
      return dirigirEntrevistaClinica(ctx);
    case 'proteccion_riesgo':
      return dirigirProteccionRiesgo(ctx);
    default:
      return dirigirRedCiudad(ctx);
  }
}
