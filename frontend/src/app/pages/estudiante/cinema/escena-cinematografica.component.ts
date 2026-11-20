import { CommonModule, isPlatformBrowser } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  EventEmitter,
  Input,
  NgZone,
  OnChanges,
  OnDestroy,
  OnInit,
  Output,
  PLATFORM_ID,
  SimpleChanges,
  ViewChild,
  computed,
  inject,
  signal,
} from '@angular/core';
import { MatIconModule } from '@angular/material/icon';
import {
  ResultadoDireccionEscena,
  resolverDireccionEscena,
} from './cinema-director';
import { ModoCamara, PerfilHeroe, PlanoCamara, TemaEscena } from './cinema.types';
import { EscenarioDecoradosComponent } from './escenario-decorados.component';
import { HeroeCineComponent } from './heroe-cine.component';
import { PersonajeActorComponent } from './personaje-actor.component';

@Component({
  selector: 'app-escena-cinematografica',
  standalone: true,
  imports: [
    CommonModule,
    MatIconModule,
    EscenarioDecoradosComponent,
    HeroeCineComponent,
    PersonajeActorComponent,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section
      class="panel cinema-frame"
      [class.is-armed]="opcionArmadaSig()"
      [class.is-decision]="opcionLanzadaSig()"
      [class.is-transitioning]="transicionando"
      [class.plano-primer-plano]="planoActivo() === 'primer_plano' || planoActivo() === 'decision'"
    >
      <!-- Cabecera técnica de dirección visual -->
      <header class="cinema-hud">
        <div class="cinema-meta">
          <span class="scene-chip">
            <mat-icon class="chip-ico" aria-hidden="true">movie</mat-icon>
            ESCENA {{ escenaOrdenSig() }}
          </span>
          <span class="theme-chip">{{ etiquetaTema }}</span>
          @if (heroeSig(); as h) {
            <span class="hero-chip" [class.hero-dc]="h.universo === 'DC'" [title]="h.valorPsicosocial">
              <mat-icon class="chip-ico" aria-hidden="true">bolt</mat-icon>
              {{ h.universo }} · {{ h.nombre }}
            </span>
            <button
              type="button"
              class="hero-reroll-btn"
              (click)="cambiarHeroe.emit()"
              title="Cambiar aleatoriamente a otro superhéroe compatible con este contexto"
            >
              <mat-icon aria-hidden="true">casino</mat-icon>
              <span>Héroe</span>
            </button>
          }
          <span class="subscene-chip">{{ subEscenaEtiqueta() }}</span>
          <span
            class="state-pill"
            [class.state-answered]="yaRespondidaSig()"
            [class.state-armed]="opcionArmadaSig()"
          >
            @if (opcionLanzadaSig()) {
              Decisión registrada
            } @else if (opcionArmadaSig()) {
              Postura lista
            } @else if (yaRespondidaSig()) {
              Respondida
            } @else {
              En curso
            }
          </span>
        </div>

        <div class="camera-controls" role="group" aria-label="Encuadre de cámara">
          <button
            type="button"
            class="cam-btn"
            [class.active]="modoCamara() === 'auto'"
            (click)="setModoCamara('auto')"
            title="Dirección automática según la narrativa"
          >
            <mat-icon aria-hidden="true">videocam</mat-icon>
            <span>Auto</span>
          </button>
          <button
            type="button"
            class="cam-btn"
            [class.active]="modoCamara() === 'general'"
            (click)="setModoCamara('general')"
            title="Plano general de toda la escena"
          >
            General
          </button>
          <button
            type="button"
            class="cam-btn"
            [class.active]="modoCamara() === 'medio'"
            (click)="setModoCamara('medio')"
            title="Plano medio sobre la interacción"
          >
            Medio
          </button>
          <button
            type="button"
            class="cam-btn"
            [class.active]="modoCamara() === 'primer_plano'"
            (click)="setModoCamara('primer_plano')"
            title="Primer plano de reacción"
          >
            Primer plano
          </button>
          <span class="shot-counter">{{ pasoIndice }}/{{ totalEscenas }}</span>
        </div>
      </header>

      <!-- Escenario cinematográfico 2.5D con capas de profundidad y cámara reactiva -->
      <div
        #viewportRef
        class="cinema-viewport"
        role="region"
        [attr.aria-label]="'Escena interactiva: ' + etiquetaTema + '. ' + direccion().subtituloNarrativo"
      >
        <!-- Capa 1: Fondo arquitectónico / atmósfera -->
        <div class="depth-layer layer-bg" [style.transform]="bgTransform()">
          <app-escenario-decorados
            [tema]="temaSig()"
            capa="fondo"
            [opcionArmada]="opcionArmadaSig()"
            [opcionLanzada]="opcionLanzadaSig()"
            [heroe]="heroeSig()"
          />
        </div>

        <!-- Capa 2: Mobiliario intermedio (respaldos de sillas / planos medios) -->
        <div class="depth-layer layer-mid-back" [style.transform]="midTransform()">
          <app-escenario-decorados
            [tema]="temaSig()"
            capa="mobiliario_medio"
            [opcionArmada]="opcionArmadaSig()"
            [opcionLanzada]="opcionLanzadaSig()"
            [heroe]="heroeSig()"
          />
        </div>

        <!-- Capa 3: Elenco actoral articulado en plano principal -->
        <div class="depth-layer layer-cast" [style.transform]="castTransform()">
          @for (actor of direccion().actores; track actor.id) {
            <div
              class="cast-slot"
              [class.cast-slot-protagonist]="actor.esProtagonista"
              [style.left.%]="actor.posicion.xPct"
              [style.bottom.px]="actor.posicion.bottomPx"
              [style.z-index]="actor.posicion.zIndex"
              [style.--actor-scale]="actor.posicion.escala"
            >
              @if (actor.esProtagonista && actor.heroe; as hCine) {
                <app-heroe-cine
                  [heroe]="hCine"
                  [postura]="actor.postura"
                  [mirada]="actor.mirada"
                  [hablando]="!!actor.hablando"
                  [poderActivo]="opcionArmadaSig() || opcionLanzadaSig() || jokerActivo"
                  [retrasoRespiracionMs]="actor.retrasoRespiracionMs ?? 120"
                />
              } @else {
                <app-personaje-actor
                  [nombre]="actor.nombre"
                  [rol]="actor.rol"
                  [pielClara]="actor.pielClara"
                  [pielSombra]="actor.pielSombra"
                  [cabelloColor]="actor.cabelloColor"
                  [cabelloBrillo]="actor.cabelloBrillo"
                  [estiloCabello]="actor.estiloCabello"
                  [vestuario]="actor.vestuario"
                  [colorTraje]="actor.colorTraje"
                  [colorTrajeSombra]="actor.colorTrajeSombra"
                  [colorCamisa]="actor.colorCamisa"
                  [colorCorbata]="actor.colorCorbata"
                  [lentes]="!!actor.lentes"
                  [maduro]="!!actor.maduro"
                  [esProtagonista]="!!actor.esProtagonista"
                  [heroe]="actor.heroe"
                  [poderActivo]="!!actor.esProtagonista && (opcionArmadaSig() || opcionLanzadaSig() || jokerActivo)"
                  [expresion]="actor.expresion"
                  [postura]="actor.postura"
                  [mirada]="actor.mirada"
                  [hablando]="!!actor.hablando"
                  [destacado]="!!actor.destacado"
                  [atenuado]="!!actor.atenuado"
                  [invertido]="!!actor.posicion.invertido"
                  [mostrarEtiqueta]="false"
                  [retrasoRespiracionMs]="actor.retrasoRespiracionMs ?? 0"
                  [retrasoParpadeoMs]="actor.retrasoParpadeoMs ?? 450"
                  [retrasoGestoMs]="actor.retrasoGestoMs ?? 0"
                />
              }
            </div>
          }
        </div>

        <!-- Capa 4: Primer plano de mobiliario (mesa directiva, pupitre, consola) -->
        <div class="depth-layer layer-fg" [style.transform]="fgTransform()">
          <app-escenario-decorados
            [tema]="temaSig()"
            capa="primer_plano"
            [opcionArmada]="opcionArmadaSig()"
            [opcionLanzada]="opcionLanzadaSig()"
            [heroe]="heroeSig()"
          />
        </div>

        <!-- Capa 4B: Etiquetas de elenco sobre el borde del mobiliario (sobre tabla, bajo subtítulo) -->
        <div class="depth-layer layer-badges" [style.transform]="castTransform()" aria-hidden="true">
          @for (actor of direccion().actores; track actor.id) {
            <div
              class="cast-nameplate"
              [class.is-protag]="actor.esProtagonista"
              [class.is-talking]="actor.hablando"
              [class.is-secondary]="!actor.esProtagonista && !actor.hablando && !actor.destacado"
              [style.left.%]="actor.posicion.xPct"
              [style.bottom.px]="actor.posicion.bottomPx + 38"
              [style.z-index]="actor.posicion.zIndex + 20"
            >
              @if (actor.hablando) {
                <span class="plate-bars"><i></i><i></i><i></i></span>
              }
              <span class="plate-text">{{ actor.nombre }}</span>
            </div>
          }
        </div>

        <!-- Capa 5: Viñeta atmosférica, luces dramáticas y matte cinematográfico -->
        <div class="cinema-atmosphere" aria-hidden="true">
          <div class="vignette-overlay"></div>
          <div class="tension-tint" [class.tint-decision]="opcionLanzadaSig()"></div>
          <div class="letterbox-bar top"></div>
          <div class="letterbox-bar bottom"></div>
          <div class="cut-dissolve" [class.active]="transicionando"></div>
        </div>

        <!-- Indicador de plano actual e impacto de decisión -->
        <div class="viewport-badges">
          <span class="plano-badge">
            <mat-icon aria-hidden="true">center_focus_strong</mat-icon>
            {{ etiquetaPlano(planoActivo()) }}
          </span>
          @if (opcionLanzadaSig() && etiquetaImpacto) {
            <span class="impact-banner">{{ etiquetaImpacto }}</span>
          }
        </div>

        <!-- Subtítulo narrativo contextual en la base del cuadro -->
        <div class="narrative-subtitle" [class.is-speaking]="hayHablante()">
          <span class="subtitle-dot" aria-hidden="true"></span>
          <p>{{ direccion().subtituloNarrativo }}</p>
        </div>
      </div>

      <!-- Nota situacional integrada del caso real (sin alterar texto original) -->
      @if (contextoSig()) {
        <div class="scene-context-bar">
          <span class="ctx-lbl">Contexto situacional</span>
          <p class="ctx-text">{{ contextoSig() }}</p>
        </div>
      }
    </section>
  `,
  styles: [`
    :host {
      display: block;
    }

    .cinema-frame {
      position: relative;
      overflow: hidden;
      padding: 14px 16px 16px;
      border: 1px solid rgba(0, 229, 244, 0.22);
      background:
        radial-gradient(circle at 12% 0%, rgba(0, 229, 244, 0.08), transparent 44%),
        radial-gradient(circle at 88% 8%, rgba(255, 184, 0, 0.07), transparent 42%),
        linear-gradient(180deg, rgba(11, 17, 30, 0.96), rgba(7, 11, 20, 0.98));
      transition: border-color 0.35s ease, box-shadow 0.35s ease;
    }

    .cinema-frame.is-armed {
      border-color: rgba(0, 229, 244, 0.45);
      box-shadow: 0 12px 34px rgba(0, 229, 244, 0.14);
    }

    .cinema-frame.is-decision {
      border-color: rgba(0, 232, 148, 0.55);
      box-shadow: 0 14px 36px rgba(0, 232, 148, 0.16);
    }

    /* HUD superior */
    .cinema-hud {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
      margin-bottom: 12px;
    }

    .cinema-meta {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }

    .scene-chip,
    .theme-chip,
    .subscene-chip,
    .state-pill {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      padding: 4px 10px;
      border-radius: 999px;
      font-family: var(--mono, monospace);
      font-size: 0.72rem;
      letter-spacing: 0.04em;
    }

    .scene-chip {
      background: rgba(0, 229, 244, 0.14);
      border: 1px solid rgba(0, 229, 244, 0.34);
      color: var(--cyan, #00e5f4);
      font-weight: 700;
    }

    .chip-ico {
      width: 14px;
      height: 14px;
      font-size: 14px;
    }

    .theme-chip {
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid rgba(255, 255, 255, 0.12);
      color: var(--text, #e2e8f0);
      font-family: var(--body, sans-serif);
      font-weight: 600;
    }

    .subscene-chip {
      background: rgba(255, 184, 0, 0.1);
      border: 1px solid rgba(255, 184, 0, 0.25);
      color: #fcd34d;
    }

    .hero-chip,
    .hero-reroll-btn {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 4px 10px;
      border-radius: 999px;
      font-family: var(--mono, monospace);
      font-size: 0.7rem;
      letter-spacing: 0.04em;
    }

    .hero-chip {
      background: linear-gradient(90deg, rgba(220, 38, 38, 0.24), rgba(0, 229, 255, 0.18));
      border: 1px solid rgba(248, 113, 113, 0.48);
      color: #fecaca;
      font-weight: 700;
    }

    .hero-chip.hero-dc {
      background: linear-gradient(90deg, rgba(37, 99, 235, 0.26), rgba(192, 38, 211, 0.2));
      border-color: rgba(96, 165, 250, 0.5);
      color: #bfdbfe;
    }

    .hero-reroll-btn {
      background: rgba(15, 23, 42, 0.8);
      border: 1px solid rgba(255, 46, 209, 0.35);
      color: #f5d0fe;
      cursor: pointer;
      transition: background 0.2s ease, border-color 0.2s ease;
    }

    .hero-reroll-btn mat-icon {
      width: 13px;
      height: 13px;
      font-size: 13px;
    }

    .hero-reroll-btn:hover {
      background: rgba(255, 46, 209, 0.16);
      border-color: rgba(0, 229, 255, 0.65);
    }

    .state-pill {
      background: rgba(148, 163, 184, 0.12);
      border: 1px solid rgba(148, 163, 184, 0.24);
      color: #cbd5e1;
    }

    .state-pill.state-armed {
      background: rgba(0, 229, 244, 0.14);
      border-color: rgba(0, 229, 244, 0.38);
      color: #67e8f9;
    }

    .state-pill.state-answered {
      background: rgba(0, 232, 148, 0.14);
      border-color: rgba(0, 232, 148, 0.36);
      color: #6ee7b7;
    }

    .camera-controls {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      flex-wrap: wrap;
      padding: 3px;
      border-radius: 10px;
      background: rgba(15, 23, 42, 0.72);
      border: 1px solid rgba(148, 163, 184, 0.18);
    }

    .cam-btn {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      border: 0;
      background: transparent;
      color: #94a3b8;
      font-size: 0.72rem;
      font-weight: 600;
      padding: 4px 8px;
      border-radius: 7px;
      cursor: pointer;
      transition: background 0.2s ease, color 0.2s ease;
    }

    .cam-btn mat-icon {
      width: 14px;
      height: 14px;
      font-size: 14px;
    }

    .cam-btn:hover {
      color: #e2e8f0;
      background: rgba(255, 255, 255, 0.06);
    }

    .cam-btn.active {
      background: rgba(0, 229, 244, 0.2);
      color: #67e8f9;
    }

    .shot-counter {
      padding: 0 8px;
      font-family: var(--mono, monospace);
      font-size: 0.72rem;
      color: #94a3b8;
      border-left: 1px solid rgba(148, 163, 184, 0.2);
    }

    /* Viewport cinematográfico multi-capa */
    .cinema-viewport {
      --cam-drift-x: 0px;
      --cam-drift-y: 0px;
      --stage-actor-mult: 1;
      position: relative;
      height: 415px;
      border-radius: 14px;
      overflow: hidden;
      background: #070b14;
      border: 1px solid rgba(148, 163, 184, 0.18);
      box-shadow: inset 0 0 60px rgba(0, 0, 0, 0.65);
    }

    .depth-layer {
      position: absolute;
      inset: -14px;
      pointer-events: none;
      transform-origin: 50% 56%;
      transition: transform 0.92s cubic-bezier(0.22, 1, 0.36, 1), filter 0.65s ease;
      will-change: transform;
    }

    .layer-bg {
      z-index: 1;
    }

    .layer-mid-back {
      z-index: 3;
    }

    .layer-cast {
      z-index: 10;
      inset: 0;
    }

    .layer-fg {
      z-index: 20;
    }

    .layer-badges {
      z-index: 24;
      inset: 0;
    }

    .cast-nameplate {
      position: absolute;
      transform: translateX(-50%);
      display: inline-flex;
      align-items: center;
      gap: 5px;
      max-width: 138px;
      padding: 2px 8px;
      border-radius: 999px;
      border: 1px solid rgba(148, 163, 184, 0.34);
      background: rgba(7, 11, 20, 0.88);
      color: #cbd5e1;
      font-family: var(--mono, monospace);
      font-size: 9.5px;
      font-weight: 600;
      letter-spacing: 0.4px;
      text-transform: uppercase;
      white-space: nowrap;
      box-shadow: 0 4px 10px rgba(0, 0, 0, 0.55);
      pointer-events: none;
    }

    .cast-nameplate .plate-text {
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .cast-nameplate.is-protag {
      border-color: rgba(0, 229, 244, 0.68);
      color: #a8f8ff;
      background: rgba(4, 22, 34, 0.94);
    }

    .cast-nameplate.is-talking {
      border-color: rgba(255, 184, 0, 0.78);
      color: #fde68a;
    }

    .plate-bars {
      display: inline-flex;
      align-items: flex-end;
      gap: 1.5px;
      height: 8px;
      flex-shrink: 0;
    }

    .plate-bars i {
      width: 2px;
      background: #ffb800;
      border-radius: 1px;
      animation: plateEq 0.45s ease-in-out infinite alternate;
    }

    .plate-bars i:nth-child(2) { animation-delay: 0.14s; }
    .plate-bars i:nth-child(3) { animation-delay: 0.28s; }

    @keyframes plateEq {
      from { height: 2px; }
      to { height: 8px; }
    }

    /* Desenfoque selectivo muy sutil del fondo solo en primer plano */
    .cinema-frame.plano-primer-plano .layer-bg {
      filter: brightness(0.88);
    }

    .cast-slot {
      position: absolute;
      width: 152px;
      height: 198px;
      transform-origin: 50% 100%;
      transform: translateX(-50%) scale(calc(var(--actor-scale, 1) * var(--stage-actor-mult, 1)));
      transition: left 0.7s ease, bottom 0.7s ease, transform 0.7s cubic-bezier(0.22, 1, 0.36, 1);
      pointer-events: none;
    }

    .cast-slot.cast-slot-protagonist {
      width: 184px;
      height: 232px;
    }

    .cinema-atmosphere {
      position: absolute;
      inset: 0;
      z-index: 26;
      pointer-events: none;
    }

    .vignette-overlay {
      position: absolute;
      inset: 0;
      background: radial-gradient(ellipse at center, transparent 54%, rgba(3, 6, 14, 0.64) 100%);
    }

    .tension-tint {
      position: absolute;
      inset: 0;
      background: radial-gradient(circle at 50% 35%, rgba(0, 229, 244, 0.05), transparent 60%);
      opacity: 0.8;
      transition: background 0.5s ease, opacity 0.5s ease;
    }

    .tension-tint.tint-decision {
      background: radial-gradient(circle at 50% 45%, rgba(0, 232, 148, 0.16), transparent 64%);
      opacity: 1;
    }

    .letterbox-bar {
      position: absolute;
      left: 0;
      right: 0;
      height: 10px;
      background: rgba(4, 7, 13, 0.92);
      transition: height 0.6s cubic-bezier(0.22, 1, 0.36, 1);
    }

    .letterbox-bar.top {
      top: 0;
    }

    .letterbox-bar.bottom {
      bottom: 0;
    }

    .cinema-frame.plano-primer-plano .letterbox-bar {
      height: 16px;
    }

    .cut-dissolve {
      position: absolute;
      inset: 0;
      background: #050810;
      opacity: 0;
      transition: opacity 0.24s ease;
    }

    .cut-dissolve.active {
      opacity: 0.78;
    }

    .viewport-badges {
      position: absolute;
      top: 22px;
      left: 16px;
      right: 16px;
      z-index: 30;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
      pointer-events: none;
    }

    .plano-badge {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      padding: 4px 9px;
      border-radius: 6px;
      background: rgba(7, 11, 20, 0.72);
      border: 1px solid rgba(148, 163, 184, 0.26);
      color: #cbd5e1;
      font-family: var(--mono, monospace);
      font-size: 0.68rem;
      backdrop-filter: blur(6px);
    }

    .plano-badge mat-icon {
      width: 13px;
      height: 13px;
      font-size: 13px;
      color: var(--cyan, #00e5f4);
    }

    .impact-banner {
      padding: 5px 12px;
      border-radius: 8px;
      background: rgba(0, 232, 148, 0.22);
      border: 1px solid rgba(0, 232, 148, 0.62);
      color: #a7f3d0;
      font-family: var(--mono, monospace);
      font-size: 0.74rem;
      font-weight: 700;
      letter-spacing: 0.04em;
      backdrop-filter: blur(8px);
      animation: impactPop 0.42s cubic-bezier(0.22, 1, 0.36, 1);
    }

    .narrative-subtitle {
      position: absolute;
      left: 18px;
      right: 18px;
      bottom: 22px;
      z-index: 32;
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 9px 14px;
      border-radius: 10px;
      background: rgba(5, 9, 18, 0.78);
      border: 1px solid rgba(148, 163, 184, 0.24);
      backdrop-filter: blur(8px);
      pointer-events: none;
    }

    .narrative-subtitle p {
      margin: 0;
      font-size: 0.84rem;
      line-height: 1.38;
      color: #f1f5f9;
      text-shadow: 0 1px 4px rgba(0, 0, 0, 0.85);
    }

    .subtitle-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      flex-shrink: 0;
      background: #64748b;
    }

    .narrative-subtitle.is-speaking .subtitle-dot {
      background: #00e5f4;
      box-shadow: 0 0 10px rgba(0, 229, 244, 0.9);
    }

    /* Bloque de contexto situacional bajo la toma */
    .scene-context-bar {
      margin-top: 12px;
      padding: 11px 14px;
      border-radius: 10px;
      background: rgba(15, 23, 42, 0.56);
      border: 1px solid rgba(148, 163, 184, 0.16);
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .ctx-lbl {
      font-family: var(--mono, monospace);
      font-size: 0.68rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--cyan, #00e5f4);
      font-weight: 700;
    }

    .ctx-text {
      margin: 0;
      font-size: 0.88rem;
      line-height: 1.5;
      color: var(--text, #e2e8f0);
    }

    @keyframes impactPop {
      from { opacity: 0; transform: translateY(-6px) scale(0.95); }
      to { opacity: 1; transform: translateY(0) scale(1); }
    }

    /* Responsividad para tablets y móviles */
    @media (max-width: 960px) {
      .cinema-viewport {
        --stage-actor-mult: 0.86;
        height: 330px;
      }
      .cast-slot {
        margin-bottom: -8px;
      }
    }

    @media (max-width: 640px) {
      .cinema-frame {
        padding: 10px 10px 12px;
      }
      .cinema-viewport {
        --stage-actor-mult: 0.72;
        height: 276px;
      }
      .cast-slot {
        margin-bottom: -16px;
      }
      .cast-nameplate.is-secondary {
        display: none;
      }
      .cast-nameplate {
        transform: translateX(-50%) translateY(14px) scale(0.9);
      }
      .narrative-subtitle {
        left: 10px;
        right: 10px;
        bottom: 18px;
        padding: 7px 10px;
      }
      .narrative-subtitle p {
        font-size: 0.76rem;
      }
      .camera-controls {
        width: 100%;
        justify-content: space-between;
      }
    }

    @media (prefers-reduced-motion: reduce) {
      .depth-layer,
      .cast-slot,
      .letterbox-bar,
      .cut-dissolve {
        transition: none !important;
      }
      .impact-banner {
        animation: none !important;
      }
    }
  `],
})
export class EscenaCinematograficaComponent implements OnInit, OnChanges, OnDestroy {
  private readonly ngZone = inject(NgZone);
  private readonly platformId = inject(PLATFORM_ID);

  @ViewChild('viewportRef', { static: false })
  private viewportRef?: ElementRef<HTMLDivElement>;

  @Input() tema: TemaEscena = 'tribunal_comite';
  @Input() escenaOrden = 1;
  @Input() totalEscenas = 1;
  @Input() pasoIndice = 1;
  @Input() etiquetaTema = 'Comité Institucional';
  @Input() contextoSituacional = '';
  @Input() preguntaEnunciado = '';
  @Input() yaRespondida = false;
  @Input() opcionArmada = false;
  @Input() opcionLanzada = false;
  @Input() etiquetaImpacto = '';
  @Input() transicionando = false;
  @Input() heroe?: PerfilHeroe;
  @Input() jokerActivo = false;

  @Output() cambiarHeroe = new EventEmitter<void>();

  readonly temaSig = signal<TemaEscena>('tribunal_comite');
  readonly escenaOrdenSig = signal<number>(1);
  readonly contextoSig = signal<string>('');
  readonly preguntaSig = signal<string>('');
  readonly yaRespondidaSig = signal<boolean>(false);
  readonly opcionArmadaSig = signal<boolean>(false);
  readonly opcionLanzadaSig = signal<boolean>(false);
  readonly heroeSig = signal<PerfilHeroe | undefined>(undefined);

  readonly modoCamara = signal<ModoCamara>('auto');
  readonly faseNarrativa = signal<number>(0);

  private timerFaseInicial: ReturnType<typeof setTimeout> | null = null;
  private timerFaseCiclo: ReturnType<typeof setInterval> | null = null;
  private rafCamId: number | null = null;
  private reducedMotion = false;

  readonly direccion = computed<ResultadoDireccionEscena>(() =>
    resolverDireccionEscena({
      tema: this.temaSig(),
      escenaOrden: this.escenaOrdenSig(),
      contextoTexto: this.contextoSig(),
      preguntaTexto: this.preguntaSig(),
      opcionArmada: this.opcionArmadaSig(),
      opcionLanzada: this.opcionLanzadaSig(),
      yaRespondida: this.yaRespondidaSig(),
      faseNarrativa: this.faseNarrativa(),
      heroe: this.heroeSig(),
    }),
  );

  readonly planoActivo = computed<PlanoCamara>(() => {
    const modo = this.modoCamara();
    if (modo === 'auto') {
      return this.direccion().planoSugerido;
    }
    return modo;
  });

  readonly hayHablante = computed<boolean>(() =>
    this.direccion().actores.some((a) => !!a.hablando),
  );

  readonly subEscenaEtiqueta = computed<string>(() => {
    switch (this.direccion().subEscena) {
      case 'VOTACION_MAYORIA_4_1':
        return 'Votación en pleno · 4:1';
      case 'INSISTENCIA_DECANO':
        return 'Presión de Decanatura';
      case 'ORDEN_LABORATORIO':
        return 'Protocolo Experimental';
      case 'CRISIS_URGENCIAS':
        return 'Sala de Urgencias';
      case 'ENTREVISTA_CLINICA':
        return 'Consultorio Clínico';
      case 'RESGUARDO_RIESGO':
        return 'Protocolo de Resguardo';
      default:
        return 'Mesa Interinstitucional';
    }
  });

  private readonly encuadre = computed(() => {
    const dir = this.direccion();
    const plano = this.planoActivo();
    if (plano === 'general') {
      return { scale: 1.02, panX: 0, panY: 0 };
    }
    if (plano === 'medio') {
      return {
        scale: dir.zoomMedio,
        panX: dir.focoX * 0.65,
        panY: dir.focoY * 0.65,
      };
    }
    if (plano === 'decision') {
      return {
        scale: Math.max(1.2, dir.zoomPrimerPlano - 0.05),
        panX: dir.focoX * 0.85,
        panY: dir.focoY,
      };
    }
    // primer_plano
    return {
      scale: dir.zoomPrimerPlano,
      panX: dir.focoX,
      panY: dir.focoY,
    };
  });

  readonly bgTransform = computed(() => {
    const { scale, panX, panY } = this.encuadre();
    const bgScale = 1 + (scale - 1) * 0.48;
    const x = panX * 0.42;
    const y = panY * 0.42;
    return `translate3d(calc(${x}% + var(--cam-drift-x) * 0.45), calc(${y}% + var(--cam-drift-y) * 0.45), 0) scale(${bgScale})`;
  });

  readonly midTransform = computed(() => {
    const { scale, panX, panY } = this.encuadre();
    const midScale = 1 + (scale - 1) * 0.76;
    const x = panX * 0.78;
    const y = panY * 0.78;
    return `translate3d(calc(${x}% + var(--cam-drift-x) * 0.75), calc(${y}% + var(--cam-drift-y) * 0.75), 0) scale(${midScale})`;
  });

  readonly castTransform = computed(() => {
    const { scale, panX, panY } = this.encuadre();
    return `translate3d(calc(${panX}% + var(--cam-drift-x)), calc(${panY}% + var(--cam-drift-y)), 0) scale(${scale})`;
  });

  readonly fgTransform = computed(() => {
    const { scale, panX, panY } = this.encuadre();
    const fgScale = 1 + (scale - 1) * 1.12;
    const x = panX * 1.15;
    const y = panY * 1.15;
    return `translate3d(calc(${x}% + var(--cam-drift-x) * 1.2), calc(${y}% + var(--cam-drift-y) * 1.2), 0) scale(${fgScale})`;
  });

  ngOnInit(): void {
    this.sincronizarInputsASignals();
    if (isPlatformBrowser(this.platformId)) {
      this.reducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;
      this.iniciarMotorCamaraOrganica();
    }
    this.reiniciarRitmoNarrativo();
  }

  ngOnChanges(changes: SimpleChanges): void {
    this.sincronizarInputsASignals();
    if (
      changes['tema'] ||
      changes['escenaOrden'] ||
      changes['preguntaEnunciado'] ||
      changes['contextoSituacional']
    ) {
      this.reiniciarRitmoNarrativo();
    }
  }

  ngOnDestroy(): void {
    this.limpiarTimersNarrativos();
    if (this.rafCamId !== null && isPlatformBrowser(this.platformId)) {
      cancelAnimationFrame(this.rafCamId);
      this.rafCamId = null;
    }
  }

  setModoCamara(modo: ModoCamara): void {
    this.modoCamara.set(modo);
  }

  etiquetaPlano(plano: PlanoCamara): string {
    switch (plano) {
      case 'general':
        return 'PLANO GENERAL';
      case 'medio':
        return 'PLANO MEDIO';
      case 'primer_plano':
        return 'PRIMER PLANO';
      case 'decision':
        return 'REACCIÓN · DECISIÓN';
    }
  }

  private sincronizarInputsASignals(): void {
    this.temaSig.set(this.tema);
    this.escenaOrdenSig.set(this.escenaOrden);
    this.contextoSig.set(this.contextoSituacional || '');
    this.preguntaSig.set(this.preguntaEnunciado || '');
    this.yaRespondidaSig.set(!!this.yaRespondida);
    this.opcionArmadaSig.set(!!this.opcionArmada);
    this.opcionLanzadaSig.set(!!this.opcionLanzada);
    this.heroeSig.set(this.heroe);
  }

  private limpiarTimersNarrativos(): void {
    if (this.timerFaseInicial !== null) {
      clearTimeout(this.timerFaseInicial);
      this.timerFaseInicial = null;
    }
    if (this.timerFaseCiclo !== null) {
      clearInterval(this.timerFaseCiclo);
      this.timerFaseCiclo = null;
    }
  }

  private reiniciarRitmoNarrativo(): void {
    this.limpiarTimersNarrativos();
    this.faseNarrativa.set(0);

    if (this.reducedMotion || !isPlatformBrowser(this.platformId)) {
      this.faseNarrativa.set(1);
      return;
    }

    // Plano general inicial para situar el espacio antes de acercar al conflicto
    this.timerFaseInicial = setTimeout(() => {
      this.faseNarrativa.set(1);
    }, 1800);

    // Alternancia sutil de foco observacional entre interlocutores mientras decide
    this.timerFaseCiclo = setInterval(() => {
      if (!this.opcionArmadaSig() && !this.opcionLanzadaSig()) {
        this.faseNarrativa.update((prev) => (prev === 1 ? 2 : 1));
      }
    }, 4400);
  }

  private iniciarMotorCamaraOrganica(): void {
    if (this.reducedMotion || this.rafCamId !== null) {
      return;
    }
    this.ngZone.runOutsideAngular(() => {
      const inicio = performance.now();
      const tick = (ahora: number) => {
        const el = this.viewportRef?.nativeElement;
        if (el) {
          const dt = ahora - inicio;
          const dx = Math.sin(dt * 0.00058) * 2.1;
          const dy = Math.cos(dt * 0.00043) * 1.1;
          el.style.setProperty('--cam-drift-x', `${dx.toFixed(2)}px`);
          el.style.setProperty('--cam-drift-y', `${dy.toFixed(2)}px`);
        }
        this.rafCamId = requestAnimationFrame(tick);
      };
      this.rafCamId = requestAnimationFrame(tick);
    });
  }
}
