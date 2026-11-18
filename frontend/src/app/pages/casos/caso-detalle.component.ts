import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatDividerModule } from '@angular/material/divider';
import { firstValueFrom } from 'rxjs';
import { CasesService } from '../../core/cases.service';
import { AuthService } from '../../core/auth.service';
import { CasoDetalleResponse } from '../../core/api.models';
import { mensajeError } from '../../core/api-error';
import { UiDialogService } from '../../core/ui-dialog.service';

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
        <div style="display: flex; align-items: center; gap: 10px;">
          <a mat-icon-button routerLink="/casos" title="Volver a casos">
            <mat-icon>arrow_back</mat-icon>
          </a>
          <div>
            <p class="eyebrow">Briefing Estructural // Caso</p>
            <h1>{{ caso()?.nombre || 'Detalle del Caso' }}</h1>
            <p class="muted">Versión: <span class="mono">{{ versionId }}</span></p>
          </div>
        </div>
        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
          @if (caso()?.estado === 'BORRADOR' && auth.tienePermiso('CREAR_CASOS')) {
            <a mat-flat-button color="primary" [routerLink]="['/casos', versionId, 'editar']">
              <mat-icon>edit</mat-icon> Editar Borrador
            </a>
            <button mat-flat-button color="accent" type="button" (click)="publicar()">
              <mat-icon>publish</mat-icon> Publicar
            </button>
          }
          @if (caso()?.estado === 'PUBLICADO' && auth.tienePermiso('CREAR_CASOS')) {
            <button mat-stroked-button color="accent" type="button" (click)="clonar()">
              <mat-icon>content_copy</mat-icon> Nueva Versión
            </button>
            <button mat-stroked-button color="warn" type="button" (click)="archivar()">
              <mat-icon>archive</mat-icon> Archivar
            </button>
          }
          @if (caso()?.estado === 'ARCHIVADO' && auth.tienePermiso('CREAR_CASOS')) {
            <button mat-flat-button color="accent" type="button" (click)="republicar()">
              <mat-icon>replay</mat-icon> Republicar como Nueva Versión
            </button>
            <button mat-stroked-button type="button" (click)="clonar()">
              <mat-icon>content_copy</mat-icon> Crear Borrador Editable
            </button>
          }
          <a mat-stroked-button [routerLink]="['/casos', versionId, 'grafo']">
            <mat-icon>account_tree</mat-icon> Ver / Configurar Grafo
          </a>
        </div>
      </div>

      @if (error()) {
        <div class="error-box">{{ error() }}</div>
      }
      @if (exito()) {
        <div class="success-box">{{ exito() }}</div>
      }

      @if (cargando()) {
        <div class="center-spin">
          <mat-spinner diameter="40"></mat-spinner>
        </div>
      } @else if (caso(); as c) {
        <!-- Ficha técnica del caso -->
        <mat-card class="panel panel-cyan-left">
          <mat-card-header>
            <mat-card-title>01 // Ficha Descriptiva</mat-card-title>
            <mat-card-subtitle>
              Estado: <span class="chip" [class.ok]="c.estado === 'PUBLICADO'" [class.warn]="c.estado === 'BORRADOR'" [class.bad]="c.estado === 'ARCHIVADO'">{{ c.estado }}</span>
              · Tiempo estimado: <strong class="cyan">{{ c.tiempo_estimado_min }} MIN</strong>
            </mat-card-subtitle>
          </mat-card-header>
          <mat-card-content class="briefing-blocks" style="padding-top: 16px;">
            <div class="objective-tile">
              <span class="obj-num">01</span>
              <div>
                <div class="obj-lbl">Desarrollo Situacional</div>
                <p>{{ c.desarrollo_situacional }}</p>
              </div>
            </div>
            <div class="objective-tile">
              <span class="obj-num">02</span>
              <div>
                <div class="obj-lbl">Contexto / Historia</div>
                <p>{{ c.contexto_historia }}</p>
              </div>
            </div>
          </mat-card-content>
        </mat-card>

        <!-- Escenarios y preguntas -->
        <mat-card class="panel">
          <mat-card-header>
            <mat-card-title>02 // Escenarios y Decisiones ({{ c.escenarios.length }})</mat-card-title>
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
                      <mat-panel-description class="mono">
                        {{ esc.preguntas.length }} pregunta(s) / decisión(es)
                      </mat-panel-description>
                    </mat-expansion-panel-header>

                    <div class="scene-context">
                      <span class="obj-lbl">Contexto de la escena</span>
                      <p>{{ esc.contexto_situacional }}</p>
                    </div>

                    <mat-divider></mat-divider>

                    <div style="margin-top: 16px;" class="stack">
                      @for (p of esc.preguntas; track p.id) {
                        <div class="pregunta-box">
                          <div class="preg-title">
                            {{ p.orden }}. {{ p.enunciado }}
                          </div>
                          <div class="stack" style="gap: 8px;">
                            @for (op of p.opciones; track op.id) {
                              <div class="opcion-item" [class.correcta]="op.es_correcta">
                                <div style="display: flex; align-items: center; gap: 8px;">
                                  <mat-icon [style.color]="op.es_correcta ? 'var(--green)' : 'var(--dim)'">
                                    {{ op.es_correcta ? 'check_circle' : 'radio_button_unchecked' }}
                                  </mat-icon>
                                  <span>{{ op.texto }}</span>
                                </div>
                                @if (op.justificacion) {
                                  <div class="just-txt">
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
        <mat-card class="panel panel-green-left">
          <mat-card-header>
            <mat-card-title>03 // Rúbrica de Evaluación</mat-card-title>
            <mat-card-subtitle *ngIf="c.rubrica">
              {{ c.rubrica.nombre }} · Regla: {{ c.rubrica.version_regla }}
            </mat-card-subtitle>
          </mat-card-header>
          <mat-card-content style="padding-top: 16px;">
            @if (!c.rubrica) {
              <p class="muted">No hay rúbrica asociada a esta versión del caso.</p>
            } @else {
              <div class="stack">
                @for (crit of c.rubrica.criterios; track crit.id) {
                  <div class="criterio-card">
                    <div class="spread">
                      <strong>{{ crit.nombre }}</strong>
                      <span class="tag amber">PESO: {{ crit.peso }}%</span>
                    </div>
                    <div class="niveles-grid">
                      @for (niv of crit.niveles; track niv.id) {
                        <div class="nivel-box">
                          <div class="nivel-head">{{ niv.nombre }} ({{ niv.puntaje }} PTS)</div>
                          <div class="muted" style="font-size: 12px; margin-top: 4px;">{{ niv.descriptor }}</div>
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
    .briefing-blocks {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 12px;
    }
    .objective-tile {
      display: grid;
      grid-template-columns: 38px 1fr;
      gap: 12px;
      padding: 14px;
      border: 1px solid rgba(0, 229, 244, 0.2);
      background: #0b1017;
    }
    .obj-num {
      width: 36px;
      height: 36px;
      display: grid;
      place-items: center;
      border: 1px solid var(--line-strong);
      background: rgba(0, 229, 244, 0.1);
      color: var(--cyan);
      font-family: var(--mono);
      font-weight: 700;
    }
    .obj-lbl {
      font-family: var(--mono);
      font-size: 11px;
      letter-spacing: 1px;
      text-transform: uppercase;
      color: var(--cyan);
      margin-bottom: 4px;
    }
    .objective-tile p {
      margin: 0;
      line-height: 1.55;
      color: var(--text);
      font-size: 14px;
    }
    .scene-context {
      padding: 12px 14px;
      background: #070a10;
      border: 1px solid var(--line);
      margin-bottom: 14px;
    }
    .scene-context p {
      margin: 4px 0 0;
      color: var(--text);
      line-height: 1.55;
    }
    .pregunta-box {
      background: rgba(11, 16, 23, 0.9);
      padding: 14px;
      border: 1px solid rgba(184, 211, 214, 0.18);
    }
    .preg-title {
      font-weight: 700;
      margin-bottom: 10px;
      color: var(--text);
      font-size: 15px;
    }
    .opcion-item {
      padding: 10px 12px;
      background: #0d121a;
      border: 1px solid rgba(184, 211, 214, 0.16);
      color: var(--text);
    }
    .opcion-item.correcta {
      border-color: rgba(0, 232, 148, 0.55);
      border-left: 4px solid var(--green);
      background: rgba(0, 232, 148, 0.08);
    }
    .just-txt {
      font-size: 12px;
      margin-left: 32px;
      margin-top: 4px;
      color: var(--muted);
    }
    .criterio-card {
      border: 1px solid var(--line);
      border-left: 4px solid var(--cyan);
      padding: 14px;
      background: #0b1017;
      color: var(--text);
    }
    .niveles-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 8px;
      margin-top: 10px;
    }
    .nivel-box {
      background: #070a10;
      border: 1px solid rgba(184, 211, 214, 0.16);
      padding: 10px;
    }
    .nivel-head {
      font-family: var(--mono);
      font-weight: 700;
      font-size: 12px;
      color: var(--cyan-soft);
    }
  `],
})
export class CasoDetalleComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly casesService = inject(CasesService);
  private readonly uiDialog = inject(UiDialogService);
  readonly auth = inject(AuthService);

  versionId = '';
  readonly caso = signal<CasoDetalleResponse | null>(null);
  readonly cargando = signal<boolean>(true);
  readonly error = signal<string | null>(null);
  readonly exito = signal<string | null>(null);

  ngOnInit(): void {
    this.route.paramMap.subscribe((pm) => {
      const id = pm.get('id') ?? '';
      if (id && id !== this.versionId) {
        this.versionId = id;
        this.cargarDetalle();
      }
    });
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

  async publicar(): Promise<void> {
    const ok = await this.uiDialog.confirmar({
      eyebrow: 'Validación y Publicación // RF-09',
      titulo: 'Publicar Caso',
      mensaje: '¿Deseas validar, completar el recorrido lineal si falta y publicar esta versión?',
      botonConfirmar: 'Publicar',
      botonCancelar: 'Cancelar',
      tono: 'green',
    });
    if (!ok) return;
    this.error.set(null);
    this.exito.set(null);
    try {
      await this.casesService.publicarInteligente(this.versionId);
      this.exito.set('Caso publicado exitosamente.');
      this.cargarDetalle();
    } catch (err) {
      this.error.set(mensajeError(err));
    }
  }

  async archivar(): Promise<void> {
    const ok = await this.uiDialog.confirmar({
      eyebrow: 'Gestión de Versiones // Casos',
      titulo: 'Archivar Versión',
      mensaje: 'Esta versión pasará a ARCHIVADO. Luego podrás republicarla o crear una nueva versión editable cuando quieras.',
      botonConfirmar: 'Archivar',
      botonCancelar: 'Cancelar',
      tono: 'warn',
    });
    if (!ok) return;
    this.error.set(null);
    this.exito.set(null);
    try {
      await firstValueFrom(this.casesService.archivar(this.versionId));
      this.exito.set('Versión archivada.');
      this.cargarDetalle();
    } catch (err) {
      this.error.set(mensajeError(err));
    }
  }

  async republicar(): Promise<void> {
    const ok = await this.uiDialog.confirmar({
      eyebrow: 'Reactivación // RF-09',
      titulo: 'Republicar como Nueva Versión Activa',
      mensaje: 'Se generará y publicará una nueva versión (v+1) con esta misma estructura, manteniendo intacta la versión archivada.',
      botonConfirmar: 'Republicar Ahora',
      botonCancelar: 'Cancelar',
      tono: 'green',
    });
    if (!ok) return;
    this.error.set(null);
    this.exito.set(null);
    try {
      const res = await firstValueFrom(this.casesService.republicar(this.versionId));
      this.exito.set('Nueva versión publicada correctamente.');
      void this.router.navigate(['/casos', res.version_id]);
    } catch (err) {
      this.error.set(mensajeError(err));
    }
  }

  async clonar(): Promise<void> {
    this.error.set(null);
    try {
      const res = await firstValueFrom(this.casesService.clonar(this.versionId));
      void this.router.navigate(['/casos', res.version_id, 'editar']);
    } catch (err) {
      this.error.set(mensajeError(err));
    }
  }
}

