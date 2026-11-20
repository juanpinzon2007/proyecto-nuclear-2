import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, Input } from '@angular/core';
import { DireccionMirada, PerfilHeroe, PosturaCorporal } from './cinema.types';

let siguienteHeroeUid = 0;

@Component({
  selector: 'app-heroe-cine',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div
      class="hero-cine-root"
      [class.power-on]="poderActivo"
      [class.is-speaking]="hablando"
      [class.posture-decided]="postura === 'decidido' || postura === 'defensa_abierta'"
      [class.posture-tense]="postura === 'retroceso_tension'"
      [style.--hero-energy]="heroe.colorEnergia"
      [style.--breath-delay]="retrasoRespiracionMs + 'ms'"
    >
      <!-- Halo volumétrico de cine según energía del personaje -->
      <div class="cinema-rim-aura" [class.aura-active]="poderActivo || hablando"></div>

      <svg
        class="hero-svg"
        viewBox="0 0 220 260"
        role="img"
        [attr.aria-label]="'Protagonista caracterizado como ' + heroe.nombre + ' (' + heroe.universo + ')'"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <linearGradient [attr.id]="idSkin" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stop-color="#f2c6aa" />
            <stop offset="68%" stop-color="#d79d7b" />
            <stop offset="100%" stop-color="#9e6748" />
          </linearGradient>

          <linearGradient [attr.id]="idArmorRed" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stop-color="#f87171" />
            <stop offset="28%" stop-color="#dc2626" />
            <stop offset="76%" stop-color="#991b1b" />
            <stop offset="100%" stop-color="#450a0a" />
          </linearGradient>

          <linearGradient [attr.id]="idGold" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stop-color="#fef9c3" />
            <stop offset="35%" stop-color="#eab308" />
            <stop offset="75%" stop-color="#b45309" />
            <stop offset="100%" stop-color="#78350f" />
          </linearGradient>

          <linearGradient [attr.id]="idChrome" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stop-color="#f8fafc" />
            <stop offset="32%" stop-color="#cbd5e1" />
            <stop offset="68%" stop-color="#64748b" />
            <stop offset="100%" stop-color="#1e293b" />
          </linearGradient>

          <linearGradient [attr.id]="idDarkKevlar" x1="0" y1="0" x2="0.6" y2="1">
            <stop offset="0%" stop-color="#334155" />
            <stop offset="45%" stop-color="#18202c" />
            <stop offset="100%" stop-color="#06090f" />
          </linearGradient>

          <linearGradient [attr.id]="idNavyArmor" x1="0" y1="0" x2="0.8" y2="1">
            <stop offset="0%" stop-color="#2563eb" />
            <stop offset="42%" stop-color="#1e3a8a" />
            <stop offset="100%" stop-color="#0b1736" />
          </linearGradient>

          <linearGradient [attr.id]="idCapeRed" x1="0" y1="0" x2="0.4" y2="1">
            <stop offset="0%" stop-color="#dc2626" />
            <stop offset="55%" stop-color="#881337" />
            <stop offset="100%" stop-color="#3b0712" />
          </linearGradient>

          <linearGradient [attr.id]="idEmerald" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stop-color="#6ee7b7" />
            <stop offset="40%" stop-color="#10b981" />
            <stop offset="100%" stop-color="#022c22" />
          </linearGradient>

          <!-- Patrón de textura hexagonal Kryptoniana / Vibranium -->
          <pattern [attr.id]="patHex" width="10" height="10" patternUnits="userSpaceOnUse">
            <path d="M 5 0 L 10 2.5 L 10 7.5 L 5 10 L 0 7.5 L 0 2.5 Z" fill="none" stroke="rgba(255,255,255,0.09)" stroke-width="0.7" />
          </pattern>

          <!-- Patrón de malla balística diagonal Kevlar -->
          <pattern [attr.id]="patKevlar" width="6" height="6" patternUnits="userSpaceOnUse">
            <path d="M 0 6 L 6 0 M -1 1 L 1 -1 M 5 7 L 7 5" stroke="rgba(255,255,255,0.07)" stroke-width="0.9" />
          </pattern>

          <filter [attr.id]="fltGlow" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="2.6" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        <!-- Sombra base -->
        <ellipse cx="110" cy="248" rx="64" ry="11" fill="rgba(0,0,0,0.56)" />

        <!-- ==================== PERSONIFICACIONES DE CINE MARVEL Y DC ==================== -->
        @switch (heroe.id) {
          <!-- 1. IRON MAN (MARK 85 CINE) -->
          @case ('iron_man') {
            <g class="rig-body">
              <!-- Hombreras y torso Mark 85 carmesí/oro titanio -->
              <path d="M 42 252 L 46 154 C 48 126 68 112 92 108 L 128 108 C 152 112 172 126 174 154 L 178 252 Z" [attr.fill]="'url(#' + idArmorRed + ')'" stroke="#450a0a" stroke-width="1.2" />
              <!-- Paneles dorados pectorales y trapecios -->
              <polygon points="48,144 68,120 82,130 76,162 52,166" [attr.fill]="'url(#' + idGold + ')'" opacity="0.92" />
              <polygon points="172,144 152,120 138,130 144,162 168,166" [attr.fill]="'url(#' + idGold + ')'" opacity="0.92" />
              <path d="M 76 164 L 94 176 L 126 176 L 144 164 L 136 226 L 84 226 Z" [attr.fill]="'url(#' + idGold + ')'" opacity="0.88" />
              <path d="M 86 112 L 110 128 L 134 112 L 126 105 L 94 105 Z" fill="#1e293b" stroke="#94a3b8" stroke-width="1" />
              <!-- Costuras mecánicas de placa -->
              <path d="M 76 132 L 110 146 L 144 132 M 62 176 L 90 194 M 158 176 L 130 194" fill="none" stroke="#450a0a" stroke-width="1.6" />

              <!-- Reactor Arc triangular Mark 85 luminoso -->
              <g transform="translate(110, 152)" [attr.filter]="'url(#' + fltGlow + ')'">
                <polygon points="0,-16 17,9 -17,9" fill="#082f49" stroke="#94a3b8" stroke-width="2.4" />
                <polygon points="0,-11 12,6 -12,6" fill="#00e5ff" />
                <polygon points="0,-6 6.5,3.5 -6.5,3.5" fill="#ffffff" />
              </g>

              <!-- Brazo y guantelete repulsor elevado al activar -->
              <g class="hero-arm-action" [class.arm-raised]="poderActivo || postura === 'decidido' || postura === 'defensa_abierta'">
                <path d="M 164 146 Q 186 178 174 202" fill="none" [attr.stroke]="'url(#' + idArmorRed + ')'" stroke-width="24" stroke-linecap="round" />
                <path d="M 174 202 Q 166 178 164 158" fill="none" [attr.stroke]="'url(#' + idGold + ')'" stroke-width="18" stroke-linecap="round" />
                <circle cx="164" cy="154" r="10" [attr.fill]="'url(#' + idArmorRed + ')'" stroke="#fbbf24" stroke-width="1.5" />
                @if (poderActivo || hablando) {
                  <circle cx="164" cy="154" r="6" fill="#ffffff" [attr.filter]="'url(#' + fltGlow + ')'" />
                  <circle cx="164" cy="154" r="16" fill="none" stroke="#00e5ff" stroke-width="2" class="pulse-ring" />
                }
              </g>
            </g>

            <!-- Casco Mark 85 completo rojo y oro -->
            <g class="rig-head">
              <path d="M 76 58 C 76 28 92 20 110 20 C 128 20 144 28 144 58 L 141 88 C 138 101 124 108 110 109 C 96 108 82 101 79 88 Z" [attr.fill]="'url(#' + idArmorRed + ')'" stroke="#450a0a" stroke-width="1.4" />
              <!-- Placa facial dorada icónica -->
              <path d="M 85 46 L 103 46 L 106 37 L 114 37 L 117 46 L 135 46 L 136 66 L 130 92 L 120 101 L 100 101 L 90 92 L 84 66 Z" [attr.fill]="'url(#' + idGold + ')'" stroke="#78350f" stroke-width="1.2" />
              <!-- Mandíbula roja inferior -->
              <path d="M 94 94 L 126 94 L 121 106 L 99 106 Z" [attr.fill]="'url(#' + idArmorRed + ')'" />
              <!-- Línea de boca mecánica + surco nasal -->
              <line x1="101" y1="90" x2="119" y2="90" stroke="#78350f" stroke-width="1.6" />
              <path d="M 85 57 L 102 64 M 135 57 L 118 64" stroke="#78350f" stroke-width="1.3" />
              <!-- Ojos cibernéticos brillantes cian -->
              <g [attr.transform]="'translate(' + miradaX() + ', 0)'" [attr.filter]="'url(#' + fltGlow + ')'">
                <polygon points="87,64 104,67 101,73 89,71" fill="#e0f2fe" stroke="#00e5ff" stroke-width="1.2" />
                <polygon points="133,64 116,67 119,73 131,71" fill="#e0f2fe" stroke="#00e5ff" stroke-width="1.2" />
              </g>
            </g>

            <!-- HUD Holográfico alrededor al activar -->
            @if (poderActivo || hablando) {
              <g class="fx-hud-orbit" pointer-events="none">
                <circle cx="110" cy="70" r="58" fill="none" stroke="#00e5ff" stroke-width="1.4" stroke-dasharray="14 8 4 8" opacity="0.72" />
                <path d="M 42 52 L 56 42 M 178 52 L 164 42" stroke="#fbbf24" stroke-width="1.8" />
              </g>
            }
          }

          <!-- 2. BATMAN (TRAJE TÁCTICO CINE + CAPUCHA KEVLAR + CAPA) -->
          @case ('batman') {
            <!-- Capa pesada oscura flotante tras hombros -->
            <g class="hero-cape">
              <path d="M 48 106 Q 16 154 14 252 L 206 252 Q 204 154 172 106 Q 140 120 110 120 Q 80 120 48 106 Z" fill="#070a10" stroke="#1e293b" stroke-width="1.4" />
              <path d="M 54 112 Q 34 166 28 252 L 74 252 L 66 124 Z" fill="#111827" opacity="0.7" />
              <path d="M 166 112 Q 186 166 192 252 L 146 252 L 154 124 Z" fill="#111827" opacity="0.7" />
            </g>

            <g class="rig-body">
              <!-- Armadura Kevlar segmentada -->
              <path d="M 45 252 L 50 150 C 54 122 76 112 110 112 C 144 112 166 122 170 150 L 175 252 Z" [attr.fill]="'url(#' + idDarkKevlar + ')'" stroke="#334155" stroke-width="1.3" />
              <path d="M 45 252 L 50 150 C 54 122 76 112 110 112 C 144 112 166 122 170 150 L 175 252 Z" [attr.fill]="'url(#' + patKevlar + ')'" />
              <!-- Placas pectorales y hombreras balísticas -->
              <polygon points="54,132 104,136 98,174 56,166" fill="#1e293b" stroke="#475569" stroke-width="1.2" />
              <polygon points="166,132 116,136 122,174 164,166" fill="#1e293b" stroke="#475569" stroke-width="1.2" />
              <polygon points="74,180 146,180 140,204 80,204" fill="#111827" stroke="#334155" stroke-width="1.1" />
              <!-- Cuello rígido táctico y doble broche de capa -->
              <path d="M 76 112 L 110 124 L 144 112 L 136 102 L 84 102 Z" fill="#0f172a" stroke="#475569" stroke-width="1.2" />
              <!-- Emblema Bat esculpido en relieve metálico sobre pecho -->
              <path
                d="M 76 146 Q 90 135 101 144 L 106 135 L 110 140 L 114 135 L 119 144 Q 130 135 144 146 Q 128 152 120 159 L 110 165 L 100 159 Q 92 152 76 146 Z"
                fill="#020617"
                [attr.stroke]="poderActivo ? '#38bdf8' : '#64748b'"
                stroke-width="1.4"
              />
            </g>

            <!-- Capucha de murciélago con orejas puntiagudas y mandíbula severa -->
            <g class="rig-head">
              <!-- Rostro humano inferior expuesto bajo capucha -->
              <path d="M 80 68 L 140 68 L 137 88 C 134 101 122 108 110 109 C 98 108 86 101 83 88 Z" [attr.fill]="'url(#' + idSkin + ')'" />
              <!-- Mandíbula firme y boca seria -->
              <path d="M 99 95 Q 110 94 121 95" fill="none" stroke="#5b3428" stroke-width="1.8" stroke-linecap="round" />
              <path d="M 105 101 Q 110 103 115 101" fill="none" stroke="rgba(0,0,0,0.28)" stroke-width="1" />
              <!-- Ojos intensos dentro de cuencas oscuras -->
              <g [attr.transform]="'translate(' + miradaX() + ', 0)'">
                <ellipse cx="94" cy="67" rx="7" ry="4" fill="#020617" />
                <ellipse cx="126" cy="67" rx="7" ry="4" fill="#020617" />
                <circle cx="94" cy="67" r="2.2" fill="#e2e8f0" />
                <circle cx="126" cy="67" r="2.2" fill="#e2e8f0" />
              </g>
              <!-- Capucha Kevlar superior con orejas afiladas -->
              <path
                d="M 75 74 L 74 44 L 78 6 L 91 32 Q 110 26 129 32 L 142 6 L 146 44 L 145 74 L 136 86 L 132 76 L 117 75 L 110 83 L 103 75 L 88 76 L 84 86 Z"
                [attr.fill]="'url(#' + idDarkKevlar + ')'"
                stroke="#475569"
                stroke-width="1.3"
              />
              <!-- Reflejo de luz fría cian en el borde de la capucha -->
              <path d="M 79 14 L 89 35 M 141 14 L 131 35" stroke="rgba(56,189,248,0.45)" stroke-width="1.3" />
            </g>

            @if (poderActivo || hablando) {
              <g class="fx-hud-orbit" pointer-events="none">
                <path d="M 38 90 A 78 78 0 0 1 64 34" fill="none" stroke="#38bdf8" stroke-width="1.8" stroke-dasharray="10 6" />
                <path d="M 182 90 A 78 78 0 0 0 156 34" fill="none" stroke="#38bdf8" stroke-width="1.8" stroke-dasharray="10 6" />
              </g>
            }
          }

          <!-- 3. SPIDER-MAN (TRAJE MCU TEXTURIZADO + TELARAÑAS 3D + LENTES EXPRESIVOS) -->
          @case ('spider_man') {
            <g class="rig-body">
              <!-- Base rojo y azul oscuro MCU -->
              <path d="M 48 252 L 53 152 C 56 125 76 114 110 114 C 144 114 164 125 167 152 L 172 252 Z" [attr.fill]="'url(#' + idNavyArmor + ')'" />
              <!-- Pecho y hombros superiores carmesí -->
              <path d="M 52 154 C 54 126 76 114 110 114 C 144 114 166 126 168 154 L 150 184 L 134 196 L 86 196 L 70 184 Z" [attr.fill]="'url(#' + idArmorRed + ')'" />
              <!-- Patrón geométrico de telaraña sobre el pecho -->
              <g stroke="#0f172a" stroke-width="1.2" opacity="0.72" fill="none">
                <line x1="110" y1="114" x2="110" y2="196" />
                <line x1="110" y1="146" x2="64" y2="128" />
                <line x1="110" y1="146" x2="156" y2="128" />
                <line x1="110" y1="146" x2="60" y2="164" />
                <line x1="110" y1="146" x2="160" y2="164" />
                <path d="M 78 134 Q 110 144 142 134" />
                <path d="M 70 154 Q 110 166 150 154" />
              </g>
              <!-- Araña pectoral dorada/negra -->
              <g transform="translate(110, 152)">
                <ellipse cx="0" cy="0" rx="5.5" ry="9" fill="#090d16" stroke="#fbbf24" stroke-width="1" />
                <path d="M -4 -4 L -14 -14 L -16 -22 M 4 -4 L 14 -14 L 16 -22 M -5 0 L -18 -2 L -20 12 M 5 0 L 18 -2 L 20 12 M -4 5 L -14 16 L -12 24 M 4 5 L 14 16 L 12 24" fill="none" stroke="#090d16" stroke-width="2.1" stroke-linecap="round" />
              </g>
            </g>

            <!-- Máscara completa carmesí con telarañas radiales y lentes mecánicos -->
            <g class="rig-head">
              <path d="M 76 62 C 76 32 92 22 110 22 C 128 22 144 32 144 62 C 144 88 130 107 110 109 C 90 107 76 88 76 62 Z" [attr.fill]="'url(#' + idArmorRed + ')'" stroke="#450a0a" stroke-width="1.3" />
              <!-- Líneas de telaraña facial convergentes en el puente nasal -->
              <g stroke="#0f172a" stroke-width="1.15" opacity="0.72" fill="none">
                <line x1="110" y1="22" x2="110" y2="109" />
                <line x1="110" y1="68" x2="84" y2="30" /><line x1="110" y1="68" x2="136" y2="30" />
                <line x1="110" y1="68" x2="76" y2="56" /><line x1="110" y1="68" x2="144" y2="56" />
                <line x1="110" y1="68" x2="84" y2="96" /><line x1="110" y1="68" x2="136" y2="96" />
                <ellipse cx="110" cy="65" rx="22" ry="26" />
              </g>
              <!-- Lentes expresivos MCU con borde negro grueso -->
              <g [attr.transform]="'translate(' + miradaX() + ', 0)'">
                <path d="M 80 56 Q 94 54 104 68 Q 92 78 82 70 Z" fill="#f8fafc" stroke="#090d16" stroke-width="3.4" stroke-linejoin="round" />
                <path d="M 140 56 Q 126 54 116 68 Q 128 78 138 70 Z" fill="#f8fafc" stroke="#090d16" stroke-width="3.4" stroke-linejoin="round" />
              </g>
            </g>

            <!-- Sentido arácnido animado -->
            @if (poderActivo || hablando) {
              <g class="fx-pulse-aura" pointer-events="none" [attr.filter]="'url(#' + fltGlow + ')'">
                <path d="M 56 32 L 42 22 L 50 38 L 34 38" fill="none" stroke="#fbbf24" stroke-width="2.5" stroke-linecap="round" />
                <path d="M 164 32 L 178 22 L 170 38 L 186 38" fill="none" stroke="#fbbf24" stroke-width="2.5" stroke-linecap="round" />
              </g>
            }
          }

          <!-- 4. CAPTAIN AMERICA (ARMADURA ESCAMADA ENDGAME + CASCO A + ESCUDO VIBRANIUM) -->
          @case ('captain_america') {
            <g class="rig-body">
              <path d="M 46 252 L 52 150 C 56 124 78 112 110 112 C 142 112 164 124 168 150 L 174 252 Z" [attr.fill]="'url(#' + idNavyArmor + ')'" stroke="#0f172a" stroke-width="1.3" />
              <!-- Escamas Endgame metálicas en pecho superior -->
              <path d="M 56 132 L 164 132 L 154 178 L 66 178 Z" [attr.fill]="'url(#' + patHex + ')'" />
              <!-- Bandas rojas y blancas abdominales -->
              <g>
                <rect x="82" y="180" width="11" height="44" fill="#dc2626" />
                <rect x="93" y="180" width="11" height="44" fill="#f8fafc" />
                <rect x="104" y="180" width="12" height="44" fill="#dc2626" />
                <rect x="116" y="180" width="11" height="44" fill="#f8fafc" />
                <rect x="127" y="180" width="11" height="44" fill="#dc2626" />
              </g>
              <!-- Arneses tácticos de cuero café -->
              <path d="M 72 114 L 82 184 M 148 114 L 138 184" stroke="#78350f" stroke-width="8" stroke-linecap="round" />
              <path d="M 72 114 L 82 184 M 148 114 L 138 184" stroke="#b45309" stroke-width="2" />
              <!-- Estrella plateada central -->
              <polygon points="110,134 114.5,144 125,145 117,152 119,163 110,157 101,163 103,152 95,145 105.5,144" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1" />

              <!-- Escudo Vibranium en brazo derecho / guardia -->
              <g class="shield-rig" [class.shield-raised]="poderActivo || postura === 'decidido' || postura === 'defensa_abierta'" transform="translate(166, 156) rotate(-14)">
                <circle r="34" [attr.fill]="'url(#' + idArmorRed + ')'" stroke="#e2e8f0" stroke-width="1.5" />
                <circle r="26" fill="#f8fafc" />
                <circle r="19" [attr.fill]="'url(#' + idArmorRed + ')'" />
                <circle r="12" fill="#1d4ed8" />
                <polygon points="0,-9 2.6,-2.5 9.2,-2 4.2,2.4 5.8,9 0,5.2 -5.8,9 -4.2,2.4 -9.2,-2 -2.6,-2.5" fill="#ffffff" />
              </g>
            </g>

            <!-- Casco táctico azul con A frontal, alas sutiles y correa de barbilla -->
            <g class="rig-head">
              <path d="M 78 60 C 78 30 92 22 110 22 C 128 22 142 30 142 60 L 140 88 C 138 101 124 108 110 109 C 96 108 82 101 80 88 Z" [attr.fill]="'url(#' + idSkin + ')'" />
              <!-- Casco superior + orejeras -->
              <path d="M 76 64 C 75 30 90 21 110 21 C 130 21 145 30 144 64 L 137 64 L 135 52 L 85 52 L 83 64 Z" [attr.fill]="'url(#' + idNavyArmor + ')'" stroke="#0f172a" stroke-width="1.2" />
              <!-- Alas blancas grabadas en casco + letra A plateada -->
              <path d="M 79 44 L 88 40 L 86 48 Z M 141 44 L 132 40 L 134 48 Z" fill="#e2e8f0" />
              <text x="110" y="42" text-anchor="middle" fill="#f8fafc" font-size="14" font-weight="900" font-family="sans-serif">A</text>
              <!-- Correa de barbilla táctico -->
              <path d="M 80 76 L 86 101 L 96 105 M 140 76 L 134 101 L 124 105" fill="none" stroke="#78350f" stroke-width="3.6" />
              <!-- Ojos y cejas decididas -->
              <g [attr.transform]="'translate(' + miradaX() + ', 0)'">
                <path d="M 88 59 Q 95 57 101 60 M 119 60 Q 125 57 132 59" stroke="#3a2618" stroke-width="2.1" fill="none" />
                <ellipse cx="95" cy="66" rx="5.5" ry="3.2" fill="#f8fafc" />
                <ellipse cx="125" cy="66" rx="5.5" ry="3.2" fill="#f8fafc" />
                <circle cx="95" cy="66" r="2.2" fill="#1d4ed8" />
                <circle cx="125" cy="66" r="2.2" fill="#1d4ed8" />
                <path d="M 101 92 Q 110 92 119 92" stroke="#6b3428" stroke-width="1.8" fill="none" />
              </g>
            </g>
          }

          <!-- 5. DOCTOR STRANGE (CAPA DE LEVITACIÓN + OJO DE AGAMOTTO + MANDALAS) -->
          @case ('doctor_strange') {
            <!-- Cuello altísimo rojo icónico de la Capa de Levitación -->
            <g class="hero-cape">
              <path d="M 40 252 L 42 128 L 62 82 L 88 104 L 132 104 L 158 82 L 178 128 L 180 252 Z" [attr.fill]="'url(#' + idCapeRed + ')'" stroke="#f59e0b" stroke-width="1.4" />
              <path d="M 62 82 L 76 116 L 88 104 Z M 158 82 L 144 116 L 132 104 Z" fill="#450a0a" opacity="0.65" />
            </g>

            <g class="rig-body">
              <!-- Túnica del Sanctum azul petróleo cruzada -->
              <path d="M 52 252 L 58 148 C 62 124 80 114 110 114 C 140 114 158 124 162 148 L 168 252 Z" fill="#0f2f44" stroke="#082f49" stroke-width="1.4" />
              <path d="M 74 118 L 122 184 L 148 118" fill="none" stroke="#1e40af" stroke-width="10" opacity="0.7" />
              <path d="M 76 120 L 114 186" stroke="#38bdf8" stroke-width="1.2" opacity="0.45" />
              <!-- Cierre dorado de capa + Ojo de Agamotto -->
              <circle cx="72" cy="134" r="6" [attr.fill]="'url(#' + idGold + ')'" />
              <circle cx="148" cy="134" r="6" [attr.fill]="'url(#' + idGold + ')'" />
              <g transform="translate(110, 148)" [attr.filter]="'url(#' + fltGlow + ')'">
                <ellipse rx="13" ry="9" [attr.fill]="'url(#' + idGold + ')'" stroke="#fef08a" stroke-width="1.2" />
                <ellipse rx="6" ry="4" fill="#10b981" />
                <circle r="2" fill="#a7f3d0" />
              </g>
            </g>

            <!-- Rostro con sienes plateadas y perilla característica -->
            <g class="rig-head">
              <path d="M 80 58 C 80 30 94 22 110 22 C 126 22 140 30 140 58 C 140 84 126 106 110 108 C 94 106 80 84 80 58 Z" [attr.fill]="'url(#' + idSkin + ')'" />
              <!-- Cabello oscuro con mechones blancos en las sienes -->
              <path d="M 78 58 C 77 30 92 18 110 18 C 128 18 143 30 142 58 C 136 42 124 34 110 35 C 96 34 84 42 78 58 Z" fill="#1e2430" />
              <path d="M 78 50 L 84 42 L 85 56 Z M 142 50 L 136 42 L 135 56 Z" fill="#e2e8f0" />
              <!-- Barba perilla estilizada -->
              <path d="M 97 86 Q 110 83 123 86 M 102 96 L 110 107 L 118 96 Z" fill="none" stroke="#1e2430" stroke-width="2.4" stroke-linecap="round" />
              <g [attr.transform]="'translate(' + miradaX() + ', 0)'">
                <ellipse cx="96" cy="64" rx="5.5" ry="3.2" fill="#f8fafc" />
                <ellipse cx="124" cy="64" rx="5.5" ry="3.2" fill="#f8fafc" />
                <circle cx="96" cy="64" r="2.2" fill="#0f766e" />
                <circle cx="124" cy="64" r="2.2" fill="#0f766e" />
                <path d="M 89 57 L 103 58 M 117 58 L 131 57" stroke="#1e2430" stroke-width="2" />
              </g>
            </g>

            <!-- Mandalas arcanos dorados girando en ambas manos -->
            <g pointer-events="none" [attr.opacity]="poderActivo || hablando ? '0.96' : '0.45'" [attr.filter]="'url(#' + fltGlow + ')'">
              <g transform="translate(46, 166)">
                <g class="fx-spin-mandala">
                  <circle r="28" fill="none" stroke="#f59e0b" stroke-width="2" stroke-dasharray="6 3" />
                  <rect x="-18" y="-18" width="36" height="36" fill="none" stroke="#fbbf24" stroke-width="1.4" />
                  <rect x="-18" y="-18" width="36" height="36" transform="rotate(45)" fill="none" stroke="#fde047" stroke-width="1.4" />
                </g>
              </g>
              <g transform="translate(174, 166)">
                <g class="fx-spin-mandala-rev">
                  <circle r="28" fill="none" stroke="#f59e0b" stroke-width="2" stroke-dasharray="6 3" />
                  <polygon points="0,-22 19,12 -19,12" fill="none" stroke="#fde047" stroke-width="1.4" />
                  <polygon points="0,22 19,-12 -19,-12" fill="none" stroke="#fbbf24" stroke-width="1.4" />
                </g>
              </g>
            </g>
          }

          <!-- 6. SUPERMAN (MAN OF STEEL SUIT TEXTURIZADO + S KRYPTONIANA + HEAT VISION) -->
          @case ('superman') {
            <g class="hero-cape">
              <path d="M 50 118 Q 22 162 20 252 L 200 252 Q 198 162 170 118 Z" [attr.fill]="'url(#' + idCapeRed + ')'" />
            </g>

            <g class="rig-body">
              <path d="M 46 252 L 52 148 C 56 120 78 110 110 110 C 142 110 164 120 168 148 L 174 252 Z" [attr.fill]="'url(#' + idNavyArmor + ')'" />
              <path d="M 46 252 L 52 148 C 56 120 78 110 110 110 C 142 110 164 120 168 148 L 174 252 Z" [attr.fill]="'url(#' + patHex + ')'" />
              <!-- Pipings metálicos kryptonianos -->
              <path d="M 68 124 Q 76 168 72 222 M 152 124 Q 144 168 148 222" fill="none" stroke="#60a5fa" stroke-width="1.5" opacity="0.55" />
              <!-- Escudo House of El pentagonal en relieves oro/carmesí -->
              <g transform="translate(110, 152)">
                <polygon points="-24,-14 24,-14 31,0 0,24 -31,0" fill="#eab308" stroke="#991b1b" stroke-width="2.2" />
                <polygon points="-21,-11 21,-11 26,0 0,20 -26,0" fill="#991b1b" />
                <path d="M -12 -6 C 4 -10 14 -1 -2 3 C -14 6 -6 14 14 10" fill="none" stroke="#eab308" stroke-width="5.2" stroke-linecap="round" />
              </g>
            </g>

            <g class="rig-head">
              <path d="M 80 58 C 80 30 94 22 110 22 C 126 22 140 30 140 58 C 140 86 126 106 110 108 C 94 106 80 86 80 58 Z" [attr.fill]="'url(#' + idSkin + ')'" />
              <!-- Cabello negro con rizo clásico frontal -->
              <path d="M 78 55 C 77 28 92 18 110 18 C 128 18 143 28 142 55 C 134 38 122 33 110 34 C 98 33 86 38 78 55 Z" fill="#0f172a" />
              <path d="M 108 32 Q 116 42 106 47" fill="none" stroke="#0f172a" stroke-width="3.2" stroke-linecap="round" />
              <g [attr.transform]="'translate(' + miradaX() + ', 0)'">
                <ellipse cx="95" cy="64" rx="5.5" ry="3.2" [attr.fill]="poderActivo ? '#fef08a' : '#f8fafc'" />
                <ellipse cx="125" cy="64" rx="5.5" ry="3.2" [attr.fill]="poderActivo ? '#fef08a' : '#f8fafc'" />
                <circle cx="95" cy="64" r="2.3" [attr.fill]="poderActivo ? '#ef4444' : '#0284c7'" [attr.filter]="poderActivo ? 'url(#' + fltGlow + ')' : ''" />
                <circle cx="125" cy="64" r="2.3" [attr.fill]="poderActivo ? '#ef4444' : '#0284c7'" [attr.filter]="poderActivo ? 'url(#' + fltGlow + ')' : ''" />
                <path d="M 101 92 Q 110 94 119 92" stroke="#6b3428" stroke-width="1.8" fill="none" />
              </g>
            </g>
          }

          <!-- 7. BLACK PANTHER (HÁBITO VIBRANIUM + GARRAS DE PLATA + VENAS CINÉTICAS) -->
          @case ('black_panther') {
            <g class="rig-body">
              <path d="M 46 252 L 52 148 C 56 122 76 112 110 112 C 144 112 164 122 168 148 L 174 252 Z" [attr.fill]="'url(#' + idDarkKevlar + ')'" />
              <path d="M 46 252 L 52 148 C 56 122 76 112 110 112 C 144 112 164 122 168 148 L 174 252 Z" [attr.fill]="'url(#' + patHex + ')'" />
              <!-- Collar plateado de garras Wakanda -->
              <path d="M 78 118 Q 110 156 142 118" fill="none" [attr.stroke]="'url(#' + idChrome + ')'" stroke-width="4.5" />
              <g [attr.fill]="'url(#' + idChrome + ')'">
                <polygon points="88,128 92,143 96,130" />
                <polygon points="99,134 102,150 106,136" />
                <polygon points="108,136 110,154 112,136" />
                <polygon points="114,136 118,150 121,134" />
                <polygon points="124,130 128,143 132,128" />
              </g>
              <!-- Venas cinéticas vibranium púrpuras -->
              <path
                d="M 64 148 L 96 176 L 110 212 L 124 176 L 156 148 M 74 176 L 146 176"
                fill="none"
                stroke="#a855f7"
                [attr.stroke-width]="poderActivo ? '2.6' : '1.3'"
                [attr.opacity]="poderActivo ? '0.95' : '0.42'"
                [attr.filter]="poderActivo ? 'url(#' + fltGlow + ')' : ''"
              />
            </g>

            <g class="rig-head">
              <!-- Casco pantera esculpido -->
              <path d="M 76 58 L 78 16 L 94 30 L 126 30 L 142 16 L 144 58 C 144 88 130 107 110 109 C 90 107 76 88 76 58 Z" [attr.fill]="'url(#' + idDarkKevlar + ')'" stroke="#475569" stroke-width="1.2" />
              <path d="M 86 42 L 106 54 L 110 88 L 114 54 L 134 42" fill="none" stroke="#94a3b8" stroke-width="1.3" />
              <!-- Lentes de pantera luminosos plata/violeta -->
              <polygon points="86,60 103,66 96,72 86,67" [attr.fill]="poderActivo ? '#d8b4fe' : '#f1f5f9'" [attr.filter]="'url(#' + fltGlow + ')'" />
              <polygon points="134,60 117,66 124,72 134,67" [attr.fill]="poderActivo ? '#d8b4fe' : '#f1f5f9'" [attr.filter]="'url(#' + fltGlow + ')'" />
            </g>
          }

          <!-- 8. WONDER WOMAN (ARMADURA ÁGUILA ORO/CARMESÍ + TIARA + LAZO DE LA VERDAD) -->
          @case ('wonder_woman') {
            <g class="rig-body">
              <path d="M 52 252 L 58 150 L 82 114 L 138 114 L 162 150 L 168 252 Z" [attr.fill]="'url(#' + idSkin + ')'" />
              <!-- Coraza guerrera roja y águila dorada -->
              <path d="M 68 144 L 84 128 L 110 140 L 136 128 L 152 144 L 144 218 L 76 218 Z" [attr.fill]="'url(#' + idArmorRed + ')'" stroke="#eab308" stroke-width="1.5" />
              <path d="M 68 144 L 90 132 L 110 144 L 130 132 L 152 144 L 138 156 L 110 149 L 82 156 Z" [attr.fill]="'url(#' + idGold + ')'" />
              <!-- Lazo dorado brillante enrollado al costado -->
              <g [attr.filter]="poderActivo ? 'url(#' + fltGlow + ')' : ''">
                <ellipse cx="154" cy="186" rx="18" ry="11" fill="none" stroke="#fde047" stroke-width="2.6" />
                <ellipse cx="154" cy="190" rx="16" ry="9" fill="none" stroke="#facc15" stroke-width="2.2" />
              </g>
            </g>

            <g class="rig-head">
              <!-- Cabello oscuro ondulado detrás -->
              <path d="M 66 44 C 58 84 58 122 68 148 L 152 148 C 162 122 162 84 154 44 Z" fill="#1e1b24" />
              <path d="M 80 58 C 80 30 94 22 110 22 C 126 22 140 30 140 58 C 140 84 126 104 110 106 C 94 104 80 84 80 58 Z" [attr.fill]="'url(#' + idSkin + ')'" />
              <path d="M 78 52 C 80 24 94 18 110 18 C 126 18 140 24 142 52 C 134 38 122 33 110 34 C 98 33 86 38 78 52 Z" fill="#1e1b24" />
              <!-- Tiara dorada con estrella roja -->
              <path d="M 80 50 L 95 40 L 110 34 L 125 40 L 140 50 L 125 46 L 110 43 L 95 46 Z" [attr.fill]="'url(#' + idGold + ')'" stroke="#78350f" stroke-width="0.9" />
              <polygon points="110,33 112,38 117,38 113,41 114,46 110,43 106,46 107,41 103,38 108,38" fill="#dc2626" />
              <g [attr.transform]="'translate(' + miradaX() + ', 0)'">
                <ellipse cx="96" cy="64" rx="5.5" ry="3.2" fill="#f8fafc" />
                <ellipse cx="124" cy="64" rx="5.5" ry="3.2" fill="#f8fafc" />
                <circle cx="96" cy="64" r="2.2" fill="#1e3a8a" />
                <circle cx="124" cy="64" r="2.2" fill="#1e3a8a" />
                <path d="M 102 90 Q 110 94 118 90" stroke="#991b1b" stroke-width="2" fill="none" />
              </g>
            </g>

            @if (poderActivo || hablando) {
              <g pointer-events="none" [attr.filter]="'url(#' + fltGlow + ')'">
                <ellipse cx="110" cy="144" rx="76" ry="28" transform="rotate(-12 110 144)" fill="none" stroke="#fde047" stroke-width="2.2" stroke-dasharray="14 6" class="pulse-ring" />
              </g>
            }
          }

          <!-- 9. THE FLASH (ARMADURA ROJA CON CONDUCTOS DE ORO + CASCO ALAS + RAYOS SPEED FORCE) -->
          @case ('flash') {
            <g class="rig-body">
              <path d="M 48 252 L 54 150 C 58 122 78 112 110 112 C 142 112 162 122 166 150 L 172 252 Z" [attr.fill]="'url(#' + idArmorRed + ')'" stroke="#450a0a" stroke-width="1.3" />
              <!-- Líneas energéticas doradas en armadura -->
              <path d="M 68 128 L 88 156 L 74 204 M 152 128 L 132 156 L 146 204" fill="none" stroke="#facc15" stroke-width="1.8" opacity="0.85" />
              <!-- Emblema circular blanco + rayo oro -->
              <g transform="translate(110, 152)" [attr.filter]="poderActivo ? 'url(#' + fltGlow + ')' : ''">
                <circle r="17" fill="#f8fafc" stroke="#eab308" stroke-width="2.6" />
                <polygon points="4,-14 -6,1 2,1 -5,14 9,-2 1,-2" fill="#eab308" stroke="#991b1b" stroke-width="1" />
              </g>
            </g>

            <g class="rig-head">
              <path d="M 78 60 C 78 30 92 22 110 22 C 128 22 142 30 142 60 L 140 88 C 138 101 124 108 110 109 C 96 108 82 101 80 88 Z" [attr.fill]="'url(#' + idSkin + ')'" />
              <!-- Capucha roja completa con rayos laterales -->
              <path d="M 76 74 C 75 30 90 20 110 20 C 130 20 145 30 144 74 L 135 80 L 132 62 L 118 60 L 110 74 L 102 60 L 88 62 L 85 80 Z" [attr.fill]="'url(#' + idArmorRed + ')'" />
              <!-- Alas-rayo doradas en orejas -->
              <polygon points="75,64 62,48 70,58 60,56 76,72" fill="#facc15" />
              <polygon points="145,64 158,48 150,58 160,56 144,72" fill="#facc15" />
              <g [attr.transform]="'translate(' + miradaX() + ', 0)'">
                <ellipse cx="95" cy="66" rx="5.2" ry="3" fill="#f8fafc" />
                <ellipse cx="125" cy="66" rx="5.2" ry="3" fill="#f8fafc" />
                <circle cx="95" cy="66" r="2.2" [attr.fill]="poderActivo ? '#38bdf8' : '#0284c7'" />
                <circle cx="125" cy="66" r="2.2" [attr.fill]="poderActivo ? '#38bdf8' : '#0284c7'" />
                <path d="M 101 92 Q 110 93 119 92" stroke="#6b3428" stroke-width="1.8" fill="none" />
              </g>
            </g>

            @if (poderActivo || hablando) {
              <g class="fx-lightning-fast" pointer-events="none" [attr.filter]="'url(#' + fltGlow + ')'">
                <polyline points="32,138 54,114 44,106 66,80" fill="none" stroke="#fde047" stroke-width="2.6" />
                <polyline points="188,138 166,114 176,106 154,80" fill="none" stroke="#38bdf8" stroke-width="2.6" />
              </g>
            }
          }

          <!-- 10. GREEN LANTERN (TRAJE CORPS ESMERALDA + ANTIFAZ + ANILLO DE PODER) -->
          @case ('green_lantern') {
            <g class="rig-body">
              <path d="M 48 252 L 54 150 C 58 122 78 112 110 112 C 142 112 162 122 166 150 L 172 252 Z" [attr.fill]="'url(#' + idDarkKevlar + ')'" />
              <path d="M 70 118 L 150 118 L 138 188 L 82 188 Z" [attr.fill]="'url(#' + idEmerald + ')'" />
              <path d="M 70 118 L 150 118 L 138 188 L 82 188 Z" [attr.fill]="'url(#' + patHex + ')'" />
              <!-- Linterna pecho brillante -->
              <g transform="translate(110, 150)" [attr.filter]="'url(#' + fltGlow + ')'">
                <circle r="15" fill="#ecfdf5" stroke="#10b981" stroke-width="2" />
                <circle r="7.5" fill="none" stroke="#059669" stroke-width="3" />
                <line x1="-10" y1="-9" x2="10" y2="-9" stroke="#059669" stroke-width="2.6" />
                <line x1="-10" y1="9" x2="10" y2="9" stroke="#059669" stroke-width="2.6" />
              </g>
              <!-- Puño alzado con anillo esmeralda luminoso -->
              <g transform="translate(168, 156)">
                <circle r="10" fill="#065f46" stroke="#34d399" stroke-width="1.8" />
                <circle cx="-4" cy="-3" r="4.5" fill="#a7f3d0" [attr.filter]="'url(#' + fltGlow + ')'" />
                @if (poderActivo || hablando) {
                  <circle cx="-4" cy="-3" r="18" fill="none" stroke="#34d399" stroke-width="2.2" class="pulse-ring" />
                }
              </g>
            </g>

            <g class="rig-head">
              <path d="M 80 58 C 80 30 94 22 110 22 C 126 22 140 30 140 58 C 140 84 126 104 110 106 C 94 104 80 84 80 58 Z" [attr.fill]="'url(#' + idSkin + ')'" />
              <path d="M 78 52 C 78 24 94 17 110 17 C 126 17 142 24 142 52 C 134 36 122 31 110 32 C 98 31 86 36 78 52 Z" fill="#291d18" />
              <!-- Antifaz esmeralda limpio -->
              <path d="M 81 58 Q 95 54 110 60 Q 125 54 139 58 L 136 72 Q 122 75 114 70 L 110 68 L 106 70 Q 98 75 84 72 Z" fill="#064e3b" stroke="#34d399" stroke-width="1.2" />
              <g [attr.transform]="'translate(' + miradaX() + ', 0)'">
                <ellipse cx="95" cy="64" rx="5" ry="2.8" fill="#a7f3d0" [attr.filter]="'url(#' + fltGlow + ')'" />
                <ellipse cx="125" cy="64" rx="5" ry="2.8" fill="#a7f3d0" [attr.filter]="'url(#' + fltGlow + ')'" />
                <path d="M 101 90 Q 110 92 119 90" stroke="#6b3428" stroke-width="1.8" fill="none" />
              </g>
            </g>
          }

          <!-- 11. DAREDEVIL (CASCO CON CUERNOS ROJOS + VISOR CARMESÍ + SONAR) -->
          @case ('daredevil') {
            <g class="rig-body">
              <path d="M 48 252 L 54 150 C 58 122 78 112 110 112 C 142 112 162 122 166 150 L 172 252 Z" fill="#450a0a" stroke="#1e1b18" stroke-width="1.4" />
              <path d="M 48 252 L 54 150 C 58 122 78 112 110 112 C 142 112 162 122 166 150 L 172 252 Z" [attr.fill]="'url(#' + patKevlar + ')'" />
              <polygon points="74,132 146,132 138,184 82,184" fill="#7f1d1d" stroke="#ef4444" stroke-width="1.2" />
              <text x="110" y="164" text-anchor="middle" fill="#fca5a5" font-size="18" font-weight="900" font-family="serif">DD</text>
            </g>

            <g class="rig-head">
              <path d="M 80 62 L 140 62 L 138 88 C 134 101 122 108 110 109 C 98 108 86 101 82 88 Z" [attr.fill]="'url(#' + idSkin + ')'" />
              <!-- Casco rojo oscuro con cuernos cortos -->
              <path d="M 78 72 C 77 32 90 22 110 22 C 130 22 143 32 142 72 L 128 74 L 116 74 L 110 82 L 104 74 L 92 74 Z" fill="#7f1d1d" stroke="#450a0a" stroke-width="1.3" />
              <polygon points="86,36 79,14 96,28" fill="#dc2626" />
              <polygon points="134,36 141,14 124,28" fill="#dc2626" />
              <!-- Lentes visor rojo -->
              <rect x="84" y="61" width="21" height="10" rx="3" fill="#dc2626" stroke="#fca5a5" stroke-width="1" />
              <rect x="115" y="61" width="21" height="10" rx="3" fill="#dc2626" stroke="#fca5a5" stroke-width="1" />
              <path d="M 101 92 L 119 92" stroke="#5b3428" stroke-width="1.8" />
            </g>

            @if (poderActivo || hablando) {
              <g class="fx-pulse-aura" pointer-events="none">
                <circle cx="110" cy="66" r="46" fill="none" stroke="#f43f5e" stroke-width="1.8" stroke-dasharray="8 6" />
                <circle cx="110" cy="66" r="62" fill="none" stroke="#fb7185" stroke-width="1.2" opacity="0.6" />
              </g>
            }
          }

          <!-- 12. CYBORG (MITAD HUMANO / MITAD TITANIO CROMADO + NÚCLEO MOTHERBOX) -->
          @default {
            <g class="rig-body">
              <path d="M 44 252 L 50 148 C 54 120 76 110 110 110 C 144 110 166 120 170 148 L 176 252 Z" [attr.fill]="'url(#' + idChrome + ')'" stroke="#0f172a" stroke-width="1.5" />
              <path d="M 64 134 L 96 154 L 84 198 M 156 134 L 124 154 L 136 198" fill="none" stroke="#1e293b" stroke-width="2" />
              <!-- Núcleo energético cyan pectoral -->
              <g transform="translate(110, 152)" [attr.filter]="'url(#' + fltGlow + ')'">
                <circle r="14" fill="#082f49" stroke="#38bdf8" stroke-width="2.4" />
                <circle r="7" fill="#00e5ff" />
                <circle r="3" fill="#ffffff" />
              </g>
            </g>

            <g class="rig-head">
              <!-- Mitad humana derecha (pantalla izquierda) -->
              <path d="M 80 58 C 80 30 94 22 110 22 L 110 108 C 94 106 80 86 80 58 Z" [attr.fill]="'url(#' + idSkin + ')'" />
              <path d="M 79 52 C 79 26 94 18 110 18 L 110 35 C 96 34 86 40 79 52 Z" fill="#18181b" />
              <!-- Mitad cibernética titanio (pantalla derecha) -->
              <path d="M 110 20 C 128 20 143 30 143 58 C 143 86 128 106 110 109 Z" [attr.fill]="'url(#' + idChrome + ')'" stroke="#334155" stroke-width="1.3" />
              <!-- Ojo humano + ojo biónico láser rojo -->
              <g [attr.transform]="'translate(' + miradaX() + ', 0)'">
                <ellipse cx="95" cy="64" rx="5.2" ry="3" fill="#f8fafc" />
                <circle cx="95" cy="64" r="2.2" fill="#291d18" />
                <circle cx="126" cy="64" r="5" fill="#450a0a" stroke="#00e5ff" stroke-width="1.2" />
                <circle cx="126" cy="64" r="2.6" fill="#ef4444" [attr.filter]="'url(#' + fltGlow + ')'" />
                <path d="M 101 91 Q 106 92 110 91" stroke="#6b3428" stroke-width="1.8" fill="none" />
                <line x1="110" y1="91" x2="121" y2="91" stroke="#334155" stroke-width="2" />
              </g>
            </g>
          }
        }
      </svg>
    </div>
  `,
  styles: [`
    .hero-cine-root {
      position: relative;
      width: 184px;
      height: 232px;
      display: grid;
      place-items: end center;
      transition: transform 0.6s cubic-bezier(0.22, 1, 0.36, 1);
      will-change: transform;
    }
    .hero-cine-root.power-on {
      transform: translateY(-4px) scale(1.03);
    }
    .hero-cine-root.posture-decided {
      transform: translateY(-3px) scale(1.02);
    }
    .hero-cine-root.posture-tense {
      transform: translateX(-2px) scale(0.99);
    }
    .cinema-rim-aura {
      position: absolute;
      inset: 16px 24px 30px;
      border-radius: 50%;
      background: radial-gradient(circle, color-mix(in srgb, var(--hero-energy, #00e5ff) 32%, transparent), transparent 68%);
      filter: blur(12px);
      opacity: 0.72;
      pointer-events: none;
      transition: opacity 0.4s ease, transform 0.4s ease;
    }
    .cinema-rim-aura.aura-active {
      opacity: 1;
      transform: scale(1.1);
    }
    .hero-svg {
      width: 100%;
      height: 100%;
      overflow: visible;
      filter: drop-shadow(0 14px 22px rgba(0, 0, 0, 0.68));
    }
    .rig-body {
      transform-origin: 110px 240px;
      animation: heroBreathe 4.2s ease-in-out infinite;
      animation-delay: var(--breath-delay, 0ms);
    }
    .rig-head {
      transform-origin: 110px 104px;
      animation: heroHeadIdle 5.2s ease-in-out infinite alternate;
      animation-delay: var(--breath-delay, 0ms);
    }
    .hero-cape {
      transform-origin: 110px 115px;
      animation: capeSweep 3.4s ease-in-out infinite alternate;
    }
    .fx-spin-mandala {
      transform-box: fill-box;
      transform-origin: center;
      animation: spinSlow 7s linear infinite;
    }
    .fx-spin-mandala-rev {
      transform-box: fill-box;
      transform-origin: center;
      animation: spinSlowRev 6s linear infinite;
    }
    .shield-rig {
      transition: transform 0.55s cubic-bezier(0.22, 1, 0.36, 1);
    }
    .shield-rig.shield-raised {
      transform: translate(152px, 146px) rotate(4deg) scale(1.1);
    }
    .hero-arm-action {
      transition: transform 0.5s cubic-bezier(0.22, 1, 0.36, 1);
      transform-origin: 164px 146px;
    }
    .hero-arm-action.arm-raised {
      transform: translate(-6px, -8px) rotate(-14deg);
    }
    .pulse-ring,
    .fx-pulse-aura,
    .fx-hud-orbit {
      transform-box: fill-box;
      transform-origin: center;
      animation: heroPulseFX 1.8s ease-in-out infinite alternate;
    }
    .fx-lightning-fast {
      animation: lightningZap 0.7s ease-in-out infinite alternate;
    }
    @keyframes heroBreathe {
      0%, 100% { transform: translateY(0) scaleY(1); }
      50% { transform: translateY(-1.8px) scaleY(1.012); }
    }
    @keyframes heroHeadIdle {
      0% { transform: rotate(-1deg); }
      100% { transform: rotate(1.4deg) translateY(-1px); }
    }
    @keyframes capeSweep {
      0% { transform: skewX(-1.5deg); }
      100% { transform: skewX(2.2deg); }
    }
    @keyframes spinSlow {
      from { transform: rotate(0deg); }
      to { transform: rotate(360deg); }
    }
    @keyframes spinSlowRev {
      from { transform: rotate(360deg); }
      to { transform: rotate(0deg); }
    }
    @keyframes heroPulseFX {
      0% { opacity: 0.62; transform: scale(0.96); }
      100% { opacity: 1; transform: scale(1.06); }
    }
    @keyframes lightningZap {
      0% { opacity: 0.55; transform: translateX(-2px); }
      100% { opacity: 1; transform: translateX(2px); }
    }
    @media (prefers-reduced-motion: reduce) {
      .rig-body,
      .rig-head,
      .hero-cape,
      .fx-spin-mandala,
      .fx-spin-mandala-rev,
      .pulse-ring,
      .fx-pulse-aura,
      .fx-hud-orbit,
      .fx-lightning-fast {
        animation: none !important;
      }
    }
  `],
})
export class HeroeCineComponent {
  private readonly uid = ++siguienteHeroeUid;

  @Input({ required: true }) heroe!: PerfilHeroe;
  @Input() postura: PosturaCorporal = 'sentado_firme';
  @Input() mirada: DireccionMirada = 'centro';
  @Input() hablando = false;
  @Input() poderActivo = false;
  @Input() retrasoRespiracionMs = 120;

  readonly idSkin = `h_skin_${this.uid}`;
  readonly idArmorRed = `h_ared_${this.uid}`;
  readonly idGold = `h_gold_${this.uid}`;
  readonly idChrome = `h_chr_${this.uid}`;
  readonly idDarkKevlar = `h_kev_${this.uid}`;
  readonly idNavyArmor = `h_nav_${this.uid}`;
  readonly idCapeRed = `h_cpred_${this.uid}`;
  readonly idEmerald = `h_em_${this.uid}`;
  readonly patHex = `h_phex_${this.uid}`;
  readonly patKevlar = `h_pkev_${this.uid}`;
  readonly fltGlow = `h_glow_${this.uid}`;

  miradaX(): number {
    if (this.mirada === 'izquierda') return -2.2;
    if (this.mirada === 'derecha') return 2.2;
    return 0;
  }
}
