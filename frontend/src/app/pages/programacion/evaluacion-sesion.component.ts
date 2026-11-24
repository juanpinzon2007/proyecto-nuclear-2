import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatDividerModule } from '@angular/material/divider';
import { MatIconModule } from '@angular/material/icon';
import { MatPaginatorModule } from '@angular/material/paginator';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { firstValueFrom } from 'rxjs';
import { mensajeError } from '../../core/api-error';
import {
  ConsolidacionSesion,
  ConvocatoriaPreparacionRespuesta,
  EstudianteDisponibleItem,
  PreparacionSesionRespuesta,
  ResultadoTecnicoRespuesta,
} from '../../core/api.models';
import { IdentityService } from '../../core/identity.service';
import { SchedulingService } from '../../core/scheduling.service';
import { UiDialogService } from '../../core/ui-dialog.service';
import { avatarUsuario } from '../../core/user-avatar';
import { ListaPaginada, etiquetaEstado } from '../../core/lista-paginada';

interface FilaCalificacion {
  convocatoria_id: string;
  id_estudiante: number;
  nombre_estudiante?: string;
  grupo_nombre?: string;
  situacion?: string;
  nota?: string | number | null;
  id_ausencia?: string | null;
}

@Component({
  selector: 'app-evaluacion-sesion',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    FormsModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatPaginatorModule,
    MatProgressSpinnerModule,
    MatDividerModule,
    MatSnackBarModule,
  ],
  template: `
    <div class="page">
      <div class="page-header">
        <div class="page-heading">
          <a mat-icon-button routerLink="/programacion" aria-label="Volver a programación" title="Volver a programación">
            <mat-icon>arrow_back</mat-icon>
          </a>
          <div>
            <p class="eyebrow">Cierre de cohorte</p>
            <h1>Evaluación, ausencias y publicación</h1>
            <p class="muted">Sesión: <span class="mono">{{ sesionId }}</span></p>
          </div>
        </div>
        <div class="action-group">
          <button mat-stroked-button (click)="cargarPreparacion()" [disabled]="accionEnProgreso()">
            <mat-icon>refresh</mat-icon> Actualizar
          </button>
        </div>
      </div>

      @if (error()) { <div class="error-box">{{ error() }}</div> }
      @if (mensajeExito()) { <div class="success-box">{{ mensajeExito() }}</div> }

      @if (cargando()) {
        <div class="center-spin">
          <mat-spinner diameter="40"></mat-spinner>
        </div>
      } @else if (preparacion(); as p) {
        <!-- Estado general -->
        <mat-card class="panel panel-cyan-left">
          <mat-card-header>
            <mat-card-title>Estado de la sesión y visibilidad de resultados</mat-card-title>
            <mat-card-subtitle>
              Estado: <span class="chip">{{ etiquetaEstado(p.estado_sesion) }}</span>
              · Publicable:
              <span class="chip" [class.ok]="p.publicable" [class.bad]="!p.publicable">
                {{ p.publicable ? 'Lista para publicar' : 'Con pendientes' }}
              </span>
            </mat-card-subtitle>
          </mat-card-header>
          <mat-card-content style="padding-top: 16px;">
            @if (p.pendientes.length > 0) {
              <div class="warn-box" style="margin-bottom: 12px;">
                <strong class="mono amber">Pendientes para la publicación oficial</strong>
                <ul style="margin: 6px 0 0 18px;">
                  @for (pend of p.pendientes; track pend) {
                    <li>{{ pend }}</li>
                  }
                </ul>
              </div>
            }

            <div class="action-group">
              <button mat-stroked-button (click)="cambiarVisibilidad(true)" [disabled]="accionEnProgreso()">
                <mat-icon>visibility</mat-icon> Mostrar resultados provisionales
              </button>
              <button mat-stroked-button (click)="cambiarVisibilidad(false)" [disabled]="accionEnProgreso()">
                <mat-icon>visibility_off</mat-icon> Ocultar resultados provisionales
              </button>
            </div>
          </mat-card-content>
        </mat-card>

        @let revision = consolidacion();
        <mat-card class="panel panel-green-left">
          <mat-card-content class="grade-panel">
            <div class="section-toolbar">
              <h2>Calificaciones</h2>
              <div class="action-group">
                <button mat-stroked-button type="button" (click)="consolidar()" [disabled]="accionEnProgreso()">
                  <mat-icon>calculate</mat-icon> Consolidar notas
                </button>
                @if (revision) {
                  <button mat-flat-button type="button" color="primary" (click)="publicarOficial(revision.revision_sha256)"
                    [disabled]="!revision.publicable || accionEnProgreso()">
                    <mat-icon>publish</mat-icon> Publicar calificaciones
                  </button>
                }
              </div>
            </div>
            @if (revision && revision.filas?.length) {
              <div class="list-tools">
                <label class="list-search">
                  <span>Buscar calificaciones</span>
                  <input #buscarNota type="search" placeholder="Estudiante, grupo o estado"
                    [value]="notas.busqueda()" (input)="notas.buscar(buscarNota.value)" />
                </label>
              </div>
              <div class="grades-scroll" tabindex="0" role="region" aria-label="Tabla de calificaciones">
                <table class="grades-table" aria-label="Calificaciones de la sesión">
                  <thead>
                    <tr><th scope="col">Estudiante</th><th scope="col">Estado</th><th scope="col">Nota</th><th scope="col">Acciones</th></tr>
                  </thead>
                  <tbody>
                    @for (f of notas.visibles(); track f.convocatoria_id) {
                      <tr>
                        <th scope="row">
                          {{ f.nombre_estudiante || nombreEstudianteId(f.id_estudiante) }}
                          @if (f.grupo_nombre) { <small>{{ f.grupo_nombre }}</small> }
                        </th>
                        <td><span class="chip" [class.ok]="f.situacion === 'COMPLETA'" [class.bad]="f.situacion === 'AUSENTE'">
                          {{ etiquetaEstado(f.situacion || 'PENDIENTE') }}
                        </span></td>
                        <td class="nota-val mono">{{ f.nota == null ? '—' : f.nota + ' / 100' }}</td>
                        <td><div class="action-group">
                          @if (f.id_ausencia) {
                            <button mat-stroked-button type="button" [disabled]="accionEnProgreso()"
                              (click)="rectificarAusencia(f.convocatoria_id, f.id_ausencia)">
                              <mat-icon>undo</mat-icon> Rectificar ausencia
                            </button>
                          }
                          @if (publicacionActiva()) {
                            <button mat-stroked-button type="button" [disabled]="accionEnProgreso()"
                              (click)="notificarCalificacion(f.convocatoria_id, f.id_estudiante)">
                              <mat-icon>mail</mat-icon> Notificar nota
                            </button>
                          }
                          @if (!f.id_ausencia && !publicacionActiva()) { <span class="muted">—</span> }
                        </div></td>
                      </tr>
                    } @empty {
                      <tr><td colspan="4">No hay calificaciones que coincidan con la búsqueda.</td></tr>
                    }
                  </tbody>
                </table>
              </div>
              <mat-paginator class="list-pager" aria-label="Paginación de calificaciones" showFirstLastButtons
                [length]="notas.filtrados().length" [pageSize]="notas.tamano()" [pageIndex]="notas.pagina()"
                [pageSizeOptions]="[10, 25, 50]" (page)="notas.cambiar($event)" />
            } @else {
              <p class="muted">{{ revision ? 'La sesión aún no tiene calificaciones para mostrar.' : 'Consolida las notas para revisar la cohorte.' }}</p>
            }
          </mat-card-content>
        </mat-card>

        <!-- Detalle Técnico de Intento -->
        @if (resultadoSeleccionado(); as res) {
          <mat-card class="panel panel-amber-left">
            <mat-card-header>
              <mat-card-title>Resultado técnico · Intento {{ res.id_intento }}</mat-card-title>
              <mat-card-subtitle>
                Nota: <strong class="nota-val">{{ res.nota_final }} / 100</strong> · Modalidad: {{ etiquetaEstado(res.modalidad) }} · Ámbito: {{ etiquetaEstado(res.ambito) }}
              </mat-card-subtitle>
            </mat-card-header>
            <mat-card-content style="padding-top: 12px;">
              <p>
                Regla: <strong>{{ res.version_regla }}</strong> · Fecha: {{ res.fecha_calculo | date:'medium' }}
                @if (res.preguntas_respondidas !== null && res.preguntas_respondidas !== undefined) {
                  · Respondidas: <strong>{{ res.preguntas_respondidas }} / {{ res.preguntas_exigidas ?? '?' }}</strong>
                }
              </p>
              <button mat-button type="button" (click)="resultadoSeleccionado.set(null)">Cerrar detalle</button>
            </mat-card-content>
          </mat-card>
        }

        <!-- Participantes Convocados -->
        <mat-card class="panel">
          <mat-card-header>
            <mat-card-title>Estudiantes convocados ({{ p.convocatorias.length }})</mat-card-title>
          </mat-card-header>
          <mat-card-content style="padding-top: 16px;">
            <div class="list-tools">
              <label class="list-search">
                <span>Buscar estudiantes convocados</span>
                <input #buscarConvocado type="search" placeholder="Nombre, correo o estado"
                  [value]="convocados.busqueda()" (input)="convocados.buscar(buscarConvocado.value)" />
              </label>
            </div>
            <div class="stack">
              @for (conv of convocados.visibles(); track conv.id_convocatoria) {
                <div class="convocatoria-row">
                  <div class="user-inline">
                    <img class="game-avatar" [src]="avatarEstudianteId(conv.id_estudiante)" [alt]="nombreEstudianteId(conv.id_estudiante)" />
                    <div>
                      <div class="est-title">{{ nombreEstudianteId(conv.id_estudiante) }}</div>
                      <div class="mono muted" style="font-size: 11px;">Convocatoria: {{ conv.id_convocatoria }}</div>
                      <div style="margin-top:6px; display:flex; gap:6px; align-items:center; flex-wrap:wrap;">
                        <span class="chip" [class.ok]="conv.estado === 'ACTIVA'" [class.bad]="conv.estado === 'RETIRADA'">
                          {{ etiquetaEstado(conv.estado) }}
                        </span>
                        @if (conv.id_participacion) {
                          <span class="chip">Participación #{{ conv.id_participacion }}</span>
                        }
                      </div>
                    </div>
                  </div>

                  <div class="action-group participant-actions">
                    @for (intento of conv.intentos; track intento.id_intento) {
                      <button mat-stroked-button color="primary" (click)="verResultadoTecnico(intento.id_intento)" [disabled]="accionEnProgreso()">
                        <mat-icon>analytics</mat-icon> Intento {{ intento.numero }} ({{ etiquetaEstado(intento.estado) }})
                      </button>
                    }

                    @if (conv.id_participacion && p.estado_sesion !== 'FINALIZADO') {
                      <button mat-stroked-button color="accent" (click)="autorizarRepeticion(conv.id_estudiante)"
                              [disabled]="accionEnProgreso()" title="Autorizar un intento adicional excepcional">
                        <mat-icon>replay</mat-icon> Autorizar repetición
                      </button>
                    }

                    @if (conv.intentos.length === 0) {
                      @if (p.estado_sesion === 'FINALIZADO') {
                        <button mat-button color="warn" (click)="marcarAusencia(conv.id_convocatoria)" [disabled]="accionEnProgreso()">
                          <mat-icon>person_off</mat-icon> Marcar ausencia
                        </button>
                      } @else {
                        <span class="chip" title="Las ausencias solo pueden confirmarse cuando la sesión finalice">
                          Ausencia disponible al finalizar
                        </span>
                      }
                    }
                  </div>
                </div>
              } @empty {
                <p class="muted">No hay estudiantes convocados que coincidan con la búsqueda.</p>
              }
            </div>
            <mat-paginator class="list-pager" aria-label="Paginación de estudiantes convocados" showFirstLastButtons
              [length]="convocados.filtrados().length" [pageSize]="convocados.tamano()" [pageIndex]="convocados.pagina()"
              [pageSizeOptions]="[10, 25, 50]" (page)="convocados.cambiar($event)" />
          </mat-card-content>
        </mat-card>
      }
    </div>
  `,
  styles: [`
    .convocatoria-row {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
      align-items: center;
      padding: 12px 16px;
      border: 1px solid var(--line);
      background: #0b1017;
      gap: 14px;
    }
    .convocatoria-row .user-inline { min-width: 0; overflow-wrap: anywhere; }
    .participant-actions { justify-content: flex-end; }
    .grade-panel { padding-top: 16px; }
    .grade-panel h2 { margin: 0; }
    .grades-scroll {
      overflow-x: auto;
      border: 1px solid var(--line);
      border-radius: 8px;
      scrollbar-color: var(--line-strong) transparent;
    }
    .grades-table { width: 100%; min-width: 570px; border-collapse: collapse; text-align: start; }
    .grades-table :is(th, td) { text-align: start; padding: 10px 14px; border-bottom: 1px solid var(--line); }
    .grades-table thead { background: var(--surface-raised); color: var(--text); }
    .grades-table tbody tr:nth-child(even) { background: #1020305e; }
    .grades-table tbody tr:last-child :is(th, td) { border-bottom: 0; }
    .grades-table small { display: block; margin-top: 3px; color: var(--muted); }
    .grades-table .nota-val { white-space: nowrap; }
    @media (max-width: 730px) {
      .convocatoria-row { grid-template-columns: minmax(0, 1fr); }
      .participant-actions { justify-content: flex-start; }
    }
    .est-title { font-weight: 700; color: var(--text); font-size: 15px; }
    .nota-val { color: var(--green); font-size: 15px; font-weight: 700; }
    .warn-box {
      background: rgba(255, 184, 0, 0.1);
      border: 1px solid rgba(255, 184, 0, 0.5);
      border-left: 4px solid var(--amber);
      color: var(--text);
      padding: 12px 14px;
    }
  `],
})
export class EvaluacionSesionComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly schedulingService = inject(SchedulingService);
  private readonly identityService = inject(IdentityService);
  private readonly snack = inject(MatSnackBar);
  private readonly uiDialog = inject(UiDialogService);

  sesionId = '';
  readonly preparacion = signal<PreparacionSesionRespuesta | null>(null);
  readonly consolidacion = signal<ConsolidacionSesion | null>(null);
  readonly publicacionActiva = signal<boolean>(false);
  readonly resultadoSeleccionado = signal<ResultadoTecnicoRespuesta | null>(null);
  readonly estudiantes = signal<EstudianteDisponibleItem[]>([]);
  private readonly estudiantesPorId = computed(() =>
    new Map(this.estudiantes().map((estudiante) => [String(estudiante.id_usuario), estudiante])),
  );
  readonly etiquetaEstado = etiquetaEstado;
  readonly notas = new ListaPaginada(
    () => (this.consolidacion()?.filas ?? []) as FilaCalificacion[],
    (fila) => `${fila.nombre_estudiante ?? ''} ${this.nombreEstudianteId(fila.id_estudiante)} ${fila.grupo_nombre ?? ''} ${fila.situacion ?? 'Pendiente'}`,
  );
  readonly convocados = new ListaPaginada(
    () => this.preparacion()?.convocatorias ?? [] as ConvocatoriaPreparacionRespuesta[],
    (fila) => `${this.nombreEstudianteId(fila.id_estudiante)} ${fila.estado}`,
  );

  readonly cargando = signal<boolean>(true);
  readonly accionEnProgreso = signal<boolean>(false);
  readonly error = signal<string | null>(null);
  readonly mensajeExito = signal<string | null>(null);

  ngOnInit(): void {
    this.sesionId = this.route.snapshot.paramMap.get('id') ?? '';
    if (this.sesionId) void this.cargarPreparacion();
  }

  async cargarPreparacion(): Promise<void> {
    this.cargando.set(true);
    this.error.set(null);
    try {
      const [prep, ests] = await Promise.all([
        firstValueFrom(this.schedulingService.preparacion(this.sesionId)),
        firstValueFrom(this.schedulingService.estudiantes()),
      ]);
      this.preparacion.set(prep);
      this.estudiantes.set(ests);
      try {
        await firstValueFrom(this.schedulingService.publicaciones(this.sesionId));
        this.publicacionActiva.set(true);
      } catch {
        this.publicacionActiva.set(false);
      }
      if (prep.estado_sesion === 'FINALIZADO') {
        try {
          const cons = await firstValueFrom(this.schedulingService.consolidacion(this.sesionId));
          this.consolidacion.set(cons);
        } catch {
          // Opcional hasta consolidar explícitamente
        }
      }
    } catch (err) {
      this.error.set(mensajeError(err));
    } finally {
      this.cargando.set(false);
    }
  }

  nombreEstudianteId(idEst: number | string): string {
    const e = this.estudiantesPorId().get(String(idEst));
    return e ? `${e.nombre} (${e.correo})` : `Estudiante #${idEst}`;
  }

  avatarEstudianteId(idEst: number | string): string {
    const e = this.estudiantesPorId().get(String(idEst));
    return avatarUsuario({
      id_usuario: e?.id_usuario ?? idEst,
      nombre: e?.nombre,
      correo: e?.correo,
      rol: 'ESTUDIANTE',
    });
  }

  async verResultadoTecnico(idIntento: number): Promise<void> {
    this.accionEnProgreso.set(true);
    this.error.set(null);
    try {
      const res = await firstValueFrom(this.schedulingService.resultadoTecnico(this.sesionId, idIntento));
      this.resultadoSeleccionado.set(res);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch {
      try {
        const res = await firstValueFrom(this.schedulingService.calcularResultadoTecnico(this.sesionId, idIntento));
        this.resultadoSeleccionado.set(res);
        window.scrollTo({ top: 0, behavior: 'smooth' });
      } catch (err) {
        this.error.set(mensajeError(err));
      }
    } finally {
      this.accionEnProgreso.set(false);
    }
  }

  async consolidar(): Promise<void> {
    this.accionEnProgreso.set(true);
    this.error.set(null);
    try {
      const data = await firstValueFrom(this.schedulingService.consolidacion(this.sesionId));
      this.consolidacion.set(data);
      this.mensajeExito.set('Sesión consolidada correctamente.');
    } catch (err) {
      this.error.set(mensajeError(err));
    } finally {
      this.accionEnProgreso.set(false);
    }
  }

  async publicarOficial(revisionSha256: string): Promise<void> {
    const ok = await this.uiDialog.confirmar({
      eyebrow: 'Acta Oficial',
      titulo: 'Publicar calificaciones oficiales',
      mensaje: 'Publicar congela las notas definitivas de la sesión, habilita el reporte oficial y notifica automáticamente a toda la cohorte.',
      botonConfirmar: 'Publicar Acta Oficial',
      botonCancelar: 'Cancelar',
      tono: 'green',
    });
    if (!ok) return;
    this.accionEnProgreso.set(true);
    this.error.set(null);
    try {
      await firstValueFrom(this.schedulingService.publicar(this.sesionId, revisionSha256));
      this.publicacionActiva.set(true);
      this.mensajeExito.set('Calificaciones oficiales publicadas y notificadas.');
      await this.cargarPreparacion();
    } catch (err) {
      this.error.set(mensajeError(err));
    } finally {
      this.accionEnProgreso.set(false);
    }
  }

  async cambiarVisibilidad(mostrar: boolean): Promise<void> {
    this.accionEnProgreso.set(true);
    try {
      await firstValueFrom(this.schedulingService.visibilidad(this.sesionId, mostrar));
      this.mensajeExito.set(`Visibilidad provisional ${mostrar ? 'habilitada' : 'ocultada'}.`);
    } catch (err) {
      this.error.set(mensajeError(err));
    } finally {
      this.accionEnProgreso.set(false);
    }
  }

  async marcarAusencia(convocatoriaId: string): Promise<void> {
    const motivo = await this.uiDialog.solicitarTexto({
      eyebrow: 'Inasistencia Académica',
      titulo: 'Confirmar Ausencia (Nota 0)',
      mensaje: 'Registra la justificación institucional o académica para confirmar la inasistencia del estudiante en esta sesión.',
      etiquetaCampo: 'Motivo de la ausencia',
      placeholder: 'Ej: Inasistencia injustificada a la sesión evaluativa.',
      botonConfirmar: 'Confirmar Ausencia',
      tono: 'warn',
    });
    if (!motivo) return;
    this.accionEnProgreso.set(true);
    try {
      await firstValueFrom(this.schedulingService.registrarAusencia(this.sesionId, convocatoriaId, motivo));
      this.mensajeExito.set('Ausencia confirmada (nota 0).');
      await this.cargarPreparacion();
    } catch (err) {
      this.error.set(mensajeError(err));
    } finally {
      this.accionEnProgreso.set(false);
    }
  }

  async rectificarAusencia(convocatoriaId: string, idConfirmacion: string): Promise<void> {
    const motivo = await this.uiDialog.solicitarTexto({
      eyebrow: 'Rectificación Académica',
      titulo: 'Anular o Rectificar ausencia',
      mensaje: 'Indica el motivo académico por el cual se rectifica o anula la ausencia registrada.',
      etiquetaCampo: 'Motivo de rectificación',
      placeholder: 'Ej: Excusa médica o reprogramación autorizada.',
      botonConfirmar: 'Rectificar ausencia',
      tono: 'amber',
    });
    if (!motivo) return;
    this.accionEnProgreso.set(true);
    try {
      await firstValueFrom(
        this.schedulingService.rectificarAusencia(this.sesionId, convocatoriaId, motivo, idConfirmacion),
      );
      this.mensajeExito.set('Ausencia rectificada correctamente.');
      await this.cargarPreparacion();
    } catch (err) {
      this.error.set(mensajeError(err));
    } finally {
      this.accionEnProgreso.set(false);
    }
  }

  async autorizarRepeticion(idEstudiante: number): Promise<void> {
    this.accionEnProgreso.set(true);
    try {
      await firstValueFrom(
        this.identityService.autorizarRepeticion({
          id_sesion: this.sesionId,
          id_estudiante: String(idEstudiante),
        }),
      );
      this.snack.open('Repetición excepcional autorizada.', 'OK', { duration: 3500 });
    } catch (err) {
      this.error.set(mensajeError(err));
    } finally {
      this.accionEnProgreso.set(false);
    }
  }

  async notificarCalificacion(convocatoriaId: string, idEstudianteInt: number): Promise<void> {
    const est = this.estudiantesPorId().get(String(idEstudianteInt));
    if (!est?.uuid_scheduling) {
      this.snack.open('El estudiante ya recibió la notificación automática al publicar.', 'OK', { duration: 3000 });
      return;
    }
    this.accionEnProgreso.set(true);
    try {
      await firstValueFrom(this.schedulingService.notificarCalificacion(est.uuid_scheduling, convocatoriaId));
      this.snack.open(`Recordatorio de calificación enviado a ${est.nombre}.`, 'OK', { duration: 3000 });
    } catch (err) {
      this.error.set(mensajeError(err));
    } finally {
      this.accionEnProgreso.set(false);
    }
  }
}
