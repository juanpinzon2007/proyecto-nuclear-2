import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { firstValueFrom } from 'rxjs';
import { mensajeError } from '../../core/api-error';
import {
  EscenarioWorkspace,
  PreguntaWorkspace,
  ResultadoIntentoDetalle,
  WorkspaceIntento,
} from '../../core/api.models';
import { ParticipationService } from '../../core/participation.service';

interface PasoPlano {
  escenario: EscenarioWorkspace;
  pregunta: PreguntaWorkspace;
}

@Component({
  selector: 'app-simulador',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterLink,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatProgressBarModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
  ],
  template: `
    <div class="sim-wrap">
      @if (cargando()) {
        <div class="center-spin"><mat-spinner diameter="44"></mat-spinner></div>
      } @else if (resultado(); as res) {
        <!-- PANTALLA RF-14: RESULTADO FINAL, CRITERIOS DE RÚBRICA, JUSTIFICACIONES Y FEEDBACK DOCENTE -->
        <div class="res-header">
          <a mat-stroked-button routerLink="/estudiante">
            <mat-icon>arrow_back</mat-icon> Volver al Portal
          </a>
          <span class="state-chip">{{ res.estado_intento }} · {{ res.modalidad }}</span>
        </div>

        <mat-card class="hero-score">
          <mat-card-content>
            <div class="hero-grid">
              <div>
                <div class="hero-lbl">Resultado de la Simulación (RF-13 · RF-14)</div>
                <h2>{{ res.caso_nombre }}</h2>
                <p class="muted">{{ res.comentario_automatico }}</p>
                <div class="stats-row">
                  <span>Aciertos: <strong>{{ res.aciertos }} / {{ res.total_preguntas }}</strong></span>
                  <span>Respondidas: <strong>{{ res.respondidas }} / {{ res.total_preguntas }}</strong></span>
                  <span>Rúbrica: <strong>{{ res.rubrica_nombre }}</strong></span>
                </div>
              </div>
              <div class="score-circle">
                <span class="score-num">{{ res.nota_final | number:'1.1-2' }}</span>
                <span class="score-sub">/ 100 pts</span>
              </div>
            </div>
          </mat-card-content>
        </mat-card>

        @if (res.retroalimentacion_docente) {
          <mat-card class="fb-card">
            <mat-card-header>
              <mat-card-title>Retroalimentación General del Docente (RF-26)</mat-card-title>
              <mat-card-subtitle>{{ res.fecha_retroalimentacion | date:'medium' }}</mat-card-subtitle>
            </mat-card-header>
            <mat-card-content style="padding-top:12px; font-size:15px; line-height:1.6;">
              {{ res.retroalimentacion_docente }}
            </mat-card-content>
          </mat-card>
        }

        @if (res.criterios.length) {
          <mat-card>
            <mat-card-header>
              <mat-card-title>Desglose por Criterios de Rúbrica (RF-17)</mat-card-title>
            </mat-card-header>
            <mat-card-content style="padding-top:14px;">
              <div class="criterios-grid">
                @for (c of res.criterios; track c.id_criterio) {
                  <div class="crit-card">
                    <div class="crit-top">
                      <strong>{{ c.nombre }}</strong>
                      <span class="gold-pill">Peso {{ c.peso }}%</span>
                    </div>
                    <div class="crit-score">
                      <span>{{ c.puntaje_obtenido | number:'1.1-2' }} / 100</span>
                      <span class="level-badge">{{ c.nivel_nombre }}</span>
                    </div>
                    <p class="muted" style="margin:6px 0 0; font-size:12px;">{{ c.nivel_descriptor }}</p>
                  </div>
                }
              </div>
            </mat-card-content>
          </mat-card>
        }

        <mat-card>
          <mat-card-header>
            <mat-card-title>Retroalimentación y Justificaciones Teóricas por Pregunta (RF-08 · RF-14)</mat-card-title>
          </mat-card-header>
          <mat-card-content style="padding-top:14px;">
            <div class="q-review-list">
              @for (q of res.preguntas; track q.pregunta_id; let qi = $index) {
                <div class="q-review" [class.q-ok]="q.es_correcta" [class.q-bad]="!q.es_correcta">
                  <div class="q-rev-head">
                    <strong>Escenario {{ q.escenario_orden }} · {{ qi + 1 }}. {{ q.enunciado }}</strong>
                    <span class="chip" [class.ok]="q.es_correcta" [class.bad]="!q.es_correcta">
                      {{ !q.respondida ? 'SIN RESPONDER (0 pts)' : (q.es_correcta ? 'CORRECTA' : 'INCORRECTA') }}
                    </span>
                  </div>
                  <div class="q-ans"><strong>Tu selección:</strong> {{ q.opcion_elegida_texto }}</div>
                  <div class="q-just"><strong>Justificación:</strong> {{ q.justificacion_elegida }}</div>
                  @if (!q.es_correcta && q.opcion_correcta_texto) {
                    <div class="q-corr">
                      <strong>Respuesta esperada:</strong> {{ q.opcion_correcta_texto }}
                      @if (q.justificacion_correcta) {
                        <div style="margin-top:4px;"><em>Fundamento:</em> {{ q.justificacion_correcta }}</div>
                      }
                    </div>
                  }
                  @if (q.reflexion_estudiante) {
                    <div class="q-refl"><strong>Tu reflexión:</strong> {{ q.reflexion_estudiante }}</div>
                  }
                </div>
              }
            </div>
          </mat-card-content>
        </mat-card>
      } @else if (workspace(); as ws) {
        <!-- MODO ACTIVO: ESPACIO DE TRABAJO EDITABLE RF-10 + TEMPORIZADOR RF-23 -->
        <div class="hud-bar">
          <div>
            <div class="hud-title">{{ ws.caso_nombre }} <span class="mode-tag">Intento #{{ ws.numero_intento }} · {{ ws.modo_recorrido }}</span></div>
            <div class="hud-sub">
              Progreso: {{ ws.respondidas ?? 0 }} / {{ ws.total_preguntas ?? 0 }} respondidas ·
              Cambios realizados: {{ ws.cambios_realizados ?? 0 }}
            </div>
          </div>

          <div class="timer-box" [class.timer-warn]="segundosRestantes() <= 300" [class.timer-crit]="segundosRestantes() <= 60">
            <mat-icon>timer</mat-icon>
            <span class="mono timer-txt">{{ formatearTiempo(segundosRestantes()) }}</span>
          </div>
        </div>

        <mat-progress-bar mode="determinate"
                          [value]="((ws.respondidas ?? 0) / Math.max(1, ws.total_preguntas ?? 1)) * 100"
                          style="margin-bottom:16px; border-radius:4px;">
        </mat-progress-bar>

        <div class="play-grid">
          <!-- Stepper navegable Anterior / Siguiente / Saltar (RF-10) -->
          <mat-card class="nav-card">
            <mat-card-header>
              <mat-card-title>Preguntas (RF-10)</mat-card-title>
              <mat-card-subtitle>Puedes volver atrás y modificar tus respuestas antes de entregar</mat-card-subtitle>
            </mat-card-header>
            <mat-card-content style="padding-top:12px;">
              <div class="step-list">
                @for (item of pasosPlanos(); track item.pregunta.id; let idx = $index) {
                  <button type="button"
                          class="step-btn"
                          [class.step-active]="idx === indiceActual()"
                          [class.step-done]="estaRespondida(item.pregunta.id)"
                          (click)="irAPregunta(idx)">
                    <span>Esc. {{ item.escenario.orden }} · P{{ idx + 1 }}</span>
                    <mat-icon>{{ estaRespondida(item.pregunta.id) ? 'check_circle' : 'radio_button_unchecked' }}</mat-icon>
                  </button>
                }
              </div>
            </mat-card-content>
          </mat-card>

          <!-- Escenario y Pregunta Actual -->
          @if (pasoActual(); as actual) {
            <mat-card class="question-card">
              <mat-card-header>
                <mat-card-title>Escenario {{ actual.escenario.orden }} — Decisión {{ indiceActual() + 1 }} de {{ pasosPlanos().length }}</mat-card-title>
              </mat-card-header>
              <mat-card-content style="padding-top:16px;">
                <div class="context-panel">
                  <div class="ctx-lbl">Situación Clínica / Ética</div>
                  <p>{{ actual.escenario.contexto_situacional }}</p>
                </div>

                <h3 class="q-enunciado">{{ actual.pregunta.enunciado }}</h3>

                <div class="options-stack">
                  @for (op of actual.pregunta.opciones; track op.id) {
                    <label class="option-card" [class.option-selected]="opcionElegida === op.id">
                      <input type="radio"
                             [name]="'q_' + actual.pregunta.id"
                             [value]="op.id"
                             [(ngModel)]="opcionElegida" />
                      <span>{{ op.texto }}</span>
                    </label>
                  }
                </div>

                <div class="refl-edit">
                  <label class="ctx-lbl" for="reflInput">Reflexión o sustento personal (opcional, editable antes de enviar):</label>
                  <textarea id="reflInput" class="refl-textarea" rows="3" [(ngModel)]="reflexionInput"
                            placeholder="Argumenta brevemente tu decisión..."></textarea>
                </div>

                <div class="play-actions">
                  <div style="display:flex; gap:10px;">
                    <button mat-stroked-button type="button" (click)="anterior()" [disabled]="indiceActual() === 0 || guardando()">
                      <mat-icon>arrow_back</mat-icon> Anterior
                    </button>
                    <button mat-flat-button color="primary" type="button" (click)="guardarYAvanzar()"
                            [disabled]="!opcionElegida || guardando()">
                      <mat-icon>save</mat-icon>
                      {{ indiceActual() < pasosPlanos().length - 1 ? 'Guardar y Siguiente' : 'Guardar Respuesta' }}
                    </button>
                  </div>

                  <button mat-flat-button color="accent" type="button" (click)="entregarSimulacion()" [disabled]="guardando()">
                    <mat-icon>done_all</mat-icon> Entregar Simulación Definitiva
                  </button>
                </div>
              </mat-card-content>
            </mat-card>
          }
        </div>
      }
    </div>
  `,
  styles: [`
    .sim-wrap { padding: 8px 0 40px; }
    .center-spin { display: flex; justify-content: center; padding: 60px; }
    .hud-bar { display: flex; justify-content: space-between; align-items: center; gap: 16px; margin-bottom: 12px; flex-wrap: wrap; }
    .hud-title { font-size: 20px; font-weight: 700; color: #f8fafc; }
    .hud-sub { font-size: 13px; color: #94a3b8; margin-top: 2px; }
    .mode-tag { font-size: 11px; margin-left: 8px; padding: 2px 8px; border-radius: 999px; background: rgba(16,185,129,0.18); color: #34d399; }
    .timer-box { display: flex; align-items: center; gap: 8px; padding: 8px 16px; border-radius: 10px; background: rgba(15,23,42,0.9); border: 1px solid rgba(16,185,129,0.5); color: #34d399; }
    .timer-box.timer-warn { border-color: #f59e0b; color: #fbbf24; }
    .timer-box.timer-crit { border-color: #ef4444; color: #f87171; animation: pulse 1s infinite; }
    @keyframes pulse { 0%,100% { opacity:1; } 50% { opacity:0.65; } }
    .timer-txt { font-size: 20px; font-weight: 800; letter-spacing: 0.06em; }
    .play-grid { display: grid; grid-template-columns: 270px 1fr; gap: 18px; align-items: start; }
    @media (max-width: 960px) { .play-grid { grid-template-columns: 1fr; } }
    .step-list { display: flex; flex-direction: column; gap: 8px; }
    .step-btn { display: flex; justify-content: space-between; align-items: center; padding: 10px 12px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1); background: rgba(6,11,22,0.65); color: #cbd5e1; cursor: pointer; font-weight: 600; transition: all 0.2s; }
    .step-btn.step-done { border-color: rgba(16,185,129,0.45); color: #34d399; }
    .step-btn.step-active { border-color: #fbbf24; background: rgba(245,158,11,0.14); color: #f8fafc; }
    .context-panel { background: rgba(6,11,22,0.7); border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 14px; margin-bottom: 16px; }
    .context-panel p { margin: 6px 0 0; line-height: 1.6; color: #e2e8f0; }
    .ctx-lbl { font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; color: #94a3b8; font-weight: 700; display: block; }
    .q-enunciado { font-size: 18px; font-weight: 700; color: #f8fafc; margin: 0 0 14px; }
    .options-stack { display: flex; flex-direction: column; gap: 10px; margin-bottom: 18px; }
    .option-card { display: flex; align-items: flex-start; gap: 12px; padding: 14px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.12); background: rgba(15,23,42,0.72); cursor: pointer; transition: all 0.2s; color: #f8fafc; }
    .option-card:hover { border-color: rgba(16,185,129,0.45); }
    .option-card.option-selected { border-color: #10b981; background: rgba(16,185,129,0.14); }
    .refl-edit { margin-bottom: 18px; }
    .refl-textarea { width: 100%; box-sizing: border-box; margin-top: 6px; background: rgba(6,11,22,0.8); color: #f8fafc; border: 1px solid rgba(255,255,255,0.16); border-radius: 8px; padding: 10px; font-family: inherit; }
    .play-actions { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; }
    .res-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
    .state-chip { background: rgba(16,185,129,0.18); border: 1px solid rgba(16,185,129,0.45); color: #34d399; padding: 4px 12px; border-radius: 999px; font-weight: 700; font-size: 12px; }
    .hero-score { border: 1px solid rgba(16,185,129,0.4) !important; }
    .hero-grid { display: flex; justify-content: space-between; align-items: center; gap: 20px; flex-wrap: wrap; }
    .hero-lbl { font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em; color: #10b981; font-weight: 700; }
    .stats-row { display: flex; gap: 18px; margin-top: 10px; font-size: 13px; color: #cbd5e1; flex-wrap: wrap; }
    .score-circle { min-width: 130px; height: 130px; border-radius: 50%; background: rgba(16,185,129,0.12); border: 3px solid #10b981; display: flex; flex-direction: column; align-items: center; justify-content: center; }
    .score-num { font-size: 32px; font-weight: 800; color: #34d399; }
    .score-sub { font-size: 12px; color: #94a3b8; }
    .fb-card { border-left: 4px solid #fbbf24 !important; }
    .criterios-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 12px; }
    .crit-card { background: rgba(6,11,22,0.65); border: 1px solid rgba(255,255,255,0.1); border-radius: 10px; padding: 14px; }
    .crit-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
    .gold-pill { color: #fbbf24; font-weight: 700; font-size: 12px; }
    .crit-score { display: flex; justify-content: space-between; align-items: center; font-size: 15px; font-weight: 700; color: #34d399; }
    .level-badge { background: rgba(16,185,129,0.2); padding: 2px 8px; border-radius: 6px; font-size: 12px; }
    .q-review-list { display: flex; flex-direction: column; gap: 12px; }
    .q-review { padding: 14px; border-radius: 10px; background: rgba(6,11,22,0.7); border: 1px solid rgba(255,255,255,0.1); display: flex; flex-direction: column; gap: 6px; }
    .q-review.q-ok { border-color: rgba(16,185,129,0.45); }
    .q-review.q-bad { border-color: rgba(239,68,68,0.45); }
    .q-rev-head { display: flex; justify-content: space-between; align-items: center; gap: 10px; flex-wrap: wrap; }
    .q-corr { background: rgba(16,185,129,0.1); border-radius: 6px; padding: 8px 10px; font-size: 13px; color: #a7f3d0; }
    .q-refl { background: rgba(15,23,42,0.8); border-radius: 6px; padding: 8px 10px; font-size: 13px; }
  `],
})
export class SimuladorComponent implements OnInit, OnDestroy {
  private readonly route = inject(ActivatedRoute);
  private readonly participation = inject(ParticipationService);
  private readonly snack = inject(MatSnackBar);

  readonly Math = Math;
  idIntento = 0;

  readonly cargando = signal(true);
  readonly guardando = signal(false);
  readonly workspace = signal<WorkspaceIntento | null>(null);
  readonly resultado = signal<ResultadoIntentoDetalle | null>(null);
  readonly indiceActual = signal(0);
  readonly segundosRestantes = signal(0);

  opcionElegida = '';
  reflexionInput = '';

  readonly pasosPlanos = computed<PasoPlano[]>(() => {
    const ws = this.workspace();
    if (!ws?.escenarios) return [];
    const lista: PasoPlano[] = [];
    for (const esc of ws.escenarios) {
      for (const preg of esc.preguntas) {
        lista.push({ escenario: esc, pregunta: preg });
      }
    }
    return lista;
  });

  readonly pasoActual = computed<PasoPlano | null>(() => {
    const list = this.pasosPlanos();
    const idx = this.indiceActual();
    return list[idx] ?? null;
  });

  private timerHandle: ReturnType<typeof setInterval> | null = null;
  private vencimientoAutoEjecutado = false;

  ngOnInit(): void {
    this.idIntento = Number(this.route.snapshot.paramMap.get('id') ?? '0');
    if (this.idIntento) {
      this.participation.recordarIntento(this.idIntento);
      void this.cargarEstado();
    }
  }

  ngOnDestroy(): void {
    if (this.timerHandle) clearInterval(this.timerHandle);
  }

  async cargarEstado(): Promise<void> {
    this.cargando.set(true);
    try {
      const ws = await firstValueFrom(this.participation.obtenerWorkspace(this.idIntento));
      if (ws.cerrado && ws.resultado) {
        this.resultado.set(ws.resultado);
        this.workspace.set(null);
      } else {
        this.workspace.set(ws);
        this.segundosRestantes.set(ws.segundos_restantes ?? 0);
        this.posicionarInicial();
        this.iniciarTimer();
      }
    } catch (e) {
      this.snack.open(mensajeError(e), 'Cerrar', { duration: 4500 });
    } finally {
      this.cargando.set(false);
    }
  }

  private posicionarInicial(): void {
    const pasos = this.pasosPlanos();
    const idxPend = pasos.findIndex((p) => !this.estaRespondida(p.pregunta.id));
    this.irAPregunta(idxPend >= 0 ? idxPend : 0);
  }

  private iniciarTimer(): void {
    if (this.timerHandle) clearInterval(this.timerHandle);
    this.timerHandle = setInterval(() => {
      const ws = this.workspace();
      if (!ws?.vence_en) return;
      const diff = Math.max(0, Math.floor((new Date(ws.vence_en).getTime() - Date.now()) / 1000));
      this.segundosRestantes.set(diff);
      if (diff <= 0 && !this.vencimientoAutoEjecutado) {
        this.vencimientoAutoEjecutado = true;
        if (this.timerHandle) clearInterval(this.timerHandle);
        void this.cierrePorTiempoAgotado();
      }
    }, 1000);
  }

  private async cierrePorTiempoAgotado(): Promise<void> {
    this.snack.open('Tiempo máximo agotado (RF-23). Cerrando intento y calculando resultado...', 'OK', { duration: 4000 });
    try {
      const res = await firstValueFrom(this.participation.enviarSimulacion(this.idIntento, true));
      this.resultado.set(res);
      this.workspace.set(null);
    } catch {
      await this.cargarEstado();
    }
  }

  estaRespondida(preguntaId: string): boolean {
    return !!this.workspace()?.borradores?.[preguntaId];
  }

  irAPregunta(idx: number): void {
    const pasos = this.pasosPlanos();
    if (idx < 0 || idx >= pasos.length) return;
    this.indiceActual.set(idx);
    const pregId = pasos[idx].pregunta.id;
    const draft = this.workspace()?.borradores?.[pregId];
    this.opcionElegida = draft?.id_opcion ?? '';
    this.reflexionInput = draft?.reflexion_estudiante ?? '';
  }

  anterior(): void {
    if (this.indiceActual() > 0) this.irAPregunta(this.indiceActual() - 1);
  }

  async guardarYAvanzar(): Promise<void> {
    const actual = this.pasoActual();
    if (!actual || !this.opcionElegida) return;
    this.guardando.set(true);
    try {
      const prevIdx = this.indiceActual();
      const wsActualizado = await firstValueFrom(
        this.participation.guardarBorrador(
          this.idIntento,
          actual.pregunta.id,
          this.opcionElegida,
          this.reflexionInput.trim() || null,
        ),
      );
      if (wsActualizado.cerrado && wsActualizado.resultado) {
        this.resultado.set(wsActualizado.resultado);
        this.workspace.set(null);
        return;
      }
      this.workspace.set(wsActualizado);
      const nuevos = this.pasosPlanos();
      const sigIdx = prevIdx + 1 < nuevos.length ? prevIdx + 1 : prevIdx;
      this.irAPregunta(sigIdx);
      this.snack.open('Respuesta guardada (editable hasta entregar).', 'OK', { duration: 1800 });
    } catch (e) {
      this.snack.open(mensajeError(e), 'Cerrar', { duration: 4000 });
    } finally {
      this.guardando.set(false);
    }
  }

  async entregarSimulacion(): Promise<void> {
    const ws = this.workspace();
    if (!ws) return;

    // Guardar cambio pendiente si hay uno elegido sin guardar aún
    const actual = this.pasoActual();
    if (actual && this.opcionElegida) {
      const draft = ws.borradores?.[actual.pregunta.id];
      if (!draft || draft.id_opcion !== this.opcionElegida || (draft.reflexion_estudiante ?? '') !== this.reflexionInput.trim()) {
        await firstValueFrom(
          this.participation.guardarBorrador(
            this.idIntento,
            actual.pregunta.id,
            this.opcionElegida,
            this.reflexionInput.trim() || null,
          ),
        );
      }
    }

    const wsFresco = await firstValueFrom(this.participation.obtenerWorkspace(this.idIntento));
    this.workspace.set(wsFresco);

    let permitirParcial = false;
    if (!wsFresco.listo_para_enviar) {
      const ok = confirm(
        `Faltan preguntas por responder (${wsFresco.respondidas}/${wsFresco.total_preguntas}). ` +
          'Las preguntas pendientes obtendrán 0 puntos. ¿Confirmas entrega parcial definitiva?',
      );
      if (!ok) return;
      permitirParcial = true;
    } else {
      if (!confirm('¿Confirmas la entrega definitiva? Una vez enviada no podrás modificar tus respuestas.')) {
        return;
      }
    }

    this.guardando.set(true);
    try {
      const res = await firstValueFrom(this.participation.enviarSimulacion(this.idIntento, permitirParcial));
      if (this.timerHandle) clearInterval(this.timerHandle);
      this.resultado.set(res);
      this.workspace.set(null);
      this.snack.open('Simulación entregada y calificada correctamente.', 'OK', { duration: 3500 });
    } catch (e) {
      this.snack.open(mensajeError(e), 'Cerrar', { duration: 4500 });
    } finally {
      this.guardando.set(false);
    }
  }

  formatearTiempo(seg: number): string {
    const mins = Math.floor(seg / 60);
    const secs = seg % 60;
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  }
}
