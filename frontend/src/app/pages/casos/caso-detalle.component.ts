import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatDividerModule } from '@angular/material/divider';
import { CasesService } from '../../core/cases.service';
import { CasoDetalleResponse } from '../../core/api.models';
import { mensajeError } from '../../core/api-error';

@Component({
  selector: 'app-caso-detalle',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatExpansionModule,
    MatProgressSpinnerModule,
    MatDividerModule,
  ],
  template: `
    <div class="page">
      <div class="page-header">
        <div style="display: flex; align-items: center; gap: 8px;">
          <a mat-icon-button routerLink="/casos" title="Volver a casos">
            <mat-icon>arrow_back</mat-icon>
          </a>
          <div>
            <h1>{{ caso()?.nombre || 'Detalle del Caso' }}</h1>
            <p class="muted">Versión: <span class="mono">{{ versionId }}</span></p>
          </div>
        </div>
        <div style="display: flex; gap: 8px;">
          <a mat-stroked-button [routerLink]="['/casos', versionId, 'grafo']">
            <mat-icon>account_tree</mat-icon> Ver Grafo de Transiciones
          </a>
        </div>
      </div>

      @if (error()) {
        <div class="error-box">{{ error() }}</div>
      }

      @if (cargando()) {
        <div style="display: flex; justify-content: center; padding: 40px;">
          <mat-spinner diameter="40"></mat-spinner>
        </div>
      } @else if (caso(); as c) {
        <!-- Ficha técnica del caso -->
        <mat-card>
          <mat-card-header>
            <mat-card-title>Ficha Descriptiva</mat-card-title>
            <mat-card-subtitle>
              Estado: <span class="chip" [class.ok]="c.estado === 'PUBLICADO'" [class.warn]="c.estado === 'BORRADOR'">{{ c.estado }}</span>
              · Tiempo estimado: <strong>{{ c.tiempo_estimado_min }} minutos</strong>
            </mat-card-subtitle>
          </mat-card-header>
          <mat-card-content class="stack" style="padding-top: 16px;">
            <div>
              <strong class="muted">Desarrollo Situacional:</strong>
              <p style="margin: 4px 0 12px; line-height: 1.5;">{{ c.desarrollo_situacional }}</p>
            </div>
            <div>
              <strong class="muted">Contexto / Historia:</strong>
              <p style="margin: 4px 0; line-height: 1.5;">{{ c.contexto_historia }}</p>
            </div>
          </mat-card-content>
        </mat-card>

        <!-- Escenarios y preguntas -->
        <mat-card>
          <mat-card-header>
            <mat-card-title>Escenarios y Decisiones ({{ c.escenarios.length }})</mat-card-title>
          </mat-card-header>
          <mat-card-content style="padding-top: 16px;">
            @if (c.escenarios.length === 0) {
              <p class="muted">Este caso no tiene escenarios registrados en esta versión.</p>
            } @else {
              <mat-accordion multi>
                @for (esc of c.escenarios; track esc.id) {
                  <mat-expansion-panel [expanded]="true">
                    <mat-expansion-panel-header>
                      <mat-panel-title>
                        <strong>Escenario {{ esc.orden }}</strong>
                      </mat-panel-title>
                      <mat-panel-description>
                        {{ esc.preguntas.length }} pregunta(s) / decisión(es)
                      </mat-panel-description>
                    </mat-expansion-panel-header>

                    <div style="margin-bottom: 16px;">
                      <strong class="muted">Contexto de la escena:</strong>
                      <p style="margin-top: 4px;">{{ esc.contexto_situacional }}</p>
                    </div>

                    <mat-divider></mat-divider>

                    <div style="margin-top: 16px;" class="stack">
                      @for (p of esc.preguntas; track p.id) {
                        <div class="pregunta-box">
                          <div style="font-weight: 500; margin-bottom: 8px;">
                            {{ p.orden }}. {{ p.enunciado }}
                          </div>
                          <div class="stack" style="gap: 6px;">
                            @for (op of p.opciones; track op.id) {
                              <div class="opcion-item" [class.correcta]="op.es_correcta">
                                <div style="display: flex; align-items: center; gap: 8px;">
                                  <mat-icon [style.color]="op.es_correcta ? 'green' : 'gray'">
                                    {{ op.es_correcta ? 'check_circle' : 'radio_button_unchecked' }}
                                  </mat-icon>
                                  <span>{{ op.texto }}</span>
                                </div>
                                @if (op.justificacion) {
                                  <div class="muted" style="font-size: 12px; margin-left: 32px;">
                                    <em>Justificación:</em> {{ op.justificacion }}
                                  </div>
                                }
                              </div>
                            }
                          </div>
                        </div>
                      }
                    </div>
                  </mat-expansion-panel>
                }
              </mat-accordion>
            }
          </mat-card-content>
        </mat-card>

        <!-- Rúbrica de evaluación -->
        <mat-card>
          <mat-card-header>
            <mat-card-title>Rúbrica de Evaluación</mat-card-title>
            <mat-card-subtitle *ngIf="c.rubrica">
              {{ c.rubrica.nombre }} (Regla: {{ c.rubrica.version_regla }})
            </mat-card-subtitle>
          </mat-card-header>
          <mat-card-content style="padding-top: 16px;">
            @if (!c.rubrica) {
              <p class="muted">No hay rúbrica asociada a esta versión del caso.</p>
            } @else {
              <div class="stack">
                @for (crit of c.rubrica.criterios; track crit.id) {
                  <div class="criterio-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                      <strong>{{ crit.nombre }}</strong>
                      <span class="chip">Peso: {{ crit.peso }}</span>
                    </div>
                    <div class="niveles-grid">
                      @for (niv of crit.niveles; track niv.id) {
                        <div class="nivel-box">
                          <div style="font-weight: 600; font-size: 13px;">{{ niv.nombre }} ({{ niv.puntaje }} pts)</div>
                          <div style="font-size: 12px; color: var(--mat-sys-on-surface-variant); margin-top: 4px;">{{ niv.descriptor }}</div>
                        </div>
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
    .pregunta-box {
      background: var(--mat-sys-surface-container-low);
      padding: 12px;
      border-radius: 8px;
    }
    .opcion-item {
      padding: 8px 12px;
      background: white;
      border-radius: 6px;
      border: 1px solid var(--mat-sys-outline-variant);
    }
    .opcion-item.correcta {
      border-color: #4caf50;
      background: #f1f8e9;
    }
    .criterio-card {
      border: 1px solid var(--mat-sys-outline-variant);
      border-radius: 8px;
      padding: 12px;
      background: white;
    }
    .niveles-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 8px;
      margin-top: 10px;
    }
    .nivel-box {
      background: var(--mat-sys-surface-container-lowest);
      border: 1px solid var(--mat-sys-outline-variant);
      border-radius: 6px;
      padding: 8px;
    }
  `],
})
export class CasoDetalleComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly casesService = inject(CasesService);

  versionId = '';
  readonly caso = signal<CasoDetalleResponse | null>(null);
  readonly cargando = signal<boolean>(true);
  readonly error = signal<string | null>(null);

  ngOnInit(): void {
    this.versionId = this.route.snapshot.paramMap.get('id') ?? '';
    if (this.versionId) {
      this.cargarDetalle();
    }
  }

  cargarDetalle(): void {
    this.cargando.set(true);
    this.error.set(null);
    this.casesService.obtener(this.versionId).subscribe({
      next: (data) => {
        this.caso.set(data);
        this.cargando.set(false);
      },
      error: (err) => {
        this.error.set(mensajeError(err));
        this.cargando.set(false);
      },
    });
  }
}

