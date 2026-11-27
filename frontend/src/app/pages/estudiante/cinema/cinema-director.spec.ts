import { describe, expect, it } from 'vitest';
import { resolverDireccionEscena } from './cinema-director';
import type { PlanoCamara, SubEscena, TemaEscena } from './cinema.types';

const escenarios: [TemaEscena, string, SubEscena][] = [
  ['tribunal_comite', 'El decano interviene', 'INSISTENCIA_DECANO'],
  ['tribunal_comite', 'El comité vota', 'VOTACION_MAYORIA_4_1'],
  ['laboratorio_autoridad', '', 'ORDEN_LABORATORIO'],
  ['hospital_urgencias', '', 'CRISIS_URGENCIAS'],
  ['entrevista_clinica', '', 'ENTREVISTA_CLINICA'],
  ['proteccion_riesgo', '', 'RESGUARDO_RIESGO'],
  ['red_ciudad', '', 'MESA_INTERINSTITUCIONAL'],
];
const fases: [PlanoCamara, number, boolean, boolean][] = [
  ['general', 0, false, false],
  ['medio', 1, false, false],
  ['primer_plano', 1, true, false],
  ['decision', 1, true, true],
];

describe.each(escenarios)('%s · %s', (tema, contextoTexto, subEscena) => {
  it.each(fases)('elige el plano %s y conserva al protagonista', (plano, faseNarrativa, opcionArmada, opcionLanzada) => {
    const escena = resolverDireccionEscena({
      tema, contextoTexto, faseNarrativa, opcionArmada, opcionLanzada,
      escenaOrden: 1, preguntaTexto: '', yaRespondida: false,
    });
    expect(escena.planoSugerido).toBe(plano);
    expect(escena.subEscena).toBe(subEscena);
    const protagonistas = escena.actores.filter(actor => actor.esProtagonista);
    expect(protagonistas).toHaveLength(1);
    if (subEscena === 'INSISTENCIA_DECANO') {
      expect(protagonistas[0].mirada).toBe('izquierda');
    }
  });
});
