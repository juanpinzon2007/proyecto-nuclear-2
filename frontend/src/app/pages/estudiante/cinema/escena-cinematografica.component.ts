import { CommonModule, isPlatformBrowser } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  EventEmitter,
  Input,
  OnChanges,
  OnDestroy,
  OnInit,
  Output,
  PLATFORM_ID,
  SimpleChanges,
  computed,
  inject,
  signal,
} from '@angular/core';
import { MatIconModule } from '@angular/material/icon';
import {
  ResultadoDireccionEscena,
  resolverDireccionEscena,
} from './cinema-director';
import { asignarReparto } from './cinema-heroes';
import { ModoCamara, PerfilHeroe, PlanoCamara, TemaEscena } from './cinema.types';
import { EscenarioDecoradosComponent } from './escenario-decorados.component';
import { HeroeCineComponent } from './heroe-cine.component';

@Component({
  selector: 'app-escena-cinematografica',
  standalone: true,
  imports: [
    CommonModule,
    MatIconModule,
    EscenarioDecoradosComponent,
    HeroeCineComponent,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @let subEscena = direccion().subEscena;
    <section
      class="panel cinema-frame"
      [class.is-armed]="opcionArmadaSig()"
      [class.is-decision]="opcionLanzadaSig()"
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
            <span class="hero-chip" [style.--hero-accent]="h.colorEnergia" [title]="h.valorPsicosocial">
              <mat-icon class="chip-ico" aria-hidden="true">bolt</mat-icon>
              {{ h.nombre }}
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
        class="cinema-viewport"
        role="region"
        [attr.data-set]="subEscena"
        [attr.data-cast-size]="reparto().length"
        [attr.aria-label]="'Escena interactiva: ' + subEscenaEtiqueta()"
      >
        <!-- Capa 1: Fondo arquitectónico / atmósfera -->
        <div class="depth-layer layer-bg" [style.transform]="bgTransform()">
          <app-escenario-decorados
            [subEscena]="subEscena"
            capa="fondo"
            [opcionArmada]="opcionArmadaSig()"
            [opcionLanzada]="opcionLanzadaSig()"
            [heroe]="heroeSig()"
          />
        </div>

        <!-- Capa 2: Mobiliario intermedio (respaldos de sillas / planos medios) -->
        <div class="depth-layer layer-mid-back" [style.transform]="midTransform()">
          <app-escenario-decorados
            [subEscena]="subEscena"
            capa="mobiliario_medio"
            [opcionArmada]="opcionArmadaSig()"
            [opcionLanzada]="opcionLanzadaSig()"
            [heroe]="heroeSig()"
          />
        </div>

        <!-- Capa 3: Elenco actoral articulado en plano principal -->
        <div class="depth-layer layer-cast" [style.transform]="castTransform()">
          @for (actor of reparto(); track actor.id) {
            <div
              class="cast-slot"
              [style.left.%]="actor.posicion.xPct"
              [style.z-index]="actor.posicion.zIndex"
            >
              <app-heroe-cine
                [heroe]="actor.heroe"
                [etiqueta]="actor.esProtagonista ? 'Tú' : actor.nombre + ', ' + actor.rol"
                [postura]="actor.postura"
                [mirada]="actor.mirada"
                [hablando]="!!actor.hablando"
                [poderActivo]="!!actor.esProtagonista && (opcionArmadaSig() || opcionLanzadaSig() || jokerActivo)"
                [retrasoRespiracionMs]="actor.retrasoRespiracionMs ?? 120"
                [retrasoGestoMs]="actor.retrasoGestoMs ?? 0"
              />
            </div>
          }
        </div>

        <!-- Capa 4: Primer plano de mobiliario (mesa directiva, pupitre, consola) -->
        <div class="depth-layer layer-fg" [style.transform]="fgTransform()">
          <app-escenario-decorados
            [subEscena]="subEscena"
            capa="primer_plano"
            [opcionArmada]="opcionArmadaSig()"
            [opcionLanzada]="opcionLanzadaSig()"
            [heroe]="heroeSig()"
          />
        </div>

        <!-- Capa 4B: Etiquetas de elenco sobre el borde del mobiliario (sobre tabla, bajo subtítulo) -->
        <div class="depth-layer layer-badges" [style.transform]="castTransform()" aria-hidden="true">
          @for (actor of reparto(); track actor.id) {
            <div
              class="cast-nameplate"
              [class.is-protag]="actor.esProtagonista"
              [class.is-talking]="actor.hablando"
              [style.left.%]="actor.posicion.xPct"
              [style.--cast-accent]="actor.heroe.colorEnergia"
              [style.z-index]="actor.posicion.zIndex + 20"
            >
              @if (actor.hablando) {
                <span class="plate-bars"><i></i><i></i><i></i></span>
              }
              <span class="plate-text">
                <strong>{{ actor.heroe.nombre }}</strong>
                <small>{{ actor.esProtagonista ? 'Tú' : actor.nombre }}</small>
              </span>
            </div>
          }
        </div>

        <!-- Capa 5: Viñeta atmosférica, luces dramáticas y matte cinematográfico -->
        <div class="cinema-atmosphere" aria-hidden="true">
          <div class="vignette-overlay"></div>
          <div class="tension-tint" [class.tint-decision]="opcionLanzadaSig()"></div>
          <div class="letterbox-bar top"></div>
          <div class="letterbox-bar bottom"></div>
          @for (paso of [pasoIndice]; track paso) {
            <div class="cut-dissolve"></div>
          }
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
      border: 1px solid #64dafa63;
      background:
        radial-gradient(circle at 12% 0%, rgba(0, 229, 244, 0.08), transparent 44%),
        radial-gradient(circle at 88% 8%, rgba(255, 184, 0, 0.07), transparent 42%),
        linear-gradient(180deg, rgba(11, 17, 30, 0.96), rgba(7, 11, 20, 0.98));
      box-shadow: inset 0 1px #b2efff25, 0 16px 32px #03071288;
      transition: border-color var(--motion-enter) ease, box-shadow var(--motion-enter) ease;
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
      background: color-mix(in srgb, var(--hero-accent) 18%, #0c1625);
      border: 1px solid color-mix(in srgb, var(--hero-accent) 52%, #22344a);
      color: color-mix(in srgb, var(--hero-accent) 62%, #fff);
      font-weight: 700;
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
      --cast-portrait-size: min(20%, 208px);
      --cast-base: 66px;
      position: relative;
      height: 415px;
      border-radius: 14px;
      overflow: hidden;
      background: #070b14;
      border: 1px solid rgba(148, 163, 184, 0.18);
      box-shadow: inset 0 0 60px rgba(0, 0, 0, 0.65);
    }

    .cinema-viewport::after {
      position: absolute;
      z-index: 28;
      inset: 14px;
      background:
        linear-gradient(#90eafb99, #90eafb99) left top / 21px 1px,
        linear-gradient(#90eafb99, #90eafb99) left top / 1px 13px,
        linear-gradient(#90eafb99, #90eafb99) right top / 21px 1px,
        linear-gradient(#90eafb99, #90eafb99) right top / 1px 13px;
      background-repeat: no-repeat;
      pointer-events: none;
      content: '';
    }

    .depth-layer {
      position: absolute;
      inset: -14px;
      pointer-events: none;
      transform-origin: 50% 56%;
      transition: transform 680ms var(--motion-decelerate), filter 400ms ease;
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
      bottom: var(--cast-base);
      transform: translateX(-50%);
      display: inline-flex;
      align-items: center;
      gap: 5px;
      width: max-content;
      max-width: min(146px, 18%);
      padding: 5px 9px;
      border-radius: 5px;
      border: 1px solid color-mix(in srgb, var(--cast-accent) 42%, #263044);
      border-top: 2px solid var(--cast-accent);
      background: linear-gradient(180deg, #111c2c, #080e19);
      color: #f1f5f9;
      font-family: var(--mono, monospace);
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 0.25px;
      white-space: nowrap;
      box-shadow: 0 4px 10px rgba(0, 0, 0, 0.55);
      pointer-events: none;
    }

    .cast-nameplate .plate-text {
      display: grid;
      gap: 1px;
      min-width: 0;
    }

    .plate-text strong,
    .plate-text small {
      overflow: hidden;
      text-overflow: ellipsis;
      line-height: 1.15;
    }

    .plate-text strong {
      color: color-mix(in srgb, var(--cast-accent) 55%, #fff);
    }

    .plate-text small {
      font-size: 0.84em;
      color: #cbd5e1;
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
      height: 8px;
      background: #ffb800;
      border-radius: 1px;
      transform-origin: bottom;
      animation: plateEq 0.45s ease-in-out infinite alternate;
    }

    .plate-bars i:nth-child(2) { animation-delay: 0.14s; }
    .plate-bars i:nth-child(3) { animation-delay: 0.28s; }

    @keyframes plateEq {
      from { transform: scaleY(0.25); }
      to { transform: scaleY(1); }
    }

    /* Desenfoque selectivo muy sutil del fondo solo en primer plano */
    .cinema-frame.plano-primer-plano .layer-bg {
      filter: brightness(0.88);
    }

    .cast-slot {
      position: absolute;
      bottom: var(--cast-base);
      width: var(--cast-portrait-size);
      aspect-ratio: 1;
      transform: translateX(-50%);
      pointer-events: none;
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
      background: radial-gradient(circle at 50% 45%, rgba(0, 232, 148, 0.16), transparent 64%);
      opacity: 0;
      transition: opacity 380ms ease;
    }

    .tension-tint.tint-decision {
      opacity: 1;
    }
    .tension-tint.tint-decision::after {
      position: absolute;
      inset: 0;
      background: linear-gradient(115deg, transparent 25%, #78ffd23d, transparent 72%);
      opacity: 0;
      content: '';
      animation: decision-light 620ms var(--motion-decelerate);
    }
    @keyframes decision-light {
      0% { opacity: 0; transform: translateX(-45%); }
      28% { opacity: 0.85; }
      100% { opacity: 0; transform: translateX(45%); }
    }

    .letterbox-bar {
      position: absolute;
      left: 0;
      right: 0;
      height: 16px;
      background: rgba(4, 7, 13, 0.92);
      transform: scaleY(0.625);
      transition: transform 520ms var(--motion-decelerate);
    }

    .letterbox-bar.top {
      top: 0;
      transform-origin: top;
    }

    .letterbox-bar.bottom {
      bottom: 0;
      transform-origin: bottom;
    }

    .cinema-frame.plano-primer-plano .letterbox-bar {
      transform: scaleY(1);
    }

    .cut-dissolve {
      position: absolute;
      inset: 0;
      background: #050810;
      opacity: 0;
      animation: revealScene 440ms var(--motion-decelerate);
    }

    @keyframes revealScene {
      from { opacity: 0.58; }
      to { opacity: 0; }
    }

    [data-set='INSISTENCIA_DECANO'] .cut-dissolve {
      background: linear-gradient(90deg, #25151e 18%, #5b3627 55%, transparent 100%);
      animation: officeCut 740ms var(--motion-decelerate);
    }

    [data-set='ORDEN_LABORATORIO'] .cut-dissolve,
    [data-set='RESGUARDO_RIESGO'] .cut-dissolve {
      background: linear-gradient(180deg, transparent 36%, #2ceec34d 49%, #0c252e 53%, transparent 68%);
      animation: scanCut 680ms ease-out;
    }

    [data-set='CRISIS_URGENCIAS'] .cut-dissolve {
      background: linear-gradient(90deg, #0d4f76, transparent 38% 62%, #123954);
      animation: emergencyCut 620ms ease-out;
    }

    @keyframes officeCut {
      from { opacity: 0.88; transform: translateX(0); }
      to { opacity: 0; transform: translateX(-65%); }
    }

    @keyframes scanCut {
      0% { opacity: 0; transform: translateY(-54%); }
      20% { opacity: 0.85; }
      100% { opacity: 0; transform: translateY(54%); }
    }

    @keyframes emergencyCut {
      from { opacity: 0.8; transform: scaleX(0.85); }
      to { opacity: 0; transform: scaleX(1.18); }
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
        --cast-portrait-size: min(21%, 176px);
        --cast-base: 59px;
        height: 330px;
      }
    }

    @media (max-width: 640px) {
      .cinema-frame {
        padding: 10px 10px 12px;
      }
      .cinema-viewport {
        --cast-portrait-size: min(24%, 148px);
        --cast-base: 64px;
        height: clamp(220px, 62vw, 306px);
      }
      .cast-nameplate {
        bottom: calc(var(--cast-base) + 9px);
        padding: 3px 4px;
        font-size: 9px;
        text-align: center;
        white-space: normal;
      }
      [data-cast-size='5'] .cast-nameplate {
        max-width: 15.5%;
      }
      .cast-nameplate .plate-text small,
      .cast-nameplate .plate-bars {
        display: none;
      }
      .cast-nameplate .plate-text strong {
        overflow-wrap: anywhere;
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
      .letterbox-bar,
      .tension-tint {
        transition: none;
      }
      .cinema-viewport .cut-dissolve,
      .plate-bars i,
      .tension-tint.tint-decision::after,
      .impact-banner {
        animation: none !important;
      }
    }
  `],
})
export class EscenaCinematograficaComponent implements OnInit, OnChanges, OnDestroy {
  private readonly platformId = inject(PLATFORM_ID);

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
  private motionPreference?: MediaQueryList;
  private readonly onMotionPreferenceChange = () => this.reiniciarRitmoNarrativo();

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

  readonly reparto = computed(() =>
    asignarReparto(this.direccion().actores, this.temaSig(), this.escenaOrdenSig(), this.heroeSig()),
  );

  readonly subEscenaEtiqueta = computed<string>(() => {
    switch (this.direccion().subEscena) {
      case 'VOTACION_MAYORIA_4_1':
        return 'Votación en pleno · 4:1';
      case 'INSISTENCIA_DECANO':
        return 'Despacho de Decanatura';
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
      return { scale: 1, panX: 0, panY: 0 };
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
    return `translate3d(${x}%, ${y}%, 0) scale(${bgScale})`;
  });

  readonly midTransform = computed(() => {
    const { scale, panX, panY } = this.encuadre();
    const midScale = 1 + (scale - 1) * 0.76;
    const x = panX * 0.78;
    const y = panY * 0.78;
    return `translate3d(${x}%, ${y}%, 0) scale(${midScale})`;
  });

  readonly castTransform = computed(() => {
    const { scale, panX, panY } = this.encuadre();
    return `translate3d(${panX}%, ${panY}%, 0) scale(${scale})`;
  });

  readonly fgTransform = computed(() => {
    const { scale, panX, panY } = this.encuadre();
    const fgScale = 1 + (scale - 1) * 1.12;
    const x = panX * 1.15;
    const y = panY * 1.15;
    return `translate3d(${x}%, ${y}%, 0) scale(${fgScale})`;
  });

  ngOnInit(): void {
    this.sincronizarInputsASignals();
    if (isPlatformBrowser(this.platformId)) {
      this.motionPreference = window.matchMedia('(prefers-reduced-motion: reduce)');
      this.motionPreference.addEventListener('change', this.onMotionPreferenceChange);
    }
    this.reiniciarRitmoNarrativo();
  }

  ngOnChanges(changes: SimpleChanges): void {
    this.sincronizarInputsASignals();
    if (
      changes['tema'] ||
      changes['pasoIndice'] ||
      changes['escenaOrden'] ||
      changes['preguntaEnunciado'] ||
      changes['contextoSituacional']
    ) {
      this.reiniciarRitmoNarrativo();
    }
  }

  ngOnDestroy(): void {
    this.limpiarTimersNarrativos();
    this.motionPreference?.removeEventListener('change', this.onMotionPreferenceChange);
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
    if (this.motionPreference?.matches || !isPlatformBrowser(this.platformId)) {
      this.faseNarrativa.set(1);
      return;
    }
    this.faseNarrativa.set(0);

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
}
