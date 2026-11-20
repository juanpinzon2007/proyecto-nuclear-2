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
import { CATALOGO_HEROES, elegirHeroeAleatorio } from './cinema/cinema-heroes';
import { PerfilHeroe, TemaEscena } from './cinema/cinema.types';
import { CyberCartaComponent } from './cinema/cyber-carta.component';
import { EscenaCinematograficaComponent } from './cinema/escena-cinematografica.component';
import {
  CartaBaraja,
  ResultadoAyudaJoker,
  barajarBaraja52,
  construirAyudaJoker,
  repartirManoDesdeBaraja,
} from './cinema/poker-deck';
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
    CyberCartaComponent,
    EscenaCinematograficaComponent,
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
                PROGRESO: {{ ws.respondidas ?? 0 }}/{{ ws.total_preguntas ?? 0 }} · CAMBIOS DE DECISIÓN: {{ ws.cambios_realizados ?? 0 }}
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
          <app-escena-cinematografica
            [tema]="escenarioTema()"
            [escenaOrden]="actual.escenario.orden"
            [totalEscenas]="pasosPlanos().length"
            [pasoIndice]="indiceActual() + 1"
            [etiquetaTema]="etiquetaTemaEscenario()"
            [contextoSituacional]="actual.escenario.contexto_situacional"
            [preguntaEnunciado]="actual.pregunta.enunciado"
            [yaRespondida]="estaRespondida(actual.pregunta.id)"
            [opcionArmada]="!!opcionElegida && !opcionLanzada()"
            [opcionLanzada]="!!opcionLanzada()"
            [etiquetaImpacto]="etiquetaImpactoCarta()"
            [transicionando]="transicionandoEscena()"
            [heroe]="heroeActual()"
            [jokerActivo]="!!ayudaJokerActual()"
            (cambiarHeroe)="rotarHeroeAleatorio()"
          />

          <!-- Coach Neuro reactivo -->
          <section class="coach panel" [class.coach-pulse]="!!opcionElegida || !!respuestaAnimada()">
            <div class="coach-orb"><mat-icon aria-hidden="true">psychology</mat-icon></div>
            <div class="grow">
              <span class="eyebrow">Asistente SPS · Guía Táctica</span>
              <p class="coach-msg">{{ coachMensaje() }}</p>
            </div>
            <span class="tag" [class.green]="!!opcionElegida || !!opcionLanzada()">
              {{ opcionLanzada() ? 'REGISTRADO ✓' : (opcionElegida ? 'CARTA ARMADA' : 'ELIGE UNA CARTA') }}
            </span>
          </section>

          <!-- Visor de Baraja Completa Aleatoria (52 cartas) + Ayuda Comodín JOKER -->
          <section class="panel deck-52-panel">
            <div class="deck-52-head">
              <div>
                <span class="eyebrow">Baraja Cyber Completa · 52 Cartas Aleatorias</span>
                <p class="deck-52-sub">
                  En mano ahora: <strong>{{ manoActualResumen() }}</strong>
                </p>
              </div>
              <button
                type="button"
                class="shuffle-52-btn"
                (click)="rebarajarBaraja()"
                [disabled]="!!opcionLanzada() || guardando()"
              >
                <mat-icon aria-hidden="true">shuffle</mat-icon>
                <span>Rebarajar 52 cartas</span>
              </button>
            </div>

            <div class="deck-52-strip" aria-label="Baraja inglesa completa de 52 cartas mezclada aleatoriamente">
              @for (card of barajaCompleta(); track card.id) {
                <span
                  class="mini-cyber-card"
                  [class.is-red]="card.esRojo"
                  [class.is-dealt]="cartasEnManoIds().has(card.id)"
                  [title]="card.rango + card.simbolo + ' · ' + card.arquetipo"
                >
                  <b>{{ card.rango }}</b>
                  <i>{{ card.simbolo }}</i>
                </span>
              }
            </div>
          </section>

          <!-- Enunciado de Decisión -->
          <div class="prompt-banner panel" [class.stage-enter]="transicionandoEscena()">
            <p class="eyebrow amber">Dilema a resolver</p>
            <h2 class="q-enunciado">{{ actual.pregunta.enunciado }}</h2>
          </div>

          <!-- Estación del Comodín JOKER para el estudiante -->
          <section class="panel joker-station" [class.joker-active]="!!ayudaJokerActual()">
            <div class="joker-card-slot">
              <app-cyber-carta
                [esJoker]="true"
                rango="JK"
                [arquetipo]="ayudaJokerActual() ? 'COMODÍN ACTIVO' : 'AYUDA JOKER (' + jokersRestantes() + '/' + maxJokers() + ')'"
                [texto]="ayudaJokerActual() ? 'Lectura táctica habilitada para este dilema.' : 'Activa tu comodín para recibir orientación ética y contraste estratégico.'"
                [selloPie]="ayudaJokerActual() ? 'JOKER USADO EN PASO' : (jokersRestantes() > 0 ? 'USAR COMODÍN' : 'SIN COMODINES')"
              />
            </div>

            <div class="joker-body">
              <div class="joker-top">
                <div>
                  <span class="eyebrow amber">Asistencia Táctica Estudiantil</span>
                  <h3 class="joker-title">Carta Comodín JOKER</h3>
                </div>
                <span class="joker-quota mono">
                  DISPONIBLES: {{ jokersRestantes() }} / {{ maxJokers() }}
                </span>
              </div>

              @if (ayudaJokerActual(); as jHelp) {
                <div class="joker-insight">
                  <div class="joker-hero-line">
                    <mat-icon aria-hidden="true">bolt</mat-icon>
                    <span>Asesor activo: <strong>{{ jHelp.heroeAsesor }}</strong></span>
                  </div>
                  <p><strong>Marco psicosocial:</strong> {{ jHelp.principioPsicosocial }}</p>
                  <p><strong>Contraste de opciones:</strong> {{ jHelp.contrasteEstrategico }}</p>
                  @if (jHelp.etiquetaCartaRiesgo) {
                    <div class="joker-flag-note">
                      <mat-icon aria-hidden="true">warning_amber</mat-icon>
                      <span>{{ jHelp.etiquetaCartaRiesgo }}</span>
                    </div>
                  }
                </div>
              } @else {
                <p class="joker-desc">
                  Cada estudiante cuenta con apoyo de <strong>Comodín JOKER</strong> durante el caso para desglosar el dilema psicológico y contrastar las cartas de decisión sin alterar las reglas de evaluación.
                </p>
                <div class="joker-actions">
                  <button
                    type="button"
                    mat-flat-button
                    color="accent"
                    (click)="activarJoker()"
                    [disabled]="jokersRestantes() <= 0 || !!opcionLanzada() || guardando()"
                  >
                    <mat-icon>auto_awesome</mat-icon>
                    {{ jokersRestantes() > 0 ? 'Activar Ayuda JOKER' : 'Comodines agotados en este intento' }}
                  </button>
                </div>
              }
            </div>
          </section>

          <!-- Mazo de Cartas Cyber-Neón (Baraja aleatoria completa A..K × ♠ ♥ ♦ ♣) -->
          <div class="card-rail" [class.has-selection]="!!opcionElegida" [class.locked]="!!opcionLanzada()">
            @for (op of actual.pregunta.opciones; track op.id; let oi = $index) {
              @let carta = cartaDeOpcion(oi);
              <label
                class="cyber-card-slot"
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
                <app-cyber-carta
                  [rango]="carta.rango"
                  [simbolo]="carta.simbolo"
                  [esRojo]="carta.esRojo"
                  [arquetipo]="carta.arquetipo"
                  [texto]="op.texto"
                  [etiquetaSuperior]="'OPC0' + (oi + 1)"
                  [seleccionada]="opcionElegida === op.id"
                  [lanzada]="opcionLanzada() === op.id"
                  [riesgoJoker]="ayudaJokerActual()?.cartaRiesgoId === op.id"
                />
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
              <div class="launch-ico" [class.rocket-launch]="!!opcionLanzada()"><mat-icon aria-hidden="true">rocket_launch</mat-icon></div>
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

    .prompt-banner.stage-enter { animation: stageEnter .4s cubic-bezier(.22,1,.36,1); }

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
      border: 1px solid rgba(0, 229, 244, 0.42);
      background: rgba(0, 229, 244, 0.1);
      box-shadow: 0 0 16px rgba(0, 229, 244, 0.16);
      animation: moonFloat 3.2s ease-in-out infinite;
    }
    .coach-orb mat-icon {
      color: var(--cyan);
      width: 24px;
      height: 24px;
      font-size: 24px;
    }
    .grow { min-width: 0; }
    .coach-msg {
      margin: 4px 0 0;
      font-size: 14px;
      line-height: 1.45;
      color: var(--text);
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

    /* ==================== BARAJA 52 CARTAS, JOKER Y MANO CYBER-NEÓN ==================== */
    .deck-52-panel {
      padding: 14px 16px;
      display: grid;
      gap: 10px;
      border-color: rgba(0, 229, 255, 0.24);
      background:
        radial-gradient(circle at 85% 0%, rgba(255, 46, 209, 0.1), transparent 46%),
        rgba(8, 12, 22, 0.94);
    }
    .deck-52-head {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }
    .deck-52-sub {
      margin: 4px 0 0;
      font-size: 12.5px;
      color: var(--muted);
    }
    .deck-52-sub strong {
      color: #a5f3fc;
      font-family: var(--mono);
    }
    .shuffle-52-btn {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 12px;
      border-radius: 999px;
      border: 1px solid rgba(255, 46, 209, 0.48);
      background: linear-gradient(90deg, rgba(0, 229, 255, 0.14), rgba(255, 46, 209, 0.14));
      color: #f5d0fe;
      font-family: var(--mono);
      font-size: 11px;
      font-weight: 700;
      cursor: pointer;
      transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .shuffle-52-btn mat-icon {
      width: 16px;
      height: 16px;
      font-size: 16px;
    }
    .shuffle-52-btn:hover:not(:disabled) {
      transform: translateY(-1px);
      box-shadow: 0 0 16px rgba(0, 229, 255, 0.35);
    }
    .shuffle-52-btn:disabled {
      opacity: 0.45;
      cursor: not-allowed;
    }
    .deck-52-strip {
      display: flex;
      gap: 5px;
      overflow-x: auto;
      padding: 4px 2px 6px;
      scrollbar-color: rgba(0, 229, 255, 0.45) transparent;
    }
    .mini-cyber-card {
      flex: 0 0 auto;
      min-width: 34px;
      height: 46px;
      padding: 3px 4px;
      border-radius: 7px;
      background: linear-gradient(155deg, #0d1323, #060811);
      border: 1px solid rgba(0, 229, 255, 0.28);
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      line-height: 1;
      color: #a5f3fc;
      font-family: Georgia, serif;
      font-size: 11px;
      user-select: none;
      transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
    }
    .mini-cyber-card.is-red {
      border-color: rgba(255, 46, 209, 0.34);
      color: #f5d0fe;
    }
    .mini-cyber-card i {
      font-style: normal;
      font-size: 11px;
      margin-top: 2px;
    }
    .mini-cyber-card.is-dealt {
      transform: translateY(-4px) scale(1.06);
      border-color: #00e5ff;
      box-shadow: 0 0 12px rgba(0, 229, 255, 0.5), 0 0 10px rgba(255, 46, 209, 0.35);
      background: linear-gradient(155deg, #13213a, #1d0e2f);
      color: #ffffff;
    }

    .joker-station {
      display: grid;
      grid-template-columns: 186px 1fr;
      gap: 18px;
      padding: 16px 18px;
      align-items: center;
      border-color: rgba(250, 204, 21, 0.36);
      background:
        radial-gradient(circle at 12% 20%, rgba(250, 204, 21, 0.1), transparent 46%),
        radial-gradient(circle at 90% 80%, rgba(255, 46, 209, 0.1), transparent 48%),
        rgba(8, 11, 20, 0.96);
    }
    .joker-station.joker-active {
      border-color: rgba(0, 229, 255, 0.56);
      box-shadow: 0 0 28px rgba(250, 204, 21, 0.16);
    }
    .joker-card-slot {
      width: 186px;
      min-height: 245px;
      transform: scale(0.92);
      transform-origin: center center;
    }
    .joker-body {
      display: grid;
      gap: 10px;
      min-width: 0;
    }
    .joker-top {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }
    .joker-title {
      margin: 3px 0 0;
      font-family: var(--display);
      font-size: 20px;
      text-transform: uppercase;
      color: #fef08a;
    }
    .joker-quota {
      padding: 4px 10px;
      border-radius: 999px;
      border: 1px solid rgba(250, 204, 21, 0.45);
      background: rgba(113, 63, 18, 0.25);
      color: #fde047;
      font-size: 11px;
      font-weight: 700;
    }
    .joker-desc {
      margin: 0;
      color: var(--text);
      font-size: 13.5px;
      line-height: 1.5;
    }
    .joker-insight {
      display: grid;
      gap: 7px;
      padding: 12px 14px;
      border-radius: 12px;
      background: rgba(6, 10, 22, 0.85);
      border: 1px solid rgba(0, 229, 255, 0.34);
    }
    .joker-insight p {
      margin: 0;
      font-size: 13px;
      line-height: 1.45;
      color: #e2e8f0;
    }
    .joker-hero-line {
      display: flex;
      align-items: center;
      gap: 6px;
      color: #67e8f9;
      font-family: var(--mono);
      font-size: 11.5px;
    }
    .joker-hero-line mat-icon,
    .joker-flag-note mat-icon {
      width: 16px;
      height: 16px;
      font-size: 16px;
    }
    .joker-flag-note {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      width: max-content;
      max-width: 100%;
      padding: 5px 10px;
      border-radius: 8px;
      background: rgba(120, 53, 15, 0.48);
      border: 1px solid rgba(245, 158, 11, 0.55);
      color: #fde68a;
      font-family: var(--mono);
      font-size: 11px;
    }

    .card-rail {
      display: flex;
      gap: 20px;
      overflow-x: auto;
      overflow-y: visible;
      padding: 20px 12px 28px;
      scroll-snap-type: x mandatory;
      scrollbar-color: #ff2ed1 transparent;
    }
    .card-rail.has-selection .cyber-card-slot:not(.selected) {
      opacity: 0.68;
      filter: saturate(0.8);
      transform: scale(0.97) rotate(var(--tilt, 0deg));
    }
    .card-rail.locked .cyber-card-slot:not(.launched) {
      opacity: 0.36;
      transform: scale(0.94);
      pointer-events: none;
    }
    .cyber-card-slot {
      position: relative;
      flex: 0 0 min(82vw, 256px);
      min-height: 356px;
      display: block;
      cursor: pointer;
      scroll-snap-align: center;
      transform: rotate(var(--tilt, 0deg));
      transition: transform 0.28s cubic-bezier(0.22, 1, 0.36, 1), opacity 0.24s ease;
      animation: pokerDeal 0.42s cubic-bezier(0.22, 1, 0.36, 1) backwards;
      animation-delay: var(--deal-delay, 0ms);
    }
    .cyber-card-slot:nth-child(2) { margin-top: 8px; }
    .cyber-card-slot:nth-child(3) { margin-top: 4px; }
    .cyber-card-slot:hover,
    .cyber-card-slot.selected {
      opacity: 1 !important;
      filter: none !important;
      transform: translateY(-12px) rotate(0deg) scale(1.02);
    }
    .cyber-card-slot.launched {
      opacity: 1 !important;
      filter: none !important;
      animation: cardLaunch 0.85s cubic-bezier(0.22, 1, 0.36, 1) forwards;
    }
    .sr-only-radio { position: absolute; opacity: 0; width: 1px; height: 1px; pointer-events: none; }

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
      display: grid;
      place-items: center;
      color: var(--cyan);
      line-height: 1;
      transition: transform 0.3s ease;
    }
    .launch-ico mat-icon {
      width: 28px;
      height: 28px;
      font-size: 28px;
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
    @keyframes pokerDeal {
      from { opacity: 0; transform: translateY(24px) scale(0.92) rotate(0deg); }
      to { opacity: 1; transform: translateY(0) scale(1) rotate(var(--tilt, 0deg)); }
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
    @keyframes moonFloat {
      0%, 100% { transform: translateY(0); }
      50% { transform: translateY(-5px); }
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

    @media (max-width: 780px) {
      .joker-station { grid-template-columns: 1fr; justify-items: center; }
      .launch-pad { grid-template-columns: 1fr; }
      .coach { grid-template-columns: auto 1fr; }
      .coach .tag { grid-column: 1 / -1; justify-self: start; }
      .play-actions { width: 100%; justify-content: stretch; }
      .play-actions button { flex: 1 1 140px; }
    }
    @media (max-width: 520px) {
      .cyber-card-slot { flex: 0 0 min(84vw, 238px); min-height: 325px; }
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

  readonly barajaCompleta = signal<CartaBaraja[]>(barajarBaraja52());
  readonly shuffleSeed = signal(0);
  readonly heroesPorEscenario = signal<Record<string, PerfilHeroe>>({});
  readonly jokersUsados = signal<Record<string, ResultadoAyudaJoker>>({});

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

  readonly manoActual = computed<CartaBaraja[]>(() => {
    const actual = this.pasoActual();
    if (!actual) return [];
    const inicio = (this.indiceActual() * 5 + this.shuffleSeed() * 7) % 52;
    return repartirManoDesdeBaraja(this.barajaCompleta(), inicio, actual.pregunta.opciones.length);
  });

  readonly cartasEnManoIds = computed<Set<string>>(() => new Set(this.manoActual().map((c) => c.id)));

  readonly heroeActual = computed<PerfilHeroe>(() => {
    const actual = this.pasoActual();
    if (!actual) return CATALOGO_HEROES.captain_america;
    return this.heroesPorEscenario()[actual.escenario.id] ?? CATALOGO_HEROES.captain_america;
  });

  readonly maxJokers = computed<number>(() => (this.pasosPlanos().length >= 3 ? 2 : 1));
  readonly jokersRestantes = computed<number>(() =>
    Math.max(0, this.maxJokers() - Object.keys(this.jokersUsados()).length),
  );
  readonly ayudaJokerActual = computed<ResultadoAyudaJoker | null>(() => {
    const actual = this.pasoActual();
    if (!actual) return null;
    return this.jokersUsados()[actual.pregunta.id] ?? null;
  });

  private timerHandle: ReturnType<typeof setInterval> | null = null;
  private transitionHandle: ReturnType<typeof setTimeout> | null = null;
  private vencimientoAutoEjecutado = false;

  ngOnInit(): void {
    this.idIntento = Number(this.route.snapshot.paramMap.get('id') ?? '0');
    if (this.idIntento) {
      this.participation.recordarIntento(this.idIntento);
      this.restaurarJokersIntento();
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

  cartaDeOpcion(index: number): CartaBaraja {
    const mano = this.manoActual();
    if (mano[index]) return mano[index];
    return this.barajaCompleta()[index % this.barajaCompleta().length];
  }

  manoActualResumen(): string {
    return this.manoActual()
      .map((c) => `${c.rango}${c.simbolo}`)
      .join(' · ') || '—';
  }

  rebarajarBaraja(): void {
    if (this.opcionLanzada() || this.guardando()) return;
    this.barajaCompleta.set(barajarBaraja52());
    this.shuffleSeed.update((s) => s + 1);
  }

  rotarHeroeAleatorio(): void {
    const actual = this.pasoActual();
    if (!actual) return;
    const tema = this.resolverTemaPaso(this.workspace()?.caso_nombre ?? '', actual.escenario, actual.pregunta);
    const actualHeroe = this.heroesPorEscenario()[actual.escenario.id];
    const nuevo = elegirHeroeAleatorio(tema, actualHeroe?.id);
    this.heroesPorEscenario.update((prev) => ({
      ...prev,
      [actual.escenario.id]: nuevo,
    }));
  }

  activarJoker(): void {
    const actual = this.pasoActual();
    if (!actual || this.ayudaJokerActual() || this.jokersRestantes() <= 0 || this.opcionLanzada() || this.guardando()) {
      return;
    }
    const ayuda = construirAyudaJoker({
      tema: this.escenarioTema(),
      contextoTexto: actual.escenario.contexto_situacional,
      preguntaTexto: actual.pregunta.enunciado,
      opciones: actual.pregunta.opciones,
      heroe: this.heroeActual(),
    });
    this.jokersUsados.update((prev) => {
      const next = { ...prev, [actual.pregunta.id]: ayuda };
      this.guardarJokersIntento(next);
      return next;
    });
    this.snack.open('Comodín JOKER activado: lectura táctica aplicada.', 'OK', { duration: 2400 });
  }

  private restaurarJokersIntento(): void {
    try {
      const raw = sessionStorage.getItem(`sps.joker.${this.idIntento}`);
      if (raw) {
        const parsed = JSON.parse(raw) as Record<string, ResultadoAyudaJoker>;
        this.jokersUsados.set(parsed);
      }
    } catch {
      // Ignorar almacenamiento bloqueado
    }
  }

  private guardarJokersIntento(data: Record<string, ResultadoAyudaJoker>): void {
    try {
      sessionStorage.setItem(`sps.joker.${this.idIntento}`, JSON.stringify(data));
    } catch {
      // Ignorar almacenamiento bloqueado
    }
  }

  private asignarHeroesEscenarios(ws: WorkspaceIntento): void {
    const escenarios = ws.escenarios ?? [];
    if (!escenarios.length) return;
    const actuales = { ...this.heroesPorEscenario() };
    let cambio = false;
    for (const esc of escenarios) {
      if (!actuales[esc.id]) {
        const tema = this.resolverTemaPaso(ws.caso_nombre ?? '', esc, esc.preguntas[0]);
        actuales[esc.id] = elegirHeroeAleatorio(tema);
        cambio = true;
      }
    }
    if (cambio) {
      this.heroesPorEscenario.set(actuales);
    }
  }

  private resolverTemaPaso(
    casoNombre: string,
    escenario: EscenarioWorkspace,
    pregunta?: PreguntaWorkspace,
  ): TemaEscena {
    const raw = `${casoNombre} ${escenario.contexto_situacional} ${pregunta?.enunciado ?? ''}`
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
    const temas: TemaEscena[] = ['tribunal_comite', 'entrevista_clinica', 'proteccion_riesgo', 'red_ciudad'];
    return temas[(escenario.orden - 1) % temas.length];
  }

  escenarioTema(): TemaEscena {
    const actual = this.pasoActual();
    const ws = this.workspace();
    if (!actual) return 'red_ciudad';
    return this.resolverTemaPaso(ws?.caso_nombre ?? '', actual.escenario, actual.pregunta);
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
    const carta = this.cartaDeOpcion(Math.max(0, idx));
    return `${carta.rango}${carta.simbolo} // ${carta.arquetipo}`;
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
        this.asignarHeroesEscenarios(ws);
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
    this.snack.open('Tiempo máximo agotado. Cerrando intento y calculando resultado...', 'OK', { duration: 4000 });
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
          eyebrow: 'Entrega Parcial',
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
          eyebrow: 'Entrega Definitiva',
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
