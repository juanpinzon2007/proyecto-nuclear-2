import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatDividerModule } from '@angular/material/divider';
import { SchedulingService } from '../../core/scheduling.service';
import { ConsolidacionSesion, PreparacionSesionRespuesta, ResultadoTecnicoRespuesta } from '../../core/api.models';
import { mensajeError } from '../../core/api-error';

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
  ],
  template: `
    <div class="page">
      <div class="page-header">
        <div style="display: flex; align-items: center; gap: 8px;">
          <a mat-icon-button routerLink="/programacion" title="Volver a programación">
            <mat-icon>arrow_back</mat-icon>
          </a>
          <div>
            <h1>Evaluación y Consolidación de Sesión</h1>
            <p class="muted">Sesión ID: <span class="mono">{{ sesionId }}</span></p>
          </div>
        </div>
        <div style="display: flex; gap: 8px;">
          <button mat-flat-button color="accent" (click)="consolidar()" [disabled]="accionEnProgreso()">
            <mat-icon>calculate</mat-icon> Consolidar Notas
          </button>
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
      } @else if (preparacion(); as p) {
        <!-- Estado general de la preparación -->
        <mat-card>
          <mat-card-header>
            <mat-card-title>Estado de la Sesión para Publicación</mat-card-title>
            <mat-card-subtitle>
              Estado Sesión: <span class="chip">{{ p.estado_sesion }}</span>
              · Publicable:
              <span class="chip" [class.ok]="p.publicable" [class.bad]="!p.publicable">
                {{ p.publicable ? 'SÍ, LISTA' : 'BLOQUEADA' }}
              </span>
            </mat-card-subtitle>
          </mat-card-header>
          <mat-card-content style="padding-top: 16px;">
            @if (p.pendientes.length > 0) {
              <div class="error-box" style="margin-bottom: 12px;">
                <strong>Pendientes para cerrar la sesión:</strong>
                <ul style="margin: 4px 0 0 16px;">
                  @for (pend of p.pendientes; track pend) {
                    <li>{{ pend }}</li>
                  }
                </ul>
              </div>
            }

            <div style="display: flex; gap: 12px; align-items: center; flex-wrap: wrap; margin-top: 8px;">
              <button mat-stroked-button (click)="cambiarVisibilidad(true)" [disabled]="accionEnProgreso()">
                <mat-icon>visibility</mat-icon> Habilitar Vista Provisional a Estudiantes
              </button>
              <button mat-stroked-button (click)="cambiarVisibilidad(false)" [disabled]="accionEnProgreso()">
                <mat-icon>visibility_off</mat-icon> Ocultar Vista Provisional
              </button>
            </div>
          </mat-card-content>
        </mat-card>

        <!-- Consolidación y publicación de notas -->
        @if (consolidacion(); as c) {
          <mat-card style="border-left: 4px solid var(--mat-sys-primary);">
            <mat-card-header>
              <mat-card-title>Revisión Consolidada de la Sesión</mat-card-title>
              <mat-card-subtitle>
                Huella SHA256: <span class="mono" style="font-size: 11px;">{{ c.revision_sha256 }}</span>
              </mat-card-subtitle>
            </mat-card-header>
            <mat-card-content style="padding-top: 12px;">
              <p>La sesión fue consolidada y calculada con el motor de rúbricas.</p>
              @if (c.publicable) {
                <button mat-flat-button color="primary" (click)="publicarOficial(c.revision_sha256)" [disabled]="accionEnProgreso()">
                  <mat-icon>done_all</mat-icon> Publicar Calificaciones Oficiales
                </button>
              } @else {
                <p class="muted">Existen participantes pendientes antes de poder realizar la publicación oficial.</p>
              }
            </mat-card-content>
          </mat-card>
        }

        <!-- Detalle técnico seleccionado de un intento -->
        @if (resultadoSeleccionado(); as r) {
          <mat-card style="border-left: 4px solid #4caf50;">
            <mat-card-header>
              <mat-card-title style="display: flex; justify-content: space-between; width: 100%;">
                <span>Resultado Técnico del Intento #{{ r.id_intento }}</span>
                <span class="chip ok" style="font-size: 14px;">Nota Final: {{ r.nota_final }}</span>
              </mat-card-title>
              <mat-card-subtitle>
                Modalidad: {{ r.modalidad }} · Fecha cálculo: {{ r.fecha_calculo | date:'short' }}
              </mat-card-subtitle>
            </mat-card-header>
            <mat-card-content style="padding-top: 16px;">
              <div class="row" style="margin-bottom: 16px;">
                <div><strong>Preguntas Respondidas:</strong> {{ r.preguntas_respondidas }} / {{ r.preguntas_exigidas }}</div>
                <div><strong>Suma de Puntajes:</strong> {{ r.suma_puntajes }}</div>
                <div><strong>Oficial:</strong> {{ r.oficial ? 'SÍ' : 'NO' }}</div>
              </div>

              <strong>Evaluación por Criterios de Rúbrica:</strong>
              <div class="stack" style="margin-top: 8px;">
                @for (crit of r.criterios; track crit.criterio_id) {
                  <div style="background: var(--mat-sys-surface-container-low); padding: 8px 12px; border-radius: 6px; display: flex; justify-content: space-between; align-items: center;">
                    <span class="mono" style="font-size: 12px;">Criterio: {{ crit.criterio_id }}</span>
                    <span><strong>Puntaje:</strong> {{ crit.puntaje_obtenido || crit.suma_puntajes || '0' }}</span>
                  </div>
                }
              </div>

              <div style="margin-top: 16px; text-align: right;">
                <button mat-button (click)="resultadoSeleccionado.set(null)">Cerrar Detalle</button>
              </div>
            </mat-card-content>
          </mat-card>
        }

        <!-- Lista de convocatorias y participantes -->
        <mat-card>
          <mat-card-header>
            <mat-card-title>Participantes Convocados ({{ p.convocatorias.length }})</mat-card-title>
          </mat-card-header>
          <mat-card-content style="padding-top: 16px;">
            @if (p.convocatorias.length === 0) {
              <p class="muted">No hay convocatorias en esta sesión.</p>
            } @else {
              <div class="stack">
                @for (conv of p.convocatorias; track conv.id_convocatoria) {
                  <div class="convocatoria-row">
                    <div>
                      <div><strong>Estudiante ID:</strong> {{ conv.id_estudiante }}</div>
                      <div class="mono muted" style="font-size: 11px;">Convocatoria: {{ conv.id_convocatoria }}</div>
                      <div>
                        Estado:
                        <span class="chip" [class.ok]="conv.estado === 'ACTIVA'" [class.bad]="conv.estado === 'RETIRADA'">
                          {{ conv.estado }}
                        </span>
                        @if (conv.id_participacion) {
                          <span class="chip" style="margin-left: 6px;">Participación #{{ conv.id_participacion }}</span>
                        }
                      </div>
                    </div>

                    <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
                      @for (intento of conv.intentos; track intento.id_intento) {
                        <button mat-stroked-button color="primary" (click)="verOcularResultadoTecnico(intento.id_intento)" [disabled]="accionEnProgreso()">
                          <mat-icon>analytics</mat-icon> Intento #{{ intento.numero }} ({{ intento.estado }})
                        </button>
                      }

                      @if (conv.intentos.length === 0) {
                        <button mat-button color="warn" (click)="marcarAusencia(conv.id_convocatoria)">
                          Marcar Ausencia
                        </button>
                      }
                    </div>
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
    .convocatoria-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px;
      border: 1px solid var(--mat-sys-outline-variant);
      border-radius: 8px;
      background: white;
      gap: 16px;
      flex-wrap: wrap;
    }
  `],
})
export class EvaluacionSesionComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly schedulingService = inject(SchedulingService);

  sesionId = '';
  readonly preparacion = signal<PreparacionSesionRespuesta | null>(null);
  readonly consolidacion = signal<ConsolidacionSesion | null>(null);
  readonly resultadoSeleccionado = signal<ResultadoTecnicoRespuesta | null>(null);

  readonly cargando = signal<boolean>(true);
  readonly accionEnProgreso = signal<boolean>(false);
  readonly error = signal<string | null>(null);
  readonly mensajeExito = signal<string | null>(null);

  ngOnInit(): void {
    this.sesionId = this.route.snapshot.paramMap.get('id') ?? '';
    if (this.sesionId) {
      this.cargarPreparacion();
    }
  }

  cargarPreparacion(): void {
    this.cargando.set(true);
    this.error.set(null);
    this.schedulingService.preparacion(this.sesionId).subscribe({
      next: (data) => {
        this.preparacion.set(data);
        this.cargando.set(false);
      },
      error: (err) => {
        this.error.set(mensajeError(err));
        this.cargando.set(false);
      },
    });
  }

  verOcularResultadoTecnico(idIntento: number): void {
    this.accionEnProgreso.set(true);
    this.error.set(null);
    this.schedulingService.calcularResultadoTecnico(this.sesionId, idIntento).subscribe({
      next: (res) => {
        this.resultadoSeleccionado.set(res);
        this.accionEnProgreso.set(false);
      },
      error: (err) => {
        // Si ya estaba calculado, consultar GET
        this.schedulingService.resultadoTecnico(this.sesionId, idIntento).subscribe({
          next: (resGet) => {
            this.resultadoSeleccionado.set(resGet);
            this.accionEnProgreso.set(false);
          },
          error: (err2) => {
            this.error.set(mensajeError(err2 || err));
            this.accionEnProgreso.set(false);
          },
        });
      },
    });
  }

  consolidar(): void {
    this.accionEnProgreso.set(true);
    this.error.set(null);
    this.schedulingService.consolidacion(this.sesionId).subscribe({
      next: (data) => {
        this.consolidacion.set(data);
        this.mensajeExito.set('Sesión consolidada exitosamente.');
        this.accionEnProgreso.set(false);
      },
      error: (err) => {
        this.error.set(mensajeError(err));
        this.accionEnProgreso.set(false);
      },
    });
  }

  publicarOficial(revisionSha256: string): void {
    if (!confirm('¿Deseas publicar las calificaciones oficiales de la sesión?')) return;
    this.accionEnProgreso.set(true);
    this.error.set(null);
    this.schedulingService.publicar(this.sesionId, revisionSha256).subscribe({
      next: () => {
        this.mensajeExito.set('Calificaciones oficiales publicadas.');
        this.accionEnProgreso.set(false);
        this.cargarPreparacion();
      },
      error: (err) => {
        this.error.set(mensajeError(err));
        this.accionEnProgreso.set(false);
      },
    });
  }

  cambiarVisibilidad(mostrar: boolean): void {
    this.accionEnProgreso.set(true);
    this.error.set(null);
    this.schedulingService.visibilidad(this.sesionId, mostrar).subscribe({
      next: () => {
        this.mensajeExito.set(`Visibilidad provisional ${mostrar ? 'activada' : 'desactivada'}.`);
        this.accionEnProgreso.set(false);
      },
      error: (err) => {
        this.error.set(mensajeError(err));
        this.accionEnProgreso.set(false);
      },
    });
  }

  marcarAusencia(convocatoriaId: string): void {
    const motivo = prompt('Ingresa el motivo de la inasistencia:');
    if (!motivo) return;
    this.accionEnProgreso.set(true);
    this.schedulingService.registrarAusencia(this.sesionId, convocatoriaId, motivo).subscribe({
      next: () => {
        this.mensajeExito.set('Ausencia registrada.');
        this.accionEnProgreso.set(false);
        this.cargarPreparacion();
      },
      error: (err) => {
        this.error.set(mensajeError(err));
        this.accionEnProgreso.set(false);
      },
    });
  }
}

