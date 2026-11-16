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
        <div style="display: flex; align-items: center; gap: 8px;">
          <a mat-icon-button routerLink="/seguimiento" title="Volver a seguimiento">
            <mat-icon>arrow_back</mat-icon>
          </a>
          <div>
            <h1>Auditoría de Participación y Feedback (RF-15 · RF-25 · RF-26)</h1>
            <p class="muted">Participación #{{ participacionId }}</p>
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
        <div style="display: flex; justify-content: center; padding: 40px;">
          <mat-spinner diameter="40"></mat-spinner>
        </div>
      } @else if (detalle(); as d) {
        <mat-card>
          <mat-card-header>
            <mat-card-title>{{ d.nombre_estudiante || ('Estudiante #' + d.id_estudiante) }}</mat-card-title>
            <mat-card-subtitle>{{ d.correo_estudiante }} · Caso: {{ d.nombre_caso || d.id_caso }}</mat-card-subtitle>
          </mat-card-header>
          <mat-card-content style="padding-top: 14px; display:flex; gap:18px; flex-wrap:wrap; align-items:center;">
            <div><strong>Estado:</strong> <span class="chip ok">{{ d.estado }}</span></div>
            @if (d.nota_final !== null && d.nota_final !== undefined) {
              <div><strong>Nota obtenida:</strong> <strong class="nota-big">{{ d.nota_final | number:'1.1-2' }} / 100</strong> ({{ d.modalidad }})</div>
            }
            @if (d.intentos?.length) {
              <div><strong>Intentos realizados:</strong> {{ d.intentos!.length }}</div>
            }
          </mat-card-content>
        </mat-card>

        <!-- Retroalimentación docente RF-26 -->
        <mat-card style="border-left: 4px solid #10b981;">
          <mat-card-header>
            <mat-card-title>Retroalimentación General Docente (RF-26)</mat-card-title>
          </mat-card-header>
          <mat-card-content style="padding-top: 16px;">
            @if (feedback(); as fb) {
              <div class="info-box">
                <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                  <strong>Valoración registrada</strong>
                  <span class="muted" style="font-size: 12px;">{{ fb.fecha | date:'short' }}</span>
                </div>
                <p style="margin: 0; font-size: 14px;">{{ fb.texto }}</p>
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
        <mat-card>
          <mat-card-header>
            <mat-card-title>Decisiones y Justificaciones ({{ d.respuestas.length }})</mat-card-title>
          </mat-card-header>
          <mat-card-content style="padding-top: 16px;">
            @if (d.respuestas.length === 0) {
              <p class="muted">No hay respuestas registradas en esta participación.</p>
            } @else {
              <div class="stack" style="gap:12px;">
                @for (r of d.respuestas; track r.id_pregunta + '_' + r.numero_paso) {
                  <div class="respuesta-box" [class.ok-resp]="r.es_correcta === true" [class.bad-resp]="r.es_correcta === false">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px; gap:10px;">
                      <strong style="color:#f8fafc;">{{ r.enunciado_pregunta || ('Pregunta ' + r.id_pregunta) }}</strong>
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
                      <strong>Respuesta elegida:</strong>
                      <span style="margin-left: 8px; color:#cbd5e1;">{{ r.texto_opcion || r.id_opcion || 'Sin responder' }}</span>
                    </div>
                    @if (r.reflexion_estudiante) {
                      <div class="refl-box">
                        <strong class="muted" style="font-size: 12px;">Reflexión del estudiante:</strong>
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
    .nota-big { color: #34d399; font-size: 18px; }
    .info-box { background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.35); border-radius: 10px; padding: 12px; color: #e2e8f0; }
    .respuesta-box {
      background: rgba(6, 11, 22, 0.65);
      padding: 14px;
      border-radius: 10px;
      border: 1px solid rgba(255, 255, 255, 0.1);
    }
    .respuesta-box.ok-resp { border-color: rgba(16, 185, 129, 0.45); }
    .respuesta-box.bad-resp { border-color: rgba(239, 68, 68, 0.45); }
    .refl-box {
      margin-top: 8px;
      background: rgba(15, 23, 42, 0.85);
      padding: 8px 10px;
      border-radius: 6px;
      border: 1px solid rgba(255, 255, 255, 0.1);
      color: #e2e8f0;
    }
    .full { width: 100%; }
    .success-box { background: rgba(16, 185, 129, 0.14); border: 1px solid rgba(16, 185, 129, 0.45); color: #a7f3d0; padding: 12px; border-radius: 8px; margin-bottom: 12px; }
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
