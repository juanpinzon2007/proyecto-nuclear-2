import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import {
  AceptacionRespuesta, AceptarConsentimiento, ActualizarUsuarioAdminSolicitud, AutorizacionRepeticion,
  AutorizacionesDocente, CatalogoUsuariosRespuesta, CrearDocente, CrearUsuarioAdminSolicitud,
  DetalleParticipacion, DocumentoRespuesta, FeedbackDocente, PaginaDocentesRespuesta, PerfilPermisosDocentesRespuesta,
  ReporteFiltros, ResumenCaso, ResumenParticipacion, SolicitudRepeticion, UsuarioGestionItem, UsuarioPublico,
} from './api.models';

const BASE = '/api/v1/identity';

/** Endpoints de Identity: administración, consentimiento, seguimiento docente y excepciones. */
@Injectable({ providedIn: 'root' })
export class IdentityService {
  private readonly http = inject(HttpClient);

  // Administración de docentes
  listarDocentes(limite = 50, desplazamiento = 0): Observable<PaginaDocentesRespuesta> {
    const params = new HttpParams().set('limite', limite).set('desplazamiento', desplazamiento);
    return this.http.get<PaginaDocentesRespuesta>(`${BASE}/docentes`, { params });
  }
  crearDocente(body: CrearDocente): Observable<UsuarioPublico> {
    return this.http.post<UsuarioPublico>(`${BASE}/docentes`, body);
  }
  actualizarAutorizaciones(idDocente: string, body: AutorizacionesDocente): Observable<UsuarioPublico> {
    return this.http.put<UsuarioPublico>(`${BASE}/docentes/${encodeURIComponent(idDocente)}/autorizaciones`, body);
  }
  permisosRolDocente(): Observable<PerfilPermisosDocentesRespuesta> {
    return this.http.get<PerfilPermisosDocentesRespuesta>(`${BASE}/roles/docente/permisos`);
  }
  actualizarPermisosRolDocente(permisos: string[]): Observable<PerfilPermisosDocentesRespuesta> {
    return this.http.put<PerfilPermisosDocentesRespuesta>(`${BASE}/roles/docente/permisos`, { permisos });
  }
  listarUsuarios(): Observable<CatalogoUsuariosRespuesta> {
    return this.http.get<CatalogoUsuariosRespuesta>(`${BASE}/usuarios`);
  }
  crearUsuario(body: CrearUsuarioAdminSolicitud): Observable<UsuarioGestionItem> {
    return this.http.post<UsuarioGestionItem>(`${BASE}/usuarios`, body);
  }
  actualizarUsuario(idUsuario: string, body: ActualizarUsuarioAdminSolicitud): Observable<UsuarioGestionItem> {
    return this.http.patch<UsuarioGestionItem>(`${BASE}/usuarios/${encodeURIComponent(idUsuario)}`, body);
  }
  asegurarIdentidades(idUsuario: string): Observable<UsuarioGestionItem> {
    return this.http.post<UsuarioGestionItem>(`${BASE}/usuarios/${encodeURIComponent(idUsuario)}/identidades-academicas`, {});
  }
  autorizarRepeticion(body: SolicitudRepeticion): Observable<AutorizacionRepeticion> {
    return this.http.post<AutorizacionRepeticion>(`${BASE}/excepciones/repeticiones`, body);
  }

  // Consentimiento informado (estudiante)
  documentoConsentimiento(convocatoriaId: string, idAsignacion: number): Observable<DocumentoRespuesta> {
    return this.http.get<DocumentoRespuesta>(`${BASE}/convocatorias/${convocatoriaId}/asignaciones/${idAsignacion}/consentimiento`);
  }
  consultarAceptacion(convocatoriaId: string, idAsignacion: number): Observable<AceptacionRespuesta> {
    return this.http.get<AceptacionRespuesta>(
      `${BASE}/convocatorias/${convocatoriaId}/asignaciones/${idAsignacion}/consentimiento/aceptacion`);
  }
  aceptarConsentimiento(convocatoriaId: string, idAsignacion: number, body: AceptarConsentimiento): Observable<AceptacionRespuesta> {
    return this.http.post<AceptacionRespuesta>(
      `${BASE}/convocatorias/${convocatoriaId}/asignaciones/${idAsignacion}/consentimiento/aceptacion`, body);
  }

  // Seguimiento docente
  casosSeguimiento(): Observable<ResumenCaso[]> {
    return this.http.get<ResumenCaso[]>(`${BASE}/seguimiento/casos`);
  }
  participacionesCaso(idCaso: string): Observable<ResumenParticipacion[]> {
    return this.http.get<ResumenParticipacion[]>(`${BASE}/seguimiento/casos/${encodeURIComponent(idCaso)}/participaciones`);
  }
  detalleParticipacion(id: string): Observable<DetalleParticipacion> {
    return this.http.get<DetalleParticipacion>(`${BASE}/seguimiento/participaciones/${encodeURIComponent(id)}`);
  }
  feedback(id: string): Observable<FeedbackDocente> {
    return this.http.get<FeedbackDocente>(`${BASE}/seguimiento/participaciones/${encodeURIComponent(id)}/feedback`);
  }
  enviarFeedback(id: string, texto: string): Observable<FeedbackDocente> {
    return this.http.post<FeedbackDocente>(`${BASE}/seguimiento/participaciones/${encodeURIComponent(id)}/feedback`, { texto });
  }
  reporteSesion(idSesion: string, filtros: ReporteFiltros): Observable<Blob> {
    let params = new HttpParams();
    for (const [k, v] of Object.entries(filtros)) {
      if (v === null || v === undefined || v === '') continue;
      if (Array.isArray(v)) v.forEach((x) => (params = params.append(k, x)));
      else params = params.set(k, String(v));
    }
    return this.http.get(`${BASE}/seguimiento/sesiones/${encodeURIComponent(idSesion)}/reporte`, { params, responseType: 'blob' });
  }
  reporteProvisionalSesion(idSesion: string, formato: 'xlsx' | 'pdf'): Observable<Blob> {
    const params = new HttpParams().set('formato', formato);
    return this.http.get(`${BASE}/seguimiento/sesiones/${encodeURIComponent(idSesion)}/reporte-provisional`, {
      params,
      responseType: 'blob',
    });
  }
}

