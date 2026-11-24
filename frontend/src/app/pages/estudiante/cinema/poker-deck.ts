import { PerfilHeroe, TemaEscena } from './cinema.types';

export type PaloSimbolo = '♠' | '♥' | '♦' | '♣';
export type RangoCarta = 'A' | '2' | '3' | '4' | '5' | '6' | '7' | '8' | '9' | '10' | 'J' | 'Q' | 'K';

export interface CartaBaraja {
  id: string;
  rango: RangoCarta;
  simbolo: PaloSimbolo;
  nombrePalo: string;
  arquetipo: string;
  tono: 'cian' | 'magenta' | 'oro' | 'esmeralda';
  esRojo: boolean;
  ordenBaraja: number;
}

export interface ResultadoAyudaJoker {
  titulo: string;
  heroeAsesor: string;
  principioPsicosocial: string;
  contrasteEstrategico: string;
  cartaRiesgoId: string | null;
  etiquetaCartaRiesgo: string | null;
}

const RANGOS: RangoCarta[] = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K'];

const METADATA_PALOS: Array<{
  simbolo: PaloSimbolo;
  nombre: string;
  tono: CartaBaraja['tono'];
  esRojo: boolean;
  arquetipos: string[];
}> = [
  {
    simbolo: '♠',
    nombre: 'Picas',
    tono: 'cian',
    esRojo: false,
    arquetipos: ['Juicio crítico', 'Rectitud', 'Criterio ético', 'Firmeza'],
  },
  {
    simbolo: '♥',
    nombre: 'Corazones',
    tono: 'magenta',
    esRojo: true,
    arquetipos: ['Empatía', 'Bienestar', 'Vínculo', 'Cuidado'],
  },
  {
    simbolo: '♦',
    nombre: 'Diamantes',
    tono: 'oro',
    esRojo: true,
    arquetipos: ['Claridad', 'Estrategia', 'Evidencia', 'Rigor'],
  },
  {
    simbolo: '♣',
    nombre: 'Tréboles',
    tono: 'esmeralda',
    esRojo: false,
    arquetipos: ['Acción justa', 'Protocolo', 'Resguardo', 'Respuesta'],
  },
];

/** Construye exactamente las 52 cartas de la baraja inglesa estándar (A..K × ♠ ♥ ♦ ♣). */
export function crearBarajaCompleta(): CartaBaraja[] {
  const cartas: CartaBaraja[] = [];
  let orden = 1;
  for (const palo of METADATA_PALOS) {
    for (let rIdx = 0; rIdx < RANGOS.length; rIdx++) {
      const rango = RANGOS[rIdx];
      cartas.push({
        id: `${rango}${palo.simbolo}`,
        rango,
        simbolo: palo.simbolo,
        nombrePalo: palo.nombre,
        arquetipo: palo.arquetipos[rIdx % palo.arquetipos.length],
        tono: palo.tono,
        esRojo: palo.esRojo,
        ordenBaraja: orden++,
      });
    }
  }
  return cartas;
}

/** Baraja aleatoriamente las 52 cartas usando Fisher-Yates sin alterar las opciones académicas. */
export function barajarBaraja52(rng: () => number = Math.random): CartaBaraja[] {
  const mazo = crearBarajaCompleta();
  for (let i = mazo.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [mazo[i], mazo[j]] = [mazo[j], mazo[i]];
  }
  return mazo;
}

/** Reparte una mano sin repeticiones desde un índice dado de la baraja completa barajada. */
export function repartirManoDesdeBaraja(
  baraja: CartaBaraja[],
  inicio: number,
  cantidad: number,
): CartaBaraja[] {
  const origen = baraja.length === 52 ? baraja : crearBarajaCompleta();
  const res: CartaBaraja[] = [];
  for (let i = 0; i < cantidad; i++) {
    res.push(origen[(inicio + i) % origen.length]);
  }
  return res;
}

/** Genera la guía estratégica no-spoiler del Comodín JOKER basada en el contexto psicológico real. */
export function construirAyudaJoker(params: {
  tema: TemaEscena;
  contextoTexto: string;
  preguntaTexto: string;
  opciones: Array<{ id: string; texto: string }>;
  heroe?: PerfilHeroe;
}): ResultadoAyudaJoker {
  const { tema, opciones, heroe } = params;
  const mapaPrincipios: Record<TemaEscena, { principio: string; contraste: string }> = {
    tribunal_comite: {
      principio:
        'Efecto Asch y Debido Proceso: la presión de una mayoría unánime busca que invalides tu propio criterio para evitar conflicto social.',
      contraste:
        'Compara qué carta exige verificación y escucha justa de pruebas frente a las que ceden o callan por conveniencia.',
    },
    laboratorio_autoridad: {
      principio:
        'Paradigma de Milgram y No Maleficencia: una figura de autoridad no exime tu responsabilidad ética ante señales explícitas de daño.',
      contraste:
        'Distingue entre suspender/proteger la integridad del sujeto vs trasladar la culpa ejecutando una orden riesgosa.',
    },
    hospital_urgencias: {
      principio:
        'Triaje Ético y Contención en Crisis: bajo urgencia vital, prioriza seguridad clínica inmediata y comunicación clara sin improvisar.',
      contraste:
        'Evalúa qué acción estabiliza el riesgo físico/emocional respetando protocolos y derechos de la persona afectada.',
    },
    entrevista_clinica: {
      principio:
        'Modelo EPICEE y Alianza Terapéutica: la verdad clínica requiere contención empática, privacidad y validación emocional sin juicios.',
      contraste:
        'Observa qué alternativa facilita escucha activa y comprensión gradual frente a respuestas bruscas o evasivas.',
    },
    proteccion_riesgo: {
      principio:
        'Debida Diligencia y Resguardo: ante vulnerabilidad o violencia, la confidencialidad segura y la activación temprana salvan integridad.',
      contraste:
        'Contrapón las rutas de protección inmediata frente a medidas que exponen o dejan sin amparo a la persona.',
    },
    red_ciudad: {
      principio:
        'Articulación Interinstitucional: ningún actor aislado resuelve riesgos complejos; se requiere derivación coordinada y seguimiento.',
      contraste:
        'Analiza cuál opción conecta salud, derechos y protección en lugar de fragmentar o dilatar la atención.',
    },
  };

  const info = mapaPrincipios[tema] ?? mapaPrincipios.red_ciudad;

  // Descarte orientativo SOLO cuando hay >= 3 opciones para no regalar respuesta en dilemas binarios (2 opciones)
  let cartaRiesgoId: string | null = null;
  let etiquetaCartaRiesgo: string | null = null;
  if (opciones.length >= 3) {
    const patronPasivo =
      /(absten|silencio|evitar desacuerdo|ceder|continuar aplicando|ignorar|sin escuchar|ocultar|omitir)/i;
    const candidata = opciones.find((op) =>
      patronPasivo.test(
        op.texto
          .normalize('NFD')
          .replace(/[\u0300-\u036f]/g, ''),
      ),
    );
    if (candidata) {
      cartaRiesgoId = candidata.id;
      etiquetaCartaRiesgo = 'JOKER DETECTA SESGO PASIVO O CONFORMIDAD';
    }
  }

  return {
    titulo: 'COMODÍN JOKER · LECTURA TÁCTICA',
    heroeAsesor: heroe ? `${heroe.nombre} (${heroe.arquetipo})` : 'Consejo Estratégico SPS',
    principioPsicosocial: info.principio,
    contrasteEstrategico: info.contraste,
    cartaRiesgoId,
    etiquetaCartaRiesgo,
  };
}
