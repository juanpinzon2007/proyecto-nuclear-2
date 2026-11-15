import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatDividerModule } from '@angular/material/divider';
import { IdentityService } from '../../core/identity.service';
import { DetalleParticipacion, FeedbackDocente } from '../../core/api.models';
import { mensajeError } from '../../core/api-error';

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
            <h1>Auditoría de Participación</h1>
            <p class="muted">Participación ID: <span class="mono">{{ participacionId }}</span></p>
          </div>
        </div>
      </div>

      @if (error()) {
        <div class="error-box">{{ error() }}</div>
      }
      @if (mensajeExito()) {
        <div class="success-box">{{ mensajeExito() }}</div>
      }

      @if (cargando()) {
        <div style="display: flex; justify-content: center; padding: 40px;">
          <mat-spinner diameter="40"></mat-spinner>
        </div>
      } @else if (detalle(); as d) {
        <mat-card>
          <mat-card-header>
            <mat-card-title>Información del Estudiante</mat-card-title>
          </mat-card-header>
          <mat-card-content class="row" style="padding-top: 16px;">
            <div><strong>Estudiante ID:</strong> <span class="mono">{{ d.id_estudiante }}</span></div>
            <div><strong>Caso ID:</strong> <span class="mono">{{ d.id_caso }}</span></div>
            @if (d.id_sesion) {
              <div><strong>Sesión:</strong> <span class="mono">{{ d.id_sesion }}</span></div>
            }
            @if (d.estado) {
              <div><strong>Estado:</strong> <span class="chip ok">{{ d.estado }}</span></div>
            }
          </mat-card-content>
        </mat-card>

        <!-- Retroalimentación docente -->
        <mat-card style="border-left: 4px solid var(--mat-sys-primary);">
          <mat-card-header>
            <mat-card-title>Retroalimentación Docente</mat-card-title>
          </mat-card-header>
          <mat-card-content style="padding-top: 16px;">
            @if (feedback(); as fb) {
              <div class="info-box">
                <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                  <strong>Docente: {{ fb.id_docente }}</strong>
                  <span class="muted" style="font-size: 12px;">{{ fb.fecha | date:'short' }}</span>
                </div>
                <p style="margin: 0; font-size: 14px;">{{ fb.texto }}</p>
              </div>
            } @else {
              <p class="muted">No se ha registrado retroalimentación para esta participación.</p>
            }

            <form (ngSubmit)="guardarFeedback()" style="margin-top: 16px;">
              <mat-form-field appearance="outline" class="full">
                <mat-label>Redactar / Actualizar Retroalimentación para el estudiante</mat-label>
                <textarea matInput rows="3" [(ngModel)]="nuevoFeedbackTexto" name="nuevoFeedbackTexto" required placeholder="Observaciones sobre la toma de decisiones, reflexiones éticas y desempeño..."></textarea>
              </mat-form-field>
              <div style="display: flex; justify-content: flex-end;">
                <button mat-flat-button color="primary" type="submit" [disabled]="enviandoFeedback()">
                  @if (enviandoFeedback()) {
                    <mat-spinner diameter="18"></mat-spinner>
                  } @else {
                    <span>Enviar Retroalimentación</span>
                  }
                </button>
              </div>
            </form>
          </mat-card-content>
        </mat-card>

        <!-- Respuestas y decisiones tomadas -->
        <mat-card>
          <mat-card-header>
            <mat-card-title>Decisiones Registradas ({{ d.respuestas.length }})</mat-card-title>
          </mat-card-header>
          <mat-card-content style="padding-top: 16px;">
            @if (d.respuestas.length === 0) {
              <p class="muted">No hay decisiones registradas aún para esta participación.</p>
            } @else {
              <div class="stack">
                @for (r of d.respuestas; track r.id_pregunta) {
                  <div class="respuesta-box">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                      <span class="mono" style="font-size: 12px;">Pregunta: {{ r.id_pregunta }}</span>
                      @if (r.numero_paso) {
                        <span class="chip">Paso #{{ r.numero_paso }}</span>
                      }
                    </div>
                    <div>
                      <strong>Opción Seleccionada:</strong>
                      <span class="mono" style="margin-left: 8px;">{{ r.id_opcion || 'Sin responder' }}</span>
                    </div>
                    @if (r.reflexion_estudiante) {
                      <div style="margin-top: 8px; background: white; padding: 8px; border-radius: 4px; border: 1px solid var(--mat-sys-outline-variant);">
                        <strong class="muted" style="font-size: 12px;">Reflexión del estudiante:</strong>
                        <p style="margin: 4px 0 0;">{{ r.reflexion_estudiante }}</p>
                      </div>
                    }
                    @if (r.retroalimentacion) {
                      <div class="muted" style="font-size: 12px; margin-top: 6px;">
                        <em>Retroalimentación situacional:</em> {{ r.retroalimentacion }}
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
    .respuesta-box {
      background: var(--mat-sys-surface-container-low);
      padding: 12px;
      border-radius: 8px;
      border: 1px solid var(--mat-sys-outline-variant);
    }
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
  readonly error = signal<string | null>(null);
  readonly mensajeExito = signal<string | null>(null);

  nuevoFeedbackTexto = '';

  ngOnInit(): void {
    this.participacionId = this.route.snapshot.paramMap.get('id') ?? '';
    if (this.participacionId) {
      this.cargarDetalle();
    }
  }

  cargarDetalle(): void {
    this.cargando.set(true);
    this.error.set(null);

    this.identityService.detalleParticipacion(this.participacionId).subscribe({
      next: (d) => {
        this.detalle.set(d);
        this.cargando.set(false);
      },
      error: (err) => {
        this.error.set(mensajeError(err));
        this.cargando.set(false);
      },
    });

    this.identityService.feedback(this.participacionId).subscribe({
      next: (fb) => this.feedback.set(fb),
      error: () => {},
    });
  }

  guardarFeedback(): void {
    if (!this.nuevoFeedbackTexto.trim()) return;
    this.enviandoFeedback.set(true);
    this.error.set(null);
    this.mensajeExito.set(null);

    this.identityService.enviarFeedback(this.participacionId, this.nuevoFeedbackTexto.trim()).subscribe({
      next: (fb) => {
        this.feedback.set(fb);
        this.nuevoFeedbackTexto = '';
        this.enviandoFeedback.set(false);
        this.mensajeExito.set('Retroalimentación enviada al estudiante.');
      },
      error: (err) => {
        this.error.set(mensajeError(err));
        this.enviandoFeedback.set(false);
      },
    });
  }
}

