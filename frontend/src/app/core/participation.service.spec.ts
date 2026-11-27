import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { firstValueFrom, Observable } from 'rxjs';
import { afterEach, beforeEach, expect, it } from 'vitest';
import { ParticipationService } from './participation.service';

let api: ParticipationService;
let http: HttpTestingController;
beforeEach(() => {
  TestBed.configureTestingModule({providers: [provideHttpClient(), provideHttpClientTesting()]});
  api = TestBed.inject(ParticipationService);
  http = TestBed.inject(HttpTestingController);
});
afterEach(() => http.verify());

const inicio = { id_asignacion: 2, codigo_acceso: '078912', id_consentimiento: 15 };
const decision = { id_opcion: 'opcion-2' };
const casos: [string, string, unknown, () => Observable<unknown>][] = [
  ['POST', 'convocatorias/c/intentos', inicio, () => api.iniciar('c', inicio)],
  ['GET', 'attempts/4/current-scenario', null, () => api.escenarioActual(4)],
  ['POST', 'attempts/4/decisions/p', decision, () => api.decidir(4, 'p', decision)],
  ['GET', 'attempts/4/progress', null, () => api.progreso(4)],
  ['POST', 'attempts/4/finish', {}, () => api.finalizar(4)],
  ['GET', 'simulacion/convocatorias/c/consentimiento', null, () => api.consultarConsentimiento('c')],
  ['POST', 'simulacion/convocatorias/c/consentimiento', {}, () => api.aceptarConsentimiento('c')],
  ['POST', 'simulacion/convocatorias/c/iniciar', {}, () => api.iniciarSimulacion('c')],
  ['GET', 'simulacion/intentos/4/workspace', null, () => api.obtenerWorkspace(4)],
  ['PUT', 'simulacion/intentos/4/borradores/p', { id_opcion: 'o', reflexion_estudiante: null }, () => api.guardarBorrador(4, 'p', 'o')],
  ['PUT', 'simulacion/intentos/4/borradores/p', { id_opcion: 'o', reflexion_estudiante: 'mi decisión' }, () => api.guardarBorrador(4, 'p', 'o', 'mi decisión')],
  ['POST', 'simulacion/intentos/4/enviar', { permitir_parcial: false }, () => api.enviarSimulacion(4)],
  ['POST', 'simulacion/intentos/4/enviar', { permitir_parcial: true }, () => api.enviarSimulacion(4, true)],
  ['GET', 'simulacion/intentos/4/resultado', null, () => api.resultadoSimulacion(4)],
];
it.each(casos)('%s %s conserva los datos de la solicitud y la respuesta', async (method, ruta, body, ejecutar) => {
  const respuesta = firstValueFrom(ejecutar());
  const req = http.expectOne({method, url: '/api/v1/' + ruta});
  expect(req.request.body).toEqual(body);
  req.flush({ id_intento: 4 });
  expect(await respuesta).toEqual({ id_intento: 4 });
});

it('recupera el intento activo de la pestaña', () => {
  sessionStorage.removeItem('sps.intento');
  try {
    expect(api.intentoRecordado()).toBeNull();
    api.recordarIntento(17);
    expect(api.intentoRecordado()).toBe(17);
  } finally {
    sessionStorage.removeItem('sps.intento');
  }
});
