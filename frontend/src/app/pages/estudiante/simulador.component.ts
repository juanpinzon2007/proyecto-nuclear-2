import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatRadioModule } from '@angular/material/radio';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatDividerModule } from '@angular/material/divider';
import { ParticipationService } from '../../core/participation.service';
import { IdentityService } from '../../core/identity.service';
import { EscenarioActualRespuesta, FeedbackDocente, IntentoRespuesta, ProgresoRespuesta } from '../../core/api.models';
import { mensajeError } from '../../core/api-error';

@Component({
  selector: 'app-simulador',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    FormsModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatRadioModule,
    MatFormFieldModule,
    MatInputModule,
    MatProgressBarModule,
    MatProgressSpinnerModule,
    MatDividerModule,
  ],
  template: `
    <div class="page" style="max-width: 860px;">
      <!-- Encabezado y barra de progreso -->
      <div class="page-header">
        <div>
          <h1>Simulador de Toma de Decisiones</h1>
          <p class="muted">Intento #{{ idIntento }}</p>
        </div>
        <div>
          <a mat-stroked-button routerLink="/estudiante">
            <mat-icon>arrow_back</mat-icon> Volver al Portal
          </a>
        </div>
      </div>

      <!-- Barra de progreso -->
      @if (progreso(); as prog) {
        <mat-card style="margin-bottom: 20px;">
          <mat-card-content style="padding: 16px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px;">
              <span><strong>Progreso:</strong> {{ prog.respondidas }} decisiones respondidas</span>
              @if (prog.total_aplicable) {
                <span>Total estimado: {{ prog.total_aplicable }}</span>
              }
            </div>
            <mat-progress-bar mode="determinate" [value]="calcularPorcentajeProgreso(prog)"></mat-progress-bar>
          </mat-card-content>
        </mat-card>
      }

      @if (error()) {
        <div class="error-box">{{ error() }}</div>
      }
      @if (mensajeExito()) {
        <div class="success-box">{{ mensajeExito() }}</div>
      }

      @if (cargando()) {
        <div style="display: flex; justify-content: center; padding: 60px;">
          <mat-spinner diameter="48"></mat-spinner>
        </div>
      } @else if (simulacionFinalizada()) {
        <!-- Pantalla de Intento Finalizado -->
        <mat-card style="border-left: 6px solid #4caf50; padding: 24px; text-align: center;">
          <mat-icon style="font-size: 64px; height: 64px; width: 64px; color: #4caf50; margin: 0 auto 16px;">
            check_circle
          </mat-icon>
          <h2>¡Has finalizado la simulación con éxito!</h2>
          <p class="muted" style="max-width: 500px; margin: 0 auto 20px;">
            Tu recorrido ha sido registrado y almacenado en el sistema para la consolidación del docente y la evaluación por rúbrica.
          </p>

          @if (feedback(); as fb) {
            <div class="info-box" style="text-align: left; max-width: 600px; margin: 16px auto;">
              <strong>Retroalimentación del Docente:</strong>
              <p style="margin: 8px 0 0;">{{ fb.texto }}</p>
            </div>
          }

          <div style="margin-top: 24px;">
            <a mat-flat-button color="primary" routerLink="/estudiante">
              Volver al Portal
            </a>
          </div>
        </mat-card>
      } @else if (escenario(); as esc) {
        @if (esc.recorrido_finalizado) {
          <!-- Recorrido finalizado, listo para hacer finish -->
          <mat-card style="border-left: 4px solid var(--mat-sys-primary);">
            <mat-card-header>
              <mat-card-title>Recorrido Completado</mat-card-title>
            </mat-card-header>
            <mat-card-content style="padding-top: 16px;">
              <p>Has respondido todas las decisiones de este caso. Presiona el botón a continuación para enviar y finalizar tu intento de forma definitiva:</p>
              <button mat-flat-button color="primary" style="height: 48px; margin-top: 12px;" (click)="finalizarIntento()" [disabled]="enviando()">
                @if (enviando()) {
                  <mat-spinner diameter="20"></mat-spinner>
                } @else {
                  <span>Finalizar Intento</span>
                }
              </button>
            </mat-card-content>
          </mat-card>
        } @else {
          <!-- Escena Actual y Pregunta -->
          <mat-card style="margin-bottom: 24px;">
            <mat-card-header>
              <mat-card-title>Situación Actual</mat-card-title>
            </mat-card-header>
            <mat-card-content style="padding-top: 16px;">
              <div class="escena-contexto">
                {{ esc.contexto }}
              </div>

              @if (esc.pregunta; as p) {
                <div style="margin-top: 24px;">
                  <h3 style="margin-bottom: 16px;">{{ p.enunciado }}</h3>

                  <!-- Opciones de decisión -->
                  <div class="stack" style="gap: 12px;">
                    @for (op of p.opciones; track op.id) {
                      <div class="opcion-selectable" [class.seleccionada]="opcionSeleccionadaId === op.id" (click)="opcionSeleccionadaId = op.id">
                        <mat-radio-button [value]="op.id" [checked]="opcionSeleccionadaId === op.id">
                          <span style="font-size: 15px;">{{ op.texto }}</span>
                        </mat-radio-button>
                      </div>
                    }
                  </div>

                  <!-- Reflexión opcional del estudiante -->
                  <div style="margin-top: 20px;">
                    <mat-form-field appearance="outline" class="full">
                      <mat-label>Reflexión o justificación de tu decisión (Opcional)</mat-label>
                      <textarea matInput rows="3" [(ngModel)]="reflexionEstudiante" placeholder="Explica brevemente por qué tomaste esta decisión ante este dilema..."></textarea>
                    </mat-form-field>
                  </div>

                  <div style="display: flex; justify-content: flex-end; margin-top: 16px;">
                    <button mat-flat-button color="primary" style="height: 48px; font-size: 15px;" (click)="enviarDecision(p.id)" [disabled]="!opcionSeleccionadaId || enviando()">
                      @if (enviando()) {
                        <mat-spinner diameter="20"></mat-spinner>
                      } @else {
                        <span>Confirmar y Avanzar</span>
                      }
                    </button>
                  </div>
                </div>
              }
            </mat-card-content>
          </mat-card>
        }
      }
    </div>
  `,
  styles: [`
    .escena-contexto {
      background: var(--mat-sys-surface-container-low);
      padding: 16px;
      border-radius: 8px;
      font-size: 15px;
      line-height: 1.6;
      border-left: 4px solid var(--mat-sys-primary);
    }
    .opcion-selectable {
      padding: 12px 16px;
      border: 1px solid var(--mat-sys-outline-variant);
      border-radius: 8px;
      background: white;
      cursor: pointer;
      transition: all 0.15s;
    }
    .opcion-selectable:hover {
      border-color: var(--mat-sys-primary);
      background: var(--mat-sys-surface-container-lowest);
    }
    .opcion-selectable.seleccionada {
      border-color: var(--mat-sys-primary);
      background: var(--mat-sys-primary-container);
    }
  `],
})
export class SimuladorComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly participationService = inject(ParticipationService);
  private readonly identityService = inject(IdentityService);

  idIntento = 0;
  opcionSeleccionadaId = '';
  reflexionEstudiante = '';

  readonly escenario = signal<EscenarioActualRespuesta | null>(null);
  readonly progreso = signal<ProgresoRespuesta | null>(null);
  readonly feedback = signal<FeedbackDocente | null>(null);

  readonly cargando = signal<boolean>(true);
  readonly enviando = signal<boolean>(false);
  readonly simulacionFinalizada = signal<boolean>(false);
  readonly error = signal<string | null>(null);
  readonly mensajeExito = signal<string | null>(null);

  ngOnInit(): void {
    const rawId = this.route.snapshot.paramMap.get('id');
    this.idIntento = Number(rawId);
    if (this.idIntento) {
      this.cargarEscenarioYProgreso();
    }
  }

  cargarEscenarioYProgreso(): void {
    this.cargando.set(true);
    this.error.set(null);

    this.participationService.progreso(this.idIntento).subscribe({
      next: (p) => {
        this.progreso.set(p);
        if (p.intento.estado === 'FINALIZADO' || p.intento.estado === 'VENCIDO') {
          this.simulacionFinalizada.set(true);
          this.cargando.set(false);
          this.consultarFeedback(p.intento.id_participacion);
          return;
        }

        this.participationService.escenarioActual(this.idIntento).subscribe({
          next: (esc) => {
            this.escenario.set(esc);
            this.opcionSeleccionadaId = '';
            this.reflexionEstudiante = '';
            this.cargando.set(false);
          },
          error: (err) => {
            this.error.set(mensajeError(err));
            this.cargando.set(false);
          },
        });
      },
      error: (err) => {
        this.error.set(mensajeError(err));
        this.cargando.set(false);
      },
    });
  }

  enviarDecision(decisionId: string): void {
    if (!this.opcionSeleccionadaId) return;
    this.enviando.set(true);
    this.error.set(null);

    this.participationService.decidir(this.idIntento, decisionId, {
      id_opcion: this.opcionSeleccionadaId,
      reflexion_estudiante: this.reflexionEstudiante || null,
    }).subscribe({
      next: () => {
        this.enviando.set(false);
        this.cargarEscenarioYProgreso();
      },
      error: (err) => {
        this.error.set(mensajeError(err));
        this.enviando.set(false);
      },
    });
  }

  finalizarIntento(): void {
    this.enviando.set(true);
    this.error.set(null);

    this.participationService.finalizar(this.idIntento).subscribe({
      next: (res) => {
        this.simulacionFinalizada.set(true);
        this.enviando.set(false);
        this.consultarFeedback(res.id_participacion);
      },
      error: (err) => {
        this.error.set(mensajeError(err));
        this.enviando.set(false);
      },
    });
  }

  consultarFeedback(idParticipacion: number): void {
    this.identityService.feedback(String(idParticipacion)).subscribe({
      next: (fb) => this.feedback.set(fb),
      error: () => {},
    });
  }

  calcularPorcentajeProgreso(p: ProgresoRespuesta): number {
    if (!p.total_aplicable || p.total_aplicable === 0) {
      return p.respondidas > 0 ? 50 : 0;
    }
    return Math.min(100, Math.round((p.respondidas / p.total_aplicable) * 100));
  }
}

