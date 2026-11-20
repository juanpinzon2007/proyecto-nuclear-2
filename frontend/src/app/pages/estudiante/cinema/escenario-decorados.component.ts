import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, Input } from '@angular/core';
import { PerfilHeroe, TemaEscena } from './cinema.types';

let siguienteIdDecorado = 0;

@Component({
  selector: 'app-escenario-decorados',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <svg
      class="decor-svg"
      viewBox="0 0 960 400"
      preserveAspectRatio="xMidYMid slice"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <defs>
        <linearGradient [attr.id]="idCrepusculo" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#0b1024" />
          <stop offset="52%" stop-color="#2c193f" />
          <stop offset="100%" stop-color="#7c3336" />
        </linearGradient>
        <linearGradient [attr.id]="idMesaMadera" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#2e211b" />
          <stop offset="28%" stop-color="#1d1412" />
          <stop offset="100%" stop-color="#0b090b" />
        </linearGradient>
        <linearGradient [attr.id]="idReflejoMesa" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stop-color="rgba(0, 229, 255, 0.14)" />
          <stop offset="50%" stop-color="rgba(255, 255, 255, 0.18)" />
          <stop offset="100%" stop-color="rgba(255, 46, 209, 0.16)" />
        </linearGradient>
        <linearGradient [attr.id]="idLuzCenital" x1="0.5" y1="0" x2="0.5" y2="1">
          <stop offset="0%" stop-color="#a8f8ff" stop-opacity="0.22" />
          <stop offset="100%" stop-color="#a8f8ff" stop-opacity="0" />
        </linearGradient>
        <linearGradient [attr.id]="idLuzCalida" x1="0.5" y1="0" x2="0.5" y2="1">
          <stop offset="0%" stop-color="#fbbf24" stop-opacity="0.22" />
          <stop offset="100%" stop-color="#fbbf24" stop-opacity="0" />
        </linearGradient>
      </defs>

      @if (capa === 'fondo') {
        @switch (tema) {
          @case ('tribunal_comite') {
            <!-- Paredes en perspectiva arquitectónica -->
            <rect x="0" y="0" width="960" height="400" fill="#0b101b" />
            <polygon points="0,0 130,36 130,310 0,370" fill="#111827" />
            <polygon points="960,0 830,36 830,310 960,370" fill="#111827" />
            <!-- Ventanal panorámico nocturno institucional con acento Universo Heroico -->
            <rect x="130" y="34" width="700" height="224" [attr.fill]="'url(#' + idCrepusculo + ')'" stroke="#263449" stroke-width="4" />
            @if (heroe) {
              <!-- Halo atmosférico del universo Marvel / DC en el horizonte -->
              <circle
                cx="480"
                cy="118"
                r="82"
                [attr.fill]="heroe.colorEnergia"
                [attr.opacity]="opcionArmada || opcionLanzada ? '0.2' : '0.11'"
              />
              @if (heroe.universo === 'DC') {
                <!-- Proyección cenital nocturna sutil estilo Metrópolis/Gotham -->
                <polygon
                  points="448,142 512,142 570,34 390,34"
                  [attr.fill]="heroe.colorEnergia"
                  opacity="0.08"
                />
              } @else {
                <!-- Aguja futurista sutil estilo Torre Marvel en skyline -->
                <rect x="476" y="88" width="8" height="144" fill="#091528" />
                <circle cx="480" cy="112" r="10" [attr.fill]="heroe.colorEnergia" opacity="0.35" />
              }
            }
            <!-- Silueta urbana discreta tras cristal -->
            <path
              d="M130 232 L175 232 L175 186 L218 186 L218 232 L265 232 L265 152 L320 152 L320 232 L460 232 L460 170 L505 170 L505 232 L630 232 L630 144 L695 144 L695 232 L752 232 L752 192 L830 192 L830 258 L130 258 Z"
              fill="#080c17"
              opacity="0.86"
            />
            <!-- Ventanas iluminadas de edificios al fondo -->
            <g fill="#f59e0b" opacity="0.45">
              <rect x="278" y="166" width="8" height="4" />
              <rect x="296" y="182" width="8" height="4" />
              <rect x="646" y="158" width="10" height="4" />
              <rect x="668" y="176" width="10" height="4" />
            </g>
            <!-- Parteluces metálicos del ventanal -->
            <g stroke="#1e293b" stroke-width="4">
              <line x1="305" y1="34" x2="305" y2="258" />
              <line x1="480" y1="34" x2="480" y2="258" />
              <line x1="655" y1="34" x2="655" y2="258" />
              <line x1="130" y1="150" x2="830" y2="150" stroke-width="2" opacity="0.6" />
            </g>
            <!-- Zócalo de madera institucional -->
            <rect x="130" y="256" width="700" height="62" fill="#171419" />
            <line x1="130" y1="256" x2="830" y2="256" stroke="#3b2c25" stroke-width="3" />
            <!-- Haces de luz cenital sobre los participantes -->
            <polygon points="180,0 420,0 470,340 120,340" [attr.fill]="'url(#' + idLuzCenital + ')'" opacity="0.55" />
            <polygon points="540,0 780,0 840,340 490,340" [attr.fill]="'url(#' + idLuzCalida + ')'" opacity="0.55" />
            <!-- Tablero discreto de acta en pared superior izquierda -->
            <g transform="translate(362, 46)">
              <rect x="0" y="0" width="236" height="48" rx="6" fill="rgba(7,11,20,0.86)" stroke="rgba(255,184,0,0.45)" stroke-width="1.5" />
              <text x="118" y="18" text-anchor="middle" fill="#ffb800" font-size="9.5" font-family="monospace" letter-spacing="1.4">
                {{ opcionLanzada ? 'ACTA DE DECISIÓN REGISTRADA' : (opcionArmada ? 'POSTURA PREPARADA' : 'VOTACIÓN EN SALA · 4 : 1') }}
              </text>
              <g transform="translate(34, 28)">
                <rect x="0" y="0" width="26" height="6" rx="2" [attr.fill]="opcionLanzada ? '#64748b' : '#ef4444'" />
                <rect x="34" y="0" width="26" height="6" rx="2" [attr.fill]="opcionLanzada ? '#64748b' : '#ef4444'" />
                <rect x="68" y="0" width="26" height="6" rx="2" [attr.fill]="opcionArmada || opcionLanzada ? '#00e5f4' : '#475569'" />
                <rect x="102" y="0" width="26" height="6" rx="2" [attr.fill]="opcionLanzada ? '#64748b' : '#ef4444'" />
                <rect x="136" y="0" width="26" height="6" rx="2" [attr.fill]="opcionLanzada ? '#64748b' : '#ef4444'" />
              </g>
            </g>
          }

          @case ('laboratorio_autoridad') {
            <rect x="0" y="0" width="960" height="400" fill="#091118" />
            <!-- Zona izquierda: cámara de observación tras vidrio biselado -->
            <rect x="36" y="38" width="248" height="248" fill="#0d1b24" stroke="#1e3a4c" stroke-width="4" />
            <line x1="36" y1="38" x2="284" y2="286" stroke="rgba(168,248,255,0.08)" stroke-width="26" />
            <line x1="88" y1="38" x2="210" y2="286" stroke="rgba(168,248,255,0.06)" stroke-width="12" />
            <rect x="48" y="50" width="76" height="16" rx="3" fill="rgba(239,68,68,0.22)" stroke="#ef4444" stroke-width="1" />
            <text x="86" y="61" text-anchor="middle" fill="#fca5a5" font-size="8.5" font-family="monospace">SALA B</text>
            <!-- Muro técnico laboratorio -->
            <rect x="308" y="28" width="616" height="270" fill="#111a26" stroke="#1e293b" stroke-width="2" />
            <!-- Rack instrumental de pared: Voltímetro + Osciloscopio -->
            <rect x="380" y="52" width="220" height="92" rx="6" fill="#090d14" stroke="#334155" stroke-width="2" />
            <circle cx="430" cy="96" r="24" fill="#0f172a" stroke="#f59e0b" stroke-width="2" />
            <line x1="430" y1="96" [attr.x2]="opcionArmada ? '418' : '444'" y2="79" stroke="#ef4444" stroke-width="2.5" stroke-linecap="round" />
            <text x="430" y="132" text-anchor="middle" fill="#fbbf24" font-size="9" font-family="monospace">150V - 300V</text>
            <rect x="472" y="68" width="112" height="58" rx="4" fill="#051319" stroke="#0891b2" stroke-width="1.5" />
            <path
              class="svg-wave-anim"
              d="M 476 97 L 492 97 L 500 79 L 508 115 L 516 88 L 524 97 L 544 97 L 552 76 L 560 116 L 568 88 L 580 97"
              fill="none"
              stroke="#00e5f4"
              stroke-width="2"
            />
            <polygon points="340,0 640,0 690,340 290,340" [attr.fill]="'url(#' + idLuzCenital + ')'" opacity="0.48" />
          }

          @case ('hospital_urgencias') {
            <rect x="0" y="0" width="960" height="400" fill="#08101c" />
            <!-- Ventanal exterior noche lluviosa -->
            <rect x="44" y="40" width="250" height="190" fill="#0b182e" stroke="#1e3a5f" stroke-width="4" />
            <g class="rain-lines" stroke="rgba(125,211,252,0.22)" stroke-width="1.4">
              <line x1="70" y1="45" x2="55" y2="95" /><line x1="125" y1="60" x2="110" y2="115" />
              <line x1="185" y1="50" x2="170" y2="108" /><line x1="245" y1="70" x2="230" y2="128" />
              <line x1="100" y1="145" x2="84" y2="205" /><line x1="210" y1="150" x2="194" y2="210" />
            </g>
            <!-- Puertas dobles de urgencias -->
            <rect x="355" y="48" width="250" height="250" fill="#101e30" stroke="#29435c" stroke-width="3" />
            <line x1="480" y1="48" x2="480" y2="298" stroke="#09131e" stroke-width="4" />
            <rect x="380" y="74" width="76" height="92" rx="4" fill="rgba(56,189,248,0.12)" stroke="#38bdf8" stroke-opacity="0.35" />
            <rect x="504" y="74" width="76" height="92" rx="4" fill="rgba(56,189,248,0.12)" stroke="#38bdf8" stroke-opacity="0.35" />
            <rect x="430" y="22" width="100" height="18" rx="3" fill="#7f1d1d" stroke="#ef4444" />
            <text x="480" y="34" text-anchor="middle" fill="#fecaca" font-size="9" font-family="monospace">URGENCIAS 24H</text>
            <!-- Monitor multiparámetro derecho -->
            <rect x="665" y="64" width="210" height="110" rx="8" fill="#07111a" stroke="#1f3b4d" stroke-width="2" />
            <path
              class="svg-wave-anim"
              d="M 680 120 L 718 120 L 728 96 L 738 144 L 748 106 L 758 120 L 795 120 L 806 94 L 816 146 L 826 108 L 836 120 L 865 120"
              fill="none"
              stroke="#00e894"
              stroke-width="2.2"
            />
            <polygon points="300,0 660,0 740,340 220,340" [attr.fill]="'url(#' + idLuzCenital + ')'" opacity="0.4" />
          }

          @case ('entrevista_clinica') {
            <rect x="0" y="0" width="960" height="400" fill="#13161f" />
            <!-- Ventanal cálido con persianas venecianas proyectando luz suave -->
            <rect x="90" y="36" width="280" height="220" fill="#2a2220" stroke="#3c2f29" stroke-width="4" />
            <g fill="rgba(251,191,36,0.16)">
              <rect x="98" y="48" width="264" height="10" /><rect x="98" y="72" width="264" height="10" />
              <rect x="98" y="96" width="264" height="10" /><rect x="98" y="120" width="264" height="10" />
              <rect x="98" y="144" width="264" height="10" /><rect x="98" y="168" width="264" height="10" />
            </g>
            <!-- Cuadro geométrico sutil en pared derecha + lámpara cálida -->
            <rect x="590" y="58" width="180" height="110" rx="4" fill="#1a1f2b" stroke="#364152" stroke-width="3" />
            <circle cx="655" cy="112" r="28" fill="rgba(0, 229, 244, 0.16)" />
            <circle cx="695" cy="112" r="24" fill="rgba(251, 191, 36, 0.18)" />
            <polygon points="110,36 370,36 520,360 120,360" [attr.fill]="'url(#' + idLuzCalida + ')'" opacity="0.55" />
          }

          @case ('proteccion_riesgo') {
            <rect x="0" y="0" width="960" height="400" fill="#0b1219" />
            <!-- Puerta segura institucional al fondo izquierda -->
            <rect x="82" y="54" width="136" height="240" rx="6" fill="#0d1f26" stroke="#00e894" stroke-opacity="0.55" stroke-width="2.5" />
            <circle cx="196" cy="176" r="6" fill="#00e894" />
            <!-- Panel de evaluación de riesgo en pared -->
            <rect x="340" y="48" width="280" height="130" rx="8" fill="#0c1522" stroke="#1e3a5f" stroke-width="2" />
            <text x="480" y="74" text-anchor="middle" fill="#a8f8ff" font-size="10" font-family="monospace">PROTOCOLO DE RESGUARDO</text>
            <rect x="372" y="96" width="216" height="12" rx="6" fill="#091017" stroke="#334155" />
            <rect x="374" y="98" [attr.width]="opcionLanzada ? '88' : '152'" height="8" rx="4" [attr.fill]="opcionLanzada ? '#00e894' : '#f59e0b'" />
            <polygon points="310,0 650,0 710,340 250,340" [attr.fill]="'url(#' + idLuzCenital + ')'" opacity="0.45" />
          }

          @default {
            <!-- Mesa Interinstitucional / Red de Cuidado -->
            <rect x="0" y="0" width="960" height="400" fill="#0a111e" />
            <rect x="190" y="42" width="580" height="204" rx="8" fill="#091525" stroke="rgba(0,229,244,0.3)" stroke-width="2" />
            <!-- Red territorial discreta integrada en tablero de sala -->
            <g stroke="rgba(0,229,244,0.28)" stroke-width="1.4" fill="none">
              <line x1="270" y1="110" x2="480" y2="145" />
              <line x1="480" y1="145" x2="690" y2="108" />
              <line x1="340" y1="205" x2="480" y2="145" />
              <line x1="480" y1="145" x2="635" y2="198" />
            </g>
            <g fill="#00e5f4">
              <circle cx="270" cy="110" r="4" /><circle cx="690" cy="108" r="4" />
              <circle cx="340" cy="205" r="4" /><circle cx="635" cy="198" r="4" />
              <circle cx="480" cy="145" r="6" fill="#00e894" />
            </g>
            <polygon points="280,0 680,0 740,340 220,340" [attr.fill]="'url(#' + idLuzCenital + ')'" opacity="0.45" />
          }
        }
      }

      @if (capa === 'mobiliario_medio') {
        @if (tema === 'tribunal_comite' || tema === 'red_ciudad') {
          <!-- Respaldos ergonómicos de sillas ejecutivas detrás de los personajes -->
          <g fill="#161e2e" stroke="#2c3a52" stroke-width="1.5" opacity="0.92">
            <rect x="108" y="182" width="64" height="106" rx="14" />
            <rect x="272" y="188" width="66" height="106" rx="14" />
            <rect x="446" y="198" width="72" height="110" rx="16" stroke="rgba(0,229,244,0.35)" />
            <rect x="626" y="188" width="66" height="106" rx="14" />
            <rect x="790" y="182" width="64" height="106" rx="14" />
          </g>
        } @else if (tema === 'entrevista_clinica') {
          <g fill="#262129" stroke="#3f3644" stroke-width="1.5">
            <rect x="200" y="206" width="96" height="104" rx="18" />
            <rect x="556" y="206" width="100" height="104" rx="18" />
            <rect x="756" y="214" width="84" height="96" rx="16" />
          </g>
        }
      }

      @if (capa === 'primer_plano') {
        @switch (tema) {
          @case ('tribunal_comite') {
            <!-- Mesa directiva trapezoidal en perspectiva con reflejo y expedientes -->
            <polygon points="56,306 904,306 960,400 0,400" [attr.fill]="'url(#' + idMesaMadera + ')'" stroke="#4b3932" stroke-width="2" />
            <polygon points="88,312 872,312 910,362 50,362" [attr.fill]="'url(#' + idReflejoMesa + ')'" />
            <!-- Carpeta / expediente de votación ante el protagonista -->
            <polygon points="434,328 526,328 536,368 424,368" fill="#1e293b" stroke="#00e5f4" stroke-width="1.2" />
            <line x1="444" y1="342" x2="516" y2="342" stroke="#94a3b8" stroke-width="2" />
            <line x1="442" y1="352" x2="498" y2="352" stroke="#64748b" stroke-width="2" />
            <!-- Micrófonos de mesa y dossiers laterales -->
            <g stroke="#64748b" stroke-width="2" fill="none">
              <path d="M 294 334 Q 302 316 312 314" />
              <path d="M 666 334 Q 658 316 648 314" />
            </g>
            <circle cx="312" cy="314" r="3" fill="#ef4444" />
            <circle cx="648" cy="314" r="3" fill="#ef4444" />
          }

          @case ('laboratorio_autoridad') {
            <!-- Pupitre de mando de laboratorio en primer plano -->
            <polygon points="80,312 880,312 940,400 20,400" fill="#131c28" stroke="#2e4157" stroke-width="2" />
            <rect x="380" y="326" width="200" height="44" rx="6" fill="#091019" stroke="#f59e0b" stroke-opacity="0.55" />
            <circle cx="422" cy="348" r="8" fill="#00e894" opacity="0.8" />
            <circle cx="456" cy="348" r="8" fill="#f59e0b" opacity="0.85" />
            <circle cx="490" cy="348" r="8" [attr.fill]="opcionArmada ? '#00e5f4' : '#ef4444'" />
          }

          @case ('hospital_urgencias') {
            <polygon points="40,326 920,326 960,400 0,400" fill="#111c29" stroke="#28425c" stroke-width="2" />
            <rect x="426" y="338" width="110" height="42" rx="4" fill="#0f2536" stroke="#38bdf8" stroke-opacity="0.45" />
          }

          @case ('entrevista_clinica') {
            <!-- Mesa clínica cálida con libreta terapéutica -->
            <polygon points="110,322 850,322 920,400 40,400" fill="#231c1a" stroke="#473730" stroke-width="2" />
            <polygon points="216,336 284,336 294,372 206,372" fill="#f1f5f9" opacity="0.88" />
            <line x1="224" y1="348" x2="276" y2="348" stroke="#64748b" stroke-width="2" />
            <line x1="222" y1="358" x2="268" y2="358" stroke="#94a3b8" stroke-width="2" />
          }

          @default {
            <polygon points="70,316 890,316 950,400 10,400" fill="#121a27" stroke="#293d54" stroke-width="2" />
            <polygon points="96,320 864,320 900,362 60,362" [attr.fill]="'url(#' + idReflejoMesa + ')'" />
          }
        }
      }
    </svg>
  `,
  styles: [`
    .decor-svg {
      display: block;
      width: 100%;
      height: 100%;
    }
    .svg-wave-anim {
      stroke-dasharray: 220;
      animation: waveTrace 2.4s linear infinite;
    }
    .rain-lines {
      animation: rainStreak 1.1s linear infinite;
    }
    @keyframes waveTrace {
      from { stroke-dashoffset: 220; }
      to { stroke-dashoffset: 0; }
    }
    @keyframes rainStreak {
      from { transform: translate(0, -10px); opacity: 0.45; }
      to { transform: translate(-8px, 14px); opacity: 0.85; }
    }
    @media (prefers-reduced-motion: reduce) {
      .svg-wave-anim,
      .rain-lines {
        animation: none !important;
      }
    }
  `],
})
export class EscenarioDecoradosComponent {
  private readonly uid = ++siguienteIdDecorado;

  @Input() tema: TemaEscena = 'tribunal_comite';
  @Input() capa: 'fondo' | 'mobiliario_medio' | 'primer_plano' = 'fondo';
  @Input() opcionArmada = false;
  @Input() opcionLanzada = false;
  @Input() heroe?: PerfilHeroe;

  readonly idCrepusculo = `crep_${this.uid}`;
  readonly idMesaMadera = `mesa_${this.uid}`;
  readonly idReflejoMesa = `refl_${this.uid}`;
  readonly idLuzCenital = `luzc_${this.uid}`;
  readonly idLuzCalida = `luzk_${this.uid}`;
}
