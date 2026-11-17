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
import { UiDialogService } from '../../core/ui-dialog.service';

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
    <div class="sim-wrap content">
      @if (cargando()) {
        <div class="center-spin"><mat-spinner diameter="44"></mat-spinner></div>
      } @else if (resultado(); as res) {
        <!-- PANTALLA RF-14: RESULTADO FINAL GAMIFICADO (.score-ring + .chart-card + .events) -->
        <div class="res-header">
          <a mat-stroked-button routerLink="/estudiante">
            <mat-icon>arrow_back</mat-icon> Volver al Portal
          </a>
          <span class="tag green">{{ res.estado_intento }} · {{ res.modalidad }}</span>
        </div>

        <mat-card class="panel result-head stagger">
          <mat-card-content>
            <div class="spread head-top">
              <div>
                <p class="eyebrow green">Estado: Simulación Finalizada (RF-13 · RF-14)</p>
                <h1>{{ res.caso_nombre }}</h1>
              </div>
              <span class="ref mono">{{ res.rubrica_nombre }}</span>
            </div>

            <div class="score-layout">
              <div class="score-ring" [style.--score]="res.nota_final + '%'">
                <div class="score-value">
                  <span>{{ res.nota_final | number:'1.1-2' }}</span>
                  <small>/ 100 PTS</small>
                </div>
              </div>

              <div class="score-copy">
                <div class="spread mono">
                  <span>ÍNDICE DE DESEMPEÑO GLOBAL</span>
                  <b class="green">{{ res.nota_final | number:'1.1-2' }} / 100</b>
                </div>
                <div class="meter">
                  <span [style.width.%]="res.nota_final" style="--meter-color: var(--green)"></span>
                </div>
                <div class="stats-row mono">
                  <span>ACIERTOS: <strong class="cyan">{{ res.aciertos }} / {{ res.total_preguntas }}</strong></span>
                  <span>RESPONDIDAS: <strong class="cyan">{{ res.respondidas }} / {{ res.total_preguntas }}</strong></span>
                </div>
                <p class="summary">{{ res.comentario_automatico }}</p>
              </div>
            </div>
          </mat-card-content>
        </mat-card>

        @if (res.retroalimentacion_docente) {
          <mat-card class="panel fb-card">
            <mat-card-header>
              <mat-card-title>Retroalimentación General del Docente (RF-26)</mat-card-title>
              <mat-card-subtitle>{{ res.fecha_retroalimentacion | date:'medium' }}</mat-card-subtitle>
            </mat-card-header>
            <mat-card-content style="padding-top:14px; font-size:15px; line-height:1.6;">
              {{ res.retroalimentacion_docente }}
            </mat-card-content>
          </mat-card>
        }

        @if (res.criterios.length) {
          <section class="panel panel-pad chart-card">
            <div class="spread">
              <div>
                <p class="eyebrow green">Desglose de Evaluación</p>
                <h2 class="section-heading">Criterios de Rúbrica (RF-17)</h2>
              </div>
              <span class="tag green">RÚBRICA</span>
            </div>

            <div class="chart-bars">
              @for (c of res.criterios; track c.id_criterio) {
                <div class="chart-row">
                  <span>{{ c.nombre }} ({{ c.peso }}%)</span>
                  <i><b [style.width.%]="c.puntaje_obtenido"></b></i>
                  <strong>{{ c.puntaje_obtenido | number:'1.1-2' }}</strong>
                </div>
              }
            </div>

            <div class="criterios-grid stagger">
              @for (c of res.criterios; track c.id_criterio) {
                <article class="crit-card">
                  <div class="crit-top">
                    <strong>{{ c.nombre }}</strong>
                    <span class="tag amber">PESO {{ c.peso }}%</span>
                  </div>
                  <div class="crit-score mono">
                    <span>{{ c.puntaje_obtenido | number:'1.1-2' }}<small>/100</small></span>
                    <span class="tag green">{{ c.nivel_nombre }}</span>
                  </div>
                  <div class="meter" style="height: 8px;">
                    <span [style.width.%]="c.puntaje_obtenido"></span>
                  </div>
                  <p class="muted crit-desc">{{ c.nivel_descriptor }}</p>
                </article>
              }
            </div>
          </section>
        }

        <section class="panel events">
          <div class="events-head spread">
            <div>
              <p class="eyebrow">Bitácora de Decisiones (RF-08 · RF-14)</p>
              <h3>Justificaciones Teóricas por Pregunta</h3>
            </div>
            <span class="tag">{{ res.preguntas.length }} ITEMS</span>
          </div>

          <div class="q-review-list">
            @for (q of res.preguntas; track q.pregunta_id; let qi = $index) {
              <div class="event-row" [class.q-ok]="q.es_correcta" [class.q-bad]="!q.es_correcta">
                <div class="event-top">
                  <b class="event-badge" [class.amber]="!q.es_correcta">
                    {{ q.es_correcta ? '✓' : '!' }}
                  </b>
                  <span class="mono cyan">ESC-{{ q.escenario_orden }} · P{{ qi + 1 }}</span>
                  <strong class="q-title-txt">{{ q.enunciado }}</strong>
                  <span class="chip" [class.ok]="q.es_correcta" [class.bad]="!q.es_correcta">
                    {{ !q.respondida ? 'SIN RESPONDER (0 PTS)' : (q.es_correcta ? 'CORRECTA' : 'INCORRECTA') }}
                  </span>
                </div>

                <div class="event-body">
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
              </div>
            }
          </div>
        </section>
      } @else if (workspace(); as ws) {
        <!-- MODO ACTIVO: CONSOLA TÁCTICA + MAZO DE CARTAS INTERACTIVO (RF-10 + RF-23) -->
        <section class="panel panel-pad mission-strip">
          <div class="spread mission-top">
            <div>
              <p class="eyebrow">Misión Activa // {{ ws.modo_recorrido }}</p>
              <div class="hud-title">
                {{ ws.caso_nombre }}
                <span class="tag green">INTENTO #{{ ws.numero_intento }}</span>
              </div>
              <div class="hud-sub mono">
                PROGRESO: {{ ws.respondidas ?? 0 }}/{{ ws.total_preguntas ?? 0 }} · CAMBIOS RF-10: {{ ws.cambios_realizados ?? 0 }}
              </div>
            </div>

            <div class="timer-box" [class.timer-warn]="segundosRestantes() <= 300" [class.timer-crit]="segundosRestantes() <= 60">
              <mat-icon>timer</mat-icon>
              <div>
                <small class="timer-lbl">TIEMPO RESTANTE</small>
                <span class="mono timer-txt">{{ formatearTiempo(segundosRestantes()) }}</span>
              </div>
            </div>
          </div>

          <mat-progress-bar
            mode="determinate"
            [value]="((ws.respondidas ?? 0) / Math.max(1, ws.total_preguntas ?? 1)) * 100"
            class="hud-progress"
          ></mat-progress-bar>

          <!-- Progress Steps Discretos Navegables RF-10 -->
          <div class="progress-steps" aria-label="Navegador de preguntas">
            @for (item of pasosPlanos(); track item.pregunta.id; let idx = $index) {
              <button
                type="button"
                class="step-btn"
                [class.step-active]="idx === indiceActual()"
                [class.step-done]="estaRespondida(item.pregunta.id)"
                (click)="irAPregunta(idx)"
                [disabled]="guardando() || !!opcionLanzada()"
                [title]="'Ir a Escenario ' + item.escenario.orden + ' Pregunta ' + (idx + 1)"
              >
                <span class="step-code">E{{ item.escenario.orden }}·P{{ idx + 1 }}</span>
                <mat-icon>{{ estaRespondida(item.pregunta.id) ? 'check_circle' : 'radio_button_unchecked' }}</mat-icon>
              </button>
            }
          </div>
        </section>

        @if (pasoActual(); as actual) {
          <!-- Escenario Diorama Animado (heredado de proyecto-nuclear-final) -->
          <section
            class="panel scene-frame"
            [class.scene-armed]="!!opcionElegida && !opcionLanzada()"
            [class.scene-responding]="!!opcionLanzada()"
            [class.stage-enter]="transicionandoEscena()"
            [class.comisaria]="(actual.escenario.orden - 1) % 4 === 2"
          >
            <span class="tag scene-tag">ESCENARIO 0{{ actual.escenario.orden }} · DECISIÓN {{ indiceActual() + 1 }}/{{ pasosPlanos().length }}</span>
            <div class="fx-orb o1"></div>
            <div class="fx-orb o2"></div>

            @switch ((actual.escenario.orden - 1) % 4) {
              @case (0) {
                <div class="stage hospital-crisis" aria-hidden="true">
                  <div class="rain"></div>
                  <div class="moon"></div>
                  <div class="hospital"><b>CASO</b><i></i><i></i><i></i><i></i><em></em></div>
                  <div class="ambulance"><span></span><b></b><i></i><i></i></div>
                  <div class="family"><span></span><span></span><span></span></div>
                  <div class="pulse-line"></div>
                </div>
              }
              @case (1) {
                <div class="stage epicee-room" aria-hidden="true">
                  <div class="room-light"></div>
                  <div class="clinician"><i></i><b></b></div>
                  <div class="family-group"><span></span><span></span><span></span></div>
                  <div class="message-card"><b>DIÁLOGO</b><small>Escucha y análisis</small></div>
                  <div class="calm-wave w1"></div>
                  <div class="calm-wave w2"></div>
                </div>
              }
              @case (2) {
                <div class="stage protection-risk" aria-hidden="true">
                  <div class="safe-door"></div>
                  <div class="person protected"></div>
                  <div class="risk-meter"><span></span></div>
                  <div class="shield">CRITERIO ÉTICO</div>
                  <div class="path"></div>
                </div>
              }
              @default {
                <div class="stage care-network" aria-hidden="true">
                  <div class="node victim">Caso</div>
                  <div class="node rights">Ética</div>
                  <div class="node health">Protocolo</div>
                  <div class="node mental">Contexto</div>
                  <div class="node risk">Riesgo</div>
                  <div class="net l1"></div>
                  <div class="net l2"></div>
                  <div class="route-dot"></div>
                </div>
              }
            }

            <div class="scene-note">
              <div class="ctx-lbl">Situación del Escenario {{ actual.escenario.orden }}</div>
              <p>{{ actual.escenario.contexto_situacional }}</p>
            </div>
          </section>

          <!-- Coach Neuro reactivo -->
          <section class="coach panel" [class.coach-pulse]="!!opcionElegida || !!respuestaAnimada()">
            <div class="coach-orb">🧠</div>
            <div class="grow">
              <span class="eyebrow">Asistente SPS · Guía de Escenario</span>
              <p class="coach-msg">{{ coachMensaje() }}</p>
            </div>
            <span class="tag" [class.green]="!!opcionElegida || !!opcionLanzada()">
              {{ opcionLanzada() ? 'REGISTRADO ✓' : (opcionElegida ? 'CARTA ARMADA' : 'ELIGE CARTA') }}
            </span>
          </section>

          <!-- Enunciado de Decisión -->
          <div class="prompt-banner panel" [class.stage-enter]="transicionandoEscena()">
            <p class="eyebrow amber">Dilema a resolver</p>
            <h2 class="q-enunciado">{{ actual.pregunta.enunciado }}</h2>
          </div>

          <!-- Carril Horizontal de Cartas Inclinadas (Deck Gamificado) -->
          <div class="card-rail" [class.has-selection]="!!opcionElegida" [class.locked]="!!opcionLanzada()">
            @for (op of actual.pregunta.opciones; track op.id; let oi = $index) {
              <label
                class="action-card"
                [class.selected]="opcionElegida === op.id"
                [class.option-selected]="opcionElegida === op.id"
                [class.launched]="opcionLanzada() === op.id"
                [style.--tilt]="cardTilt(oi)"
              >
                <input
                  type="radio"
                  class="sr-only-radio"
                  [name]="'q_' + actual.pregunta.id"
                  [value]="op.id"
                  [(ngModel)]="opcionElegida"
                  [disabled]="!!opcionLanzada() || guardando()"
                />

                <div class="card-top-row">
                  <span class="mode-pill" [class.good]="opcionElegida === op.id || opcionLanzada() === op.id">
                    OPCIÓN 0{{ oi + 1 }}
                  </span>
                  <span class="card-symbol">{{ opcionLanzada() === op.id ? '🚀' : (opcionElegida === op.id ? '✦' : '◆') }}</span>
                </div>

                <span class="card-kicker">{{ opcionLanzada() === op.id ? 'DECISIÓN LANZADA' : 'CARTA DE INTERVENCIÓN' }}</span>
                <strong class="card-decision-text">{{ op.texto }}</strong>

                <div class="stats">
                  <label>
                    <span>IMPACTO</span>
                    <i><b [style.width.%]="70 + ((oi * 9) % 25)"></b></i>
                  </label>
                  <label>
                    <span>CRITERIO</span>
                    <i><b [style.width.%]="65 + ((oi * 13) % 30)"></b></i>
                  </label>
                </div>

                <div class="touch-label">
                  {{
                    opcionLanzada() === op.id
                      ? '[ ✓ CARTA LANZADA ]'
                      : opcionElegida === op.id
                        ? '[ ● CARTA SELECCIONADA ]'
                        : '[ TOCA PARA SELECCIONAR ]'
                  }}
                </div>
              </label>
            }
          </div>

          @if (respuestaAnimada(); as rAnim) {
            <section class="panel panel-pad feedback">
              <div class="spread">
                <span class="eyebrow green">🎉 Decisión registrada en Escenario {{ rAnim.paso }}</span>
                <span class="tag green">PASO GUARDADO ✓</span>
              </div>
              <p>{{ rAnim.texto }}</p>
              <div class="meter stress">
                <span [style.width.%]="((ws.respondidas ?? 0) / Math.max(1, ws.total_preguntas ?? 1)) * 100"></span>
              </div>
            </section>
          }

          <!-- Reflexión Terminal + Launch Pad -->
          <mat-card class="panel refl-panel">
            <label class="ctx-lbl" for="reflInput">Bitácora de sustento personal (opcional, editable antes de entregar)</label>
            <textarea
              id="reflInput"
              class="refl-textarea"
              rows="3"
              [(ngModel)]="reflexionInput"
              placeholder="Argumenta brevemente el criterio psicológico y ético de tu elección..."
            ></textarea>
          </mat-card>

          <section class="panel launch-pad">
            <div class="selected-brief">
              <div class="launch-ico" [class.rocket-launch]="!!opcionLanzada()">🚀</div>
              <div>
                <small>{{ opcionLanzada() ? 'LANZAMIENTO CONFIRMADO' : (opcionElegida ? 'CARTA PREPARADA PARA LANZAMIENTO' : 'SELECCIONA UNA CARTA DEL MAZO SUPERIOR') }}</small>
                <b>{{ opcionLanzada() ? 'Guardando decisión...' : (opcionElegida ? 'Decisión #' + (indiceActual() + 1) + ' lista para registrar' : 'Esperando selección...') }}</b>
              </div>
            </div>

            <div class="play-actions">
              <button mat-stroked-button type="button" (click)="anterior()" [disabled]="indiceActual() === 0 || guardando() || !!opcionLanzada()">
                <mat-icon>arrow_back</mat-icon> Anterior
              </button>
              <button mat-flat-button color="primary" type="button" (click)="guardarYAvanzar()" [disabled]="!opcionElegida || guardando() || !!opcionLanzada()">
                <mat-icon>{{ opcionLanzada() ? 'hourglass_top' : 'rocket_launch' }}</mat-icon>
                {{ opcionLanzada() ? 'Registrando...' : (indiceActual() < pasosPlanos().length - 1 ? 'Lanzar y Siguiente' : 'Lanzar Respuesta') }}
              </button>
              <button mat-flat-button color="accent" type="button" (click)="entregarSimulacion()" [disabled]="guardando() || !!opcionLanzada()">
                <mat-icon>done_all</mat-icon> Entregar Simulación
              </button>
            </div>
          </section>
        }
      }
    </div>
  `,
  styles: [`
    .sim-wrap {
      padding: 4px 0 40px;
      max-width: 980px;
      display: grid;
      gap: 16px;
    }

    /* ==================== HUD SUPERIOR DE MISIÓN ==================== */
    .mission-strip {
      display: grid;
      gap: 12px;
      border-left: 4px solid var(--cyan);
      background:
        radial-gradient(circle at right top, rgba(0, 229, 244, 0.1), transparent 45%),
        rgba(16, 20, 27, 0.96);
    }
    .hud-title {
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
      font-family: var(--display);
      font-size: clamp(24px, 4vw, 32px);
      font-weight: 700;
      text-transform: uppercase;
      color: var(--text);
      margin-top: 4px;
    }
    .hud-sub {
      color: var(--muted);
      margin-top: 2px;
    }
    .timer-box {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 10px 16px;
      border: 1px solid rgba(0, 232, 148, 0.5);
      background: rgba(5, 12, 14, 0.9);
      color: var(--green);
    }
    .timer-box.timer-warn {
      border-color: var(--amber);
      color: var(--amber);
    }
    .timer-box.timer-crit {
      border-color: var(--red);
      color: var(--coral);
      animation: pulse 1s infinite;
    }
    .timer-lbl {
      display: block;
      font-family: var(--mono);
      font-size: 9px;
      letter-spacing: 1px;
      opacity: 0.85;
    }
    .timer-txt {
      font-size: 22px;
      font-weight: 700;
      letter-spacing: 1.5px;
      color: inherit !important;
    }
    .hud-progress {
      height: 8px;
      border-radius: 99px;
    }
    .progress-steps {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      padding-top: 4px;
    }
    .step-btn {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 7px 11px;
      border: 1px solid rgba(184, 211, 214, 0.2);
      background: #0b1017;
      color: var(--muted);
      font-family: var(--mono);
      font-size: 11px;
      transition: all 0.2s ease;
    }
    .step-btn mat-icon {
      font-size: 16px;
      width: 16px;
      height: 16px;
    }
    .step-btn.step-done {
      border-color: rgba(0, 232, 148, 0.5);
      background: rgba(0, 232, 148, 0.08);
      color: var(--green);
    }
    .step-btn.step-active {
      border-color: var(--cyan);
      background: rgba(0, 229, 244, 0.14);
      color: var(--cyan-soft);
      box-shadow: 0 0 14px rgba(0, 229, 244, 0.22);
    }

    /* ==================== SCENE FRAME DIORAMA ANIMADO ==================== */
    .scene-frame {
      position: relative;
      overflow: hidden;
      min-height: 310px;
      padding: 20px;
      display: grid;
      gap: 14px;
      background:
        radial-gradient(circle at 80% 18%, rgba(0, 229, 244, 0.16), transparent 44%),
        linear-gradient(180deg, rgba(11, 18, 28, 0.96), rgba(7, 10, 16, 0.98));
      transition: border-color 0.28s ease, box-shadow 0.28s ease, transform 0.28s ease;
    }
    .scene-frame.comisaria {
      background:
        radial-gradient(circle at 22% 20%, rgba(255, 184, 0, 0.14), transparent 44%),
        linear-gradient(180deg, rgba(16, 20, 28, 0.97), rgba(7, 10, 16, 0.99));
    }
    .scene-frame.scene-armed {
      border-color: rgba(0, 229, 244, 0.72);
      box-shadow: 0 0 28px rgba(0, 229, 244, 0.16);
    }
    .scene-frame.scene-responding {
      border-color: var(--green);
      box-shadow: 0 0 36px rgba(0, 232, 148, 0.26);
      animation: sceneRespond 0.65s ease;
    }
    .scene-frame.stage-enter,
    .prompt-banner.stage-enter {
      animation: stageEnter 0.34s cubic-bezier(0.22, 1, 0.36, 1);
    }
    .scene-tag {
      position: relative;
      z-index: 3;
      width: max-content;
    }
    .fx-orb {
      position: absolute;
      border-radius: 50%;
      filter: blur(22px);
      pointer-events: none;
      opacity: 0.38;
      animation: orbDrift 7s ease-in-out infinite alternate;
    }
    .fx-orb.o1 {
      width: 140px;
      height: 140px;
      top: -30px;
      right: 12%;
      background: rgba(0, 229, 244, 0.3);
    }
    .fx-orb.o2 {
      width: 110px;
      height: 110px;
      bottom: 40px;
      left: 8%;
      background: rgba(0, 232, 148, 0.22);
      animation-delay: -3.2s;
    }
    .stage {
      position: relative;
      z-index: 2;
      height: 168px;
      border-radius: 14px;
      border: 1px solid rgba(184, 211, 214, 0.2);
      background: linear-gradient(180deg, rgba(7, 12, 20, 0.92), rgba(14, 21, 32, 0.95));
      overflow: hidden;
    }

    /* Escenario 1: Hospital / Urgencia clínica */
    .hospital-crisis .rain {
      position: absolute;
      inset: 0;
      background-image: repeating-linear-gradient(
        105deg,
        transparent 0 18px,
        rgba(0, 229, 244, 0.14) 18px 20px
      );
      animation: rainFall 1.1s linear infinite;
      opacity: 0.45;
    }
    .hospital-crisis .moon {
      position: absolute;
      top: 16px;
      right: 26px;
      width: 30px;
      height: 30px;
      border-radius: 50%;
      background: rgba(168, 248, 255, 0.85);
      box-shadow: 0 0 20px rgba(0, 229, 244, 0.55);
      animation: moonFloat 4s ease-in-out infinite;
    }
    .hospital-crisis .hospital {
      position: absolute;
      left: 28px;
      bottom: 24px;
      width: 116px;
      height: 92px;
      border: 2px solid rgba(184, 211, 214, 0.45);
      background: #121c2a;
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 6px;
      padding: 24px 10px 10px;
    }
    .hospital-crisis .hospital b {
      position: absolute;
      top: 4px;
      left: 8px;
      font: 700 10px var(--mono);
      color: var(--cyan);
      letter-spacing: 1.5px;
    }
    .hospital-crisis .hospital i {
      display: block;
      background: rgba(0, 229, 244, 0.26);
      border-radius: 2px;
      animation: blinkWin 2.4s ease-in-out infinite;
    }
    .hospital-crisis .hospital i:nth-of-type(2) { animation-delay: 0.5s; }
    .hospital-crisis .hospital i:nth-of-type(3) { animation-delay: 1.1s; }
    .hospital-crisis .hospital em {
      position: absolute;
      top: -9px;
      right: 10px;
      width: 14px;
      height: 14px;
      border-radius: 50%;
      background: var(--red);
      box-shadow: 0 0 14px var(--red);
      animation: sirenGlow 0.9s ease-in-out infinite alternate;
    }
    .hospital-crisis .ambulance {
      position: absolute;
      right: 36px;
      bottom: 26px;
      width: 82px;
      height: 36px;
      border-radius: 8px 14px 4px 4px;
      background: #d9edf2;
      border: 2px solid var(--cyan);
      animation: ambulanceDrive 3.8s ease-in-out infinite;
    }
    .hospital-crisis .ambulance span {
      position: absolute;
      top: -6px;
      left: 22px;
      width: 14px;
      height: 6px;
      background: var(--cyan);
      box-shadow: 0 0 10px var(--cyan);
      animation: sirenGlow 0.6s linear infinite alternate;
    }
    .hospital-crisis .ambulance b {
      position: absolute;
      top: 7px;
      right: 8px;
      width: 22px;
      height: 12px;
      border-radius: 3px;
      background: #0d2230;
    }
    .hospital-crisis .ambulance i {
      position: absolute;
      bottom: -8px;
      width: 14px;
      height: 14px;
      border-radius: 50%;
      background: #0b0e14;
      border: 2px solid var(--cyan);
    }
    .hospital-crisis .ambulance i:first-of-type { left: 10px; }
    .hospital-crisis .ambulance i:last-of-type { right: 10px; }
    .hospital-crisis .family {
      position: absolute;
      left: 46%;
      bottom: 26px;
      display: flex;
      gap: 7px;
      transform: translateX(-50%);
    }
    .hospital-crisis .family span {
      width: 12px;
      height: 32px;
      border-radius: 8px 8px 3px 3px;
      background: linear-gradient(180deg, var(--amber), rgba(255, 184, 0, 0.35));
      animation: moonFloat 2.6s ease-in-out infinite;
    }
    .hospital-crisis .family span:nth-child(2) { height: 38px; animation-delay: 0.4s; }
    .hospital-crisis .family span:nth-child(3) { height: 26px; animation-delay: 0.8s; }
    .hospital-crisis .pulse-line {
      position: absolute;
      left: 0;
      right: 0;
      bottom: 14px;
      height: 2px;
      background: linear-gradient(90deg, transparent, var(--cyan), var(--green), transparent);
      animation: pulseBeat 2.2s ease-in-out infinite;
    }

    /* Escenario 2: Sala EPICEE / Diálogo clínico */
    .epicee-room .room-light {
      position: absolute;
      top: 12px;
      left: 50%;
      width: 170px;
      height: 54px;
      transform: translateX(-50%);
      border-radius: 50%;
      background: radial-gradient(circle, rgba(0, 229, 244, 0.32), transparent 72%);
      animation: roomGlow 3.2s ease-in-out infinite;
    }
    .epicee-room .clinician {
      position: absolute;
      left: 48px;
      bottom: 28px;
      display: grid;
      justify-items: center;
      gap: 4px;
    }
    .epicee-room .clinician i {
      width: 22px;
      height: 22px;
      border-radius: 50%;
      background: var(--cyan);
      box-shadow: 0 0 14px rgba(0, 229, 244, 0.5);
    }
    .epicee-room .clinician b {
      width: 34px;
      height: 44px;
      border-radius: 12px 12px 4px 4px;
      background: linear-gradient(180deg, #1b3848, #0f1d28);
      border: 1px solid rgba(0, 229, 244, 0.55);
    }
    .epicee-room .family-group {
      position: absolute;
      right: 48px;
      bottom: 28px;
      display: flex;
      align-items: flex-end;
      gap: 8px;
    }
    .epicee-room .family-group span {
      width: 18px;
      height: 48px;
      border-radius: 10px 10px 4px 4px;
      background: linear-gradient(180deg, var(--green), rgba(0, 232, 148, 0.28));
      animation: moonFloat 3.4s ease-in-out infinite;
    }
    .epicee-room .family-group span:nth-child(2) { height: 56px; animation-delay: 0.45s; }
    .epicee-room .family-group span:nth-child(3) { height: 38px; animation-delay: 0.9s; }
    .epicee-room .message-card {
      position: absolute;
      left: 50%;
      top: 32px;
      transform: translateX(-50%);
      padding: 10px 16px;
      border-radius: 12px;
      border: 1px solid rgba(0, 229, 244, 0.5);
      background: rgba(11, 18, 28, 0.94);
      text-align: center;
      animation: cardFloat 3s ease-in-out infinite;
    }
    .epicee-room .message-card b {
      display: block;
      font: 700 11px var(--mono);
      letter-spacing: 1.5px;
      color: var(--cyan);
    }
    .epicee-room .message-card small {
      color: var(--text);
      font-size: 12px;
    }
    .epicee-room .calm-wave {
      position: absolute;
      left: 50%;
      bottom: 24px;
      width: 160px;
      height: 22px;
      transform: translateX(-50%);
      border-radius: 50%;
      border: 1px solid rgba(0, 232, 148, 0.45);
      animation: waveExpand 2.8s ease-out infinite;
    }
    .epicee-room .calm-wave.w2 { animation-delay: 1.4s; }

    /* Escenario 3: Protección, riesgo y criterio ético */
    .protection-risk .safe-door {
      position: absolute;
      left: 34px;
      bottom: 22px;
      width: 58px;
      height: 98px;
      border-radius: 10px 10px 2px 2px;
      border: 2px solid var(--green);
      background: linear-gradient(180deg, rgba(0, 232, 148, 0.24), rgba(0, 232, 148, 0.05));
      box-shadow: 0 0 22px rgba(0, 232, 148, 0.18);
    }
    .protection-risk .person.protected {
      position: absolute;
      left: 112px;
      bottom: 24px;
      width: 24px;
      height: 54px;
      border-radius: 12px 12px 4px 4px;
      background: linear-gradient(180deg, var(--cyan), #173a48);
      animation: moonFloat 3s ease-in-out infinite;
    }
    .protection-risk .risk-meter {
      position: absolute;
      top: 24px;
      right: 30px;
      width: 136px;
      height: 14px;
      border-radius: 999px;
      border: 1px solid rgba(255, 184, 0, 0.55);
      background: #0a0f16;
      overflow: hidden;
    }
    .protection-risk .risk-meter span {
      display: block;
      height: 100%;
      width: 66%;
      background: linear-gradient(90deg, var(--amber), var(--red));
      animation: meterPulse 2.4s ease-in-out infinite alternate;
    }
    .protection-risk .shield {
      position: absolute;
      left: 50%;
      top: 56px;
      transform: translateX(-50%);
      padding: 10px 18px;
      border-radius: 999px;
      border: 1px solid var(--cyan);
      background: rgba(0, 229, 244, 0.14);
      font: 700 12px var(--mono);
      letter-spacing: 1.4px;
      color: var(--cyan-soft);
      animation: shieldPulse 2.6s ease-in-out infinite;
    }
    .protection-risk .path {
      position: absolute;
      left: 24px;
      right: 24px;
      bottom: 20px;
      height: 3px;
      background: linear-gradient(90deg, var(--green), var(--cyan), var(--amber));
      animation: pathTrace 2.8s ease-in-out infinite;
    }

    /* Escenario 4: Red de cuidado y articulación */
    .care-network .node {
      position: absolute;
      padding: 6px 12px;
      border-radius: 999px;
      border: 1px solid rgba(0, 229, 244, 0.5);
      background: rgba(9, 16, 26, 0.92);
      font: 700 11px var(--mono);
      text-transform: uppercase;
      color: var(--cyan-soft);
      box-shadow: 0 0 16px rgba(0, 229, 244, 0.14);
      animation: nodeOrbit 3.6s ease-in-out infinite;
    }
    .care-network .node.victim { left: 50%; top: 50%; transform: translate(-50%, -50%); border-color: var(--green); color: var(--green); animation: none; }
    .care-network .node.rights { left: 26px; top: 22px; }
    .care-network .node.health { right: 26px; top: 22px; animation-delay: 0.6s; }
    .care-network .node.mental { left: 28px; bottom: 20px; animation-delay: 1.2s; }
    .care-network .node.risk { right: 28px; bottom: 20px; border-color: var(--amber); color: var(--amber); animation-delay: 1.8s; }
    .care-network .net {
      position: absolute;
      left: 16%;
      right: 16%;
      height: 1px;
      background: linear-gradient(90deg, transparent, rgba(0, 229, 244, 0.48), transparent);
      pointer-events: none;
    }
    .care-network .net.l1 { top: 44px; transform: rotate(10deg); }
    .care-network .net.l2 { bottom: 42px; transform: rotate(-10deg); }
    .care-network .route-dot {
      position: absolute;
      top: 50%;
      left: 20%;
      width: 10px;
      height: 10px;
      margin-top: -5px;
      border-radius: 50%;
      background: var(--green);
      box-shadow: 0 0 14px var(--green);
      animation: dotTravel 3s ease-in-out infinite;
    }

    /* Coach Neuro */
    .coach {
      display: grid;
      grid-template-columns: auto 1fr auto;
      align-items: center;
      gap: 14px;
      padding: 14px 18px;
      transition: border-color 0.25s ease, box-shadow 0.25s ease;
    }
    .coach.coach-pulse {
      border-color: rgba(0, 232, 148, 0.55);
      box-shadow: 0 0 22px rgba(0, 232, 148, 0.14);
      animation: coachPulse 0.45s ease;
    }
    .coach-orb {
      width: 44px;
      height: 44px;
      border-radius: 14px;
      display: grid;
      place-items: center;
      font-size: 22px;
      border: 1px solid rgba(0, 229, 244, 0.42);
      background: rgba(0, 229, 244, 0.1);
      box-shadow: 0 0 16px rgba(0, 229, 244, 0.16);
      animation: moonFloat 3.2s ease-in-out infinite;
    }
    .grow { min-width: 0; }
    .coach-msg {
      margin: 4px 0 0;
      font-size: 14px;
      line-height: 1.45;
      color: var(--text);
    }

    .scene-note {
      position: relative;
      z-index: 2;
      padding: 14px 16px;
      border: 1px solid rgba(0, 229, 244, 0.25);
      background: rgba(9, 14, 22, 0.86);
      backdrop-filter: blur(8px);
    }
    .scene-note p {
      margin: 6px 0 0;
      font-size: 15px;
      line-height: 1.6;
      color: var(--text);
    }
    .ctx-lbl {
      font-family: var(--mono);
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 1.2px;
      color: var(--cyan);
      display: block;
    }

    .prompt-banner {
      padding: 16px 20px;
      border-left: 4px solid var(--amber);
    }
    .q-enunciado {
      margin: 6px 0 0;
      font-family: var(--display);
      font-size: clamp(22px, 3vw, 28px);
      line-height: 1.12;
      text-transform: uppercase;
      color: var(--text);
    }

    /* ==================== MAZO DE CARTAS INTERACTIVO (.card-rail) ==================== */
    .card-rail {
      display: flex;
      gap: 20px;
      overflow-x: auto;
      overflow-y: visible;
      padding: 18px 10px 24px;
      scroll-snap-type: x mandatory;
      scrollbar-color: var(--cyan) transparent;
    }
    .card-rail.has-selection .action-card:not(.selected) {
      opacity: 0.62;
      filter: saturate(0.7);
    }
    .card-rail.locked .action-card:not(.launched) {
      opacity: 0.35;
      transform: scale(0.95);
      pointer-events: none;
    }
    .action-card {
      position: relative;
      flex: 0 0 265px;
      min-height: 310px;
      display: flex;
      flex-direction: column;
      gap: 10px;
      padding: 20px 18px;
      border: 1px solid rgba(184, 211, 214, 0.22);
      border-radius: 20px;
      color: var(--text);
      background: linear-gradient(155deg, rgba(23, 27, 35, 0.98), rgba(8, 12, 18, 0.98));
      box-shadow: 0 20px 40px rgba(0, 0, 0, 0.38);
      text-align: left;
      cursor: pointer;
      scroll-snap-align: center;
      transform: rotate(var(--tilt, 0deg));
      transition: transform 0.24s cubic-bezier(0.22, 1, 0.36, 1), border-color 0.22s ease, box-shadow 0.22s ease, opacity 0.22s ease;
    }
    .action-card:nth-child(2) { margin-top: 8px; }
    .action-card:nth-child(3) { margin-top: 4px; }
    .action-card:hover,
    .action-card.selected {
      opacity: 1 !important;
      filter: none !important;
      border-color: var(--cyan-soft);
      box-shadow:
        0 0 0 2px rgba(168, 248, 255, 0.28),
        0 26px 46px rgba(0, 0, 0, 0.5);
      transform: translateY(-10px) rotate(0deg);
    }
    .action-card.selected {
      border-color: var(--green);
      box-shadow:
        0 0 0 2px rgba(0, 232, 148, 0.35),
        0 26px 46px rgba(0, 232, 148, 0.14);
    }
    .action-card.launched {
      opacity: 1 !important;
      filter: none !important;
      border-color: var(--green);
      box-shadow:
        0 0 0 3px rgba(0, 232, 148, 0.5),
        0 28px 60px rgba(0, 232, 148, 0.28);
      animation: cardLaunch 0.68s cubic-bezier(0.22, 1, 0.36, 1) forwards;
    }
    .sr-only-radio {
      position: absolute;
      opacity: 0;
      width: 1px;
      height: 1px;
      pointer-events: none;
    }
    .card-top-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .mode-pill {
      width: max-content;
      padding: 5px 10px;
      border-radius: 999px;
      background: var(--cyan-soft);
      color: #062026;
      font: 700 11px var(--mono);
      letter-spacing: 1.4px;
      text-transform: uppercase;
    }
    .mode-pill.good {
      background: var(--green);
      color: #021c11;
    }
    .card-symbol {
      font-size: 26px;
      line-height: 1;
      color: var(--cyan);
    }
    .card-kicker {
      color: var(--cyan-soft);
      font: 11px var(--mono);
      letter-spacing: 1.8px;
      text-transform: uppercase;
    }
    .card-decision-text {
      color: #fff;
      font: 600 15px/1.45 var(--body);
    }
    .stats {
      display: grid;
      gap: 7px;
      margin-top: auto;
      padding-top: 10px;
      border-top: 1px dashed rgba(184, 211, 214, 0.2);
    }
    .stats label {
      display: grid;
      grid-template-columns: 64px 1fr;
      align-items: center;
      gap: 8px;
      font: 10px var(--mono);
      color: var(--dim);
    }
    .stats i {
      display: block;
      height: 6px;
      background: #232a34;
      border-radius: 99px;
      overflow: hidden;
    }
    .stats b {
      display: block;
      height: 100%;
      background: var(--cyan);
    }
    .touch-label {
      font: 11px var(--mono);
      color: var(--dim);
      text-align: center;
      padding-top: 4px;
    }
    .action-card.selected .touch-label {
      color: var(--green);
      font-weight: 700;
    }

    /* ==================== REFLEXIÓN & LAUNCH PAD ==================== */
    .refl-panel {
      padding: 16px 18px !important;
      margin-bottom: 0 !important;
    }
    .refl-textarea {
      width: 100%;
      box-sizing: border-box;
      margin-top: 8px;
      background: rgba(5, 8, 13, 0.78);
      color: var(--text);
      border: 1px solid rgba(184, 211, 214, 0.22);
      border-radius: 0;
      padding: 12px;
      font-family: var(--body);
    }
    .refl-textarea:focus {
      outline: none;
      border-color: var(--cyan);
    }
    .launch-pad {
      display: grid;
      grid-template-columns: 1fr auto;
      align-items: center;
      gap: 16px;
      padding: 16px 18px;
      border-style: dashed;
      border-color: var(--line-strong);
      border-radius: 18px;
    }
    .selected-brief {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .launch-ico {
      font-size: 28px;
      line-height: 1;
      transition: transform 0.3s ease;
    }
    .launch-ico.rocket-launch {
      animation: rocketTakeoff 0.65s cubic-bezier(0.22, 1, 0.36, 1);
    }
    .feedback {
      padding: 16px 18px !important;
      border: 1px solid rgba(0, 232, 148, 0.45);
      background: linear-gradient(135deg, rgba(0, 232, 148, 0.1), rgba(10, 16, 24, 0.96));
      animation: feedbackPop 0.35s cubic-bezier(0.22, 1, 0.36, 1);
    }
    .feedback p {
      margin: 8px 0 12px;
      color: var(--text);
      font-size: 14px;
      line-height: 1.5;
    }
    .eyebrow.green { color: var(--green); }
    .meter.stress {
      height: 8px;
      border-radius: 999px;
      background: rgba(184, 211, 214, 0.16);
      overflow: hidden;
    }
    .meter.stress > span {
      display: block;
      height: 100%;
      background: linear-gradient(90deg, var(--cyan), var(--green));
      box-shadow: 0 0 12px rgba(0, 232, 148, 0.45);
      transition: width 0.4s ease;
    }

    @keyframes stageEnter {
      from { opacity: 0; transform: translateY(10px) scale(0.985); }
      to { opacity: 1; transform: translateY(0) scale(1); }
    }
    @keyframes sceneRespond {
      0% { transform: scale(1); }
      45% { transform: scale(1.012); }
      100% { transform: scale(1); }
    }
    @keyframes cardLaunch {
      0% { transform: translateY(-10px) scale(1); }
      45% { transform: translateY(-24px) scale(1.04) rotate(0deg); }
      100% { transform: translateY(-14px) scale(1.01) rotate(0deg); }
    }
    @keyframes rocketTakeoff {
      0% { transform: translateY(0) scale(1); }
      55% { transform: translate(6px, -14px) scale(1.25) rotate(-10deg); }
      100% { transform: translateY(0) scale(1); }
    }
    @keyframes feedbackPop {
      from { opacity: 0; transform: translateY(12px) scale(0.98); }
      to { opacity: 1; transform: translateY(0) scale(1); }
    }
    @keyframes coachPulse {
      0% { transform: scale(1); }
      50% { transform: scale(1.01); }
      100% { transform: scale(1); }
    }
    @keyframes orbDrift {
      from { transform: translate(0, 0) scale(1); }
      to { transform: translate(14px, -10px) scale(1.12); }
    }
    @keyframes rainFall {
      from { background-position: 0 0; }
      to { background-position: -32px 64px; }
    }
    @keyframes moonFloat {
      0%, 100% { transform: translateY(0); }
      50% { transform: translateY(-5px); }
    }
    @keyframes blinkWin {
      0%, 100% { opacity: 0.35; }
      50% { opacity: 0.92; }
    }
    @keyframes sirenGlow {
      from { opacity: 0.45; transform: scale(0.92); }
      to { opacity: 1; transform: scale(1.12); }
    }
    @keyframes ambulanceDrive {
      0%, 100% { transform: translateX(0); }
      50% { transform: translateX(-18px); }
    }
    @keyframes pulseBeat {
      0%, 100% { opacity: 0.35; }
      50% { opacity: 0.95; }
    }
    @keyframes roomGlow {
      0%, 100% { opacity: 0.55; }
      50% { opacity: 0.95; }
    }
    @keyframes waveExpand {
      0% { opacity: 0.7; transform: translateX(-50%) scale(0.78); }
      100% { opacity: 0; transform: translateX(-50%) scale(1.35); }
    }
    @keyframes cardFloat {
      0%, 100% { transform: translate(-50%, 0); }
      50% { transform: translate(-50%, -6px); }
    }
    @keyframes meterPulse {
      from { width: 48%; }
      to { width: 78%; }
    }
    @keyframes shieldPulse {
      0%, 100% { box-shadow: 0 0 12px rgba(0, 229, 244, 0.22); }
      50% { box-shadow: 0 0 24px rgba(0, 232, 148, 0.44); }
    }
    @keyframes pathTrace {
      0%, 100% { opacity: 0.55; }
      50% { opacity: 1; }
    }
    @keyframes nodeOrbit {
      0%, 100% { transform: translateY(0); }
      50% { transform: translateY(-5px); }
    }
    @keyframes dotTravel {
      0%, 100% { left: 18%; }
      50% { left: 78%; }
    }
    .selected-brief small,
    .selected-brief b {
      display: block;
    }
    .selected-brief small {
      color: var(--cyan);
      font: 11px var(--mono);
      text-transform: uppercase;
      letter-spacing: 1px;
    }
    .selected-brief b {
      color: #fff;
      font: 700 20px var(--display);
      text-transform: uppercase;
    }
    .play-actions {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }

    /* ==================== PANTALLA RESULTADOS (.score-ring + .chart-card + .events) ==================== */
    .res-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
    }
    .result-head {
      padding: 22px !important;
      margin-bottom: 0 !important;
    }
    .head-top {
      margin-bottom: 16px;
    }
    .head-top h1 {
      margin: 4px 0 0;
      font-family: var(--display);
      font-size: clamp(28px, 4.5vw, 38px);
      text-transform: uppercase;
      color: var(--text);
    }
    .ref {
      padding: 8px 12px;
      border: 1px solid rgba(184, 211, 214, 0.3);
      background: #232a34;
      color: var(--text) !important;
    }
    .score-layout {
      display: grid;
      grid-template-columns: 150px 1fr;
      gap: 20px;
      align-items: center;
    }
    .score-ring {
      --score: 76%;
      width: 142px;
      height: 142px;
      display: grid;
      place-items: center;
      position: relative;
      border-radius: 50%;
      background: conic-gradient(var(--green) var(--score), rgba(184, 211, 214, 0.14) 0);
      box-shadow: 0 0 28px rgba(0, 232, 148, 0.16);
    }
    .score-ring::after {
      content: '';
      position: absolute;
      inset: 14px;
      border-radius: 50%;
      background: #0d1219;
      border: 1px solid rgba(184, 211, 214, 0.14);
    }
    .score-value {
      position: relative;
      z-index: 1;
      display: grid;
      place-items: center;
      line-height: 1;
      text-align: center;
      font-family: var(--mono);
    }
    .score-value span {
      color: var(--green);
      font-size: 30px;
      font-weight: 700;
    }
    .score-value small {
      margin-top: 4px;
      color: var(--muted);
      font-size: 11px;
    }
    .score-copy {
      display: grid;
      gap: 10px;
    }
    .stats-row {
      display: flex;
      gap: 18px;
      flex-wrap: wrap;
      color: var(--muted);
    }
    .summary {
      margin: 0;
      padding-top: 10px;
      border-top: 1px solid rgba(184, 211, 214, 0.14);
      color: var(--text);
      font-size: 14px;
      line-height: 1.55;
    }
    .fb-card {
      border-left: 4px solid var(--amber) !important;
      margin-bottom: 0 !important;
    }
    .chart-card {
      display: grid;
      gap: 16px;
      background: linear-gradient(145deg, rgba(0, 229, 244, 0.06), rgba(0, 232, 148, 0.04)), rgba(16, 20, 27, 0.94);
    }
    .section-heading {
      margin: 4px 0 0;
      font-family: var(--display);
      font-size: 26px;
      text-transform: uppercase;
    }
    .chart-bars {
      display: grid;
      gap: 12px;
    }
    .chart-row {
      display: grid;
      grid-template-columns: 1.1fr 1.6fr 56px;
      gap: 10px;
      align-items: center;
    }
    .chart-row span {
      font: 12px var(--mono);
      text-transform: uppercase;
      color: #cbd6d8;
    }
    .chart-row i {
      height: 14px;
      border: 1px solid rgba(184, 211, 214, 0.2);
      background: #05080d;
      overflow: hidden;
    }
    .chart-row b {
      display: block;
      height: 100%;
      background: var(--cyan);
      box-shadow: 0 0 14px var(--cyan);
    }
    .chart-row strong {
      color: var(--cyan);
      font: 15px var(--mono);
      text-align: right;
    }
    .criterios-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
      gap: 12px;
    }
    .crit-card {
      display: grid;
      gap: 10px;
      padding: 16px;
      background: #0b1017;
      border: 1px solid var(--line);
      border-left: 4px solid var(--cyan);
    }
    .crit-top {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 8px;
    }
    .crit-score {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 22px;
      color: var(--cyan);
    }
    .crit-score small {
      font-size: 12px;
      color: var(--muted);
    }
    .crit-desc {
      margin: 0;
      font-size: 12px;
    }
    .events-head {
      padding: 18px 20px;
      border-bottom: 1px solid var(--line);
    }
    .events-head h3 {
      margin: 4px 0 0;
      font-family: var(--display);
      font-size: 24px;
      text-transform: uppercase;
    }
    .q-review-list {
      display: grid;
    }
    .event-row {
      padding: 16px 20px;
      border-top: 1px solid rgba(184, 211, 214, 0.12);
      display: grid;
      gap: 8px;
    }
    .event-row.q-ok {
      border-left: 4px solid var(--green);
    }
    .event-row.q-bad {
      border-left: 4px solid var(--red);
    }
    .event-top {
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }
    .event-badge {
      display: grid;
      place-items: center;
      width: 26px;
      height: 26px;
      border-radius: 50%;
      border: 1px solid rgba(0, 232, 148, 0.55);
      color: var(--green);
      font: 700 14px var(--mono);
    }
    .event-badge.amber {
      border-color: rgba(255, 184, 0, 0.65);
      color: var(--amber);
    }
    .q-title-txt {
      flex: 1;
      color: var(--text);
      font-size: 15px;
    }
    .event-body {
      display: grid;
      gap: 6px;
      padding-left: 36px;
      font-size: 13px;
      color: var(--muted);
    }
    .q-corr {
      background: rgba(0, 232, 148, 0.08);
      border: 1px solid rgba(0, 232, 148, 0.3);
      padding: 8px 12px;
      color: #a7f3d0;
    }
    .q-refl {
      background: #0b1017;
      border: 1px solid rgba(184, 211, 214, 0.16);
      padding: 8px 12px;
      color: var(--text);
    }

    @media (max-width: 780px) {
      .launch-pad, .score-layout, .chart-row {
        grid-template-columns: 1fr;
      }
      .score-ring {
        margin: auto;
      }
      .chart-row strong {
        text-align: left;
      }
      .play-actions {
        justify-content: flex-start;
      }
      .event-body {
        padding-left: 0;
      }
    }
  `],
})
export class SimuladorComponent implements OnInit, OnDestroy {
  private readonly route = inject(ActivatedRoute);
  private readonly participation = inject(ParticipationService);
  private readonly snack = inject(MatSnackBar);
  private readonly uiDialog = inject(UiDialogService);

  readonly Math = Math;
  idIntento = 0;

  readonly cargando = signal(true);
  readonly guardando = signal(false);
  readonly workspace = signal<WorkspaceIntento | null>(null);
  readonly resultado = signal<ResultadoIntentoDetalle | null>(null);
  readonly indiceActual = signal(0);
  readonly segundosRestantes = signal(0);
  readonly opcionLanzada = signal<string | null>(null);
  readonly respuestaAnimada = signal<{ texto: string; paso: number } | null>(null);
  readonly transicionandoEscena = signal(false);

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
  private transitionHandle: ReturnType<typeof setTimeout> | null = null;
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
    if (this.transitionHandle) clearTimeout(this.transitionHandle);
  }

  cardTilt(index: number): string {
    return `${[-2.4, 1.4, -1.5, 2.1][index % 4]}deg`;
  }

  coachMensaje(): string {
    const actual = this.pasoActual();
    const ws = this.workspace();
    if (!actual || !ws) return 'Analiza el escenario clínico antes de lanzar tu carta de decisión.';
    if (this.opcionLanzada()) {
      return '¡Carta lanzada! Registrando tu criterio ético y preparando el siguiente movimiento...';
    }
    if (this.respuestaAnimada()) {
      return (ws.respondidas ?? 0) >= this.pasosPlanos().length
        ? '¡Completaste todas las decisiones! Ya puedes pulsar "Entregar Simulación" para recibir tu calificación y retroalimentación.'
        : 'Decisión guardada correctamente. Puedes revisarla o continuar con el escenario.';
    }
    if (this.opcionElegida) {
      return `Carta preparada para el Escenario ${actual.escenario.orden}. Puedes añadir tu sustento en la bitácora y pulsar "Lanzar".`;
    }
    if (this.estaRespondida(actual.pregunta.id)) {
      return 'Este dilema ya tiene una respuesta guardada. Puedes cambiar tu carta antes de entregar definitivamente.';
    }
    return `Lee el contexto del Escenario ${actual.escenario.orden} y toca la carta de intervención que mejor responda al dilema.`;
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
    if (this.guardando() || this.opcionLanzada()) return;
    const pasos = this.pasosPlanos();
    if (idx < 0 || idx >= pasos.length) return;
    this.opcionLanzada.set(null);
    this.respuestaAnimada.set(null);
    this.transicionandoEscena.set(true);
    if (this.transitionHandle) clearTimeout(this.transitionHandle);
    this.transitionHandle = setTimeout(() => this.transicionandoEscena.set(false), 320);

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
    if (!actual || !this.opcionElegida || this.guardando()) return;
    const elegidaId = this.opcionElegida;
    const opObj = actual.pregunta.opciones.find((o) => o.id === elegidaId);

    this.guardando.set(true);
    this.opcionLanzada.set(elegidaId);
    try {
      const prevIdx = this.indiceActual();
      const wsActualizado = await firstValueFrom(
        this.participation.guardarBorrador(
          this.idIntento,
          actual.pregunta.id,
          elegidaId,
          this.reflexionInput.trim() || null,
        ),
      );
      if (wsActualizado.cerrado && wsActualizado.resultado) {
        if (this.timerHandle) clearInterval(this.timerHandle);
        this.opcionLanzada.set(null);
        this.resultado.set(wsActualizado.resultado);
        this.workspace.set(null);
        return;
      }
      this.workspace.set(wsActualizado);
      this.respuestaAnimada.set({
        texto: opObj?.texto ?? 'Decisión registrada en bitácora.',
        paso: actual.escenario.orden,
      });

      await new Promise((resolve) => setTimeout(resolve, 700));
      const nuevos = this.pasosPlanos();
      this.opcionLanzada.set(null);
      this.guardando.set(false);

      if (prevIdx + 1 < nuevos.length) {
        this.irAPregunta(prevIdx + 1);
        this.snack.open('Respuesta guardada (editable hasta entregar).', 'OK', { duration: 1800 });
      } else {
        this.snack.open('Última decisión guardada. Ya puedes pulsar "Entregar Simulación".', 'OK', { duration: 2800 });
      }
    } catch (e) {
      this.opcionLanzada.set(null);
      this.respuestaAnimada.set(null);
      this.snack.open(mensajeError(e), 'Cerrar', { duration: 4000 });
    } finally {
      this.guardando.set(false);
    }
  }

  async entregarSimulacion(): Promise<void> {
    const ws = this.workspace();
    if (!ws || this.guardando() || this.opcionLanzada()) return;

    this.guardando.set(true);
    try {
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
      if (wsFresco.cerrado && wsFresco.resultado) {
        if (this.timerHandle) clearInterval(this.timerHandle);
        this.resultado.set(wsFresco.resultado);
        this.workspace.set(null);
        return;
      }

      let permitirParcial = false;
      if (!wsFresco.listo_para_enviar) {
        const ok = await this.uiDialog.confirmar({
          eyebrow: 'Entrega Parcial // RF-12',
          titulo: 'Preguntas Pendientes',
          mensaje: `Faltan preguntas por responder (${wsFresco.respondidas}/${wsFresco.total_preguntas}). Las preguntas pendientes obtendrán 0 puntos. ¿Confirmas la entrega parcial definitiva?`,
          botonConfirmar: 'Confirmar Entrega Parcial',
          botonCancelar: 'Seguir Respondiendo',
          tono: 'amber',
        });
        if (!ok) return;
        permitirParcial = true;
      } else {
        const ok = await this.uiDialog.confirmar({
          eyebrow: 'Entrega Definitiva // RF-12',
          titulo: 'Finalizar Simulación',
          mensaje: '¿Confirmas la entrega definitiva? Una vez enviada no podrás modificar tus respuestas y se calculará tu resultado.',
          botonConfirmar: 'Sí, Entregar Ahora',
          botonCancelar: 'Revisar Respuestas',
          tono: 'green',
        });
        if (!ok) return;
      }

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
