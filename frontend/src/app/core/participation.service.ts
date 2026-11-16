import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import {
  ConsentimientoEstado, EscenarioActualRespuesta, InicioConvocatoriaSolicitud, IntentoRespuesta,
  ProgresoRespuesta, ResultadoIntentoDetalle, SeleccionSolicitud, WorkspaceIntento,
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

  // Flujo interactivo completo (consentimiento, RF-22, borradores editables RF-10, envío y resultado RF-14)
  consultarConsentimiento(convocatoriaId: string): Observable<ConsentimientoEstado> {
    return this.http.get<ConsentimientoEstado>(`${BASE}/simulacion/convocatorias/${convocatoriaId}/consentimiento`);
  }
  aceptarConsentimiento(convocatoriaId: string): Observable<{ aceptado: boolean; id_consentimiento: number; fecha_aceptacion: string }> {
    return this.http.post<{ aceptado: boolean; id_consentimiento: number; fecha_aceptacion: string }>(
      `${BASE}/simulacion/convocatorias/${convocatoriaId}/consentimiento`, {});
  }
  iniciarSimulacion(convocatoriaId: string): Observable<{ id_intento: number; numero_intento: number; estado: string; retomado: boolean }> {
    return this.http.post<{ id_intento: number; numero_intento: number; estado: string; retomado: boolean }>(
      `${BASE}/simulacion/convocatorias/${convocatoriaId}/iniciar`, {});
  }
  obtenerWorkspace(idIntento: number): Observable<WorkspaceIntento> {
    return this.http.get<WorkspaceIntento>(`${BASE}/simulacion/intentos/${idIntento}/workspace`);
  }
  guardarBorrador(idIntento: number, preguntaId: string, idOpcion: string, reflexionEstudiante?: string | null): Observable<WorkspaceIntento> {
    return this.http.put<WorkspaceIntento>(`${BASE}/simulacion/intentos/${idIntento}/borradores/${preguntaId}`, {
      id_opcion: idOpcion,
      reflexion_estudiante: reflexionEstudiante ?? null,
    });
  }
  enviarSimulacion(idIntento: number, permitirParcial = false): Observable<ResultadoIntentoDetalle> {
    return this.http.post<ResultadoIntentoDetalle>(`${BASE}/simulacion/intentos/${idIntento}/enviar`, {
      permitir_parcial: permitirParcial,
    });
  }
  resultadoSimulacion(idIntento: number): Observable<ResultadoIntentoDetalle> {
    return this.http.get<ResultadoIntentoDetalle>(`${BASE}/simulacion/intentos/${idIntento}/resultado`);
  }

  /** Recuerda el intento activo en la pestaña (el backend no expone un listado de intentos del estudiante). */
  recordarIntento(id: number): void { sessionStorage.setItem(INTENTO_KEY, String(id)); }
  intentoRecordado(): number | null {
    const v = sessionStorage.getItem(INTENTO_KEY);
    return v ? Number(v) : null;
  }
}

