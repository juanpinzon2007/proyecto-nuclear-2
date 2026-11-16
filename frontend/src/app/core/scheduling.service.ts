import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import {
  ActualizarSesionRequest, ComprobanteAdmision, ConsolidacionSesion, ConvocatoriaDetalleResponse, ConvocatoriaResponse,
  DocenteBreve, EspacioAcademicoResponse, EspacioConAutorizaciones, EstudianteDisponibleItem, GrupoResponse,
  MiConvocatoriaItem, NotificacionResponse, PreparacionSesionRespuesta, ProgramarSesionRequest, ResultadoTecnicoRespuesta,
  SesionConAsignacionResponse, SesionResponse,
} from './api.models';

const BASE = '/scheduling';

/** Endpoints del módulo Scheduling: espacios, sesiones, convocatorias, admisión y evaluación. */
@Injectable({ providedIn: 'root' })
export class SchedulingService {
  private readonly http = inject(HttpClient);

  // Espacios académicos
  espacios(): Observable<EspacioAcademicoResponse[]> { return this.http.get<EspacioAcademicoResponse[]>(`${BASE}/espacios`); }
  crearEspacio(nombre: string): Observable<EspacioAcademicoResponse> {
    return this.http.post<EspacioAcademicoResponse>(`${BASE}/espacios`, { nombre });
  }

  // Sesiones
  sesiones(filtro: { docente_id?: string; espacio_id?: string } = {}): Observable<SesionResponse[]> {
    let params = new HttpParams();
    if (filtro.docente_id) params = params.set('docente_id', filtro.docente_id);
    if (filtro.espacio_id) params = params.set('espacio_id', filtro.espacio_id);
    return this.http.get<SesionResponse[]>(`${BASE}/sesiones`, { params });
  }
  sesion(id: string): Observable<SesionResponse> { return this.http.get<SesionResponse>(`${BASE}/sesiones/${id}`); }
  programar(body: ProgramarSesionRequest): Observable<SesionConAsignacionResponse | SesionResponse> {
    return this.http.post<SesionConAsignacionResponse | SesionResponse>(`${BASE}/sesiones`, body);
  }
  cambiarEstado(id: string, accion: 'iniciar' | 'finalizar'): Observable<SesionResponse> {
    return this.http.post<SesionResponse>(`${BASE}/sesiones/${id}/estado`, { accion });
  }

  // Convocatorias
  convocatorias(sesionId: string): Observable<ConvocatoriaDetalleResponse[]> {
    return this.http.get<ConvocatoriaDetalleResponse[]>(`${BASE}/sesiones/${sesionId}/convocatorias`);
  }
  crearConvocatoria(sesionId: string, estudianteId: string): Observable<ConvocatoriaResponse> {
    return this.http.post<ConvocatoriaResponse>(`${BASE}/sesiones/${sesionId}/convocatorias`, { estudiante_id: estudianteId });
  }
  retirarConvocatoria(sesionId: string, convocatoriaId: string): Observable<ConvocatoriaDetalleResponse> {
    return this.http.delete<ConvocatoriaDetalleResponse>(`${BASE}/sesiones/${sesionId}/convocatorias/${convocatoriaId}`);
  }

  // Admisión (estudiante)
  admision(convocatoriaId: string): Observable<ComprobanteAdmision> {
    return this.http.get<ComprobanteAdmision>(`${BASE}/convocatorias/${convocatoriaId}/admision`);
  }
  solicitarEspera(convocatoriaId: string, codigoAcceso: string): Observable<ComprobanteAdmision> {
    return this.http.post<ComprobanteAdmision>(`${BASE}/convocatorias/${convocatoriaId}/espera`, { codigo_acceso: codigoAcceso });
  }
  validarIngreso(convocatoriaId: string, estudianteId: string, codigoAcceso: string): Observable<SesionResponse> {
    return this.http.post<SesionResponse>(`${BASE}/validar-ingreso`,
      { convocatoria_id: convocatoriaId, estudiante_id: estudianteId, codigo_acceso: codigoAcceso });
  }
  notificaciones(destinatarioId: string): Observable<NotificacionResponse[]> {
    return this.http.get<NotificacionResponse[]>(`${BASE}/notificaciones`, { params: { destinatario_id: destinatarioId } });
  }

  // Evaluación (docente)
  preparacion(sesionId: string): Observable<PreparacionSesionRespuesta> {
    return this.http.get<PreparacionSesionRespuesta>(`${BASE}/sesiones/${sesionId}/evaluacion/preparacion`);
  }
  resultadoTecnico(sesionId: string, idIntento: number): Observable<ResultadoTecnicoRespuesta> {
    return this.http.get<ResultadoTecnicoRespuesta>(`${BASE}/sesiones/${sesionId}/evaluacion/intentos/${idIntento}/resultado-tecnico`);
  }
  calcularResultadoTecnico(sesionId: string, idIntento: number): Observable<ResultadoTecnicoRespuesta> {
    return this.http.post<ResultadoTecnicoRespuesta>(
      `${BASE}/sesiones/${sesionId}/evaluacion/intentos/${idIntento}/resultado-tecnico`, {});
  }
  consolidacion(sesionId: string): Observable<ConsolidacionSesion> {
    return this.http.get<ConsolidacionSesion>(`${BASE}/sesiones/${sesionId}/evaluacion/consolidacion`);
  }
  registrarAusencia(sesionId: string, convocatoriaId: string, motivo: string): Observable<unknown> {
    return this.http.post(`${BASE}/sesiones/${sesionId}/evaluacion/convocatorias/${convocatoriaId}/ausencia`, { motivo });
  }
  rectificarAusencia(sesionId: string, convocatoriaId: string, motivo: string, idConfirmacion: string): Observable<unknown> {
    return this.http.post(`${BASE}/sesiones/${sesionId}/evaluacion/convocatorias/${convocatoriaId}/ausencia/rectificacion`,
      { motivo, id_confirmacion: idConfirmacion });
  }
  publicaciones(sesionId: string): Observable<unknown> {
    return this.http.get(`${BASE}/sesiones/${sesionId}/evaluacion/publicaciones`);
  }
  publicar(sesionId: string, revisionSha256: string): Observable<unknown> {
    return this.http.post(`${BASE}/sesiones/${sesionId}/evaluacion/publicaciones`, { revision_sha256: revisionSha256 });
  }
  visibilidad(sesionId: string, mostrarProvisional: boolean): Observable<unknown> {
    return this.http.put(`${BASE}/sesiones/${sesionId}/evaluacion/visibilidad`, { mostrar_provisional: mostrarProvisional });
  }
  notificarCalificacion(estudianteId: string, participacionId: string): Observable<{ notificado: boolean; notificacion_id: string }> {
    return this.http.post<{ notificado: boolean; notificacion_id: string }>(`${BASE}/calificaciones/notificar`, {
      estudiante_id: estudianteId,
      participacion_id: participacionId,
    });
  }

  // Organización académica RF-04 & edición sesiones RF-21 & portal estudiante
  todosEspacios(): Observable<EspacioConAutorizaciones[]> {
    return this.http.get<EspacioConAutorizaciones[]>(`${BASE}/espacios/todos`);
  }
  autorizarEspacio(espacioId: string, idDocente?: number): Observable<unknown> {
    return this.http.post(`${BASE}/espacios/${espacioId}/autorizar`, idDocente !== undefined ? { id_docente: idDocente } : {});
  }
  docentes(): Observable<DocenteBreve[]> {
    return this.http.get<DocenteBreve[]>(`${BASE}/docentes`);
  }
  estudiantes(): Observable<EstudianteDisponibleItem[]> {
    return this.http.get<EstudianteDisponibleItem[]>(`${BASE}/estudiantes`);
  }
  grupos(): Observable<GrupoResponse[]> {
    return this.http.get<GrupoResponse[]>(`${BASE}/grupos`);
  }
  crearGrupo(nombre: string, periodo: string, idProfesor?: number): Observable<GrupoResponse> {
    return this.http.post<GrupoResponse>(`${BASE}/grupos`, idProfesor !== undefined ? { nombre, periodo, id_profesor: idProfesor } : { nombre, periodo });
  }
  matricularEstudiante(grupoId: number, idUsuario: number): Observable<GrupoResponse> {
    return this.http.post<GrupoResponse>(`${BASE}/grupos/${grupoId}/estudiantes`, { id_usuario: idUsuario });
  }
  retirarEstudiante(grupoId: number, idUsuario: number): Observable<GrupoResponse> {
    return this.http.delete<GrupoResponse>(`${BASE}/grupos/${grupoId}/estudiantes/${idUsuario}`);
  }
  actualizarSesion(sesionId: string, body: ActualizarSesionRequest): Observable<SesionResponse> {
    return this.http.patch<SesionResponse>(`${BASE}/sesiones/${sesionId}`, body);
  }
  misConvocatorias(): Observable<MiConvocatoriaItem[]> {
    return this.http.get<MiConvocatoriaItem[]>(`${BASE}/mis-convocatorias`);
  }
  resultadoEstudiante(convocatoriaId: string): Observable<unknown> {
    return this.http.get(`${BASE}/convocatorias/${convocatoriaId}/resultado`);
  }
}

