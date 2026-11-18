import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, firstValueFrom } from 'rxjs';
import {
  CasoDetalleResponse,
  CasoPayload,
  CasoResumenResponse,
  GrafoResponse,
  GrafoSolicitud,
  TransicionSolicitud,
  VersionResponse,
} from './api.models';

const BASE = '/api/v1/cases';

/** Endpoints y helpers del módulo Cases (docente). */
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
  republicar(versionId: string): Observable<VersionResponse> { return this.http.post<VersionResponse>(`${BASE}/${versionId}/republish`, {}); }
  clonar(versionId: string): Observable<VersionResponse> { return this.http.post<VersionResponse>(`${BASE}/${versionId}/clone`, {}); }
  grafo(versionId: string): Observable<GrafoResponse> { return this.http.get<GrafoResponse>(`${BASE}/${versionId}/graph`); }
  guardarGrafo(versionId: string, body: GrafoSolicitud): Observable<GrafoResponse> {
    return this.http.put<GrafoResponse>(`${BASE}/${versionId}/graph`, body);
  }

  /** Valida reglas editoriales mínimas antes de configurar grafo y publicar un borrador. */
  erroresPublicacion(detalle: CasoDetalleResponse): string[] {
    const errs: string[] = [];
    if (!detalle.nombre.trim()) errs.push('El caso debe tener nombre.');
    if (detalle.tiempo_estimado_min <= 0) errs.push('El tiempo estimado debe ser mayor que 0.');
    if (!detalle.escenarios.length) errs.push('El caso debe tener al menos un escenario.');

    for (const esc of detalle.escenarios) {
      if (!esc.preguntas.length) {
        errs.push(`El escenario ${esc.orden} no tiene preguntas.`);
      } else if (esc.preguntas.length !== 1) {
        errs.push(`El escenario ${esc.orden} tiene ${esc.preguntas.length} preguntas; el recorrido ejecutable admite exactamente 1 pregunta por escenario.`);
      }
      for (const preg of esc.preguntas) {
        if (preg.opciones.length < 2) errs.push(`Escenario ${esc.orden}, pregunta ${preg.orden}: requiere al menos 2 opciones.`);
        if (!preg.opciones.some((o) => o.es_correcta)) errs.push(`Escenario ${esc.orden}, pregunta ${preg.orden}: falta al menos una opción correcta.`);
        if (!preg.opciones.some((o) => !o.es_correcta)) errs.push(`Escenario ${esc.orden}, pregunta ${preg.orden}: falta al menos una opción incorrecta.`);
        for (const op of preg.opciones) {
          if (!op.justificacion?.trim()) errs.push(`Escenario ${esc.orden}, pregunta ${preg.orden}, opción ${op.orden}: falta justificación teórica.`);
        }
      }
    }

    if (!detalle.rubrica) {
      errs.push('El caso no tiene rúbrica asociada.');
    } else if (!detalle.rubrica.criterios.length) {
      errs.push('La rúbrica no tiene criterios.');
    } else {
      const suma = detalle.rubrica.criterios.reduce((acc, c) => acc + Number(c.peso), 0);
      if (Math.round(suma * 100) !== 10000) errs.push(`Los pesos de la rúbrica suman ${suma}%, deben sumar exactamente 100%.`);
      for (const crit of detalle.rubrica.criterios) {
        if (!crit.niveles.length) errs.push(`El criterio '${crit.nombre}' no tiene niveles de desempeño.`);
      }
    }
    return errs;
  }

  construirGrafoLineal(detalle: CasoDetalleResponse): GrafoSolicitud | null {
    if (!detalle.escenarios.length || !detalle.escenarios.every((e) => e.preguntas.length === 1)) {
      return null;
    }
    const transiciones: TransicionSolicitud[] = [];
    detalle.escenarios.forEach((esc, idx) => {
      const siguiente = detalle.escenarios[idx + 1];
      for (const op of esc.preguntas[0].opciones) {
        transiciones.push(
          siguiente
            ? { opcion_id: op.id, tipo: 'ESCENA', destino_id: siguiente.id }
            : { opcion_id: op.id, tipo: 'FIN', destino_id: null },
        );
      }
    });
    return {
      escenario_inicial_id: detalle.escenarios[0].id,
      transiciones,
    };
  }

  /** Completa grafo lineal si falta (cuando el borrador ya es estructuralmente válido) y publica. */
  async publicarInteligente(versionId: string): Promise<VersionResponse> {
    const detalle = await firstValueFrom(this.obtener(versionId));
    const errores = this.erroresPublicacion(detalle);
    if (errores.length === 0) {
      const g = await firstValueFrom(this.grafo(versionId));
      const tieneInicial = g.escenas.some((e) => e.inicial);
      const transPendientes = g.escenas.some((e) =>
        e.preguntas.some((p) => p.opciones.some((o) => !o.tipo)),
      );
      if (!tieneInicial || transPendientes) {
        const lineal = this.construirGrafoLineal(detalle);
        if (lineal) {
          await firstValueFrom(this.guardarGrafo(versionId, lineal));
        }
      }
    }
    return firstValueFrom(this.publicar(versionId));
  }
}

