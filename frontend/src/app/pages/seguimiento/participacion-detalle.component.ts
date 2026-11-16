import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatDividerModule } from '@angular/material/divider';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { firstValueFrom } from 'rxjs';
import { mensajeError } from '../../core/api-error';
import { DetalleParticipacion, FeedbackDocente } from '../../core/api.models';
import { IdentityService } from '../../core/identity.service';

@Component({
  selector: 'app-participacion-detalle',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    FormsModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatFormFieldModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatDividerModule,
  ],
  template: `
    <div class="page">
      <div class="page-header">
        <div style="display: flex; align-items: center; gap: 10px;">
          <a mat-icon-button routerLink="/seguimiento" title="Volver a seguimiento">
            <mat-icon>arrow_back</mat-icon>
          </a>
          <div>
            <p class="eyebrow">Revisión Individual // RF-15 · RF-25 · RF-26</p>
            <h1>Auditoría de Participación y Feedback</h1>
            <p class="muted">Participación <span class="mono">#{{ participacionId }}</span></p>
          </div>
        </div>
        @if (detalle(); as d) {
          @if (d.id_sesion) {
            <button mat-stroked-button color="accent" type="button" (click)="autorizarRepeticion(d)" [disabled]="autorizandoRep()">
              <mat-icon>replay</mat-icon> Autorizar Repetición Excepcional (RF-25)
            </button>
          }
        }
      </div>

      @if (error()) { <div class="error-box">{{ error() }}</div> }
      @if (mensajeExito()) { <div class="success-box">{{ mensajeExito() }}</div> }

      @if (cargando()) {
        <div class="center-spin">
          <mat-spinner diameter="40"></mat-spinner>
        </div>
      } @else if (detalle(); as d) {
        <mat-card class="panel panel-cyan-left">
          <mat-card-header>
            <mat-card-title>{{ d.nombre_estudiante || ('Estudiante #' + d.id_estudiante) }}</mat-card-title>
            <mat-card-subtitle>{{ d.correo_estudiante }} · Caso: {{ d.nombre_caso || d.id_caso }}</mat-card-subtitle>
          </mat-card-header>
          <mat-card-content style="padding-top: 16px; display:flex; gap:18px; flex-wrap:wrap; align-items:center;">
            <div class="metric-tile">
              <small>ESTADO</small>
              <span class="chip ok">{{ d.estado }}</span>
            </div>
            @if (d.nota_final !== null && d.nota_final !== undefined) {
              <div class="metric-tile">
                <small>CALIFICACIÓN ({{ d.modalidad }})</small>
                <strong class="nota-big mono">{{ d.nota_final | number:'1.1-2' }} / 100</strong>
              </div>
            }
            @if (d.intentos?.length) {
              <div class="metric-tile">
                <small>INTENTOS REGISTRADOS</small>
                <strong class="mono cyan">{{ d.intentos!.length }}</strong>
              </div>
            }
          </mat-card-content>
        </mat-card>

        <!-- Retroalimentación docente RF-26 -->
        <mat-card class="panel panel-green-left">
          <mat-card-header>
            <mat-card-title>Retroalimentación General Docente (RF-26)</mat-card-title>
          </mat-card-header>
          <mat-card-content style="padding-top: 16px;">
            @if (feedback(); as fb) {
              <div class="info-box">
                <div style="display: flex; justify-content: space-between; margin-bottom: 6px; gap:10px;">
                  <strong class="mono cyan">VALORACIÓN REGISTRADA</strong>
                  <span class="muted mono" style="font-size: 11px;">{{ fb.fecha | date:'short' }}</span>
                </div>
                <p style="margin: 0; font-size: 14px; color: var(--text);">{{ fb.texto }}</p>
              </div>
            } @else {
              <p class="muted">No se ha registrado retroalimentación todavía.</p>
            }

            <form (ngSubmit)="guardarFeedback()" style="margin-top: 16px;">
              <mat-form-field appearance="outline" class="full">
                <mat-label>Redactar o actualizar retroalimentación para el estudiante</mat-label>
                <textarea matInput rows="3" [(ngModel)]="nuevoFeedbackTexto" name="nuevoFeedbackTexto" required></textarea>
              </mat-form-field>
              <div style="display: flex; justify-content: flex-end;">
                <button mat-flat-button color="primary" type="submit" [disabled]="enviandoFeedback()">
                  <mat-icon>send</mat-icon> Guardar y Notificar Feedback
                </button>
              </div>
            </form>
          </mat-card-content>
        </mat-card>

        <!-- Decisiones registradas -->
        <mat-card class="panel">
          <mat-card-header>
            <mat-card-title>Decisiones y Justificaciones ({{ d.respuestas.length }})</mat-card-title>
          </mat-card-header>
          <mat-card-content style="padding-top: 16px;">
            @if (d.respuestas.length === 0) {
              <p class="muted">No hay respuestas registradas en esta participación.</p>
            } @else {
              <div class="stack stagger" style="gap:12px;">
                @for (r of d.respuestas; track r.id_pregunta + '_' + r.numero_paso) {
                  <div class="respuesta-box" [class.ok-resp]="r.es_correcta === true" [class.bad-resp]="r.es_correcta === false">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px; gap:10px; flex-wrap:wrap;">
                      <strong style="color:var(--text);">{{ r.enunciado_pregunta || ('Pregunta ' + r.id_pregunta) }}</strong>
                      <div style="display:flex; gap:6px; align-items:center;">
                        @if (r.numero_paso) {
                          <span class="chip">Paso #{{ r.numero_paso }}</span>
                        }
                        @if (r.es_correcta !== null && r.es_correcta !== undefined) {
                          <span class="chip" [class.ok]="r.es_correcta" [class.bad]="!r.es_correcta">
                            {{ r.es_correcta ? 'CORRECTA' : 'INCORRECTA' }}
                          </span>
                        }
                      </div>
                    </div>
                    <div>
                      <strong class="cyan">Respuesta elegida:</strong>
                      <span style="margin-left: 8px; color:var(--text);">{{ r.texto_opcion || r.id_opcion || 'Sin responder' }}</span>
                    </div>
                    @if (r.reflexion_estudiante) {
                      <div class="refl-box">
                        <strong class="mono cyan" style="font-size: 11px;">REFLEXIÓN DEL ESTUDIANTE:</strong>
                        <p style="margin: 4px 0 0;">{{ r.reflexion_estudiante }}</p>
                      </div>
                    }
                    @if (r.retroalimentacion) {
                      <div class="muted" style="font-size: 12px; margin-top: 8px;">
                        <em>Justificación teórica del caso:</em> {{ r.retroalimentacion }}
                      </div>
                    }
                  </div>
                }
              </div>
            }
          </mat-card-content>
        </mat-card>
      }
    </div>
  `,
  styles: [`
    .metric-tile {
      padding: 10px 14px;
      border: 1px solid var(--line);
      background: #070a10;
      display: grid;
      gap: 4px;
    }
    .metric-tile small {
      font-family: var(--mono);
      font-size: 10px;
      color: var(--dim);
      letter-spacing: 0.8px;
    }
    .nota-big { color: var(--green) !important; font-size: 20px !important; font-weight: 700; }
    .respuesta-box {
      background: #0b1017;
      padding: 14px;
      border: 1px solid var(--line);
    }
    .respuesta-box.ok-resp { border-color: rgba(0, 232, 148, 0.55); border-left: 4px solid var(--green); }
    .respuesta-box.bad-resp { border-color: rgba(232, 67, 81, 0.55); border-left: 4px solid var(--red); }
    .refl-box {
      margin-top: 8px;
      background: #070a10;
      padding: 10px 12px;
      border: 1px solid rgba(184, 211, 214, 0.16);
      color: var(--text);
    }
    .full { width: 100%; }
  `],
})
export class ParticipacionDetalleComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly identityService = inject(IdentityService);

  participacionId = '';
  readonly detalle = signal<DetalleParticipacion | null>(null);
  readonly feedback = signal<FeedbackDocente | null>(null);

  readonly cargando = signal<boolean>(true);
  readonly enviandoFeedback = signal<boolean>(false);
  readonly autorizandoRep = signal<boolean>(false);
  readonly error = signal<string | null>(null);
  readonly mensajeExito = signal<string | null>(null);

  nuevoFeedbackTexto = '';

  ngOnInit(): void {
    this.participacionId = this.route.snapshot.paramMap.get('id') ?? '';
    if (this.participacionId) void this.cargarDetalle();
  }

  async cargarDetalle(): Promise<void> {
    this.cargando.set(true);
    this.error.set(null);
    try {
      const d = await firstValueFrom(this.identityService.detalleParticipacion(this.participacionId));
      this.detalle.set(d);
      if (d.feedback_docente) {
        this.nuevoFeedbackTexto = d.feedback_docente;
      }
      try {
        const fb = await firstValueFrom(this.identityService.feedback(this.participacionId));
        this.feedback.set(fb);
      } catch {
        // Sin feedback registrado aún
      }
    } catch (err) {
      this.error.set(mensajeError(err));
    } finally {
      this.cargando.set(false);
    }
  }

  guardarFeedback(): void {
    if (!this.nuevoFeedbackTexto.trim()) return;
    this.enviandoFeedback.set(true);
    this.error.set(null);
    this.identityService.enviarFeedback(this.participacionId, this.nuevoFeedbackTexto.trim()).subscribe({
      next: (fb) => {
        this.feedback.set(fb);
        this.mensajeExito.set('Retroalimentación guardada y notificada al estudiante.');
        this.enviandoFeedback.set(false);
      },
      error: (err) => {
        this.error.set(mensajeError(err));
        this.enviandoFeedback.set(false);
      },
    });
  }

  async autorizarRepeticion(d: DetalleParticipacion): Promise<void> {
    if (!d.id_sesion) return;
    this.autorizandoRep.set(true);
    this.error.set(null);
    try {
      await firstValueFrom(
        this.identityService.autorizarRepeticion({
          id_sesion: d.id_sesion,
          id_estudiante: d.id_estudiante,
        }),
      );
      this.mensajeExito.set('Autorización excepcional de repetición concedida (RF-25).');
    } catch (err) {
      this.error.set(mensajeError(err));
    } finally {
      this.autorizandoRep.set(false);
    }
  }
}
