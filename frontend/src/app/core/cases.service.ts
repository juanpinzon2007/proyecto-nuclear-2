import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import {
  CasoDetalleResponse, CasoPayload, CasoResumenResponse, GrafoResponse, GrafoSolicitud, VersionResponse,
} from './api.models';

const BASE = '/api/v1/cases';

/** Endpoints del módulo Cases (docente). */
@Injectable({ providedIn: 'root' })
export class CasesService {
  private readonly http = inject(HttpClient);

  listar(): Observable<CasoResumenResponse[]> { return this.http.get<CasoResumenResponse[]>(BASE); }
  obtener(versionId: string): Observable<CasoDetalleResponse> { return this.http.get<CasoDetalleResponse>(`${BASE}/${versionId}`); }
  crear(body: CasoPayload): Observable<VersionResponse> { return this.http.post<VersionResponse>(BASE, body); }
  actualizar(versionId: string, body: CasoPayload): Observable<VersionResponse> {
    return this.http.put<VersionResponse>(`${BASE}/${versionId}`, body);
  }
  publicar(versionId: string): Observable<VersionResponse> { return this.http.post<VersionResponse>(`${BASE}/${versionId}/publish`, {}); }
  archivar(versionId: string): Observable<VersionResponse> { return this.http.post<VersionResponse>(`${BASE}/${versionId}/archive`, {}); }
  grafo(versionId: string): Observable<GrafoResponse> { return this.http.get<GrafoResponse>(`${BASE}/${versionId}/graph`); }
  guardarGrafo(versionId: string, body: GrafoSolicitud): Observable<GrafoResponse> {
    return this.http.put<GrafoResponse>(`${BASE}/${versionId}/graph`, body);
  }
}

