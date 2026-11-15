import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import {
  EscenarioActualRespuesta, InicioConvocatoriaSolicitud, IntentoRespuesta, ProgresoRespuesta, SeleccionSolicitud,
} from './api.models';

const BASE = '/api/v1';
const INTENTO_KEY = 'sps.intento';

/** Endpoints de Participation (estudiante): inicio, escenario actual, decisiones, progreso y cierre. */
@Injectable({ providedIn: 'root' })
export class ParticipationService {
  private readonly http = inject(HttpClient);

  iniciar(convocatoriaId: string, body: InicioConvocatoriaSolicitud): Observable<IntentoRespuesta> {
    return this.http.post<IntentoRespuesta>(`${BASE}/convocatorias/${convocatoriaId}/intentos`, body);
  }
  escenarioActual(idIntento: number): Observable<EscenarioActualRespuesta> {
    return this.http.get<EscenarioActualRespuesta>(`${BASE}/attempts/${idIntento}/current-scenario`);
  }
  decidir(idIntento: number, idDecision: string, body: SeleccionSolicitud): Observable<IntentoRespuesta> {
    return this.http.post<IntentoRespuesta>(`${BASE}/attempts/${idIntento}/decisions/${idDecision}`, body);
  }
  progreso(idIntento: number): Observable<ProgresoRespuesta> {
    return this.http.get<ProgresoRespuesta>(`${BASE}/attempts/${idIntento}/progress`);
  }
  finalizar(idIntento: number): Observable<IntentoRespuesta> {
    return this.http.post<IntentoRespuesta>(`${BASE}/attempts/${idIntento}/finish`, {});
  }

  /** Recuerda el intento activo en la pestaña (el backend no expone un listado de intentos del estudiante). */
  recordarIntento(id: number): void { sessionStorage.setItem(INTENTO_KEY, String(id)); }
  intentoRecordado(): number | null {
    const v = sessionStorage.getItem(INTENTO_KEY);
    return v ? Number(v) : null;
  }
}

