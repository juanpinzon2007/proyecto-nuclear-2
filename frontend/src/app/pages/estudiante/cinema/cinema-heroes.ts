import { ConfiguracionActor, HeroeId, PerfilHeroe, TemaEscena } from './cinema.types';

export const CATALOGO_HEROES: Record<HeroeId, PerfilHeroe> = {
  cobalto: {
    id: 'cobalto',
    nombre: 'Cobalto',
    arquetipo: 'Centinela de integridad',
    valorPsicosocial: 'Sostiene su criterio ético aunque todo el grupo vote lo contrario.',
    colorTraje: '#293e6b',
    colorTrajeSombra: '#141f38',
    colorAcento: '#cddceb',
    colorEnergia: '#88cfff',
    efectoPoder: 'escudo',
  },
  dinamo: {
    id: 'dinamo',
    nombre: 'Dínamo',
    arquetipo: 'Analista de sistemas',
    valorPsicosocial: 'Evalúa el impacto técnico y detiene protocolos que ponen a alguien en riesgo.',
    colorTraje: '#9a462b',
    colorTrajeSombra: '#442319',
    colorAcento: '#ffd286',
    colorEnergia: '#ffb871',
    efectoPoder: 'destello',
  },
  astral: {
    id: 'astral',
    nombre: 'Astral',
    arquetipo: 'Guardiana de perspectiva',
    valorPsicosocial: 'Anticipa consecuencias y considera a quienes pueden verse afectados por una decisión.',
    colorTraje: '#344476',
    colorTrajeSombra: '#192137',
    colorAcento: '#e48b4b',
    colorEnergia: '#ffc177',
    efectoPoder: 'pulso',
  },
  prisma: {
    id: 'prisma',
    nombre: 'Prisma',
    arquetipo: 'Observador empático',
    valorPsicosocial: 'Reconoce señales de malestar y las pone sobre la mesa con tacto.',
    colorTraje: '#9a495e',
    colorTrajeSombra: '#4e2436',
    colorAcento: '#f7c5c7',
    colorEnergia: '#fd8fa8',
    efectoPoder: 'destello',
  },
  bastion: {
    id: 'bastion',
    nombre: 'Bastión',
    arquetipo: 'Defensora de la dignidad',
    valorPsicosocial: 'Resiste la presión del grupo y defiende a quien está en desventaja.',
    colorTraje: '#675181',
    colorTrajeSombra: '#252033',
    colorAcento: '#cba7fa',
    colorEnergia: '#c99dff',
    efectoPoder: 'escudo',
  },
  eco: {
    id: 'eco',
    nombre: 'Eco',
    arquetipo: 'Defensora del debido proceso',
    valorPsicosocial: 'Reconoce presiones ocultas y defiende reglas justas frente a la arbitrariedad.',
    colorTraje: '#8e4650',
    colorTrajeSombra: '#41262c',
    colorAcento: '#d9bac1',
    colorEnergia: '#ff97a3',
    efectoPoder: 'pulso',
  },
  vigia: {
    id: 'vigia',
    nombre: 'Vigía',
    arquetipo: 'Estratega nocturno',
    valorPsicosocial: 'Analiza la evidencia sin ceder a intimidaciones institucionales.',
    colorTraje: '#344151',
    colorTrajeSombra: '#181f2e',
    colorAcento: '#a2ecff',
    colorEnergia: '#6cd6f6',
    efectoPoder: 'destello',
  },
  solar: {
    id: 'solar',
    nombre: 'Solar',
    arquetipo: 'Mediador del equipo',
    valorPsicosocial: 'Ayuda al grupo a recuperar la calma y orientarse hacia el bienestar común.',
    colorTraje: '#674475',
    colorTrajeSombra: '#362345',
    colorAcento: '#ffc671',
    colorEnergia: '#ffbf69',
    efectoPoder: 'pulso',
  },
  aurora: {
    id: 'aurora',
    nombre: 'Aurora',
    arquetipo: 'Clara y compasiva',
    valorPsicosocial: 'Habla con claridad y escucha con compasión a las personas y sus familias.',
    colorTraje: '#2b6c70',
    colorTrajeSombra: '#153c42',
    colorAcento: '#efd08a',
    colorEnergia: '#84f0df',
    efectoPoder: 'escudo',
  },
  pulso: {
    id: 'pulso',
    nombre: 'Pulso',
    arquetipo: 'Coordinador de respuesta',
    valorPsicosocial: 'Detecta riesgos urgentes y coordina al equipo con los recursos disponibles.',
    colorTraje: '#9c5a26',
    colorTrajeSombra: '#3d292d',
    colorAcento: '#ffcb68',
    colorEnergia: '#ffb961',
    efectoPoder: 'destello',
  },
  jade: {
    id: 'jade',
    nombre: 'Jade',
    arquetipo: 'Guardiana del resguardo',
    valorPsicosocial: 'Busca un entorno seguro para tomar decisiones bajo presión clínica.',
    colorTraje: '#366350',
    colorTrajeSombra: '#223c36',
    colorAcento: '#d6f8ce',
    colorEnergia: '#90efb3',
    efectoPoder: 'escudo',
  },
  vector: {
    id: 'vector',
    nombre: 'Vector',
    arquetipo: 'Enlace táctico',
    valorPsicosocial: 'Cruza protocolos e indicadores de seguridad antes de recomendar una acción.',
    colorTraje: '#596076',
    colorTrajeSombra: '#2c3144',
    colorAcento: '#ffbb59',
    colorEnergia: '#b7cbff',
    efectoPoder: 'pulso',
  },
};

export const HEROES_POR_TEMA: Record<TemaEscena, HeroeId[]> = {
  tribunal_comite: ['cobalto', 'vigia', 'solar', 'eco'],
  laboratorio_autoridad: ['dinamo', 'astral', 'pulso', 'vector'],
  hospital_urgencias: ['prisma', 'jade', 'aurora', 'bastion'],
  entrevista_clinica: ['aurora', 'astral', 'prisma', 'solar'],
  proteccion_riesgo: ['bastion', 'jade', 'cobalto', 'vigia'],
  red_ciudad: ['astral', 'vector', 'dinamo', 'pulso'],
};

const REPARTO_COMITE: Partial<Record<string, HeroeId>> = {
  'comite-presidencia': 'vector',
  'comite-juridica': 'aurora',
  'consejero-fondo-1': 'aurora',
  'comite-senior': 'pulso',
  'consejero-fondo-2': 'pulso',
  'comite-vocal': 'bastion',
  'decano-autoridad': 'dinamo',
};

const HEROES_REPARTO = Object.values(CATALOGO_HEROES);

export function asignarReparto(
  actores: ConfiguracionActor[],
  tema: TemaEscena,
  escenaOrden: number,
  protagonista?: PerfilHeroe,
): (ConfiguracionActor & { heroe: PerfilHeroe })[] {
  const heroePrincipal = protagonista ?? CATALOGO_HEROES[HEROES_POR_TEMA[tema][0]];
  const reservados = new Set<HeroeId>(HEROES_POR_TEMA[tema]);
  reservados.add(heroePrincipal.id);
  if (tema === 'tribunal_comite') {
    for (const id of Object.values(REPARTO_COMITE)) {
      if (id) reservados.add(id);
    }
  }

  const inicio = ((Math.max(1, escenaOrden) - 1) * 3) % HEROES_REPARTO.length;
  const suplentes = [...HEROES_REPARTO.slice(inicio), ...HEROES_REPARTO.slice(0, inicio)]
    .filter((perfil) => !reservados.has(perfil.id));
  const usados = new Set<HeroeId>([heroePrincipal.id]);

  return actores.map((actor) => {
    if (actor.esProtagonista) return { ...actor, heroe: heroePrincipal };

    const preferido = tema === 'tribunal_comite' ? REPARTO_COMITE[actor.id] : undefined;
    const heroe = preferido && !usados.has(preferido)
      ? CATALOGO_HEROES[preferido]
      : suplentes.find((perfil) => !usados.has(perfil.id))!;
    usados.add(heroe.id);
    return { ...actor, heroe };
  });
}

export function elegirHeroeAleatorio(
  tema: TemaEscena,
  excluirId?: HeroeId,
  rng: () => number = Math.random,
): PerfilHeroe {
  const candidatos = HEROES_POR_TEMA[tema] ?? HEROES_POR_TEMA.red_ciudad;
  const filtrados = excluirId && candidatos.length > 1 ? candidatos.filter((id) => id !== excluirId) : candidatos;
  const indice = Math.min(filtrados.length - 1, Math.floor(rng() * filtrados.length));
  return CATALOGO_HEROES[filtrados[Math.max(0, indice)]];
}
