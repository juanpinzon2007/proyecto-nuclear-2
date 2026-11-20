import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, Input, computed, signal } from '@angular/core';
import {
  DireccionMirada,
  EstiloCabello,
  ExpresionFacial,
  PerfilHeroe,
  PosturaCorporal,
  VestuarioActor,
} from './cinema.types';

let siguienteIdActor = 0;

@Component({
  selector: 'app-personaje-actor',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div
      class="actor-root"
      [class.is-protagonist]="esProtagonista"
      [class.is-speaking]="hablando"
      [class.is-focused]="destacado"
      [class.is-dimmed]="atenuado"
      [class.is-flipped]="invertido"
      [class.hero-power-on]="poderActivo && !!heroe"
      [style.--hero-glow]="heroe?.colorEnergia || '#00e5f4'"
      [style.--breath-delay]="retrasoRespiracionMs + 'ms'"
      [style.--blink-delay]="retrasoParpadeoMs + 'ms'"
      [style.--gesture-delay]="retrasoGestoMs + 'ms'"
    >
      <!-- Halo sutil de foco narrativo o aura de superhéroe Marvel / DC -->
      @if (hablando || destacado || (poderActivo && heroe)) {
        <div
          class="actor-rim-glow"
          [class.protag-glow]="esProtagonista"
          [class.hero-rim]="!!heroe"
        ></div>
      }

      <svg
        class="actor-svg"
        viewBox="0 0 180 230"
        role="img"
        [attr.aria-label]="nombre + ' - ' + rol"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <linearGradient [attr.id]="gradPiel" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" [attr.stop-color]="pielClara" />
            <stop offset="72%" [attr.stop-color]="pielClara" />
            <stop offset="100%" [attr.stop-color]="pielSombra" />
          </linearGradient>

          <linearGradient [attr.id]="gradTraje" x1="0" y1="0" x2="0.2" y2="1">
            <stop offset="0%" [attr.stop-color]="colorTraje" />
            <stop offset="100%" [attr.stop-color]="colorTrajeSombra" />
          </linearGradient>

          <linearGradient [attr.id]="gradCabello" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" [attr.stop-color]="cabelloBrillo" />
            <stop offset="45%" [attr.stop-color]="cabelloColor" />
            <stop offset="100%" stop-color="#0d111a" />
          </linearGradient>

          <radialGradient [attr.id]="gradRubor" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stop-color="#d97762" stop-opacity="0.22" />
            <stop offset="100%" stop-color="#d97762" stop-opacity="0" />
          </radialGradient>

          <clipPath [attr.id]="clipOjoIzq">
            <path d="M 65 73 Q 73 66 81 73 Q 73 79 65 73 Z" />
          </clipPath>
          <clipPath [attr.id]="clipOjoDer">
            <path d="M 99 73 Q 107 66 115 73 Q 107 79 99 73 Z" />
          </clipPath>
        </defs>

        <!-- Sombra corporal proyectada detrás del torso -->
        <ellipse cx="90" cy="218" rx="48" ry="10" fill="rgba(0,0,0,0.42)" />

        <!-- Capa fluida de superhéroe detrás de hombros y brazos -->
        @if (heroe?.llevaCapa) {
          <g class="hero-cape">
            <path
              d="M 48 118 Q 22 168 18 224 L 162 224 Q 158 168 132 118 Z"
              [attr.fill]="heroe?.colorCapa || '#991b1b'"
              opacity="0.92"
            />
            <path
              d="M 54 120 Q 34 168 30 224 L 150 224 Q 146 168 126 120 Z"
              fill="rgba(0, 0, 0, 0.28)"
            />
          </g>
        }

        <!-- Capa trasera de cabello para estilos largos -->
        @if (estiloCabello === 'melena_lacia' || estiloCabello === 'ondulado_medio') {
          <g class="rig-head-back" [ngClass]="clasePostura()">
            @if (estiloCabello === 'melena_lacia') {
              <path
                d="M 52 62 C 44 88 45 124 52 146 L 128 146 C 135 124 136 88 128 62 Z"
                [attr.fill]="'url(#' + gradCabello + ')'"
              />
            } @else {
              <path
                d="M 51 64 C 41 90 42 118 50 138 C 60 134 72 136 90 136 C 108 136 120 134 130 138 C 138 118 139 90 129 64 Z"
                [attr.fill]="'url(#' + gradCabello + ')'"
              />
            }
          </g>
        }

        <!-- ==================== BRAZO TRASERO / IZQUIERDO ARTICULADO ==================== -->
        <g class="rig-arm-left" [ngClass]="['posture-' + postura]">
          <!-- Hombro y brazo superior -->
          <path
            [attr.d]="brazoIzquierdoSuperiorPath()"
            fill="none"
            [attr.stroke]="'url(#' + gradTraje + ')'"
            stroke-width="20"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
          <!-- Antebrazo izquierdo -->
          <path
            [attr.d]="antebrazoIzquierdoPath()"
            fill="none"
            [attr.stroke]="vestuario === 'bata' ? '#dce5ef' : colorTrajeSombra"
            stroke-width="16"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
          <!-- Puño camisa -->
          <circle
            [attr.cx]="manoIzqCoords().cx"
            [attr.cy]="manoIzqCoords().cy"
            r="6.2"
            [attr.fill]="colorCamisa"
            opacity="0.92"
          />
          <!-- Mano anatómica -->
          <g [attr.transform]="'translate(' + manoIzqCoords().x + ',' + manoIzqCoords().y + ') rotate(' + manoIzqCoords().rot + ')'">
            <path
              d="M -6 -2 C -7 -9 -3 -14 1 -14 C 5 -14 7 -10 7 -4 L 7 3 C 7 6 3 8 -1 7 C -5 7 -6 3 -6 -2 Z"
              [attr.fill]="'url(#' + gradPiel + ')'"
              stroke="rgba(15,23,42,0.22)"
              stroke-width="0.9"
            />
            <!-- Pulgar -->
            <path
              d="M -5 0 C -9 -2 -10 -7 -7 -9 C -5 -9 -4 -6 -4 -2 Z"
              [attr.fill]="pielSombra"
            />
          </g>
        </g>

        <!-- ==================== TORSO Y VESTUARIO ESTRUCTURADO ==================== -->
        <g class="rig-torso" [ngClass]="['posture-' + postura]">
          <!-- Silueta anatómica de hombros y pecho -->
          <path
            d="M 38 228 L 43 150 C 45 128 58 118 74 115 L 106 115 C 122 118 135 128 137 150 L 142 228 Z"
            [attr.fill]="'url(#' + gradTraje + ')'"
            stroke="rgba(255,255,255,0.08)"
            stroke-width="1"
          />

          <!-- Camisa / Escote interior -->
          <path
            d="M 74 115 L 90 158 L 106 115 L 98 112 L 82 112 Z"
            [attr.fill]="colorCamisa"
          />

          <!-- Cuello de camisa izquierda y derecha -->
          <polygon points="74,115 83,128 90,122 80,111" fill="#f8fafc" opacity="0.9" />
          <polygon points="106,115 97,128 90,122 100,111" fill="#e2e8f0" opacity="0.9" />

          <!-- Corbata / Pañuelo / Estetoscopio según vestuario -->
          @if (vestuario === 'ejecutivo' || vestuario === 'decano' || vestuario === 'protagonista') {
            <polygon
              points="87,123 93,123 95,152 90,160 85,152"
              [attr.fill]="colorCorbata || (esProtagonista ? '#00c8dc' : '#475569')"
            />
            <polygon points="86,120 94,120 92,126 88,126" [attr.fill]="colorCorbata || '#334155'" />
          }

          <!-- Solapas de chaqueta o bata médica -->
          @if (vestuario !== 'casual') {
            <path
              d="M 74 115 L 65 138 L 76 144 L 72 152 L 89 178 L 88 158 Z"
              [attr.fill]="colorTrajeSombra"
              opacity="0.92"
            />
            <path
              d="M 106 115 L 115 138 L 104 144 L 108 152 L 91 178 L 92 158 Z"
              [attr.fill]="colorTrajeSombra"
              opacity="0.92"
            />
          }

          <!-- Distintivos de vestuario clínico/institucional -->
          @if (vestuario === 'bata' || vestuario === 'clinico') {
            <rect x="106" y="162" width="19" height="22" rx="2" fill="rgba(15,23,42,0.12)" stroke="rgba(148,163,184,0.35)" />
            <rect x="109" y="156" width="3" height="8" rx="1" fill="#00e5f4" />
            <rect x="114" y="158" width="11" height="6" rx="1" fill="#38bdf8" opacity="0.7" />
          }

          @if (esProtagonista) {
            <!-- Credencial / acento protagonista consistente -->
            <rect x="55" y="158" width="18" height="12" rx="2" fill="#07131d" stroke="#00e5f4" stroke-width="1.2" />
            <circle cx="60" cy="164" r="2.2" fill="#00e894" />
            <line x1="65" y1="164" x2="70" y2="164" stroke="#a8f8ff" stroke-width="1.2" />
          }

          @if (heroe; as h) {
            <!-- Líneas estilizadas de traje / armadura en hombros -->
            <path
              d="M 48 136 L 71 122 M 132 136 L 109 122"
              fill="none"
              [attr.stroke]="h.colorAcento"
              stroke-width="2"
              stroke-linecap="round"
              opacity="0.82"
            />
            <!-- Emblema pectoral estético de superhéroe (visible por encima de la mesa) -->
            <g class="hero-crest-emblem" transform="translate(90, 136)">
              @switch (h.tipoEmblema) {
                @case ('reactor_arc') {
                  <circle r="11" fill="#082f49" [attr.stroke]="h.colorEnergia" stroke-width="2" />
                  <polygon points="0,-7 6,4 -6,4" fill="#e0f2fe" [attr.stroke]="h.colorEnergia" stroke-width="1" />
                  <circle r="2.6" fill="#ffffff" />
                }
                @case ('escudo_estrella') {
                  <circle r="11.5" fill="#dc2626" stroke="#f8fafc" stroke-width="2" />
                  <circle r="6.8" fill="#1d4ed8" />
                  <polygon points="0,-5.2 1.6,-1.6 5.4,-1.2 2.4,1.3 3.4,5.2 0,3 -3.4,5.2 -2.4,1.3 -5.4,-1.2 -1.6,-1.6" fill="#ffffff" />
                }
                @case ('mandala') {
                  <circle r="10.5" fill="rgba(180,83,9,0.25)" stroke="#fbbf24" stroke-width="1.4" />
                  <rect x="-6.5" y="-6.5" width="13" height="13" fill="none" stroke="#fde047" stroke-width="1.2" />
                  <rect x="-6.5" y="-6.5" width="13" height="13" transform="rotate(45)" fill="none" stroke="#fde047" stroke-width="1.2" />
                }
                @case ('aracnido') {
                  <circle r="10.5" fill="#1e1b4b" stroke="#fb7185" stroke-width="1.4" />
                  <ellipse cx="0" cy="0" rx="3.2" ry="5.5" fill="#f43f5e" />
                  <path d="M -3 -2 L -8 -6 M 3 -2 L 8 -6 M -3 1 L -9 4 M 3 1 L 9 4" stroke="#f43f5e" stroke-width="1.3" />
                }
                @case ('pantera') {
                  <path d="M -12 -3 Q 0 11 12 -3" fill="none" stroke="#c084fc" stroke-width="2.2" />
                  <polygon points="-7,-1 -5,6 -3,-1" fill="#e9d5ff" />
                  <polygon points="0,-1 2,7 4,-1" fill="#e9d5ff" />
                  <polygon points="7,-1 5,6 3,-1" fill="#e9d5ff" />
                }
                @case ('radar') {
                  <circle r="10.5" fill="#450a0a" stroke="#fb7185" stroke-width="1.4" />
                  <circle r="5" fill="none" stroke="#fda4af" stroke-width="1.2" />
                  <circle r="1.8" fill="#ffffff" />
                }
                @case ('murcielago') {
                  <ellipse cx="0" cy="0" rx="12" ry="7.5" fill="#0f172a" stroke="#38bdf8" stroke-width="1.3" />
                  <path d="M -9 0 Q -5 -5 -2 -1 L 0 -5 L 2 -1 Q 5 -5 9 0 Q 4 2 0 5 Q -4 2 -9 0 Z" fill="#38bdf8" />
                }
                @case ('diamante_s') {
                  <polygon points="-9,-5 9,-5 12,0 0,10 -12,0" fill="#dc2626" stroke="#facc15" stroke-width="1.7" />
                  <path d="M -4 -2 C 2 -4 5 0 -1 2 C -5 3 -2 6 4 4" fill="none" stroke="#fde047" stroke-width="1.8" stroke-linecap="round" />
                }
                @case ('lazo_estrella') {
                  <polygon points="-10,-3 -3,5 0,0 3,5 10,-3 5,-5 0,2 -5,-5" fill="#facc15" />
                  <circle cx="0" cy="-1" r="10.5" fill="none" stroke="#fde047" stroke-width="1.1" stroke-dasharray="3 2" />
                }
                @case ('relampago') {
                  <circle r="10.5" fill="#fef08a" stroke="#dc2626" stroke-width="1.8" />
                  <polygon points="2,-8 -4,1 1,1 -3,8 6,-1 1,-1" fill="#b91c1c" />
                }
                @case ('anillo_linterna') {
                  <circle r="10.5" fill="#022c22" stroke="#34d399" stroke-width="1.8" />
                  <circle r="5" fill="none" stroke="#6ee7b7" stroke-width="2.1" />
                  <line x1="-8" y1="-6" x2="8" y2="-6" stroke="#34d399" stroke-width="1.8" />
                  <line x1="-8" y1="6" x2="8" y2="6" stroke="#34d399" stroke-width="1.8" />
                }
                @default {
                  <!-- bionico -->
                  <polygon points="0,-10 10,0 0,10 -10,0" fill="#0f172a" stroke="#00e5ff" stroke-width="1.6" />
                  <circle r="3.8" fill="#f43f5e" />
                }
              }
            </g>
          }

          <!-- Pliegues sutiles de tela en torso -->
          <path d="M 62 182 Q 75 190 88 184" fill="none" stroke="rgba(0,0,0,0.2)" stroke-width="1.4" />
          <path d="M 118 182 Q 105 190 92 184" fill="none" stroke="rgba(0,0,0,0.2)" stroke-width="1.4" />
        </g>

        <!-- ==================== CUELLO ANATÓMICO ==================== -->
        <g class="rig-neck" [ngClass]="['posture-' + postura]">
          <path
            d="M 79 98 L 77 120 Q 90 127 103 120 L 101 98 Z"
            [attr.fill]="'url(#' + gradPiel + ')'"
          />
          <!-- Sombra natural bajo mandíbula -->
          <path
            d="M 78 100 Q 90 112 102 100 Q 90 107 78 100 Z"
            fill="rgba(28, 16, 12, 0.32)"
          />
        </g>

        <!-- ==================== CABEZA Y ROSTRO EXPRESIVO ==================== -->
        <g class="rig-head" [ngClass]="['posture-' + postura, hablando ? 'head-talk' : '']">
          <!-- Orejas -->
          <path d="M 61 68 C 55 68 54 81 61 84" [attr.fill]="pielSombra" stroke="rgba(0,0,0,0.14)" stroke-width="0.9" />
          <path d="M 119 68 C 125 68 126 81 119 84" [attr.fill]="pielSombra" stroke="rgba(0,0,0,0.14)" stroke-width="0.9" />

          <!-- Contorno facial anatómico (pómulos, mandíbula y mentón) -->
          <path
            d="M 61 60 C 60 39 73 30 90 30 C 107 30 120 39 119 60 C 119 77 113 91 102 99 C 95 104 85 104 78 99 C 67 91 61 77 61 60 Z"
            [attr.fill]="'url(#' + gradPiel + ')'"
            stroke="rgba(30,20,14,0.18)"
            stroke-width="1"
          />

          <!-- Volumetría sutil en pómulos -->
          <ellipse cx="72" cy="81" rx="7" ry="4" [attr.fill]="'url(#' + gradRubor + ')'" />
          <ellipse cx="108" cy="81" rx="7" ry="4" [attr.fill]="'url(#' + gradRubor + ')'" />

          <!-- Grupo de rasgos faciales con desplazamiento sutil de mirada -->
          <g [attr.transform]="'translate(' + desplazamientoMiradaX() + ', 0)'">
            <!-- Líneas discretas de madurez si corresponde -->
            @if (maduro) {
              <path d="M 73 53 Q 90 50 107 53" fill="none" stroke="rgba(60,35,20,0.22)" stroke-width="0.9" />
              <path d="M 73 86 Q 70 91 73 95" fill="none" stroke="rgba(60,35,20,0.18)" stroke-width="0.8" />
              <path d="M 107 86 Q 110 91 107 95" fill="none" stroke="rgba(60,35,20,0.18)" stroke-width="0.8" />
            }

            <!-- Cejas expresivas según emoción -->
            <path
              [attr.d]="cejaIzquierdaPath()"
              fill="none"
              [attr.stroke]="cabelloColor"
              stroke-width="2.7"
              stroke-linecap="round"
            />
            <path
              [attr.d]="cejaDerechaPath()"
              fill="none"
              [attr.stroke]="cabelloColor"
              stroke-width="2.7"
              stroke-linecap="round"
            />

            <!-- Ojo izquierdo -->
            <path d="M 65 73 Q 73 66 81 73 Q 73 79 65 73 Z" fill="#f8fafc" />
            <g [attr.clip-path]="'url(#' + clipOjoIzq + ')'">
              <circle [attr.cx]="73 + pupilaX()" [attr.cy]="73 + pupilaY()" r="3.8" fill="#334155" />
              <circle [attr.cx]="73 + pupilaX()" [attr.cy]="73 + pupilaY()" r="2" fill="#090d16" />
              <circle [attr.cx]="74.2 + pupilaX()" [attr.cy]="71.6 + pupilaY()" r="0.95" fill="#ffffff" />
              <!-- Párpado animado para parpadeo natural -->
              <rect class="eyelid" x="63" y="64" width="20" height="17" [attr.fill]="pielSombra" />
            </g>
            <path d="M 65 73 Q 73 66 81 73" fill="none" stroke="#1e293b" stroke-width="1.35" stroke-linecap="round" />

            <!-- Ojo derecho -->
            <path d="M 99 73 Q 107 66 115 73 Q 107 79 99 73 Z" fill="#f8fafc" />
            <g [attr.clip-path]="'url(#' + clipOjoDer + ')'">
              <circle [attr.cx]="107 + pupilaX()" [attr.cy]="73 + pupilaY()" r="3.8" fill="#334155" />
              <circle [attr.cx]="107 + pupilaX()" [attr.cy]="73 + pupilaY()" r="2" fill="#090d16" />
              <circle [attr.cx]="108.2 + pupilaX()" [attr.cy]="71.6 + pupilaY()" r="0.95" fill="#ffffff" />
              <rect class="eyelid" x="97" y="64" width="20" height="17" [attr.fill]="pielSombra" />
            </g>
            <path d="M 99 73 Q 107 66 115 73" fill="none" stroke="#1e293b" stroke-width="1.35" stroke-linecap="round" />

            <!-- Nariz anatómica con sombra lateral -->
            <path d="M 90 67 L 88 81 Q 90 83 93 81" fill="none" stroke="rgba(68,38,24,0.42)" stroke-width="1.4" stroke-linecap="round" />

            <!-- Boca articulada + estado de diálogo -->
            <g [class.mouth-speaking]="hablando">
              <path
                [attr.d]="bocaPath()"
                [attr.fill]="hablando ? '#451a22' : 'none'"
                stroke="#6b2d2d"
                stroke-width="1.9"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
              <!-- Sombra sutil bajo labio inferior -->
              <path d="M 86 93 Q 90 95 94 93" fill="none" stroke="rgba(45,20,12,0.22)" stroke-width="1" stroke-linecap="round" />
            </g>

            <!-- Lentes institucionales (si el personaje usa gafas) -->
            @if (lentes) {
              <g fill="rgba(168, 248, 255, 0.08)" stroke="#94a3b8" stroke-width="1.4">
                <rect x="63" y="67" width="20" height="12" rx="3.5" />
                <rect x="97" y="67" width="20" height="12" rx="3.5" />
                <line x1="83" y1="72" x2="97" y2="72" stroke-width="1.3" />
              </g>
            }
          </g>

          <!-- Máscaras / visores estilizados de superhéroe sin cubrir ojos ni gestos faciales -->
          @if (heroe; as hm) {
            <g class="hero-headgear" pointer-events="none">
              @switch (hm.tipoMascara) {
                @case ('diadema_dorada') {
                  <path d="M 62 56 L 76 47 L 90 42 L 104 47 L 118 56 L 104 52 L 90 49 L 76 52 Z" fill="#facc15" stroke="#a16207" stroke-width="0.9" />
                  <polygon points="90,41 92,46 97,46 93,49 94,54 90,51 86,54 87,49 83,46 88,46" fill="#dc2626" />
                }
                @case ('capucha_murcielago') {
                  <path d="M 60 56 L 59 24 L 72 41 Q 90 36 108 41 L 121 24 L 120 56 Q 106 58 96 63 L 90 59 L 84 63 Q 74 58 60 56 Z" [attr.fill]="hm.colorTrajeSombra" opacity="0.88" />
                }
                @case ('capucha_aletas') {
                  <path d="M 59 60 L 49 44 L 62 50 Z" fill="#f8fafc" stroke="#1d4ed8" stroke-width="0.8" />
                  <path d="M 121 60 L 131 44 L 118 50 Z" fill="#f8fafc" stroke="#1d4ed8" stroke-width="0.8" />
                  <path d="M 62 56 Q 90 47 118 56" fill="none" [attr.stroke]="hm.colorAcento" stroke-width="2.4" opacity="0.85" />
                }
                @case ('visor_tech') {
                  <rect x="61" y="64" width="58" height="16" rx="6" [attr.fill]="hm.colorEnergia" fill-opacity="0.16" [attr.stroke]="hm.colorEnergia" stroke-width="1.6" />
                  <line x1="66" y1="68" x2="77" y2="68" stroke="#ffffff" stroke-width="1.2" opacity="0.7" />
                }
                @case ('antifaz_tactico') {
                  <path
                    d="M 61 66 Q 74 61 90 66 Q 106 61 119 66 L 117 77 Q 107 79 98 76 L 90 73 L 82 76 Q 73 79 63 77 Z"
                    fill="none"
                    [attr.stroke]="hm.colorAcento"
                    stroke-width="2.1"
                    opacity="0.85"
                  />
                }
                @case ('capucha_aracnida') {
                  <path d="M 64 68 Q 73 61 82 71 Q 73 78 64 68 Z" fill="none" stroke="#fb7185" stroke-width="1.9" />
                  <path d="M 98 71 Q 107 61 116 68 Q 107 78 98 71 Z" fill="none" stroke="#fb7185" stroke-width="1.9" />
                }
              }
            </g>
          }

          <!-- Cabello frontal según perfil -->
          <g class="hair-front">
            @switch (estiloCabello) {
              @case ('canoso_peinado') {
                <path
                  d="M 59 59 C 58 36 71 23 90 23 C 109 23 122 36 121 59 C 117 44 105 39 90 40 C 75 40 64 46 59 59 Z"
                  [attr.fill]="'url(#' + gradCabello + ')'"
                />
                <path d="M 65 40 Q 90 31 114 39" fill="none" stroke="rgba(255,255,255,0.35)" stroke-width="1.5" stroke-linecap="round" />
              }
              @case ('mono_alto') {
                <circle cx="90" cy="21" r="13" [attr.fill]="'url(#' + gradCabello + ')'" />
                <path
                  d="M 59 58 C 58 36 72 25 90 25 C 108 25 122 36 121 58 C 115 44 103 39 90 39 C 77 39 65 44 59 58 Z"
                  [attr.fill]="'url(#' + gradCabello + ')'"
                />
              }
              @case ('melena_lacia') {
                <path
                  d="M 58 63 C 57 35 72 24 90 24 C 108 24 123 35 122 63 C 115 44 106 39 94 38 C 78 39 66 47 58 63 Z"
                  [attr.fill]="'url(#' + gradCabello + ')'"
                />
              }
              @case ('ondulado_medio') {
                <path
                  d="M 58 61 C 57 34 72 24 90 24 C 108 24 123 34 122 61 C 113 48 103 42 90 42 C 77 42 67 48 58 61 Z"
                  [attr.fill]="'url(#' + gradCabello + ')'"
                />
              }
              @case ('clinico_recogido') {
                <path
                  d="M 59 58 C 58 35 72 25 90 25 C 108 25 122 35 121 58 C 115 43 102 38 90 38 C 76 38 65 44 59 58 Z"
                  [attr.fill]="'url(#' + gradCabello + ')'"
                />
                <circle cx="118" cy="48" r="7" [attr.fill]="cabelloColor" />
              }
              @default {
                <!-- ejecutivo_corto -->
                <path
                  d="M 60 58 C 59 35 73 24 90 24 C 107 24 121 35 120 58 C 115 43 103 37 89 37 C 75 37 64 43 60 58 Z"
                  [attr.fill]="'url(#' + gradCabello + ')'"
                />
                <path d="M 69 36 Q 90 29 110 38" fill="none" stroke="rgba(255,255,255,0.22)" stroke-width="1.3" stroke-linecap="round" />
              }
            }
          </g>
        </g>

        <!-- ==================== BRAZO DERECHO EN PRIMER PLANO ARTICULADO ==================== -->
        <g class="rig-arm-right" [ngClass]="['posture-' + postura]">
          <path
            [attr.d]="brazoDerechoSuperiorPath()"
            fill="none"
            [attr.stroke]="'url(#' + gradTraje + ')'"
            stroke-width="20"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
          <path
            [attr.d]="antebrazoDerechoPath()"
            fill="none"
            [attr.stroke]="colorTraje"
            stroke-width="16.5"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
          <circle
            [attr.cx]="manoDerCoords().cx"
            [attr.cy]="manoDerCoords().cy"
            r="6.2"
            [attr.fill]="colorCamisa"
            opacity="0.94"
          />
          <g [attr.transform]="'translate(' + manoDerCoords().x + ',' + manoDerCoords().y + ') rotate(' + manoDerCoords().rot + ')'">
            <path
              d="M -6 -2 C -7 -9 -3 -14 1 -14 C 5 -14 7 -10 7 -4 L 7 3 C 7 6 3 8 -1 7 C -5 7 -6 3 -6 -2 Z"
              [attr.fill]="'url(#' + gradPiel + ')'"
              stroke="rgba(15,23,42,0.22)"
              stroke-width="0.9"
            />
            <path d="M 5 0 C 9 -2 10 -7 7 -9 C 5 -9 4 -6 4 -2 Z" [attr.fill]="pielSombra" />
            @if (postura === 'senalar_orden') {
              <!-- Dedo índice extendido apuntando con autoridad -->
              <rect x="-2" y="-23" width="4.4" height="12" rx="2.2" [attr.fill]="pielClara" />
            }
          </g>
        </g>

        <!-- ==================== ANIMACIONES DE PODER MARVEL / DC ==================== -->
        @if (heroe; as hp) {
          @if (poderActivo || hablando || destacado) {
            <g class="hero-power-fx" [class.fx-active]="poderActivo" pointer-events="none">
              @switch (hp.efectoPoder) {
                @case ('runas_arcanas') {
                  <!-- Mandalas giratorios estilo Doctor Strange -->
                  <g transform="translate(36, 146)">
                    <g class="fx-spin-mandala">
                      <circle r="24" fill="none" stroke="#fbbf24" stroke-width="1.8" stroke-dasharray="5 3" />
                      <rect x="-15" y="-15" width="30" height="30" fill="none" stroke="#f59e0b" stroke-width="1.4" />
                      <rect x="-15" y="-15" width="30" height="30" transform="rotate(45)" fill="none" stroke="#fde047" stroke-width="1.3" />
                    </g>
                  </g>
                  <g transform="translate(144, 146)">
                    <g class="fx-spin-mandala-rev">
                      <circle r="22" fill="none" stroke="#fbbf24" stroke-width="1.8" stroke-dasharray="5 3" />
                      <polygon points="0,-18 16,9 -16,9" fill="none" stroke="#fde047" stroke-width="1.3" />
                    </g>
                  </g>
                }
                @case ('escudo_vibranium') {
                  <!-- Escudo reflector estrella flotando en guardia -->
                  <g class="fx-shield-float" transform="translate(148, 134)">
                    <circle r="22" fill="rgba(220,38,38,0.22)" stroke="#ef4444" stroke-width="3" />
                    <circle r="15" fill="none" stroke="#f8fafc" stroke-width="2.5" />
                    <circle r="9" fill="rgba(29,78,216,0.45)" stroke="#38bdf8" stroke-width="1.5" />
                    <polygon points="0,-6 1.8,-1.8 6,-1.4 2.8,1.5 3.8,6 0,3.5 -3.8,6 -2.8,1.5 -6,-1.4 -1.8,-1.8" fill="#ffffff" />
                  </g>
                }
                @case ('hud_repulsor') {
                  <!-- Visor HUD holográfico estilo Iron Man -->
                  <g class="fx-pulse-hud">
                    <path d="M 32 72 A 58 58 0 0 1 64 30" fill="none" stroke="#00e5ff" stroke-width="2" stroke-dasharray="8 4" />
                    <path d="M 148 72 A 58 58 0 0 0 116 30" fill="none" stroke="#fbbf24" stroke-width="2" stroke-dasharray="6 4" />
                    <circle cx="90" cy="136" r="17" fill="none" stroke="#00e5ff" stroke-width="1.6" stroke-dasharray="4 3" />
                  </g>
                }
                @case ('sentido_aracnido') {
                  <!-- Ondas radar de sentido arácnido sobre la cabeza -->
                  <g class="fx-wave-pulse">
                    <path d="M 46 38 L 36 30 L 42 44 L 30 42" fill="none" stroke="#fbbf24" stroke-width="2.2" stroke-linecap="round" />
                    <path d="M 134 38 L 144 30 L 138 44 L 150 42" fill="none" stroke="#f43f5e" stroke-width="2.2" stroke-linecap="round" />
                  </g>
                }
                @case ('ondas_vibranium') {
                  <!-- Ondas cinéticas púrpura Black Panther -->
                  <g class="fx-wave-pulse">
                    <circle cx="90" cy="118" r="56" fill="none" stroke="#a855f7" stroke-width="2" stroke-dasharray="12 8" />
                    <circle cx="90" cy="118" r="68" fill="none" stroke="#c084fc" stroke-width="1.3" opacity="0.65" />
                  </g>
                }
                @case ('sonar_justicia') {
                  <g class="fx-wave-pulse">
                    <path d="M 38 64 A 56 56 0 0 0 38 118" fill="none" stroke="#fb7185" stroke-width="2" />
                    <path d="M 142 64 A 56 56 0 0 1 142 118" fill="none" stroke="#fb7185" stroke-width="2" />
                  </g>
                }
                @case ('batarang_tactico') {
                  <!-- Retícula detective + estela táctica Batman -->
                  <g class="fx-pulse-hud">
                    <path d="M 28 110 L 42 96 L 42 124" fill="none" stroke="#38bdf8" stroke-width="2" />
                    <path d="M 152 110 L 138 96 L 138 124" fill="none" stroke="#38bdf8" stroke-width="2" />
                    <path d="M 132 52 Q 140 44 148 52 Q 142 54 140 58 Q 138 54 132 52 Z" fill="#38bdf8" opacity="0.88" />
                  </g>
                }
                @case ('emblema_solar') {
                  <!-- Aura solar dorada Superman -->
                  <g class="fx-wave-pulse">
                    <ellipse cx="90" cy="126" rx="56" ry="74" fill="none" stroke="#fde047" stroke-width="1.8" opacity="0.7" />
                    <ellipse cx="90" cy="126" rx="64" ry="82" fill="none" stroke="#ef4444" stroke-width="1.2" stroke-dasharray="10 6" opacity="0.55" />
                  </g>
                }
                @case ('lazo_verdad') {
                  <!-- Lazo dorado luminoso Wonder Woman -->
                  <g transform="translate(90, 128)">
                    <g class="fx-spin-mandala">
                      <ellipse rx="56" ry="30" transform="rotate(-14)" fill="none" stroke="#fde047" stroke-width="2.2" stroke-dasharray="16 5" />
                      <circle cx="-46" cy="-16" r="3" fill="#fef08a" />
                      <circle cx="48" cy="14" r="3" fill="#fef08a" />
                    </g>
                  </g>
                }
                @case ('estela_speedforce') {
                  <!-- Rayos cinéticos Speed Force Flash -->
                  <g class="fx-lightning-flash">
                    <polyline points="26,120 44,104 36,98 54,80" fill="none" stroke="#facc15" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" />
                    <polyline points="154,120 136,104 144,98 126,80" fill="none" stroke="#facc15" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" />
                  </g>
                }
                @case ('constructo_esmeralda') {
                  <!-- Barrera geométrica esmeralda Linterna Verde -->
                  <g class="fx-pulse-hud">
                    <polygon points="90,34 144,68 144,148 90,180 36,148 36,68" fill="rgba(16,185,129,0.08)" stroke="#34d399" stroke-width="2" />
                  </g>
                }
                @default {
                  <!-- escaneo_cibernetico Cyborg -->
                  <g class="fx-pulse-hud">
                    <rect x="28" y="54" width="124" height="96" rx="8" fill="none" stroke="#00e5ff" stroke-width="1.4" stroke-dasharray="8 6" />
                    <line x1="28" y1="74" x2="152" y2="74" stroke="#f43f5e" stroke-width="1.5" opacity="0.7" />
                  </g>
                }
              }
            </g>
          }
        }
      </svg>

      <!-- Etiqueta discreta del rol en escena -->
      @if (mostrarEtiqueta) {
        <div class="actor-badge" [class.protag-badge]="esProtagonista" [class.talking-badge]="hablando">
          @if (hablando) {
            <span class="talk-bars" aria-hidden="true"><i></i><i></i><i></i></span>
          }
          <span>{{ nombre }}</span>
        </div>
      }
    </div>
  `,
  styles: [`
    .actor-root {
      position: relative;
      width: 152px;
      height: 198px;
      display: grid;
      place-items: end center;
      transition: filter 0.45s ease, opacity 0.45s ease, transform 0.55s cubic-bezier(0.22, 1, 0.36, 1);
      will-change: transform;
    }
    .actor-root.is-flipped .actor-svg {
      transform: scaleX(-1);
    }
    .actor-root.is-dimmed {
      filter: brightness(0.74) saturate(0.78);
    }
    .actor-root.is-focused {
      filter: brightness(1.08) drop-shadow(0 8px 18px rgba(0, 229, 244, 0.22));
    }
    .actor-rim-glow {
      position: absolute;
      inset: 14px 20px 26px;
      border-radius: 50%;
      background: radial-gradient(circle, rgba(255, 184, 0, 0.22), transparent 68%);
      filter: blur(10px);
      pointer-events: none;
      animation: pulseGlow 2.4s ease-in-out infinite alternate;
    }
    .actor-rim-glow.protag-glow {
      background: radial-gradient(circle, rgba(0, 229, 244, 0.28), transparent 68%);
    }
    .actor-rim-glow.hero-rim {
      background: radial-gradient(circle, color-mix(in srgb, var(--hero-glow, #00e5f4) 44%, transparent), transparent 68%);
    }
    .actor-root.hero-power-on {
      transform: translateY(-3px);
    }
    .hero-cape {
      transform-origin: 90px 120px;
      animation: capeBillow 3.4s ease-in-out infinite alternate;
    }
    .fx-spin-mandala {
      transform-box: fill-box;
      transform-origin: center;
      animation: mandalaSpin 7s linear infinite;
    }
    .fx-spin-mandala-rev {
      transform-box: fill-box;
      transform-origin: center;
      animation: mandalaSpinRev 6s linear infinite;
    }
    .fx-shield-float {
      animation: shieldHover 2.6s ease-in-out infinite alternate;
    }
    .fx-pulse-hud,
    .fx-wave-pulse {
      transform-origin: 90px 110px;
      animation: fxPulse 1.8s ease-in-out infinite alternate;
    }
    .fx-lightning-flash {
      animation: lightningJitter 0.9s ease-in-out infinite alternate;
    }
    .actor-svg {
      width: 100%;
      height: 100%;
      overflow: visible;
      filter: drop-shadow(0 12px 18px rgba(0, 0, 0, 0.55));
    }

    /* Animaciones orgánicas escalonadas por actor (sin sincronización robótica) */
    .rig-torso,
    .rig-neck {
      transform-origin: 90px 210px;
      animation: actorBreathe 4.2s ease-in-out infinite;
      animation-delay: var(--breath-delay, 0ms);
    }
    .rig-head,
    .rig-head-back {
      transform-origin: 90px 104px;
      animation: headIdle 5.4s ease-in-out infinite alternate;
      animation-delay: var(--breath-delay, 0ms);
      transition: transform 0.55s cubic-bezier(0.22, 1, 0.36, 1);
    }
    .rig-head.head-talk {
      animation: headTalk 1.6s ease-in-out infinite alternate;
    }
    .rig-head.posture-inclinado_adelante {
      transform: translateY(3px) scale(1.03);
    }
    .rig-head.posture-retroceso_tension {
      transform: translate(-3px, 2px) rotate(-3deg);
    }
    .rig-head.posture-escucha_empatica {
      transform: rotate(4.5deg) translateY(1px);
    }
    .rig-head.posture-decidido {
      transform: translateY(-2px) scale(1.02);
    }

    .rig-arm-right,
    .rig-arm-left {
      transition: transform 0.65s cubic-bezier(0.22, 1, 0.36, 1);
    }
    .rig-arm-right.posture-brazo_levantado {
      transform-origin: 126px 132px;
      animation: armVoteFloat 2.8s ease-in-out infinite alternate;
      animation-delay: var(--gesture-delay, 0ms);
    }
    .rig-arm-left.posture-senalar_orden,
    .rig-arm-right.posture-senalar_orden {
      transform-origin: 126px 132px;
      animation: armPointSubtle 2.1s ease-in-out infinite alternate;
    }

    .eyelid {
      transform-origin: center top;
      transform: scaleY(0);
      animation: eyeBlink 5.2s ease-in-out infinite;
      animation-delay: var(--blink-delay, 0ms);
    }
    .mouth-speaking {
      transform-origin: 90px 89px;
      animation: mouthTalk 0.42s ease-in-out infinite alternate;
    }

    .actor-badge {
      position: absolute;
      bottom: -8px;
      left: 50%;
      transform: translateX(-50%);
      display: inline-flex;
      align-items: center;
      gap: 5px;
      padding: 2px 8px;
      white-space: nowrap;
      border-radius: 999px;
      border: 1px solid rgba(148, 163, 184, 0.32);
      background: rgba(7, 11, 19, 0.88);
      color: #cbd5e1;
      font: 600 9.5px var(--mono);
      letter-spacing: 0.6px;
      text-transform: uppercase;
      pointer-events: none;
      box-shadow: 0 4px 10px rgba(0, 0, 0, 0.5);
    }
    .actor-badge.protag-badge {
      border-color: rgba(0, 229, 244, 0.65);
      color: #a8f8ff;
      background: rgba(4, 22, 32, 0.94);
    }
    .actor-badge.talking-badge {
      border-color: rgba(255, 184, 0, 0.72);
      color: #fde68a;
    }
    .talk-bars {
      display: inline-flex;
      align-items: flex-end;
      gap: 1.5px;
      height: 8px;
    }
    .talk-bars i {
      width: 2px;
      background: #ffb800;
      border-radius: 1px;
      animation: eqBar 0.45s ease-in-out infinite alternate;
    }
    .talk-bars i:nth-child(2) { animation-delay: 0.14s; }
    .talk-bars i:nth-child(3) { animation-delay: 0.28s; }

    @keyframes actorBreathe {
      0%, 100% { transform: translateY(0) scaleY(1); }
      50% { transform: translateY(-1.6px) scaleY(1.012); }
    }
    @keyframes headIdle {
      0% { transform: rotate(-1.2deg) translateY(0); }
      100% { transform: rotate(1.3deg) translateY(-1.2px); }
    }
    @keyframes headTalk {
      0% { transform: rotate(-2.2deg) translateY(0); }
      100% { transform: rotate(2.4deg) translateY(-1.8px); }
    }
    @keyframes eyeBlink {
      0%, 92%, 100% { transform: scaleY(0); }
      95% { transform: scaleY(1); }
      97% { transform: scaleY(0.1); }
      98.5% { transform: scaleY(1); }
    }
    @keyframes mouthTalk {
      0% { transform: scaleY(0.85); }
      100% { transform: scaleY(1.32); }
    }
    @keyframes armVoteFloat {
      0% { transform: translateY(1px) rotate(0deg); }
      100% { transform: translateY(-4px) rotate(-3deg); }
    }
    @keyframes armPointSubtle {
      0% { transform: translateX(0); }
      100% { transform: translateX(-3px) translateY(-1px); }
    }
    @keyframes pulseGlow {
      from { opacity: 0.55; transform: scale(0.96); }
      to { opacity: 1; transform: scale(1.05); }
    }
    @keyframes eqBar {
      from { height: 2px; }
      to { height: 8px; }
    }

    @media (prefers-reduced-motion: reduce) {
      .rig-torso,
      .rig-neck,
      .rig-head,
      .rig-head-back,
      .rig-arm-right,
      .rig-arm-left,
      .eyelid,
      .mouth-speaking,
      .actor-rim-glow,
      .hero-cape,
      .fx-spin-mandala,
      .fx-spin-mandala-rev,
      .fx-shield-float,
      .fx-pulse-hud,
      .fx-wave-pulse,
      .fx-lightning-flash,
      .talk-bars i {
        animation: none !important;
      }
    }
    @keyframes capeBillow {
      0% { transform: skewX(-1.5deg) scaleY(1); }
      100% { transform: skewX(2.5deg) scaleY(1.03); }
    }
    @keyframes mandalaSpin {
      from { transform: rotate(0deg); }
      to { transform: rotate(360deg); }
    }
    @keyframes mandalaSpinRev {
      from { transform: rotate(360deg); }
      to { transform: rotate(0deg); }
    }
    @keyframes shieldHover {
      0% { transform: translate(148px, 134px) rotate(-6deg) scale(0.96); }
      100% { transform: translate(148px, 128px) rotate(6deg) scale(1.04); }
    }
    @keyframes fxPulse {
      0% { opacity: 0.6; transform: scale(0.96); }
      100% { opacity: 1; transform: scale(1.04); }
    }
    @keyframes lightningJitter {
      0% { opacity: 0.55; transform: translateX(-1px); }
      100% { opacity: 1; transform: translateX(2px); }
    }
  `],
})
export class PersonajeActorComponent {
  private readonly uid = ++siguienteIdActor;

  @Input() nombre = 'Participante';
  @Input() rol = 'Integrante';
  @Input() pielClara = '#e2b494';
  @Input() pielSombra = '#bc8462';
  @Input() cabelloColor = '#27232b';
  @Input() cabelloBrillo = '#4c4553';
  @Input() estiloCabello: EstiloCabello = 'ejecutivo_corto';
  @Input() vestuario: VestuarioActor = 'ejecutivo';
  @Input() colorTraje = '#1e293b';
  @Input() colorTrajeSombra = '#0f172a';
  @Input() colorCamisa = '#e2e8f0';
  @Input() colorCorbata?: string;
  @Input() lentes = false;
  @Input() maduro = false;
  @Input() esProtagonista = false;
  @Input() expresion: ExpresionFacial = 'neutro';
  @Input() postura: PosturaCorporal = 'sentado_firme';
  @Input() mirada: DireccionMirada = 'centro';
  @Input() hablando = false;
  @Input() destacado = false;
  @Input() atenuado = false;
  @Input() invertido = false;
  @Input() mostrarEtiqueta = true;
  @Input() heroe?: PerfilHeroe;
  @Input() poderActivo = false;
  @Input() retrasoRespiracionMs = 0;
  @Input() retrasoParpadeoMs = 400;
  @Input() retrasoGestoMs = 0;

  readonly gradPiel = `piel_${this.uid}`;
  readonly gradTraje = `traje_${this.uid}`;
  readonly gradCabello = `cab_${this.uid}`;
  readonly gradRubor = `rub_${this.uid}`;
  readonly clipOjoIzq = `ojoi_${this.uid}`;
  readonly clipOjoDer = `ojod_${this.uid}`;

  clasePostura(): string {
    return `posture-${this.postura}`;
  }

  desplazamientoMiradaX(): number {
    if (this.mirada === 'izquierda') return -2.4;
    if (this.mirada === 'derecha') return 2.4;
    return 0;
  }

  pupilaX(): number {
    if (this.mirada === 'izquierda') return -2.2;
    if (this.mirada === 'derecha') return 2.2;
    return 0;
  }

  pupilaY(): number {
    return this.mirada === 'abajo' ? 1.6 : 0;
  }

  cejaIzquierdaPath(): string {
    switch (this.expresion) {
      case 'autoridad':
        return 'M 63 63 Q 73 61 82 66';
      case 'desacuerdo':
        return 'M 64 62 Q 73 63 82 67';
      case 'preocupacion':
      case 'inseguridad':
        return 'M 63 66 Q 73 61 82 61';
      case 'tension':
        return 'M 64 64 L 82 64';
      case 'convencimiento':
        return 'M 63 63 Q 73 59 82 63';
      default:
        return 'M 64 64 Q 73 61 81 64';
    }
  }

  cejaDerechaPath(): string {
    switch (this.expresion) {
      case 'autoridad':
        return 'M 98 66 Q 107 61 117 63';
      case 'desacuerdo':
        return 'M 98 66 Q 107 60 116 62';
      case 'preocupacion':
      case 'inseguridad':
        return 'M 98 61 Q 107 61 117 66';
      case 'tension':
        return 'M 98 64 L 116 64';
      case 'convencimiento':
        return 'M 98 63 Q 107 59 117 63';
      default:
        return 'M 99 64 Q 107 61 116 64';
    }
  }

  bocaPath(): string {
    if (this.hablando) {
      return 'M 81 88 Q 90 85 99 88 Q 96 93 90 93 Q 84 93 81 88 Z';
    }
    switch (this.expresion) {
      case 'preocupacion':
      case 'inseguridad':
        return 'M 82 91 Q 90 87 98 91';
      case 'desacuerdo':
        return 'M 81 90 Q 89 87 98 91';
      case 'autoridad':
      case 'tension':
        return 'M 82 89 Q 90 89 98 89';
      case 'convencimiento':
      case 'calma':
        return 'M 82 88 Q 90 92 98 88';
      default:
        return 'M 83 89 Q 90 90 97 89';
    }
  }

  brazoIzquierdoSuperiorPath(): string {
    switch (this.postura) {
      case 'escucha_empatica':
      case 'defensa_abierta':
        return 'M 49 126 Q 36 154 44 182';
      case 'retroceso_tension':
        return 'M 49 126 Q 41 154 55 174';
      default:
        return 'M 49 126 Q 35 156 40 190';
    }
  }

  antebrazoIzquierdoPath(): string {
    switch (this.postura) {
      case 'retroceso_tension':
        return 'M 55 174 Q 70 162 82 142';
      case 'defensa_abierta':
        return 'M 44 182 Q 52 162 62 150';
      default:
        return 'M 40 190 Q 52 196 68 196';
    }
  }

  manoIzqCoords(): { x: number; y: number; cx: number; cy: number; rot: number } {
    switch (this.postura) {
      case 'retroceso_tension':
        return { x: 83, y: 138, cx: 79, cy: 146, rot: -20 };
      case 'defensa_abierta':
        return { x: 64, y: 146, cx: 60, cy: 152, rot: -12 };
      default:
        return { x: 72, y: 196, cx: 66, cy: 196, rot: 72 };
    }
  }

  brazoDerechoSuperiorPath(): string {
    switch (this.postura) {
      case 'brazo_levantado':
        return 'M 131 126 Q 148 106 146 78';
      case 'senalar_orden':
        return 'M 131 126 Q 146 144 128 158';
      case 'inclinado_adelante':
      case 'decidido':
        return 'M 131 126 Q 142 154 126 178';
      case 'defensa_abierta':
        return 'M 131 126 Q 143 150 132 172';
      default:
        return 'M 131 126 Q 144 156 138 190';
    }
  }

  antebrazoDerechoPath(): string {
    switch (this.postura) {
      case 'brazo_levantado':
        return 'M 146 78 Q 142 54 134 36';
      case 'senalar_orden':
        return 'M 128 158 Q 106 148 84 140';
      case 'inclinado_adelante':
        return 'M 126 178 Q 112 184 96 184';
      case 'defensa_abierta':
        return 'M 132 172 Q 118 156 108 144';
      case 'decidido':
        return 'M 126 178 Q 112 176 96 172';
      default:
        return 'M 138 190 Q 124 196 108 196';
    }
  }

  manoDerCoords(): { x: number; y: number; cx: number; cy: number; rot: number } {
    switch (this.postura) {
      case 'brazo_levantado':
        return { x: 132, y: 31, cx: 136, cy: 40, rot: -12 };
      case 'senalar_orden':
        return { x: 80, y: 138, cx: 88, cy: 141, rot: -80 };
      case 'inclinado_adelante':
        return { x: 92, y: 184, cx: 99, cy: 184, rot: -75 };
      case 'defensa_abierta':
        return { x: 105, y: 140, cx: 111, cy: 147, rot: -22 };
      case 'decidido':
        return { x: 92, y: 171, cx: 99, cy: 172, rot: -72 };
      default:
        return { x: 104, y: 196, cx: 110, cy: 196, rot: -72 };
    }
  }
}
