import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatDividerModule } from '@angular/material/divider';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { firstValueFrom } from 'rxjs';
import { mensajeError } from '../../core/api-error';
import {
  ConsolidacionSesion,
  EstudianteDisponibleItem,
  PreparacionSesionRespuesta,
  ResultadoTecnicoRespuesta,
} from '../../core/api.models';
import { IdentityService } from '../../core/identity.service';
import { SchedulingService } from '../../core/scheduling.service';
import { UiDialogService } from '../../core/ui-dialog.service';
import { avatarUsuario } from '../../core/user-avatar';

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
    MatProgressSpinnerModule,
    MatDividerModule,
    MatSnackBarModule,
  ],
  template: `
    <div class="page">
      <div class="page-header">
        <div style="display: flex; align-items: center; gap: 10px;">
          <a mat-icon-button routerLink="/programacion" title="Volver a programación">
            <mat-icon>arrow_back</mat-icon>
          </a>
          <div>
            <p class="eyebrow">Cierre de Cohorte // RF-24 · RF-25 · RF-27</p>
            <h1>Evaluación, Ausencias y Publicación</h1>
            <p class="muted">Sesión ID: <span class="mono">{{ sesionId }}</span></p>
          </div>
        </div>
        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
          <button mat-stroked-button (click)="cargarPreparacion()" [disabled]="accionEnProgreso()">
            <mat-icon>refresh</mat-icon> Actualizar
          </button>
          <button mat-flat-button color="primary" (click)="consolidar()" [disabled]="accionEnProgreso()">
            <mat-icon>calculate</mat-icon> Consolidar Notas
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
            <mat-card-title>Estado de la Sesión y Visibilidad Estudiantil</mat-card-title>
            <mat-card-subtitle>
              Estado Sesión: <span class="chip">{{ p.estado_sesion }}</span>
              · Publicable:
              <span class="chip" [class.ok]="p.publicable" [class.bad]="!p.publicable">
                {{ p.publicable ? 'SÍ, LISTA PARA PUBLICAR' : 'CON PENDIENTES' }}
              </span>
            </mat-card-subtitle>
          </mat-card-header>
          <mat-card-content style="padding-top: 16px;">
            @if (p.pendientes.length > 0) {
              <div class="warn-box" style="margin-bottom: 12px;">
                <strong class="mono amber">PENDIENTES PARA PUBLICACIÓN OFICIAL:</strong>
                <ul style="margin: 6px 0 0 18px;">
                  @for (pend of p.pendientes; track pend) {
                    <li>{{ pend }}</li>
                  }
                </ul>
              </div>
            }

            <div style="display: flex; gap: 12px; align-items: center; flex-wrap: wrap;">
              <button mat-stroked-button (click)="cambiarVisibilidad(true)" [disabled]="accionEnProgreso()">
                <mat-icon>visibility</mat-icon> Habilitar Resultados Provisionales
              </button>
              <button mat-stroked-button (click)="cambiarVisibilidad(false)" [disabled]="accionEnProgreso()">
                <mat-icon>visibility_off</mat-icon> Ocultar Provisionales
              </button>
            </div>
          </mat-card-content>
        </mat-card>

        <!-- Consolidación y Publicación Oficial -->
        @if (consolidacion(); as c) {
          <mat-card class="panel panel-green-left">
            <mat-card-header>
              <mat-card-title>Revisión Consolidada de Cohorte</mat-card-title>
              <mat-card-subtitle>
                SHA256: <span class="mono">{{ c.revision_sha256 }}</span>
              </mat-card-subtitle>
            </mat-card-header>
            <mat-card-content style="padding-top: 14px;">
              @if (filasConsolidacion().length) {
                <div class="stack stagger" style="margin-bottom: 14px;">
                  @for (f of filasConsolidacion(); track f['convocatoria_id']) {
                    <div class="cons-row">
                      <div>
                        <strong>{{ f['nombre_estudiante'] || nombreEstudianteId(f['id_estudiante']) }}</strong>
                        <span class="muted"> · {{ f['grupo_nombre'] }}</span>
                      </div>
                      <div style="display:flex; gap:10px; align-items:center; flex-wrap:wrap;">
                        <span class="chip" [class.ok]="f['situacion'] === 'COMPLETA'" [class.bad]="f['situacion'] === 'AUSENTE'">
                          {{ f['situacion'] || 'PENDIENTE' }}
                        </span>
                        <strong class="nota-val mono">{{ f['nota'] ?? '--' }} / 100</strong>
                        @if (f['id_ausencia']) {
                          <button mat-stroked-button color="accent" type="button"
                                  (click)="rectificarAusencia(f['convocatoria_id'], f['id_ausencia'])">
                            <mat-icon>undo</mat-icon> Rectificar Ausencia
                          </button>
                        }
                        @if (publicacionActiva()) {
                          <button mat-stroked-button color="primary" type="button"
                                  (click)="notificarCalificacion(f['convocatoria_id'], f['id_estudiante'])">
                            <mat-icon>mail</mat-icon> Notificar Nota (RF-27)
                          </button>
                        }
                      </div>
                    </div>
                  }
                </div>
              }

              <div style="display:flex; justify-content:space-between; align-items:center; gap:12px; flex-wrap:wrap;">
                <span class="muted">Publicar congela las notas definitivas y notifica a toda la cohorte por plataforma y correo.</span>
                <button mat-flat-button color="primary" (click)="publicarOficial(c.revision_sha256)"
                        [disabled]="!c.publicable || accionEnProgreso()">
                  <mat-icon>publish</mat-icon> Publicar Calificaciones Oficiales
                </button>
              </div>
            </mat-card-content>
          </mat-card>
        }

        <!-- Detalle Técnico de Intento -->
        @if (resultadoSeleccionado(); as res) {
          <mat-card class="panel panel-amber-left">
            <mat-card-header>
              <mat-card-title>Resultado Técnico — Intento #{{ res.id_intento }}</mat-card-title>
              <mat-card-subtitle>
                Nota: <strong class="nota-val">{{ res.nota_final }} / 100</strong> · Modalidad: {{ res.modalidad }} · Ámbito: {{ res.ambito }}
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
            <mat-card-title>Estudiantes Convocados ({{ p.convocatorias.length }})</mat-card-title>
          </mat-card-header>
          <mat-card-content style="padding-top: 16px;">
            <div class="stack stagger">
              @for (conv of p.convocatorias; track conv.id_convocatoria) {
                <div class="convocatoria-row">
                  <div class="user-inline">
                    <img class="game-avatar" [src]="avatarEstudianteId(conv.id_estudiante)" [alt]="nombreEstudianteId(conv.id_estudiante)" />
                    <div>
                      <div class="est-title">{{ nombreEstudianteId(conv.id_estudiante) }}</div>
                      <div class="mono muted" style="font-size: 11px;">Convocatoria: {{ conv.id_convocatoria }}</div>
                      <div style="margin-top:6px; display:flex; gap:6px; align-items:center; flex-wrap:wrap;">
                        <span class="chip" [class.ok]="conv.estado === 'ACTIVA'" [class.bad]="conv.estado === 'RETIRADA'">
                          {{ conv.estado }}
                        </span>
                        @if (conv.id_participacion) {
                          <span class="chip">Participación #{{ conv.id_participacion }}</span>
                        }
                      </div>
                    </div>
                  </div>

                  <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
                    @for (intento of conv.intentos; track intento.id_intento) {
                      <button mat-stroked-button color="primary" (click)="verResultadoTecnico(intento.id_intento)" [disabled]="accionEnProgreso()">
                        <mat-icon>analytics</mat-icon> Intento #{{ intento.numero }} ({{ intento.estado }})
                      </button>
                    }

                    @if (conv.id_participacion && p.estado_sesion !== 'FINALIZADO') {
                      <button mat-stroked-button color="accent" (click)="autorizarRepeticion(conv.id_estudiante)"
                              [disabled]="accionEnProgreso()" title="Autorizar un intento adicional excepcional (RF-25)">
                        <mat-icon>replay</mat-icon> Autorizar Repetición (RF-25)
                      </button>
                    }

                    @if (conv.intentos.length === 0) {
                      @if (p.estado_sesion === 'FINALIZADO') {
                        <button mat-button color="warn" (click)="marcarAusencia(conv.id_convocatoria)" [disabled]="accionEnProgreso()">
                          <mat-icon>person_off</mat-icon> Marcar Ausencia (RF-24)
                        </button>
                      } @else {
                        <span class="chip" title="Las ausencias solo pueden confirmarse cuando la sesión finalice (RF-24)">
                          Ausencia disponible al finalizar
                        </span>
                      }
                    }
                  </div>
                </div>
              }
            </div>
          </mat-card-content>
        </mat-card>
      }
    </div>
  `,
  styles: [`
    .convocatoria-row, .cons-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px 16px;
      border: 1px solid var(--line);
      background: #0b1017;
      gap: 14px;
      flex-wrap: wrap;
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

  filasConsolidacion(): Record<string, any>[] {
    const c = this.consolidacion();
    return (c?.filas as Record<string, any>[]) ?? [];
  }

  nombreEstudianteId(idEst: number | string): string {
    const e = this.estudiantes().find((x) => String(x.id_usuario) === String(idEst));
    return e ? `${e.nombre} (${e.correo})` : `Estudiante #${idEst}`;
  }

  avatarEstudianteId(idEst: number | string): string {
    const e = this.estudiantes().find((x) => String(x.id_usuario) === String(idEst));
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
      eyebrow: 'Acta Oficial // RF-13 · RF-27',
      titulo: 'Publicar Calificaciones Oficiales',
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
      eyebrow: 'Inasistencia Académica // RF-24',
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
      eyebrow: 'Rectificación Académica // RF-24',
      titulo: 'Anular o Rectificar Ausencia',
      mensaje: 'Indica el motivo académico por el cual se rectifica o anula la ausencia registrada.',
      etiquetaCampo: 'Motivo de rectificación',
      placeholder: 'Ej: Excusa médica o reprogramación autorizada.',
      botonConfirmar: 'Rectificar Ausencia',
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
      this.snack.open('Repetición excepcional autorizada (RF-25).', 'OK', { duration: 3500 });
    } catch (err) {
      this.error.set(mensajeError(err));
    } finally {
      this.accionEnProgreso.set(false);
    }
  }

  async notificarCalificacion(convocatoriaId: string, idEstudianteInt: number): Promise<void> {
    const est = this.estudiantes().find((x) => x.id_usuario === idEstudianteInt);
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
