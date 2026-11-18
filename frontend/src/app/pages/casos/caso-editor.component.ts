import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatDividerModule } from '@angular/material/divider';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { firstValueFrom } from 'rxjs';
import { mensajeError } from '../../core/api-error';
import { CasoPayload } from '../../core/api.models';
import { CasesService } from '../../core/cases.service';

interface OpcionDraft {
  orden: number;
  texto: string;
  esCorrecta: boolean;
  justificacion: string;
  valoraciones: Record<string, number | undefined>;
}

interface PreguntaDraft {
  orden: number;
  enunciado: string;
  options: OpcionDraft[];
}

interface EscenarioDraft {
  orden: number;
  contextoSituacional: string;
  questions: PreguntaDraft[];
}

interface NivelDraft {
  nombre: string;
  puntaje: number;
  descriptor: string;
}

interface CriterioDraft {
  nombre: string;
  peso: number;
  niveles: NivelDraft[];
}

@Component({
  selector: 'app-caso-editor',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterLink,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatCheckboxModule,
    MatDividerModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
  ],
  template: `
    <div class="editor-wrap">
      <div class="page-header">
        <div style="display:flex; align-items:center; gap:10px;">
          <a mat-icon-button routerLink="/casos" title="Volver"><mat-icon>arrow_back</mat-icon></a>
          <div>
            <p class="eyebrow">Autoría Clínica // RF-05 · RF-06 · RF-07 · RF-08 · RF-17</p>
            <h2>{{ versionId ? 'Editar Caso de Simulación (Borrador)' : 'Nuevo Caso de Simulación & Rúbrica' }}</h2>
            <p class="subtitle">Estructura clínica, escenarios, justificaciones teóricas y matriz de evaluación</p>
          </div>
        </div>
        <div class="top-actions">
          <button mat-stroked-button type="button" (click)="guardar(false)" [disabled]="guardando()">
            <mat-icon>save</mat-icon> Guardar Borrador
          </button>
          <button mat-flat-button color="primary" type="button" (click)="guardarYPublicar()" [disabled]="guardando()">
            <mat-icon>publish</mat-icon> Validar y Publicar
          </button>
        </div>
      </div>

      @if (errorDetalle()) {
        <div class="error-banner">{{ errorDetalle() }}</div>
      }

      @if (cargando()) {
        <div class="center-spin"><mat-spinner diameter="42"></mat-spinner></div>
      } @else {
        <!-- 01. Ficha Académica (RF-05) -->
        <mat-card class="panel panel-cyan-left">
          <mat-card-header>
            <mat-card-title>01 // Ficha Académica del Caso (RF-05)</mat-card-title>
            <mat-card-subtitle>Nombre, contexto narrativo, desarrollo situacional y tiempo estimado máximo</mat-card-subtitle>
          </mat-card-header>
          <mat-card-content class="form-grid" style="padding-top:16px;">
            <mat-form-field appearance="outline" class="span-2">
              <mat-label>Nombre del caso</mat-label>
              <input matInput [(ngModel)]="casoNombre" required />
            </mat-form-field>
            <mat-form-field appearance="outline">
              <mat-label>Tiempo estimado máximo (min)</mat-label>
              <input matInput type="number" min="1" max="240" [(ngModel)]="tiempoEstimadoMin" required />
            </mat-form-field>
            <mat-form-field appearance="outline" class="span-3">
              <mat-label>Contexto / Historia clínica o institucional</mat-label>
              <textarea matInput rows="3" [(ngModel)]="contextoHistoria" required></textarea>
            </mat-form-field>
            <mat-form-field appearance="outline" class="span-3">
              <mat-label>Desarrollo situacional / Objetivos y rol del estudiante</mat-label>
              <textarea matInput rows="3" [(ngModel)]="desarrolloSituacional" required></textarea>
            </mat-form-field>
          </mat-card-content>
        </mat-card>

        <!-- 02. Rúbrica de Evaluación (RF-17) -->
        <mat-card class="panel panel-amber-left">
          <mat-card-header>
            <mat-card-title>02 // Rúbrica de Evaluación (RF-17)</mat-card-title>
            <mat-card-subtitle>
              Los pesos de los criterios deben sumar exactamente <strong>100%</strong>
              (Suma actual: <strong [class.ok-txt]="sumaPesos() === 100" [class.bad-txt]="sumaPesos() !== 100">{{ sumaPesos() }}%</strong>)
            </mat-card-subtitle>
          </mat-card-header>
          <mat-card-content style="padding-top:16px;">
            <div class="rubric-meter">
              <div class="meter">
                <span
                  [style.width.%]="sumaPesos() > 100 ? 100 : sumaPesos()"
                  [style.--meter-color]="sumaPesos() === 100 ? 'var(--green)' : 'var(--amber)'"
                ></span>
              </div>
              <span class="mono" [class.ok-txt]="sumaPesos() === 100" [class.bad-txt]="sumaPesos() !== 100">
                CALIBRACIÓN: {{ sumaPesos() }}% / 100%
              </span>
            </div>

            <div class="form-grid" style="margin-bottom:16px;">
              <mat-form-field appearance="outline" class="span-2">
                <mat-label>Nombre de la rúbrica</mat-label>
                <input matInput [(ngModel)]="rubricaNombre" required />
              </mat-form-field>
              <mat-form-field appearance="outline">
                <mat-label>Modo de cálculo</mat-label>
                <mat-select [(ngModel)]="versionRegla">
                  <mat-option value="PREGUNTAS_100_V1">Preguntas 100% Uniforme (PREGUNTAS_100_V1)</mat-option>
                  <mat-option value="RUBRICA_V1">Rúbrica Ponderada por Criterios (RUBRICA_V1)</mat-option>
                </mat-select>
              </mat-form-field>
            </div>

            @for (crit of criterios; track $index; let ci = $index) {
              <div class="sub-box">
                <div class="sub-head">
                  <strong class="mono cyan">CRITERIO #0{{ ci + 1 }}</strong>
                  <button mat-icon-button color="warn" type="button" (click)="eliminarCriterio(ci)" [disabled]="criterios.length <= 1">
                    <mat-icon>delete</mat-icon>
                  </button>
                </div>
                <div class="row-2">
                  <mat-form-field appearance="outline" style="flex:2;">
                    <mat-label>Nombre del criterio</mat-label>
                    <input matInput [(ngModel)]="crit.nombre" required />
                  </mat-form-field>
                  <mat-form-field appearance="outline" style="flex:1;">
                    <mat-label>Peso (%)</mat-label>
                    <input matInput type="number" min="1" max="100" [(ngModel)]="crit.peso" required />
                  </mat-form-field>
                </div>
                <div class="niveles-grid">
                  @for (niv of crit.niveles; track $index; let ni = $index) {
                    <div class="nivel-item">
                      <mat-form-field appearance="outline">
                        <mat-label>Nivel</mat-label>
                        <input matInput [(ngModel)]="niv.nombre" />
                      </mat-form-field>
                      <mat-form-field appearance="outline">
                        <mat-label>Puntaje min (0-100)</mat-label>
                        <input matInput type="number" min="0" max="100" [(ngModel)]="niv.puntaje" />
                      </mat-form-field>
                      <mat-form-field appearance="outline" style="flex:2;">
                        <mat-label>Descriptor</mat-label>
                        <input matInput [(ngModel)]="niv.descriptor" />
                      </mat-form-field>
                      <button mat-icon-button type="button" (click)="eliminarNivel(ci, ni)" [disabled]="crit.niveles.length <= 1">
                        <mat-icon>close</mat-icon>
                      </button>
                    </div>
                  }
                </div>
                <button mat-stroked-button type="button" (click)="agregarNivel(ci)">
                  <mat-icon>add</mat-icon> Agregar nivel de desempeño
                </button>
              </div>
            }
            <button mat-stroked-button color="primary" type="button" (click)="agregarCriterio()">
              <mat-icon>add_task</mat-icon> Agregar criterio de rúbrica
            </button>
          </mat-card-content>
        </mat-card>

        <!-- 03. Escenarios, Preguntas, Opciones y Justificaciones (RF-06, RF-07, RF-08) -->
        <mat-card class="panel panel-green-left">
          <mat-card-header>
            <mat-card-title>03 // Escenarios, Preguntas y Opciones con Justificación (RF-06 · RF-07 · RF-08)</mat-card-title>
            <mat-card-subtitle>
              Define al menos 1 pregunta clave con mínimo 2 opciones (1+ correcta) por cada escenario.
            </mat-card-subtitle>
          </mat-card-header>
          <mat-card-content style="padding-top:16px;">
            @for (esc of escenarios; track $index; let ei = $index) {
              <div class="escenario-box">
                <div class="sub-head">
                  <strong class="mono green">ESCENARIO #0{{ ei + 1 }}</strong>
                  <div class="mini-actions">
                    <button mat-icon-button type="button" (click)="moverEscenario(ei, -1)" [disabled]="ei === 0" title="Subir">
                      <mat-icon>arrow_upward</mat-icon>
                    </button>
                    <button mat-icon-button type="button" (click)="moverEscenario(ei, 1)" [disabled]="ei === escenarios.length - 1" title="Bajar">
                      <mat-icon>arrow_downward</mat-icon>
                    </button>
                    <button mat-icon-button color="warn" type="button" (click)="eliminarEscenario(ei)" [disabled]="escenarios.length <= 1">
                      <mat-icon>delete</mat-icon>
                    </button>
                  </div>
                </div>

                <mat-form-field appearance="outline" class="full-w">
                  <mat-label>Contexto situacional del escenario {{ ei + 1 }}</mat-label>
                  <textarea matInput rows="2" [(ngModel)]="esc.contextoSituacional" required></textarea>
                </mat-form-field>

                @for (preg of esc.questions; track $index; let pi = $index) {
                  <div class="preg-box">
                    <div class="sub-head">
                      <span class="mono cyan">PREGUNTA {{ ei + 1 }}.{{ pi + 1 }}</span>
                      @if (esc.questions.length > 1) {
                        <button mat-icon-button color="warn" type="button" (click)="eliminarPregunta(ei, pi)">
                          <mat-icon>close</mat-icon>
                        </button>
                      }
                    </div>
                    <mat-form-field appearance="outline" class="full-w">
                      <mat-label>Enunciado de la pregunta / dilema de decisión</mat-label>
                      <textarea matInput rows="2" [(ngModel)]="preg.enunciado" required></textarea>
                    </mat-form-field>

                    @for (op of preg.options; track $index; let oi = $index) {
                      <div class="op-box" [class.op-ok]="op.esCorrecta">
                        <div class="op-top">
                          <mat-checkbox [(ngModel)]="op.esCorrecta" (ngModelChange)="sincronizarValoracionPorDefecto(op)">
                            Opción correcta
                          </mat-checkbox>
                          <mat-form-field appearance="outline" style="flex:1;">
                            <mat-label>Texto opción {{ oi + 1 }}</mat-label>
                            <input matInput [(ngModel)]="op.texto" required />
                          </mat-form-field>
                          <button mat-icon-button color="warn" type="button" (click)="eliminarOpcion(ei, pi, oi)"
                                  [disabled]="preg.options.length <= 2">
                            <mat-icon>delete_outline</mat-icon>
                          </button>
                        </div>

                        <mat-form-field appearance="outline" class="full-w">
                          <mat-label>Justificación teórica / retroalimentación de esta opción (RF-08)</mat-label>
                          <textarea matInput rows="2" [(ngModel)]="op.justificacion" required></textarea>
                        </mat-form-field>

                        @if (versionRegla === 'RUBRICA_V1') {
                          <div class="val-row">
                            <span class="val-lbl">Puntajes por criterio (0-100):</span>
                            @for (c of criterios; track $index) {
                              <mat-form-field appearance="outline" style="width:140px;">
                                <mat-label>{{ c.nombre || 'Criterio' }}</mat-label>
                                <input matInput type="number" min="0" max="100"
                                       [ngModel]="op.valoraciones[c.nombre] ?? (op.esCorrecta ? 100 : 0)"
                                       (ngModelChange)="op.valoraciones[c.nombre] = +$event" />
                              </mat-form-field>
                            }
                          </div>
                        }
                      </div>
                    }

                    <button mat-stroked-button type="button" (click)="agregarOpcion(ei, pi)">
                      <mat-icon>add</mat-icon> Agregar opción de respuesta
                    </button>
                  </div>
                }

                <button mat-button type="button" (click)="agregarPregunta(ei)">
                  <mat-icon>help_outline</mat-icon> Agregar otra pregunta al escenario
                </button>
              </div>
            }

            <button mat-stroked-button color="primary" type="button" (click)="agregarEscenario()">
              <mat-icon>add_to_photos</mat-icon> Agregar nuevo escenario
            </button>
          </mat-card-content>
        </mat-card>
      }
    </div>
  `,
  styles: [`
    .editor-wrap { padding: 4px 0 40px; max-width: 1160px; margin: 0 auto; }
    .subtitle { margin: 4px 0 0; color: var(--muted); font-size: 13px; }
    .top-actions { display: flex; gap: 10px; flex-wrap: wrap; }
    .error-banner {
      background: rgba(232, 67, 81, 0.14);
      border: 1px solid rgba(232, 67, 81, 0.55);
      border-left: 4px solid var(--red);
      color: var(--coral);
      padding: 12px 16px;
      margin-bottom: 16px;
      font-family: var(--mono);
      font-size: 12px;
      white-space: pre-wrap;
    }
    .rubric-meter {
      display: grid;
      gap: 8px;
      padding: 12px 14px;
      background: #070a10;
      border: 1px solid var(--line);
      margin-bottom: 16px;
    }
    .form-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
    .span-2 { grid-column: span 2; }
    .span-3 { grid-column: span 3; }
    @media (max-width: 900px) { .form-grid { grid-template-columns: 1fr; } .span-2, .span-3 { grid-column: span 1; } }
    .full-w { width: 100%; }
    .row-2 { display: flex; gap: 12px; flex-wrap: wrap; }
    .sub-box, .escenario-box {
      background: #0b1017;
      border: 1px solid var(--line);
      padding: 16px;
      margin-bottom: 14px;
    }
    .sub-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; color: var(--text); }
    .mini-actions { display: flex; gap: 4px; }
    .niveles-grid { display: flex; flex-direction: column; gap: 8px; margin-bottom: 8px; }
    .nivel-item { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
    .preg-box {
      background: #080c12;
      border: 1px solid rgba(184, 211, 214, 0.14);
      padding: 14px;
      margin-bottom: 12px;
    }
    .op-box {
      border: 1px solid rgba(184, 211, 214, 0.16);
      padding: 12px;
      margin-bottom: 10px;
      background: #0d121a;
    }
    .op-box.op-ok {
      border-color: rgba(0, 232, 148, 0.55);
      border-left: 4px solid var(--green);
      background: rgba(0, 232, 148, 0.06);
    }
    .op-top { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
    .val-row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
    .val-lbl { font-family: var(--mono); font-size: 11px; color: var(--cyan); }
    .ok-txt { color: var(--green); }
    .bad-txt { color: var(--coral); }
    @media (max-width: 680px) {
      .row-2 mat-form-field,
      .nivel-item mat-form-field,
      .op-top mat-form-field,
      .val-row mat-form-field {
        width: 100% !important;
        flex: 1 1 100% !important;
      }
      .sub-box, .escenario-box, .preg-box { padding: 12px; }
    }
  `],
})
export class CasoEditorComponent implements OnInit {
  private readonly cases = inject(CasesService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly snack = inject(MatSnackBar);

  versionId: string | null = null;
  readonly cargando = signal(false);
  readonly guardando = signal(false);
  readonly errorDetalle = signal('');

  casoNombre = '';
  tiempoEstimadoMin = 30;
  contextoHistoria = '';
  desarrolloSituacional = '';
  rubricaNombre = 'Rúbrica Principal del Caso';
  versionRegla: 'PREGUNTAS_100_V1' | 'RUBRICA_V1' = 'PREGUNTAS_100_V1';

  criterios: CriterioDraft[] = [
    {
      nombre: 'Juicio clínico / ético',
      peso: 100,
      niveles: [
        { nombre: 'Inicial', puntaje: 0, descriptor: 'Decisión no fundamentada o contraria al protocolo.' },
        { nombre: 'Competente', puntaje: 70, descriptor: 'Decisión parcialmente acertada con criterios básicos.' },
        { nombre: 'Sobresaliente', puntaje: 100, descriptor: 'Decisión óptima, segura y sólidamente justificada.' },
      ],
    },
  ];

  escenarios: EscenarioDraft[] = [
    {
      orden: 1,
      contextoSituacional: '',
      questions: [
        {
          orden: 1,
          enunciado: '',
          options: [
            { orden: 1, texto: '', esCorrecta: true, justificacion: '', valoraciones: {} },
            { orden: 2, texto: '', esCorrecta: false, justificacion: '', valoraciones: {} },
          ],
        },
      ],
    },
  ];

  async ngOnInit(): Promise<void> {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.versionId = id;
      await this.cargarExistente(id);
    }
  }

  private async cargarExistente(id: string): Promise<void> {
    this.cargando.set(true);
    try {
      const d = await firstValueFrom(this.cases.obtener(id));
      if (d.estado !== 'BORRADOR') {
        this.errorDetalle.set('Solo pueden editarse versiones en estado BORRADOR.');
      }
      this.casoNombre = d.nombre;
      this.tiempoEstimadoMin = d.tiempo_estimado_min;
      this.contextoHistoria = d.contexto_historia;
      this.desarrolloSituacional = d.desarrollo_situacional;

      if (d.rubrica) {
        this.rubricaNombre = d.rubrica.nombre;
        this.versionRegla = d.rubrica.version_regla === 'RUBRICA_V1' ? 'RUBRICA_V1' : 'PREGUNTAS_100_V1';
        this.criterios = d.rubrica.criterios.map((c) => ({
          nombre: c.nombre,
          peso: Number(c.peso),
          niveles: c.niveles.map((n) => ({
            nombre: n.nombre,
            puntaje: Number(n.puntaje),
            descriptor: n.descriptor,
          })),
        }));
      }

      const critNombrePorId = new Map<string, string>(
        (d.rubrica?.criterios ?? []).map((c) => [c.id, c.nombre]),
      );

      if (d.escenarios.length) {
        this.escenarios = d.escenarios.map((e, ei) => ({
          orden: ei + 1,
          contextoSituacional: e.contexto_situacional,
          questions: e.preguntas.map((q, pi) => ({
            orden: pi + 1,
            enunciado: q.enunciado,
            options: q.opciones.map((o, oi) => ({
              orden: oi + 1,
              texto: o.texto,
              esCorrecta: o.es_correcta,
              justificacion: o.justificacion,
              valoraciones: Object.fromEntries(
                Object.entries(o.valoraciones ?? {}).map(([k, v]) => [critNombrePorId.get(k) ?? k, Number(v)]),
              ),
            })),
          })),
        }));
      }
    } catch (e) {
      this.errorDetalle.set(mensajeError(e));
    } finally {
      this.cargando.set(false);
    }
  }

  sumaPesos(): number {
    return this.criterios.reduce((acc, c) => acc + (Number(c.peso) || 0), 0);
  }

  agregarCriterio(): void {
    this.criterios.push({
      nombre: `Criterio ${this.criterios.length + 1}`,
      peso: Math.max(0, 100 - this.sumaPesos()),
      niveles: [
        { nombre: 'Inicial', puntaje: 0, descriptor: 'Desempeño insuficiente.' },
        { nombre: 'Competente', puntaje: 70, descriptor: 'Cumple los aspectos esenciales.' },
        { nombre: 'Sobresaliente', puntaje: 100, descriptor: 'Excelencia académica integral.' },
      ],
    });
  }

  eliminarCriterio(idx: number): void {
    if (this.criterios.length > 1) this.criterios.splice(idx, 1);
  }

  agregarNivel(ci: number): void {
    this.criterios[ci].niveles.push({ nombre: 'Nivel', puntaje: 50, descriptor: 'Descriptor de nivel' });
  }

  eliminarNivel(ci: number, ni: number): void {
    if (this.criterios[ci].niveles.length > 1) this.criterios[ci].niveles.splice(ni, 1);
  }

  agregarEscenario(): void {
    this.escenarios.push({
      orden: this.escenarios.length + 1,
      contextoSituacional: '',
      questions: [
        {
          orden: 1,
          enunciado: '',
          options: [
            { orden: 1, texto: '', esCorrecta: true, justificacion: '', valoraciones: {} },
            { orden: 2, texto: '', esCorrecta: false, justificacion: '', valoraciones: {} },
          ],
        },
      ],
    });
  }

  eliminarEscenario(ei: number): void {
    if (this.escenarios.length > 1) this.escenarios.splice(ei, 1);
  }

  moverEscenario(ei: number, delta: number): void {
    const target = ei + delta;
    if (target < 0 || target >= this.escenarios.length) return;
    const [item] = this.escenarios.splice(ei, 1);
    this.escenarios.splice(target, 0, item);
  }

  agregarPregunta(ei: number): void {
    this.escenarios[ei].questions.push({
      orden: this.escenarios[ei].questions.length + 1,
      enunciado: '',
      options: [
        { orden: 1, texto: '', esCorrecta: true, justificacion: '', valoraciones: {} },
        { orden: 2, texto: '', esCorrecta: false, justificacion: '', valoraciones: {} },
      ],
    });
  }

  eliminarPregunta(ei: number, pi: number): void {
    if (this.escenarios[ei].questions.length > 1) this.escenarios[ei].questions.splice(pi, 1);
  }

  agregarOpcion(ei: number, pi: number): void {
    const opts = this.escenarios[ei].questions[pi].options;
    opts.push({ orden: opts.length + 1, texto: '', esCorrecta: false, justificacion: '', valoraciones: {} });
  }

  eliminarOpcion(ei: number, pi: number, oi: number): void {
    const opts = this.escenarios[ei].questions[pi].options;
    if (opts.length > 2) opts.splice(oi, 1);
  }

  sincronizarValoracionPorDefecto(op: OpcionDraft): void {
    const val = op.esCorrecta ? 100 : 0;
    for (const c of this.criterios) {
      if (!(c.nombre in op.valoraciones)) {
        op.valoraciones[c.nombre] = val;
      }
    }
  }

  private construirPayload(): CasoPayload {
    return {
      case: {
        nombre: this.casoNombre.trim(),
        desarrolloSituacional: this.desarrolloSituacional.trim(),
        contextoHistoria: this.contextoHistoria.trim(),
        tiempoEstimadoMin: Number(this.tiempoEstimadoMin) || 30,
      },
      scenarios: this.escenarios.map((e, ei) => ({
        orden: ei + 1,
        contextoSituacional: e.contextoSituacional.trim(),
        questions: e.questions.map((q, pi) => ({
          orden: pi + 1,
          enunciado: q.enunciado.trim(),
          options: q.options.map((o, oi) => {
            const vals: Record<string, number> = {};
            const fallback = o.esCorrecta ? 100 : 0;
            for (const c of this.criterios) {
              const nombre = c.nombre.trim();
              if (this.versionRegla === 'PREGUNTAS_100_V1') {
                vals[nombre] = fallback;
              } else {
                vals[nombre] = Number(o.valoraciones[nombre] ?? fallback);
              }
            }
            return {
              orden: oi + 1,
              texto: o.texto.trim(),
              esCorrecta: o.esCorrecta,
              justificacion: o.justificacion.trim(),
              valoraciones: vals,
            };
          }),
        })),
      })),
      rubric: {
        nombre: this.rubricaNombre.trim(),
        versionRegla: this.versionRegla,
        criterios: this.criterios.map((c) => ({
          nombre: c.nombre.trim(),
          peso: Number(c.peso),
          niveles: c.niveles.map((n) => ({
            nombre: n.nombre.trim(),
            puntaje: Number(n.puntaje),
            descriptor: n.descriptor.trim(),
          })),
        })),
      },
    };
  }

  private validarAntesDePublicar(): string[] {
    const errs: string[] = [];
    if (!this.casoNombre.trim()) errs.push('El caso debe tener nombre.');
    if (!(Number(this.tiempoEstimadoMin) > 0)) errs.push('El tiempo estimado debe ser mayor que 0.');
    if (!this.contextoHistoria.trim()) errs.push('Falta el contexto / historia del caso.');
    if (!this.desarrolloSituacional.trim()) errs.push('Falta el desarrollo situacional.');
    if (!this.rubricaNombre.trim()) errs.push('La rúbrica debe tener nombre.');
    if (!this.criterios.length) errs.push('Debes definir al menos un criterio de rúbrica.');
    if (Math.round(this.sumaPesos() * 100) !== 10000) {
      errs.push(`Los pesos de la rúbrica suman ${this.sumaPesos()}%, deben sumar exactamente 100%.`);
    }
    for (let i = 0; i < this.criterios.length; i++) {
      const c = this.criterios[i];
      if (!c.nombre.trim()) errs.push(`Criterio #${i + 1}: falta nombre.`);
      if (!c.niveles.length) errs.push(`Criterio '${c.nombre}': falta al menos un nivel.`);
    }
    if (!this.escenarios.length) errs.push('Debes incluir al menos un escenario.');
    this.escenarios.forEach((esc, ei) => {
      if (!esc.contextoSituacional.trim()) errs.push(`Escenario #${ei + 1}: falta contexto situacional.`);
      if (esc.questions.length !== 1) {
        errs.push(`Escenario #${ei + 1}: debe tener exactamente 1 pregunta para el recorrido ejecutable.`);
      }
      esc.questions.forEach((q, pi) => {
        if (!q.enunciado.trim()) errs.push(`Escenario #${ei + 1}, pregunta ${pi + 1}: falta enunciado.`);
        if (q.options.length < 2) errs.push(`Escenario #${ei + 1}, pregunta ${pi + 1}: mínimo 2 opciones.`);
        if (!q.options.some((o) => o.esCorrecta)) errs.push(`Escenario #${ei + 1}, pregunta ${pi + 1}: marca al menos 1 opción correcta.`);
        if (!q.options.some((o) => !o.esCorrecta)) errs.push(`Escenario #${ei + 1}, pregunta ${pi + 1}: requiere al menos 1 opción incorrecta.`);
        q.options.forEach((o, oi) => {
          if (!o.texto.trim()) errs.push(`Escenario #${ei + 1}, opción ${oi + 1}: falta texto de respuesta.`);
          if (!o.justificacion.trim()) errs.push(`Escenario #${ei + 1}, opción ${oi + 1}: falta justificación teórica (RF-08).`);
        });
      });
    });
    return errs;
  }

  async guardar(silencioso = false): Promise<string | null> {
    this.errorDetalle.set('');
    this.guardando.set(true);
    try {
      const payload = this.construirPayload();
      if (this.versionId) {
        await firstValueFrom(this.cases.actualizar(this.versionId, payload));
      } else {
        const res = await firstValueFrom(this.cases.crear(payload));
        this.versionId = res.version_id;
      }
      if (!silencioso) {
        this.snack.open('Borrador guardado correctamente.', 'OK', { duration: 3000 });
        await this.router.navigate(['/casos', this.versionId]);
      }
      return this.versionId;
    } catch (e) {
      this.errorDetalle.set(mensajeError(e));
      return null;
    } finally {
      this.guardando.set(false);
    }
  }

  async guardarYPublicar(): Promise<void> {
    const previos = this.validarAntesDePublicar();
    if (previos.length > 0) {
      this.errorDetalle.set(`Validación previa a publicación: ${previos.join(' · ')}`);
      this.snack.open('Corrige los campos señalados arriba antes de publicar.', 'Cerrar', { duration: 4500 });
      return;
    }

    const id = await this.guardar(true);
    if (!id) return;
    this.guardando.set(true);
    this.errorDetalle.set('');
    try {
      await this.cases.publicarInteligente(id);
      this.snack.open('Caso validado y PUBLICADO con éxito.', 'OK', { duration: 3500 });
      await this.router.navigate(['/casos', id]);
    } catch (e) {
      this.errorDetalle.set(mensajeError(e));
      this.snack.open('No se pudo publicar el caso. Revisa el detalle en rojo.', 'Cerrar', { duration: 4500 });
    } finally {
      this.guardando.set(false);
    }
  }
}
