import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, Input } from '@angular/core';
import { PerfilHeroe, SubEscena } from './cinema.types';

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
      [attr.preserveAspectRatio]="capa === 'fondo' ? 'xMidYMid slice' : 'none'"
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
        <radialGradient [attr.id]="idDespacho" cx="38%" cy="24%" r="78%">
          <stop offset="0%" stop-color="#805035" />
          <stop offset="50%" stop-color="#492a2d" />
          <stop offset="100%" stop-color="#211827" />
        </radialGradient>
      </defs>

      @if (capa === 'fondo') {
        @switch (subEscena) {
          @case ('INSISTENCIA_DECANO') {
            <rect width="960" height="400" [attr.fill]="'url(#' + idDespacho + ')'" />
            <path d="M0 285 L960 285 L960 400 L0 400 Z" fill="#21151c" />
            <path d="M0 285 H960 M295 285 L92 400 M635 285 L833 400" fill="none" stroke="#a6664a" stroke-opacity=".45" stroke-width="2" />
            <path d="M0 22 L147 60 V280 L0 320 Z M960 22 L813 60 V280 L960 320 Z" fill="#421f2c" opacity=".63" />

            <!-- Archivo de Decanatura -->
            <rect x="100" y="56" width="217" height="219" rx="4" fill="#402327" stroke="#9a6347" stroke-width="4" />
            <path d="M113 72 H304 V257 H113 Z" fill="#191722" />
            <g fill="#94614b">
              <path d="M110 119 H307 V125 H110 Z M110 171 H307 V177 H110 Z M110 223 H307 V229 H110 Z" />
            </g>
            <g fill="none" stroke-width="8">
              <path d="M128 91 V118 M174 83 V118 M233 94 V118 M270 88 V118 M145 143 V171 M213 135 V171 M248 141 V171 M286 131 V171 M130 194 V223 M205 185 V223 M265 199 V223" stroke="#a55d58" />
              <path d="M143 82 V118 M161 90 V118 M195 93 L202 118 M255 84 V118 M284 94 V118 M129 131 V171 M177 138 V171 M231 146 V171 M267 148 V171 M148 184 V223 M190 194 V223 M233 191 V223 M281 190 V223" stroke="#c29660" />
              <path d="M218 88 V118 M153 139 L164 171 M192 144 V171 M165 193 V223 M249 190 V223 M295 197 V223" stroke="#6d667b" />
            </g>

            <path d="M350 54 H609 V284 H350 Z" fill="#512c31" stroke="#b77753" stroke-opacity=".54" stroke-width="2" />
            <path d="M364 68 H595 V266 H364 Z" fill="none" stroke="#e2a06a" stroke-opacity=".25" />
            <circle cx="479" cy="117" r="30" fill="#2b1b28" stroke="#d39761" stroke-width="2" />
            <path d="M479 102 L492 107 V118 Q492 126 479 133 Q466 126 466 118 V107 Z M472 117 L477 122 L486 111"
              fill="none" stroke="#edbd84" stroke-width="2" stroke-linejoin="round" />
            <text x="480" y="168" text-anchor="middle" fill="#fbd5ab" font-size="15" font-weight="700" font-family="monospace" letter-spacing="3">DECANATURA</text>
            <path d="M425 184 H535" stroke="#d39761" stroke-width="1.5" />

            <!-- Vidrio y luz cálida del despacho -->
            <path d="M654 63 H856 V269 H654 Z" fill="#211d32" stroke="#9a6347" stroke-width="4" />
            <path d="M669 78 H841 V253 H669 Z" fill="#362c49" />
            <path d="M669 219 H702 V194 H728 V224 H749 V189 H776 V216 H808 V182 H829 V209 H841 V253 H669 Z" fill="#221f34" />
            <path d="M753 78 V253 M669 157 H841" stroke="#6b4851" stroke-width="3" />
            <path d="M671 83 H837 M671 95 H837 M671 107 H837 M671 119 H837" stroke="#a47673" stroke-opacity=".55" stroke-width="4" />
            <path class="office-light" d="M652 75 H846 L930 388 H593 Z" [attr.fill]="'url(#' + idLuzCalida + ')'" />
            <path d="M462 40 H498 L510 48 H450 Z" fill="#dd9e6f" />
            <path d="M462 48 H498 L547 173 H413 Z" [attr.fill]="'url(#' + idLuzCalida + ')'" opacity=".55" />
          }

          @case ('VOTACION_MAYORIA_4_1') {
            <!-- Paredes en perspectiva arquitectónica -->
            <rect x="0" y="0" width="960" height="400" fill="#0b101b" />
            <polygon points="0,0 130,36 130,310 0,370" fill="#111827" />
            <polygon points="960,0 830,36 830,310 960,370" fill="#111827" />
            <!-- Ventanal panorámico institucional -->
            <rect x="130" y="34" width="700" height="224" [attr.fill]="'url(#' + idCrepusculo + ')'" stroke="#263449" stroke-width="4" />
            @if (heroe) {
              <!-- Luz ambiental del héroe en el horizonte -->
              <circle
                cx="480"
                cy="118"
                r="82"
                [attr.fill]="heroe.colorEnergia"
                [attr.opacity]="opcionArmada || opcionLanzada ? '0.2' : '0.11'"
              />
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
              <g transform="translate(34, 28)" class="vote-lights">
                <rect x="0" y="0" width="26" height="6" rx="2" [attr.fill]="opcionLanzada ? '#64748b' : '#ef4444'" />
                <rect x="34" y="0" width="26" height="6" rx="2" [attr.fill]="opcionLanzada ? '#64748b' : '#ef4444'" />
                <rect x="68" y="0" width="26" height="6" rx="2" [attr.fill]="opcionArmada || opcionLanzada ? '#00e5f4' : '#475569'" />
                <rect x="102" y="0" width="26" height="6" rx="2" [attr.fill]="opcionLanzada ? '#64748b' : '#ef4444'" />
                <rect x="136" y="0" width="26" height="6" rx="2" [attr.fill]="opcionLanzada ? '#64748b' : '#ef4444'" />
              </g>
            </g>
          }

          @case ('ORDEN_LABORATORIO') {
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
              class="svg-wave-anim lab-trace"
              d="M 476 97 L 492 97 L 500 79 L 508 115 L 516 88 L 524 97 L 544 97 L 552 76 L 560 116 L 568 88 L 580 97"
              fill="none"
              stroke="#00e5f4"
              stroke-width="2"
            />
            <polygon points="340,0 640,0 690,340 290,340" [attr.fill]="'url(#' + idLuzCenital + ')'" opacity="0.48" />
          }

          @case ('CRISIS_URGENCIAS') {
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

          @case ('ENTREVISTA_CLINICA') {
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
            <polygon class="consult-light" points="110,36 370,36 520,360 120,360" [attr.fill]="'url(#' + idLuzCalida + ')'" />
          }

          @case ('RESGUARDO_RIESGO') {
            <rect x="0" y="0" width="960" height="400" fill="#0b1219" />
            <!-- Puerta segura institucional al fondo izquierda -->
            <rect x="82" y="54" width="136" height="240" rx="6" fill="#0d1f26" stroke="#00e894" stroke-opacity="0.55" stroke-width="2.5" />
            <circle class="security-light" cx="196" cy="176" r="6" fill="#00e894" />
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
            <circle class="network-pulse" cx="480" cy="145" r="33" fill="none" stroke="#4deec1" stroke-width="2" />
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
        @if (subEscena === 'INSISTENCIA_DECANO') {
          <g fill="#322332" stroke="#9b6955" stroke-width="2">
            <rect x="82" y="189" width="69" height="104" rx="21" />
            <rect x="268" y="172" width="103" height="120" rx="24" />
            <rect x="606" y="189" width="76" height="115" rx="20" />
            <rect x="810" y="189" width="69" height="104" rx="21" />
          </g>
          <path d="M281 207 H358 M281 221 H358 M281 235 H358 M617 222 H671" stroke="#bd7c60" stroke-opacity=".28" stroke-width="2" />
        } @else if (subEscena === 'VOTACION_MAYORIA_4_1' || subEscena === 'MESA_INTERINSTITUCIONAL') {
          <!-- Respaldos ergonómicos de sillas ejecutivas detrás de los personajes -->
          <g fill="#161e2e" stroke="#2c3a52" stroke-width="1.5" opacity="0.92">
            <rect x="108" y="182" width="64" height="106" rx="14" />
            <rect x="272" y="188" width="66" height="106" rx="14" />
            <rect x="446" y="198" width="72" height="110" rx="16" stroke="rgba(0,229,244,0.35)" />
            <rect x="626" y="188" width="66" height="106" rx="14" />
            <rect x="790" y="182" width="64" height="106" rx="14" />
          </g>
        } @else if (subEscena === 'ENTREVISTA_CLINICA') {
          <g fill="#262129" stroke="#3f3644" stroke-width="1.5">
            <rect x="200" y="206" width="96" height="104" rx="18" />
            <rect x="556" y="206" width="100" height="104" rx="18" />
            <rect x="756" y="214" width="84" height="96" rx="16" />
          </g>
        }
      }

      @if (capa === 'primer_plano') {
        @switch (subEscena) {
          @case ('INSISTENCIA_DECANO') {
            <path d="M66 312 H166 L185 333 H48 Z M794 312 H894 L912 333 H776 Z" fill="#52363a" stroke="#8c5b49" stroke-width="2" />
            <path d="M48 333 H185 V365 H48 Z M776 333 H912 V365 H776 Z" fill="#32232e" />
            <path d="M215 318 H747 L841 393 H119 Z" fill="#693f36" stroke="#a36c4e" stroke-width="2" />
            <path d="M119 393 H841 V400 H119 Z" fill="#301d24" />
            <path d="M239 326 H725 L756 353 H207 Z" fill="#432735" stroke="#ad795a" stroke-opacity=".55" />
            <path d="M270 337 H350 L339 362 H255 Z" fill="#dfb48b" />
            <path d="M277 343 H333 M272 349 H319 M269 355 H311" stroke="#835549" stroke-width="1.4" />
            <ellipse cx="673" cy="345" rx="16" ry="5" fill="#281721" />
            <path d="M663 328 H681 L679 343 H665 Z M681 332 Q691 329 685 338 H680" fill="#d6a982" stroke="#4c2c32" stroke-width="1.4" />
          }

          @case ('VOTACION_MAYORIA_4_1') {
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

          @case ('ORDEN_LABORATORIO') {
            <!-- Pupitre de mando de laboratorio en primer plano -->
            <polygon points="80,312 880,312 940,400 20,400" fill="#131c28" stroke="#2e4157" stroke-width="2" />
            <rect x="380" y="326" width="200" height="44" rx="6" fill="#091019" stroke="#f59e0b" stroke-opacity="0.55" />
            <circle cx="422" cy="348" r="8" fill="#00e894" opacity="0.8" />
            <circle cx="456" cy="348" r="8" fill="#f59e0b" opacity="0.85" />
            <circle cx="490" cy="348" r="8" [attr.fill]="opcionArmada ? '#00e5f4' : '#ef4444'" />
          }

          @case ('CRISIS_URGENCIAS') {
            <polygon points="40,326 920,326 960,400 0,400" fill="#111c29" stroke="#28425c" stroke-width="2" />
            <rect x="426" y="338" width="110" height="42" rx="4" fill="#0f2536" stroke="#38bdf8" stroke-opacity="0.45" />
          }

          @case ('ENTREVISTA_CLINICA') {
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
    .vote-lights rect {
      animation: voteLight 580ms ease-out both;
    }
    .vote-lights rect:nth-child(2) { animation-delay: 130ms; }
    .vote-lights rect:nth-child(4) { animation-delay: 260ms; }
    .vote-lights rect:nth-child(5) { animation-delay: 390ms; }
    .office-light {
      animation: officeLight 1.1s ease-out both;
    }
    .lab-trace {
      animation-duration: 1.6s;
    }
    .consult-light {
      animation: consultLight 8s ease-in-out infinite alternate;
    }
    .security-light {
      animation: securityLight 3.8s ease-in-out infinite;
    }
    .network-pulse {
      transform-box: fill-box;
      transform-origin: center;
      animation: networkPulse 3.2s ease-out infinite;
    }
    @keyframes waveTrace {
      from { stroke-dashoffset: 220; }
      to { stroke-dashoffset: 0; }
    }
    @keyframes rainStreak {
      from { transform: translate(0, -10px); opacity: 0.45; }
      to { transform: translate(-8px, 14px); opacity: 0.85; }
    }
    @keyframes voteLight {
      from { opacity: .25; }
      to { opacity: 1; }
    }
    @keyframes officeLight {
      from { opacity: .15; transform: translateX(-18px); }
      to { opacity: .8; transform: translateX(0); }
    }
    @keyframes consultLight {
      from { opacity: .36; }
      to { opacity: .69; }
    }
    @keyframes securityLight {
      0%, 60%, 100% { opacity: .45; }
      21% { opacity: 1; }
    }
    @keyframes networkPulse {
      0% { opacity: .8; transform: scale(.22); }
      74%, 100% { opacity: 0; transform: scale(1); }
    }
    @media (prefers-reduced-motion: reduce) {
      .svg-wave-anim,
      .rain-lines,
      .vote-lights rect,
      .office-light,
      .consult-light,
      .security-light,
      .network-pulse {
        animation: none !important;
      }
    }
  `],
})
export class EscenarioDecoradosComponent {
  private readonly uid = ++siguienteIdDecorado;

  @Input() subEscena: SubEscena = 'VOTACION_MAYORIA_4_1';
  @Input() capa: 'fondo' | 'mobiliario_medio' | 'primer_plano' = 'fondo';
  @Input() opcionArmada = false;
  @Input() opcionLanzada = false;
  @Input() heroe?: PerfilHeroe;

  readonly idCrepusculo = `crep_${this.uid}`;
  readonly idMesaMadera = `mesa_${this.uid}`;
  readonly idReflejoMesa = `refl_${this.uid}`;
  readonly idLuzCenital = `luzc_${this.uid}`;
  readonly idLuzCalida = `luzk_${this.uid}`;
  readonly idDespacho = `despacho_${this.uid}`;
}
