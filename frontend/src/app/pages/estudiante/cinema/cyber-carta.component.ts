import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, Input } from '@angular/core';
import { PaloSimbolo } from './poker-deck';

let siguienteIdCarta = 0;

@Component({
  selector: 'app-cyber-carta',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div
      class="cyber-card-shell"
      [class.is-joker]="esJoker"
      [class.is-selected]="seleccionada"
      [class.is-launched]="lanzada"
      [class.is-risk-flagged]="riesgoJoker"
      [class.tone-red]="esRojo && !esJoker"
      [class.tone-dark]="!esRojo && !esJoker"
    >
      <!-- Halo de reflejo inferior estilo mesa obsidiana -->
      <div class="floor-glow" aria-hidden="true"></div>

      <!-- Chasis metálico SVG de alta precisión (cyan-to-magenta neon edges + micro-vents + emblem) -->
      <svg class="card-chassis-svg" viewBox="0 0 260 360" preserveAspectRatio="none" aria-hidden="true">
        <defs>
          <linearGradient [attr.id]="gradMarco" x1="0%" y1="0%" x2="100%" y2="100%">
            @if (esJoker) {
              <stop offset="0%" stop-color="#fde047" />
              <stop offset="50%" stop-color="#00e5ff" />
              <stop offset="100%" stop-color="#ff2ed1" />
            } @else {
              <stop offset="0%" stop-color="#00e5ff" />
              <stop offset="48%" stop-color="#7c3aed" />
              <stop offset="100%" stop-color="#ff2ed1" />
            }
          </linearGradient>

          <linearGradient [attr.id]="gradObsidiana" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#0d1222" />
            <stop offset="52%" stop-color="#060810" />
            <stop offset="100%" stop-color="#140c22" />
          </linearGradient>

          <radialGradient [attr.id]="gradNebula" cx="50%" cy="46%" r="52%">
            @if (esJoker) {
              <stop offset="0%" stop-color="#fde047" stop-opacity="0.34" />
              <stop offset="55%" stop-color="#ff2ed1" stop-opacity="0.22" />
              <stop offset="100%" stop-color="#060810" stop-opacity="0" />
            } @else if (esRojo) {
              <stop offset="0%" stop-color="#ff3b8d" stop-opacity="0.32" />
              <stop offset="55%" stop-color="#9333ea" stop-opacity="0.22" />
              <stop offset="100%" stop-color="#060810" stop-opacity="0" />
            } @else {
              <stop offset="0%" stop-color="#00e5ff" stop-opacity="0.28" />
              <stop offset="55%" stop-color="#a855f7" stop-opacity="0.22" />
              <stop offset="100%" stop-color="#060810" stop-opacity="0" />
            }
          </radialGradient>

          <linearGradient [attr.id]="gradPaloMetal" x1="0%" y1="0%" x2="100%" y2="100%">
            @if (esJoker) {
              <stop offset="0%" stop-color="#fef08a" />
              <stop offset="45%" stop-color="#00e5ff" />
              <stop offset="100%" stop-color="#f472b6" />
            } @else if (esRojo) {
              <stop offset="0%" stop-color="#ffd1dc" />
              <stop offset="40%" stop-color="#ff2ed1" />
              <stop offset="100%" stop-color="#7e22ce" />
            } @else {
              <stop offset="0%" stop-color="#e0f2fe" />
              <stop offset="45%" stop-color="#38bdf8" />
              <stop offset="100%" stop-color="#c026d3" />
            }
          </linearGradient>
        </defs>

        <!-- Cuerpo oscuro biselado -->
        <rect x="6" y="6" width="248" height="348" rx="18" [attr.fill]="'url(#' + gradObsidiana + ')'" />
        <ellipse cx="130" cy="148" rx="98" ry="112" [attr.fill]="'url(#' + gradNebula + ')'" />

        <!-- Borde neón exterior cyan -> magenta -->
        <rect
          x="6"
          y="6"
          width="248"
          height="348"
          rx="18"
          fill="none"
          [attr.stroke]="'url(#' + gradMarco + ')'"
          stroke-width="2.6"
        />

        <!-- Marco interior biselado metálico con cortes geométricos en esquinas -->
        <polygon
          points="26,16 234,16 244,28 244,332 234,344 26,344 16,332 16,28"
          fill="none"
          stroke="rgba(148,163,184,0.34)"
          stroke-width="1.3"
        />
        <polygon
          points="32,22 228,22 238,32 238,328 228,338 32,338 22,328 22,32"
          fill="none"
          [attr.stroke]="esJoker ? 'rgba(250,204,21,0.4)' : 'rgba(0,229,255,0.22)'"
          stroke-width="1"
        />

        <!-- Eje láser vertical + nodos diamante superior e inferior -->
        <line x1="130" y1="16" x2="130" y2="255" stroke="rgba(0,229,255,0.26)" stroke-width="1" />
        <polygon points="130,30 135,38 130,46 125,38" fill="#e879f9" stroke="#00e5ff" stroke-width="0.9" />
        <polygon points="130,228 135,236 130,244 125,236" fill="#00e5ff" stroke="#ff2ed1" stroke-width="0.9" />

        <!-- Rejillas tech laterales cyan (izquierda) y magenta (derecha) -->
        <g stroke="#00e5ff" stroke-width="2.6" stroke-linecap="round">
          <line x1="11" y1="126" x2="17" y2="122" />
          <line x1="11" y1="136" x2="17" y2="132" />
          <line x1="11" y1="146" x2="17" y2="142" />
        </g>
        <g stroke="#ff2ed1" stroke-width="2.6" stroke-linecap="round">
          <line x1="243" y1="194" x2="249" y2="190" />
          <line x1="243" y1="204" x2="249" y2="200" />
          <line x1="243" y1="214" x2="249" y2="210" />
        </g>
        <g stroke="#00e5ff" stroke-width="2.2" stroke-linecap="round" opacity="0.85">
          <line x1="243" y1="68" x2="249" y2="64" />
          <line x1="243" y1="77" x2="249" y2="73" />
          <line x1="243" y1="86" x2="249" y2="82" />
        </g>

        <!-- Retícula HUD circular central detrás del palo -->
        <g transform="translate(130, 108) scale(0.86)">
          <circle r="68" fill="none" stroke="rgba(0,229,255,0.22)" stroke-width="1" stroke-dasharray="6 4" />
          <circle r="54" fill="none" stroke="rgba(255,46,209,0.28)" stroke-width="1.2" stroke-dasharray="14 6 3 6" />
          <circle r="40" fill="none" stroke="rgba(168,248,255,0.22)" stroke-width="1" />
          <line x1="-82" y1="0" x2="-46" y2="0" stroke="rgba(0,229,255,0.45)" stroke-width="1.1" />
          <line x1="46" y1="0" x2="82" y2="0" stroke="rgba(255,46,209,0.45)" stroke-width="1.1" />

          <!-- Emblema facetado del palo o JOKER central -->
          @if (esJoker) {
            <!-- Corona / Bufón geométrico prismático JOKER -->
            <path
              d="M -38 22 L -44 -14 L -18 4 L 0 -32 L 18 4 L 44 -14 L 38 22 Z"
              [attr.fill]="'url(#' + gradPaloMetal + ')'"
              stroke="#fef08a"
              stroke-width="2"
              stroke-linejoin="round"
            />
            <polygon points="0,-16 11,4 0,20 -11,4" fill="#060810" stroke="#00e5ff" stroke-width="1.5" />
            <circle cx="-44" cy="-16" r="5" fill="#00e5ff" />
            <circle cx="0" cy="-35" r="6" fill="#fde047" />
            <circle cx="44" cy="-16" r="5" fill="#ff2ed1" />
          } @else {
            @switch (simbolo) {
              @case ('♠') {
                <path
                  d="M 0 -46 C -22 -24 -44 -4 -44 15 C -44 30 -30 38 -15 34 C -7 32 -4 28 -2 24 L -12 46 L 12 46 L 2 24 C 4 28 7 32 15 34 C 30 38 44 30 44 15 C 44 -4 22 -24 0 -46 Z"
                  [attr.fill]="'url(#' + gradPaloMetal + ')'"
                  stroke="#e0f2fe"
                  stroke-width="1.8"
                  stroke-linejoin="round"
                />
                <!-- Gema facetada interior -->
                <polygon points="0,-16 10,3 0,18 -10,3" fill="#e0f2fe" stroke="#00e5ff" stroke-width="1.2" opacity="0.92" />
              }
              @case ('♥') {
                <path
                  d="M 0 42 C -18 28 -44 10 -44 -14 C -44 -32 -28 -42 -14 -40 C -5 -38 0 -30 0 -24 C 0 -30 5 -38 14 -40 C 28 -42 44 -32 44 -14 C 44 10 18 28 0 42 Z"
                  [attr.fill]="'url(#' + gradPaloMetal + ')'"
                  stroke="#fbcfe8"
                  stroke-width="1.8"
                  stroke-linejoin="round"
                />
                <polygon points="0,-16 11,-2 0,16 -11,-2" fill="#fdf2f8" stroke="#ff2ed1" stroke-width="1.2" opacity="0.88" />
              }
              @case ('♦') {
                <polygon
                  points="0,-46 38,0 0,46 -38,0"
                  [attr.fill]="'url(#' + gradPaloMetal + ')'"
                  stroke="#fde68a"
                  stroke-width="1.8"
                  stroke-linejoin="round"
                />
                <polygon points="0,-24 18,0 0,24 -18,0" fill="#0b1020" fill-opacity="0.48" stroke="#00e5ff" stroke-width="1.2" />
                <polygon points="0,-11 8,0 0,11 -8,0" fill="#fef08a" opacity="0.9" />
              }
              @default {
                <!-- ♣ Trébol -->
                <g [attr.fill]="'url(#' + gradPaloMetal + ')'" stroke="#bbf7d0" stroke-width="1.6" stroke-linejoin="round">
                  <circle cx="0" cy="-22" r="20" />
                  <circle cx="-22" cy="8" r="19" />
                  <circle cx="22" cy="8" r="19" />
                  <path d="M -5 14 L -13 44 L 13 44 L 5 14 Z" />
                </g>
                <polygon points="0,-10 9,4 0,16 -9,4" fill="#ecfdf5" stroke="#00e5ff" stroke-width="1.2" opacity="0.9" />
              }
            }
          }
        </g>
      </svg>

      <!-- Esquina superior izquierda -->
      <div class="card-corner top-left">
        @if (esJoker) {
          <span class="corner-rank joker-txt">JK</span>
          <span class="corner-suit">★</span>
        } @else {
          <span class="corner-rank">{{ rango }}</span>
          <span class="corner-suit">{{ simbolo }}</span>
          @if (etiquetaSuperior) {
            <span class="corner-sub">{{ etiquetaSuperior }}</span>
          }
        }
      </div>

      <!-- Zona central informativa y contenido de decisión -->
      <div class="card-content-slot">
        <div class="archetype-tag">
          <span>{{ arquetipo }}</span>
        </div>

        <div class="decision-plate">
          <p class="decision-copy">{{ texto }}</p>
        </div>

        <div class="card-seal-row">
          @if (lanzada) {
            <span class="cyber-seal launched">JUGADA LANZADA</span>
          } @else if (seleccionada) {
            <span class="cyber-seal selected">CARTA ELEGIDA</span>
          } @else if (riesgoJoker) {
            <span class="cyber-seal risk">JOKER · RIESGO DE SESGO</span>
          } @else if (esJoker) {
            <span class="cyber-seal joker">{{ selloPie || 'ACTIVAR COMODÍN' }}</span>
          } @else {
            <span class="cyber-seal idle">{{ selloPie || ('JUGAR ' + rango + simbolo) }}</span>
          }
        </div>
      </div>

      <!-- Esquina inferior derecha invertida 180 grados como la imagen de referencia -->
      <div class="card-corner bottom-right" aria-hidden="true">
        @if (esJoker) {
          <span class="corner-rank joker-txt">JK</span>
          <span class="corner-suit">★</span>
        } @else {
          <span class="corner-rank">{{ rango }}</span>
          <span class="corner-suit">{{ simbolo }}</span>
        }
      </div>
    </div>
  `,
  styles: [`
    :host {
      display: block;
      height: 100%;
    }

    .cyber-card-shell {
      position: relative;
      height: 100%;
      min-height: 344px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      padding: 16px 15px;
      border-radius: 18px;
      overflow: hidden;
      background: #060811;
      color: #f8fafc;
      box-shadow:
        -8px 0 22px rgba(0, 229, 255, 0.2),
        8px 0 22px rgba(255, 46, 209, 0.2),
        0 20px 38px rgba(0, 0, 0, 0.72);
      transition: transform 0.28s cubic-bezier(0.22, 1, 0.36, 1), box-shadow 0.28s ease, filter 0.28s ease;
    }

    .cyber-card-shell::after {
      content: '';
      position: absolute;
      inset: -40%;
      background: linear-gradient(122deg, transparent 40%, rgba(255, 255, 255, 0.14) 50%, transparent 60%);
      transform: translateX(-110%);
      transition: transform 0.65s ease;
      pointer-events: none;
      z-index: 3;
    }

    :host(:hover) .cyber-card-shell::after {
      transform: translateX(110%);
    }

    .cyber-card-shell.is-selected {
      box-shadow:
        -10px 0 28px rgba(0, 229, 255, 0.48),
        10px 0 28px rgba(0, 232, 148, 0.42),
        0 24px 44px rgba(0, 0, 0, 0.8);
    }

    .cyber-card-shell.is-launched {
      box-shadow:
        -12px 0 36px rgba(0, 229, 255, 0.65),
        12px 0 36px rgba(255, 46, 209, 0.65),
        0 26px 50px rgba(0, 0, 0, 0.85);
    }

    .cyber-card-shell.is-joker {
      box-shadow:
        -10px 0 28px rgba(250, 204, 21, 0.32),
        10px 0 28px rgba(255, 46, 209, 0.32),
        0 20px 40px rgba(0, 0, 0, 0.78);
    }

    .cyber-card-shell.is-risk-flagged {
      filter: saturate(0.6) brightness(0.76);
      box-shadow:
        0 0 20px rgba(245, 158, 11, 0.36),
        0 16px 32px rgba(0, 0, 0, 0.72);
    }

    .floor-glow {
      position: absolute;
      left: 12%;
      right: 12%;
      bottom: -8px;
      height: 18px;
      background: linear-gradient(90deg, rgba(0, 229, 255, 0.45), rgba(255, 46, 209, 0.45));
      filter: blur(12px);
      pointer-events: none;
    }

    .card-chassis-svg {
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
      pointer-events: none;
      z-index: 1;
    }

    .card-corner {
      position: relative;
      z-index: 4;
      display: flex;
      flex-direction: column;
      align-items: center;
      width: max-content;
      line-height: 0.92;
      user-select: none;
    }

    .card-corner.top-left {
      align-self: flex-start;
    }

    .card-corner.bottom-right {
      align-self: flex-end;
      transform: rotate(180deg);
    }

    .corner-rank {
      font-family: Georgia, 'Times New Roman', serif;
      font-size: 24px;
      font-weight: 800;
      letter-spacing: -0.6px;
      color: #ffffff;
      text-shadow: 0 0 10px rgba(0, 229, 255, 0.72), 0 0 18px rgba(255, 46, 209, 0.45);
    }

    .corner-rank.joker-txt {
      font-size: 16px;
      letter-spacing: 0.8px;
      color: #fde047;
    }

    .corner-suit {
      font-size: 19px;
      line-height: 1;
      margin-top: 2px;
      color: #f0abfc;
      text-shadow: 0 0 10px rgba(255, 46, 209, 0.65);
    }

    .tone-dark .corner-suit {
      color: #a5f3fc;
      text-shadow: 0 0 10px rgba(0, 229, 255, 0.65);
    }

    .is-joker .corner-suit {
      color: #fde047;
      text-shadow: 0 0 10px rgba(250, 204, 21, 0.7);
    }

    .corner-sub {
      margin-top: 4px;
      font-family: var(--mono, monospace);
      font-size: 8.5px;
      letter-spacing: 0.8px;
      color: rgba(165, 243, 252, 0.72);
    }

    .card-content-slot {
      position: relative;
      z-index: 4;
      margin-top: 146px;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 8px;
      flex: 1;
      justify-content: flex-end;
    }

    .archetype-tag {
      padding: 2px 10px;
      border-radius: 999px;
      border: 1px solid rgba(0, 229, 255, 0.36);
      background: rgba(6, 11, 24, 0.86);
      font-family: var(--mono, monospace);
      font-size: 9px;
      letter-spacing: 1.2px;
      text-transform: uppercase;
      color: #a5f3fc;
      backdrop-filter: blur(4px);
    }

    .is-joker .archetype-tag {
      border-color: rgba(250, 204, 21, 0.55);
      color: #fef08a;
    }

    .decision-plate {
      width: 100%;
      padding: 10px 11px;
      border-radius: 10px;
      background: rgba(6, 10, 20, 0.88);
      border: 1px solid rgba(148, 163, 184, 0.24);
      backdrop-filter: blur(6px);
      text-align: center;
    }

    .decision-copy {
      margin: 0;
      font-family: var(--body, sans-serif);
      font-size: 13px;
      font-weight: 600;
      line-height: 1.38;
      color: #f1f5f9;
    }

    .card-seal-row {
      margin-bottom: 2px;
    }

    .cyber-seal {
      display: inline-block;
      padding: 4px 10px;
      border-radius: 999px;
      font-family: var(--mono, monospace);
      font-size: 9.5px;
      font-weight: 700;
      letter-spacing: 0.8px;
      text-transform: uppercase;
    }

    .cyber-seal.idle {
      background: rgba(15, 23, 42, 0.84);
      border: 1px solid rgba(0, 229, 255, 0.34);
      color: #bae6fd;
    }

    .cyber-seal.selected {
      background: rgba(6, 95, 70, 0.92);
      border: 1px solid #34d399;
      color: #ecfdf5;
      box-shadow: 0 0 12px rgba(16, 185, 129, 0.55);
    }

    .cyber-seal.launched {
      background: linear-gradient(90deg, #0284c7, #c026d3);
      border: 1px solid #f0abfc;
      color: #ffffff;
      box-shadow: 0 0 14px rgba(232, 121, 249, 0.65);
    }

    .cyber-seal.risk {
      background: rgba(120, 53, 15, 0.92);
      border: 1px solid #f59e0b;
      color: #fef3c7;
    }

    .cyber-seal.joker {
      background: linear-gradient(90deg, rgba(202, 138, 4, 0.92), rgba(192, 38, 211, 0.88));
      border: 1px solid #fde047;
      color: #ffffff;
      box-shadow: 0 0 14px rgba(250, 204, 21, 0.45);
    }
  `],
})
export class CyberCartaComponent {
  private readonly uid = ++siguienteIdCarta;

  @Input() rango = 'A';
  @Input() simbolo: PaloSimbolo = '♠';
  @Input() esRojo = false;
  @Input() arquetipo = 'JUICIO CRÍTICO';
  @Input() texto = '';
  @Input() etiquetaSuperior = '';
  @Input() selloPie = '';
  @Input() seleccionada = false;
  @Input() lanzada = false;
  @Input() esJoker = false;
  @Input() riesgoJoker = false;

  readonly gradMarco = `cm_${this.uid}`;
  readonly gradObsidiana = `co_${this.uid}`;
  readonly gradNebula = `cn_${this.uid}`;
  readonly gradPaloMetal = `cp_${this.uid}`;
}
