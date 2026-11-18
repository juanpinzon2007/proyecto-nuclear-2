import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
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
import { SimuladorResultadoComponent } from './simulador-resultado.component';

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
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatProgressBarModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    SimuladorResultadoComponent,
  ],
  template: `
    <div class="sim-wrap content">
      @if (cargando()) {
        <div class="center-spin"><mat-spinner diameter="44"></mat-spinner></div>
      } @else if (resultado(); as res) {
        <app-simulador-resultado [res]="res" />
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
          <!-- Escenario Cinemático Dinámico Estilo GTA 6 / Leonida Vice -->
          <section
            class="panel scene-frame"
            [ngClass]="'theme-' + escenarioTema()"
            [class.scene-armed]="!!opcionElegida && !opcionLanzada()"
            [class.scene-responding]="!!opcionLanzada()"
            [class.stage-enter]="transicionandoEscena()"
          >
            <div class="scene-top-bar">
              <span class="tag scene-tag">
                ESCENARIO 0{{ actual.escenario.orden }} · DECISIÓN {{ indiceActual() + 1 }}/{{ pasosPlanos().length }}
              </span>
              <span class="hud-rec-pill mono">
                <i class="rec-dot"></i> CAM-0{{ actual.escenario.orden }} // {{ etiquetaTemaEscenario() }}
              </span>
            </div>

            <div class="fx-orb o1"></div>
            <div class="fx-orb o2"></div>
            <div class="vice-lens-flare"></div>

            <div class="stage" [ngClass]="escenarioTema()" aria-hidden="true">
              <div class="vice-sky"></div>
              <div class="vice-grid-floor"></div>
              <div class="scanline-veil"></div>

              <!-- Silueta panorámica de palmeras y rascacielos Leonida / Vice -->
              <svg class="vice-skyline" viewBox="0 0 800 180" preserveAspectRatio="none">
                <defs>
                  <linearGradient id="sunGlow" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="#ff4fd8" stop-opacity="0.72" />
                    <stop offset="55%" stop-color="#ff9e3d" stop-opacity="0.55" />
                    <stop offset="100%" stop-color="#0b1220" stop-opacity="0" />
                  </linearGradient>
                </defs>
                <circle cx="620" cy="86" r="46" fill="url(#sunGlow)" />
                <path d="M0 155 L45 155 L45 110 L75 110 L75 155 L110 155 L110 82 L152 82 L152 155 L210 155 L210 120 L248 120 L248 155 L520 155 L520 96 L562 96 L562 155 L590 155 L590 70 L642 70 L642 155 L695 155 L695 108 L745 108 L745 155 L800 155 L800 180 L0 180 Z"
                      fill="#070b15" fill-opacity="0.88" />
                <g class="palm-sway" stroke="#0d1526" stroke-width="4" fill="none">
                  <path d="M90 165 Q98 118 82 88" />
                  <path d="M82 88 Q56 76 42 92 M82 88 Q62 66 84 56 M82 88 Q106 70 118 88 M82 88 Q102 88 112 104" stroke-width="3" />
                </g>
              </svg>

              @switch (escenarioTema()) {
                @case ('tribunal_comite') {
                  <div class="diorama-tribunal">
                    <div class="board-window"></div>
                    <div class="vote-scoreboard">
                      <small>COMISIÓN EN VIVO</small>
                      <b>{{ opcionLanzada() ? 'ACTA BLOQUEADA' : (opcionElegida ? 'VOTO LISTO' : 'VOTACIÓN 4 : 1') }}</b>
                      <div class="vote-bars">
                        <span class="vb warn"></span><span class="vb warn"></span>
                        <span class="vb warn"></span><span class="vb warn"></span>
                        <span class="vb you"></span>
                      </div>
                    </div>
                    <div class="council-table">
                      <div class="council-members">
                        <div class="npc raised"><i></i><b></b><em>✋</em></div>
                        <div class="npc raised d2"><i></i><b></b><em>✋</em></div>
                        <div class="npc player-seat" [class.stood]="!!opcionLanzada()"><i></i><b></b></div>
                        <div class="npc raised d3"><i></i><b></b><em>✋</em></div>
                        <div class="npc"><i></i><b></b></div>
                      </div>
                    </div>
                    <div class="spotlight s1"></div>
                    <div class="spotlight s2"></div>
                  </div>
                }
                @case ('laboratorio_autoridad') {
                  <div class="diorama-lab">
                    <div class="voltage-rack">
                      <div class="dial-face"><div class="dial-needle"></div></div>
                      <span class="volt-tag">150V // 300V</span>
                    </div>
                    <svg class="oscilloscope" viewBox="0 0 220 60">
                      <path class="wave-trace" d="M0 30 L28 30 L38 10 L48 52 L58 18 L70 30 L110 30 L122 8 L134 54 L146 22 L156 30 L220 30" />
                    </svg>
                    <div class="lab-glass"></div>
                    <div class="lab-subject"><i></i><b></b></div>
                    <div class="lab-authority"><i></i><b></b><em>👉</em></div>
                    <div class="emergency-beacon"></div>
                  </div>
                }
                @case ('hospital_urgencias') {
                  <div class="diorama-hospital">
                    <div class="rain"></div>
                    <div class="chopper-beam"></div>
                    <div class="hospital"><b>URGENCIAS 24H</b><i></i><i></i><i></i><i></i><em></em></div>
                    <div class="ambulance">
                      <span class="lightbar"></span><b></b><i></i><i></i>
                    </div>
                    <svg class="ecg-svg" viewBox="0 0 400 40" preserveAspectRatio="none">
                      <path class="ecg-path" d="M0 24 L80 24 L95 24 L105 6 L116 36 L126 14 L138 24 L240 24 L255 24 L265 4 L276 37 L288 12 L298 24 L400 24" />
                    </svg>
                  </div>
                }
                @case ('entrevista_clinica') {
                  <div class="diorama-epicee">
                    <div class="room-light"></div>
                    <div class="venetian-glow"></div>
                    <div class="clinician"><i></i><b></b></div>
                    <div class="family-group"><span></span><span></span><span></span></div>
                    <div class="message-card">
                      <b>SESIÓN EN CURSO</b>
                      <small>{{ opcionElegida ? 'Enfoque preparado' : 'Escucha activa' }}</small>
                    </div>
                    <div class="calm-wave w1"></div>
                    <div class="calm-wave w2"></div>
                  </div>
                }
                @case ('proteccion_riesgo') {
                  <div class="diorama-protection">
                    <div class="safe-door"></div>
                    <div class="hex-shield">🛡️ PROTOCOLO</div>
                    <div class="person protected"></div>
                    <div class="radar-scan"><i></i></div>
                    <div class="risk-meter"><span></span></div>
                    <div class="path"></div>
                  </div>
                }
                @default {
                  <div class="diorama-network">
                    <div class="node victim">NÚCLEO</div>
                    <div class="node rights">ÉTICA</div>
                    <div class="node health">PROTOCOLO</div>
                    <div class="node mental">CONTEXTO</div>
                    <div class="node risk">IMPACTO</div>
                    <div class="net l1"></div>
                    <div class="net l2"></div>
                    <div class="route-dot"></div>
                  </div>
                }
              }

              <!-- Overlay Cinemático GTA 6 al seleccionar o lanzar carta -->
              @if (opcionLanzada()) {
                <div class="gta-cutscene">
                  <div class="gta-stripes"></div>
                  <div class="gta-banner">
                    <span class="gta-tag">MISIÓN // DECISIÓN REGISTRADA</span>
                    <h4>{{ etiquetaImpactoCarta() }}</h4>
                    <small>ACTUALIZANDO TELEMETRÍA Y RUTA DEL CASO...</small>
                  </div>
                </div>
              }
            </div>

            <div class="scene-note">
              <div class="ctx-lbl">Contexto del Escenario 0{{ actual.escenario.orden }}</div>
              <p>{{ actual.escenario.contexto_situacional }}</p>
            </div>
          </section>

          <!-- Coach Neuro reactivo -->
          <section class="coach panel" [class.coach-pulse]="!!opcionElegida || !!respuestaAnimada()">
            <div class="coach-orb">🧠</div>
            <div class="grow">
              <span class="eyebrow">Asistente SPS · Guía Táctica</span>
              <p class="coach-msg">{{ coachMensaje() }}</p>
            </div>
            <span class="tag" [class.green]="!!opcionElegida || !!opcionLanzada()">
              {{ opcionLanzada() ? 'REGISTRADO ✓' : (opcionElegida ? 'CARTA ARMADA' : 'ELIGE UNA CARTA') }}
            </span>
          </section>

          <!-- Enunciado de Decisión -->
          <div class="prompt-banner panel" [class.stage-enter]="transicionandoEscena()">
            <p class="eyebrow amber">Dilema a resolver</p>
            <h2 class="q-enunciado">{{ actual.pregunta.enunciado }}</h2>
          </div>

          <!-- Mazo de Cartas Estilo Poker (♠ ♥ ♦ ♣) -->
          <div class="card-rail" [class.has-selection]="!!opcionElegida" [class.locked]="!!opcionLanzada()">
            @for (op of actual.pregunta.opciones; track op.id; let oi = $index) {
              @let palo = paloCarta(oi);
              <label
                class="poker-card"
                [class.suit-red]="palo.rojo"
                [class.suit-dark]="!palo.rojo"
                [class.selected]="opcionElegida === op.id"
                [class.launched]="opcionLanzada() === op.id"
                [style.--tilt]="cardTilt(oi)"
                [style.--deal-delay]="(oi * 75) + 'ms'"
              >
                <input
                  type="radio"
                  class="sr-only-radio"
                  [name]="'q_' + actual.pregunta.id"
                  [value]="op.id"
                  [(ngModel)]="opcionElegida"
                  [disabled]="!!opcionLanzada() || guardando()"
                />

                <!-- Índice superior izquierdo estilo Poker -->
                <div class="poker-corner top-left">
                  <span class="poker-rank">{{ palo.rango }}</span>
                  <span class="poker-suit">{{ palo.simbolo }}</span>
                  <span class="poker-stack mono">OPC0{{ oi + 1 }}</span>
                </div>

                <!-- Marco central ilustrado de carta estilo Poker -->
                <div class="poker-inner-frame">
                  <div class="poker-crest">
                    <svg class="crest-wreath" viewBox="0 0 80 80" aria-hidden="true">
                      <circle cx="40" cy="40" r="32" fill="none" stroke="currentColor" stroke-width="1.4" stroke-dasharray="4 3" opacity="0.45"/>
                      <polygon points="40,6 44,14 36,14" fill="currentColor" opacity="0.5"/>
                      <polygon points="40,74 44,66 36,66" fill="currentColor" opacity="0.5"/>
                    </svg>
                    <span class="crest-suit">{{ palo.simbolo }}</span>
                    <span class="crest-arquetipo">{{ palo.arquetipo }}</span>
                  </div>

                  <div class="poker-hairline"></div>
                  <strong class="poker-decision-text">{{ op.texto }}</strong>

                  <div class="poker-footer-seal">
                    @if (opcionLanzada() === op.id) {
                      <span class="seal launched-seal">⚡ JUGADA LANZADA</span>
                    } @else if (opcionElegida === op.id) {
                      <span class="seal armed-seal">★ CARTA ELEGIDA</span>
                    } @else {
                      <span class="seal idle-seal">TOCAR PARA JUGAR {{ palo.simbolo }}</span>
                    }
                  </div>
                </div>

                <!-- Índice inferior derecho invertido 180° -->
                <div class="poker-corner bottom-right" aria-hidden="true">
                  <span class="poker-rank">{{ palo.rango }}</span>
                  <span class="poker-suit">{{ palo.simbolo }}</span>
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

    /* ==================== SCENE FRAME GTA 6 / VICE LEONIDA ==================== */
    .scene-frame { position: relative; overflow: hidden; min-height: 350px; padding: 20px; display: grid; gap: 14px; border-top: 2px solid rgba(255,79,216,.55); background: radial-gradient(circle at 86% 14%, rgba(255,79,216,.22), transparent 44%), linear-gradient(180deg, rgba(16,12,30,.97), rgba(7,10,18,.99)); transition: border-color .28s ease, box-shadow .28s ease; }
    .scene-frame.scene-armed { border-color: #ff9e3d; box-shadow: 0 0 32px rgba(255,158,61,.28); }
    .scene-frame.scene-responding { border-color: #ff4fd8; box-shadow: 0 0 42px rgba(255,79,216,.4); animation: gtaImpactFlash .9s cubic-bezier(.22,1,.36,1); }
    .scene-frame.stage-enter, .prompt-banner.stage-enter { animation: stageEnter .4s cubic-bezier(.22,1,.36,1); }
    .scene-top-bar { position: relative; z-index: 3; display: flex; justify-content: space-between; align-items: center; gap: 10px; flex-wrap: wrap; }
    .scene-tag { width: max-content; }
    .hud-rec-pill { display: inline-flex; align-items: center; gap: 8px; padding: 5px 12px; border-radius: 999px; border: 1px solid rgba(255,79,216,.5); background: rgba(12,8,22,.85); color: #ffd1f5; font-size: 11px; letter-spacing: 1.2px; text-transform: uppercase; }
    .rec-dot { width: 8px; height: 8px; border-radius: 50%; background: #ff4f79; box-shadow: 0 0 10px #ff4f79; animation: sirenGlow .85s ease-in-out infinite alternate; }
    .fx-orb { position: absolute; border-radius: 50%; filter: blur(26px); pointer-events: none; opacity: .45; animation: orbDrift 7s ease-in-out infinite alternate; }
    .fx-orb.o1 { width: 170px; height: 170px; top: -40px; right: 10%; background: rgba(255,79,216,.34); }
    .fx-orb.o2 { width: 130px; height: 130px; bottom: 40px; left: 6%; background: rgba(0,229,244,.25); animation-delay: -3.2s; }
    .vice-lens-flare { position: absolute; top: 42px; left: -20%; width: 140%; height: 2px; background: linear-gradient(90deg, transparent, rgba(255,79,216,.55), rgba(0,240,255,.7), rgba(255,158,61,.45), transparent); filter: blur(1px); opacity: .45; pointer-events: none; animation: flareSweep 7s ease-in-out infinite alternate; }
    .stage { position: relative; z-index: 2; height: 214px; border-radius: 14px; border: 1px solid rgba(255,79,216,.34); background: #090c18; overflow: hidden; perspective: 900px; box-shadow: inset 0 0 42px rgba(0,0,0,.72); }
    .scene-frame.scene-armed .stage { transform: scale(1.018); transition: transform .35s cubic-bezier(.22,1,.36,1); }
    .vice-sky { position: absolute; inset: 0; background: linear-gradient(180deg, #160a2a 0%, #4d194d 45%, #c84b31 76%, #0c1220 100%); opacity: .92; animation: gtaCamFloat 10s ease-in-out infinite alternate; }
    .stage.hospital_urgencias .vice-sky { background: linear-gradient(180deg, #070d1c 0%, #162242 52%, #2b1636 82%, #070b14 100%); }
    .stage.entrevista_clinica .vice-sky { background: linear-gradient(180deg, #132234 0%, #24485a 48%, #c97a49 84%, #0b111c 100%); }
    .stage.laboratorio_autoridad .vice-sky { background: linear-gradient(180deg, #091819 0%, #0f2f35 55%, #1d122b 88%, #070a10 100%); }
    .vice-grid-floor { position: absolute; left: -20%; right: -20%; bottom: 0; height: 54px; background-image: linear-gradient(rgba(0,240,255,.22) 1px, transparent 1px), linear-gradient(90deg, rgba(255,79,216,.22) 1px, transparent 1px); background-size: 28px 14px; transform: perspective(260px) rotateX(62deg); transform-origin: bottom center; opacity: .45; }
    .scanline-veil { position: absolute; inset: 0; background: repeating-linear-gradient(0deg, rgba(255,255,255,.025) 0 1px, transparent 1px 4px); pointer-events: none; z-index: 6; }
    .vice-skyline { position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; z-index: 1; }
    .palm-sway { transform-origin: 90px 165px; animation: palmSway 4.8s ease-in-out infinite; }

    .diorama-tribunal, .diorama-lab, .diorama-hospital, .diorama-epicee, .diorama-protection, .diorama-network { position: absolute; inset: 0; z-index: 3; }

    /* 1. Tribunal / Comisión Directiva (Asch / Comité) */
    .board-window { position: absolute; left: 20px; right: 20px; top: 14px; height: 96px; border: 1px solid rgba(0, 240, 255, 0.28); background: rgba(8, 12, 24, 0.36); backdrop-filter: blur(2px); }
    .vote-scoreboard { position: absolute; top: 20px; left: 50%; transform: translateX(-50%); padding: 8px 18px; border-radius: 8px; border: 1px solid rgba(255, 158, 61, 0.65); background: rgba(11, 14, 24, 0.92); box-shadow: 0 0 24px rgba(255, 79, 216, 0.28); text-align: center; z-index: 4; }
    .vote-scoreboard small { display: block; font: 700 9px var(--mono); color: #ff9e3d; letter-spacing: 1.4px; }
    .vote-scoreboard b { display: block; font: 800 16px var(--display); letter-spacing: 1px; color: #fff; margin: 2px 0 4px; }
    .vote-bars { display: flex; justify-content: center; gap: 5px; }
    .vote-bars .vb { width: 18px; height: 5px; border-radius: 3px; }
    .vote-bars .vb.warn { background: #ff4f79; box-shadow: 0 0 8px #ff4f79; animation: blinkWin 1.4s infinite; }
    .vote-bars .vb.you { background: #00f0ff; box-shadow: 0 0 10px #00f0ff; }
    .council-table { position: absolute; left: 10%; right: 10%; bottom: 16px; height: 42px; border-radius: 22px 22px 6px 6px; background: linear-gradient(180deg, #1b253a, #0b101b); border: 1px solid rgba(0, 240, 255, 0.45); box-shadow: 0 10px 26px rgba(0, 0, 0, 0.7); }
    .council-members { position: relative; display: flex; justify-content: space-around; align-items: flex-end; top: -42px; padding: 0 16px; }
    .npc { position: relative; display: grid; justify-items: center; gap: 3px; }
    .npc i { width: 18px; height: 18px; border-radius: 50%; background: #9ca3af; }
    .npc b { width: 28px; height: 32px; border-radius: 10px 10px 3px 3px; background: linear-gradient(180deg, #334155, #1e293b); border: 1px solid rgba(255,255,255,0.2); }
    .npc em { position: absolute; top: -18px; right: -10px; font-style: normal; font-size: 16px; animation: handRaise 1.6s ease-in-out infinite alternate; }
    .npc.d2 em { animation-delay: 0.25s; }
    .npc.d3 em { animation-delay: 0.5s; }
    .npc.player-seat i { background: #00f0ff; box-shadow: 0 0 14px #00f0ff; }
    .npc.player-seat b { background: linear-gradient(180deg, #0891b2, #0f172a); border-color: #00f0ff; }
    .npc.player-seat.stood { transform: translateY(-10px) scale(1.12); transition: transform 0.35s ease; }
    .spotlight { position: absolute; top: -20px; width: 120px; height: 240px; pointer-events: none; background: linear-gradient(180deg, rgba(255, 79, 216, 0.22), transparent 82%); transform-origin: top center; animation: spotlightSweep 4.4s ease-in-out infinite alternate; }
    .spotlight.s1 { left: 16%; }
    .spotlight.s2 { right: 16%; background: linear-gradient(180deg, rgba(0, 240, 255, 0.2), transparent 82%); animation-delay: -2.2s; }

    /* 2. Laboratorio Conductual */
    .voltage-rack { position: absolute; left: 50%; top: 18px; transform: translateX(-50%); display: flex; align-items: center; gap: 10px; padding: 6px 14px; border-radius: 8px; background: rgba(10, 14, 22, 0.92); border: 1px solid rgba(255, 79, 121, 0.6); }
    .dial-face { position: relative; width: 28px; height: 28px; border-radius: 50%; border: 2px solid #ff9e3d; background: #0b0f18; }
    .dial-needle { position: absolute; left: 50%; bottom: 50%; width: 2px; height: 11px; background: #ff4f79; transform-origin: bottom center; animation: dialSwing 2.2s ease-in-out infinite alternate; }
    .volt-tag { font: 700 12px var(--mono); color: #ff9e3d; letter-spacing: 1px; }
    .oscilloscope { position: absolute; left: 50%; top: 68px; transform: translateX(-50%); width: 220px; height: 52px; background: rgba(6, 18, 22, 0.85); border: 1px solid rgba(0, 240, 255, 0.4); border-radius: 6px; }
    .wave-trace { fill: none; stroke: #00f0ff; stroke-width: 2.2; stroke-dasharray: 260; animation: oscSweep 2.1s linear infinite; }
    .lab-glass { position: absolute; left: 50%; top: 16px; bottom: 16px; width: 2px; background: linear-gradient(180deg, transparent, rgba(0, 240, 255, 0.6), transparent); }
    .lab-subject, .lab-authority { position: absolute; bottom: 26px; display: grid; justify-items: center; gap: 4px; }
    .lab-subject { left: 16%; animation: moonFloat 2.4s ease-in-out infinite; }
    .lab-authority { right: 16%; }
    .lab-subject i { width: 20px; height: 20px; border-radius: 50%; background: #ff9e3d; }
    .lab-subject b { width: 30px; height: 40px; border-radius: 10px 10px 4px 4px; background: #334155; }
    .lab-authority i { width: 22px; height: 22px; border-radius: 50%; background: #e2e8f0; }
    .lab-authority b { width: 34px; height: 48px; border-radius: 10px 10px 4px 4px; background: linear-gradient(180deg, #f8fafc, #cbd5e1); border: 1px solid #00f0ff; }
    .lab-authority em { position: absolute; left: -24px; top: 20px; font-style: normal; font-size: 18px; }
    .emergency-beacon { position: absolute; top: 14px; right: 20px; width: 14px; height: 14px; border-radius: 50%; background: #ff4f79; box-shadow: 0 0 18px #ff4f79; animation: sirenGlow 0.6s infinite alternate; }

    /* 3. Hospital */
    .diorama-hospital .rain { position: absolute; inset: 0; background-image: repeating-linear-gradient(108deg, transparent 0 16px, rgba(0, 240, 255, 0.16) 16px 18px); animation: rainFall 0.9s linear infinite; opacity: 0.55; }
    .chopper-beam { position: absolute; top: -15px; right: 18%; width: 130px; height: 230px; background: linear-gradient(180deg, rgba(168, 248, 255, 0.25), transparent 80%); transform-origin: top center; animation: spotlightSweep 3.8s ease-in-out infinite alternate; }
    .diorama-hospital .hospital { position: absolute; left: 28px; bottom: 26px; width: 126px; height: 96px; border: 2px solid rgba(0, 240, 255, 0.5); background: #10192b; display: grid; grid-template-columns: repeat(2, 1fr); gap: 6px; padding: 24px 10px 10px; }
    .diorama-hospital .hospital b { position: absolute; top: 4px; left: 8px; font: 700 10px var(--mono); color: #00f0ff; letter-spacing: 1px; }
    .diorama-hospital .hospital i { display: block; background: rgba(0, 240, 255, 0.3); border-radius: 2px; animation: blinkWin 2s infinite; }
    .diorama-hospital .hospital em { position: absolute; top: -8px; right: 10px; width: 14px; height: 14px; border-radius: 50%; background: #ff3b5c; box-shadow: 0 0 16px #ff3b5c; animation: sirenGlow 0.7s infinite alternate; }
    .diorama-hospital .ambulance { position: absolute; right: 34px; bottom: 26px; width: 92px; height: 38px; border-radius: 8px 16px 4px 4px; background: #e2f4f8; border: 2px solid #00f0ff; animation: ambulanceDrive 3.2s ease-in-out infinite; }
    .diorama-hospital .ambulance .lightbar { position: absolute; top: -7px; left: 24px; width: 18px; height: 6px; background: linear-gradient(90deg, #ff3b5c, #00f0ff); box-shadow: 0 0 14px #00f0ff; animation: sirenGlow 0.45s linear infinite alternate; }
    .diorama-hospital .ambulance b { position: absolute; top: 7px; right: 8px; width: 22px; height: 12px; border-radius: 3px; background: #0d2230; }
    .diorama-hospital .ambulance i { position: absolute; bottom: -8px; width: 14px; height: 14px; border-radius: 50%; background: #0b0e14; border: 2px solid #00f0ff; }
    .diorama-hospital .ambulance i:first-of-type { left: 10px; }
    .diorama-hospital .ambulance i:last-of-type { right: 10px; }
    .ecg-svg { position: absolute; left: 0; right: 0; bottom: 6px; height: 24px; opacity: 0.85; }
    .ecg-path { fill: none; stroke: #00e894; stroke-width: 2; stroke-dasharray: 420; animation: oscSweep 2.4s linear infinite; }

    /* 4. Entrevista Clínica / EPICEE */
    .diorama-epicee .room-light { position: absolute; top: 14px; left: 50%; width: 190px; height: 60px; transform: translateX(-50%); border-radius: 50%; background: radial-gradient(circle, rgba(255, 158, 61, 0.35), transparent 72%); animation: roomGlow 3.2s infinite; }
    .venetian-glow { position: absolute; inset: 0; background: repeating-linear-gradient(125deg, rgba(255, 158, 61, 0.06) 0 14px, transparent 14px 32px); pointer-events: none; }
    .diorama-epicee .clinician { position: absolute; left: 48px; bottom: 28px; display: grid; justify-items: center; gap: 4px; }
    .diorama-epicee .clinician i { width: 22px; height: 22px; border-radius: 50%; background: #00f0ff; box-shadow: 0 0 16px rgba(0, 240, 255, 0.55); }
    .diorama-epicee .clinician b { width: 34px; height: 44px; border-radius: 12px 12px 4px 4px; background: linear-gradient(180deg, #1b3848, #0f1d28); border: 1px solid #00f0ff; }
    .diorama-epicee .family-group { position: absolute; right: 48px; bottom: 28px; display: flex; align-items: flex-end; gap: 8px; }
    .diorama-epicee .family-group span { width: 18px; height: 48px; border-radius: 10px 10px 4px 4px; background: linear-gradient(180deg, #00e894, rgba(0, 232, 148, 0.25)); animation: moonFloat 3.4s ease-in-out infinite; }
    .diorama-epicee .family-group span:nth-child(2) { height: 56px; animation-delay: 0.45s; }
    .diorama-epicee .family-group span:nth-child(3) { height: 38px; animation-delay: 0.9s; }
    .diorama-epicee .message-card { position: absolute; left: 50%; top: 32px; transform: translateX(-50%); padding: 10px 18px; border-radius: 12px; border: 1px solid rgba(0, 240, 255, 0.55); background: rgba(11, 18, 28, 0.92); text-align: center; animation: cardFloat 3s ease-in-out infinite; }
    .diorama-epicee .message-card b { display: block; font: 700 11px var(--mono); letter-spacing: 1.5px; color: #00f0ff; }
    .diorama-epicee .message-card small { color: var(--text); font-size: 12px; }
    .diorama-epicee .calm-wave { position: absolute; left: 50%; bottom: 24px; width: 170px; height: 22px; transform: translateX(-50%); border-radius: 50%; border: 1px solid rgba(0, 232, 148, 0.5); animation: waveExpand 2.8s ease-out infinite; }
    .diorama-epicee .calm-wave.w2 { animation-delay: 1.4s; }

    /* 5. Protección */
    .diorama-protection .safe-door { position: absolute; left: 32px; bottom: 22px; width: 60px; height: 102px; border-radius: 10px 10px 2px 2px; border: 2px solid #00e894; background: linear-gradient(180deg, rgba(0, 232, 148, 0.25), rgba(0, 232, 148, 0.05)); box-shadow: 0 0 24px rgba(0, 232, 148, 0.22); }
    .diorama-protection .person.protected { position: absolute; left: 112px; bottom: 24px; width: 24px; height: 54px; border-radius: 12px 12px 4px 4px; background: linear-gradient(180deg, #00f0ff, #173a48); animation: moonFloat 3s infinite; }
    .diorama-protection .hex-shield { position: absolute; left: 50%; top: 58px; transform: translateX(-50%); padding: 10px 20px; border-radius: 999px; border: 1px solid #00f0ff; background: rgba(0, 240, 255, 0.16); font: 700 12px var(--mono); letter-spacing: 1.4px; color: #b8faff; animation: shieldPulse 2.4s infinite; }
    .diorama-protection .risk-meter { position: absolute; top: 24px; right: 26px; width: 140px; height: 14px; border-radius: 999px; border: 1px solid rgba(255, 184, 0, 0.6); background: #0a0f16; overflow: hidden; }
    .diorama-protection .risk-meter span { display: block; height: 100%; width: 66%; background: linear-gradient(90deg, #ff9e3d, #ff3b5c); animation: meterPulse 2.2s infinite alternate; }
    .radar-scan { position: absolute; right: 42px; bottom: 32px; width: 52px; height: 52px; border-radius: 50%; border: 1px solid rgba(0, 240, 255, 0.45); overflow: hidden; }
    .radar-scan i { position: absolute; inset: 0; background: conic-gradient(rgba(0, 240, 255, 0.55) 0 55deg, transparent 55deg 360deg); animation: radarSpin 2.5s linear infinite; }
    .diorama-protection .path { position: absolute; left: 24px; right: 24px; bottom: 18px; height: 3px; background: linear-gradient(90deg, #00e894, #00f0ff, #ff4fd8); animation: blinkWin 2.6s infinite; }

    /* 6. Red Ciudad */
    .diorama-network .node { position: absolute; padding: 6px 12px; border-radius: 999px; border: 1px solid rgba(0, 240, 255, 0.55); background: rgba(9, 16, 26, 0.92); font: 700 11px var(--mono); text-transform: uppercase; color: #a8f8ff; box-shadow: 0 0 18px rgba(0, 240, 255, 0.18); animation: moonFloat 3.4s ease-in-out infinite; }
    .diorama-network .node.victim { left: 50%; top: 50%; transform: translate(-50%, -50%); border-color: #ff4fd8; color: #ff9de8; animation: none; }
    .diorama-network .node.rights { left: 26px; top: 24px; }
    .diorama-network .node.health { right: 26px; top: 24px; animation-delay: 0.6s; }
    .diorama-network .node.mental { left: 28px; bottom: 22px; animation-delay: 1.2s; }
    .diorama-network .node.risk { right: 28px; bottom: 22px; border-color: #ff9e3d; color: #ffd49c; animation-delay: 1.8s; }
    .diorama-network .net { position: absolute; left: 16%; right: 16%; height: 1px; background: linear-gradient(90deg, transparent, rgba(255, 79, 216, 0.55), transparent); pointer-events: none; }
    .diorama-network .net.l1 { top: 48px; transform: rotate(9deg); }
    .diorama-network .net.l2 { bottom: 46px; transform: rotate(-9deg); }
    .diorama-network .route-dot { position: absolute; top: 50%; left: 20%; width: 10px; height: 10px; margin-top: -5px; border-radius: 50%; background: #00f0ff; box-shadow: 0 0 14px #00f0ff; animation: dotTravel 2.8s ease-in-out infinite; }

    /* Overlay Cinemático GTA 6 al lanzar jugada */
    .gta-cutscene {
      position: absolute;
      inset: 0;
      z-index: 8;
      display: grid;
      place-items: center;
      background: radial-gradient(circle, rgba(255, 79, 216, 0.22), rgba(7, 10, 18, 0.82));
      animation: cutsceneFade 0.9s ease forwards;
    }
    .gta-stripes {
      position: absolute;
      inset: 0;
      background: repeating-linear-gradient(-24deg, rgba(255, 79, 216, 0.08) 0 12px, transparent 12px 26px);
      animation: stripesMove 0.6s linear infinite;
    }
    .gta-banner {
      position: relative;
      padding: 14px 28px;
      border-radius: 10px;
      border: 2px solid #ff4fd8;
      background: linear-gradient(125deg, rgba(20, 10, 34, 0.96), rgba(9, 24, 34, 0.96));
      box-shadow: 0 0 38px rgba(255, 79, 216, 0.45), 0 0 24px rgba(0, 240, 255, 0.35);
      text-align: center;
      transform: skewX(-4deg);
      animation: gtaBannerPop 0.45s cubic-bezier(0.22, 1, 0.36, 1);
    }
    .gta-tag {
      display: block;
      font: 800 11px var(--mono);
      letter-spacing: 2.2px;
      background: linear-gradient(90deg, #ff4fd8, #ff9e3d, #00f0ff);
      -webkit-background-clip: text;
      color: transparent;
    }
    .gta-banner h4 {
      margin: 4px 0 2px;
      font-family: var(--display);
      font-size: clamp(22px, 4vw, 32px);
      text-transform: uppercase;
      color: #fff;
      text-shadow: 0 2px 16px rgba(255, 79, 216, 0.55);
    }
    .gta-banner small {
      font: 11px var(--mono);
      color: #a8f8ff;
      letter-spacing: 1px;
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

    /* ==================== MAZO DE CARTAS ESTILO POKER (.card-rail + .poker-card) ==================== */
    .card-rail {
      display: flex;
      gap: 20px;
      overflow-x: auto;
      overflow-y: visible;
      padding: 20px 12px 28px;
      scroll-snap-type: x mandatory;
      scrollbar-color: #ff4fd8 transparent;
    }
    .card-rail.has-selection .poker-card:not(.selected) {
      opacity: 0.62;
      filter: saturate(0.75);
      transform: scale(0.97) rotate(var(--tilt, 0deg));
    }
    .card-rail.locked .poker-card:not(.launched) {
      opacity: 0.34;
      transform: scale(0.94);
      pointer-events: none;
    }
    .poker-card {
      position: relative;
      flex: 0 0 min(82vw, 256px);
      min-height: 332px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      padding: 14px 12px;
      border-radius: 18px;
      background: linear-gradient(162deg, #fffdf7 0%, #f4efe1 60%, #ece3ce 100%);
      color: #111827;
      border: 2px solid #e2d8be;
      box-shadow:
        inset 0 0 0 5px #fcfaf4,
        inset 0 0 0 6px rgba(17, 24, 39, 0.2),
        0 20px 40px rgba(0, 0, 0, 0.55);
      cursor: pointer;
      scroll-snap-align: center;
      transform: rotate(var(--tilt, 0deg));
      transition: transform 0.26s cubic-bezier(0.22, 1, 0.36, 1), border-color 0.24s ease, box-shadow 0.24s ease, opacity 0.24s ease;
      overflow: hidden;
      animation: pokerDeal 0.42s cubic-bezier(0.22, 1, 0.36, 1) backwards;
      animation-delay: var(--deal-delay, 0ms);
    }
    .poker-card::before {
      content: '';
      position: absolute;
      inset: -40%;
      background: linear-gradient(125deg, transparent 40%, rgba(255, 255, 255, 0.65) 50%, transparent 60%);
      transform: translateX(-100%);
      transition: transform 0.6s ease;
      pointer-events: none;
    }
    .poker-card:hover::before {
      transform: translateX(100%);
    }
    .poker-card:nth-child(2) { margin-top: 8px; }
    .poker-card:nth-child(3) { margin-top: 4px; }
    .poker-card.suit-red .poker-corner, .poker-card.suit-red .poker-crest { color: #b91c1c; }
    .poker-card.suit-dark .poker-corner, .poker-card.suit-dark .poker-crest { color: #0f172a; }
    .poker-card:hover, .poker-card.selected {
      opacity: 1 !important; filter: none !important; transform: translateY(-12px) rotate(0deg) scale(1.02);
      border-color: #00e5f4; box-shadow: inset 0 0 0 5px #fffdf8, 0 0 26px rgba(0, 229, 244, 0.42), 0 26px 48px rgba(0,0,0,.62);
    }
    .poker-card.selected { border-color: #00e894; box-shadow: inset 0 0 0 5px #fffdf8, 0 0 32px rgba(0, 232, 148, 0.48), 0 28px 50px rgba(0,0,0,.68); }
    .poker-card.launched { opacity: 1 !important; filter: none !important; border-color: #ff4fd8; box-shadow: inset 0 0 0 5px #fffdf8, 0 0 42px rgba(255,79,216,.65); animation: cardLaunch .85s cubic-bezier(.22,1,.36,1) forwards; }
    .sr-only-radio { position: absolute; opacity: 0; width: 1px; height: 1px; pointer-events: none; }
    .poker-corner { display: flex; flex-direction: column; align-items: center; width: max-content; line-height: 0.95; z-index: 2; user-select: none; }
    .poker-corner.top-left { align-self: flex-start; }
    .poker-corner.bottom-right { align-self: flex-end; transform: rotate(180deg); }
    .poker-rank { font: 800 22px Georgia, 'Times New Roman', serif; letter-spacing: -0.5px; }
    .poker-suit { font-size: 20px; line-height: 1; }
    .poker-stack { margin-top: 2px; font-size: 9px; font-weight: 700; letter-spacing: 0.8px; opacity: 0.65; }
    .poker-inner-frame { margin: 6px 14px; padding: 12px 10px; flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: space-between; text-align: center; border: 1.5px solid rgba(15, 23, 42, 0.22); border-radius: 10px; background: radial-gradient(circle at center, rgba(255, 255, 255, 0.86), rgba(244, 237, 220, 0.7)); }
    .poker-crest { position: relative; display: grid; place-items: center; min-height: 58px; padding-top: 6px; gap: 2px; }
    .crest-wreath { position: absolute; top: -2px; width: 52px; height: 52px; pointer-events: none; }
    .crest-suit { position: relative; font-size: 32px; line-height: 1; filter: drop-shadow(0 2px 3px rgba(0, 0, 0, 0.16)); }
    .crest-arquetipo { font: 700 9px var(--mono); letter-spacing: 1.4px; text-transform: uppercase; color: #475569; margin-top: 6px; }
    .poker-hairline { width: 68%; height: 1px; margin: 6px 0; background: linear-gradient(90deg, transparent, rgba(15, 23, 42, 0.35), transparent); }
    .poker-decision-text { color: #0f172a; font: 700 13.5px/1.4 var(--body); margin: auto 0; }
    .poker-footer-seal { margin-top: 8px; }
    .seal { display: inline-block; padding: 4px 10px; border-radius: 999px; font: 700 10px var(--mono); letter-spacing: 0.8px; text-transform: uppercase; }
    .idle-seal { background: rgba(15, 23, 42, 0.08); color: #334155; border: 1px solid rgba(15, 23, 42, 0.16); }
    .armed-seal { background: #065f46; color: #ecfdf5; box-shadow: 0 0 12px rgba(0, 232, 148, 0.45); }
    .launched-seal { background: linear-gradient(90deg, #a21caf, #db2777); color: #fff; box-shadow: 0 0 14px rgba(255, 79, 216, 0.55); }

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
    @keyframes gtaCamFloat {
      0% { transform: scale(1) translate3d(0, 0, 0); }
      100% { transform: scale(1.04) translate3d(-1%, -1%, 0); }
    }
    @keyframes flareSweep {
      0% { transform: translateX(-12%) rotate(-1.5deg); opacity: 0.25; }
      100% { transform: translateX(10%) rotate(1.5deg); opacity: 0.65; }
    }
    @keyframes palmSway {
      0%, 100% { transform: rotate(-1.5deg); }
      50% { transform: rotate(2.5deg); }
    }
    @keyframes gtaImpactFlash {
      0% { transform: scale(1); filter: brightness(1); }
      22% { transform: scale(1.018); filter: brightness(1.32) saturate(1.4); }
      45% { transform: scale(0.996); filter: brightness(1.08); }
      100% { transform: scale(1); filter: brightness(1); }
    }
    @keyframes gtaBannerPop {
      0% { opacity: 0; transform: skewX(-10deg) scale(0.76); }
      70% { opacity: 1; transform: skewX(-4deg) scale(1.04); }
      100% { opacity: 1; transform: skewX(-4deg) scale(1); }
    }
    @keyframes stripesMove {
      from { background-position: 0 0; }
      to { background-position: 52px 0; }
    }
    @keyframes cutsceneFade {
      0% { opacity: 0; }
      16% { opacity: 1; }
      85% { opacity: 1; }
      100% { opacity: 0.92; }
    }
    @keyframes pokerDeal {
      from { opacity: 0; transform: translateY(24px) scale(0.92) rotate(0deg); }
      to { opacity: 1; transform: translateY(0) scale(1) rotate(var(--tilt, 0deg)); }
    }
    @keyframes handRaise {
      from { transform: translateY(2px) scale(0.92); opacity: 0.65; }
      to { transform: translateY(-4px) scale(1.1); opacity: 1; }
    }
    @keyframes spotlightSweep {
      from { transform: rotate(-14deg); opacity: 0.55; }
      to { transform: rotate(14deg); opacity: 0.9; }
    }
    @keyframes dialSwing {
      from { transform: rotate(-38deg); }
      to { transform: rotate(48deg); }
    }
    @keyframes oscSweep {
      from { stroke-dashoffset: 420; }
      to { stroke-dashoffset: 0; }
    }
    @keyframes radarSpin {
      from { transform: rotate(0deg); }
      to { transform: rotate(360deg); }
    }
    @keyframes cardLaunch {
      0% { transform: translateY(-12px) scale(1.02) rotate(0deg); }
      45% { transform: translateY(-28px) scale(1.06) rotate(-2deg); }
      100% { transform: translateY(-16px) scale(1.02) rotate(0deg); }
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
    @keyframes roomGlow {
      0%, 100% { opacity: 0.55; }
      50% { opacity: 0.95; }
    }
    @keyframes waveExpand {
      0% { opacity: 0.7; transform: translateX(-50%) scale(0.78); }
      100% { opacity: 0; transform: translateX(-50%) scale(1.35); }
    }
    @keyframes cardFloat { 0%, 100% { transform: translate(-50%, 0); } 50% { transform: translate(-50%, -6px); } }
    @keyframes meterPulse { from { width: 48%; } to { width: 78%; } }
    @keyframes shieldPulse { 0%, 100% { box-shadow: 0 0 12px rgba(0, 229, 244, 0.22); } 50% { box-shadow: 0 0 24px rgba(0, 232, 148, 0.44); } }
    @keyframes dotTravel { 0%, 100% { left: 18%; } 50% { left: 78%; } }
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

    @media (max-width: 780px) {
      .launch-pad { grid-template-columns: 1fr; }
      .coach { grid-template-columns: auto 1fr; }
      .coach .tag { grid-column: 1 / -1; justify-self: start; }
      .play-actions { width: 100%; justify-content: stretch; }
      .play-actions button { flex: 1 1 140px; }
    }
    @media (max-width: 520px) {
      .stage { height: 172px; }
      .poker-card { flex: 0 0 min(82vw, 232px); min-height: 295px; }
      .diorama-hospital .hospital { left: 12px; width: 96px; height: 80px; }
      .diorama-hospital .ambulance { right: 12px; width: 70px; }
      .diorama-epicee .clinician { left: 14px; }
      .diorama-epicee .family-group { right: 14px; }
      .diorama-protection .safe-door { left: 14px; width: 46px; }
      .diorama-protection .person.protected { left: 72px; }
      .diorama-protection .risk-meter { right: 12px; width: 106px; }
      .diorama-network .node { font-size: 9px; padding: 4px 8px; }
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
    return `${[-2.8, 1.4, -1.5, 2.5][index % 4]}deg`;
  }

  paloCarta(index: number): { rango: string; simbolo: string; arquetipo: string; rojo: boolean } {
    const palos = [
      { rango: 'A', simbolo: '♠', arquetipo: 'JUICIO', rojo: false },
      { rango: 'K', simbolo: '♥', arquetipo: 'CRITERIO', rojo: true },
      { rango: 'Q', simbolo: '♦', arquetipo: 'ESTRATEGIA', rojo: true },
      { rango: 'J', simbolo: '♣', arquetipo: 'ACCIÓN', rojo: false },
      { rango: '10', simbolo: '♠', arquetipo: 'PROTOCOLO', rojo: false },
    ];
    return palos[index % palos.length];
  }

  escenarioTema():
    | 'tribunal_comite'
    | 'laboratorio_autoridad'
    | 'hospital_urgencias'
    | 'entrevista_clinica'
    | 'proteccion_riesgo'
    | 'red_ciudad' {
    const actual = this.pasoActual();
    const ws = this.workspace();
    if (!actual) return 'red_ciudad';
    const raw = `${ws?.caso_nombre ?? ''} ${actual.escenario.contexto_situacional} ${actual.pregunta.enunciado}`
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase();

    if (/(comision|comite|directiv|votac|voto|unanime|decano|expuls|testigo|debido proceso|asch|conformidad|junta)/.test(raw)) {
      return 'tribunal_comite';
    }
    if (/(milgram|experimento|bata|descarga|voltaje|obediencia|investigador|sujeto|laboratorio|orden directa)/.test(raw)) {
      return 'laboratorio_autoridad';
    }
    if (/(hospital|ambulancia|urgenc|emergenc|triaje|medico|uci|herido|trauma|clinica)/.test(raw)) {
      return 'hospital_urgencias';
    }
    if (/(epicee|familia|entrevista|escucha|dialogo|comunicacion|paciente|duelo|consulta)/.test(raw)) {
      return 'entrevista_clinica';
    }
    if (/(proteccion|riesgo|seguridad|violencia|abuso|denuncia|custodia|refugio|alerta|vulnera)/.test(raw)) {
      return 'proteccion_riesgo';
    }
    const temas: Array<
      'tribunal_comite' | 'laboratorio_autoridad' | 'hospital_urgencias' | 'entrevista_clinica' | 'proteccion_riesgo' | 'red_ciudad'
    > = ['tribunal_comite', 'entrevista_clinica', 'proteccion_riesgo', 'red_ciudad'];
    return temas[(actual.escenario.orden - 1) % temas.length];
  }

  etiquetaTemaEscenario(): string {
    const etiquetas: Record<string, string> = {
      tribunal_comite: 'SALA DIRECTIVA · PRESIÓN GRUPAL',
      laboratorio_autoridad: 'LAB CONDUCTUAL · AUTORIDAD',
      hospital_urgencias: 'URGENCIAS 24H · CRISIS',
      entrevista_clinica: 'SALA CLÍNICA · VÍNCULO',
      proteccion_riesgo: 'PERÍMETRO · PROTECCIÓN',
      red_ciudad: 'DISTRITO · RED DE CUIDADO',
    };
    return etiquetas[this.escenarioTema()] ?? 'SIMULACIÓN ACTIVA';
  }

  etiquetaImpactoCarta(): string {
    const id = this.opcionLanzada();
    const actual = this.pasoActual();
    if (!id || !actual) return 'CARTA JUGADA';
    const idx = actual.pregunta.opciones.findIndex((o) => o.id === id);
    const palo = this.paloCarta(Math.max(0, idx));
    return `${palo.rango}${palo.simbolo} // ${palo.arquetipo}`;
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

      await new Promise((resolve) => setTimeout(resolve, 950));
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
