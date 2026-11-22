import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { DireccionMirada, PerfilHeroe, PosturaCorporal } from './cinema.types';

@Component({
  selector: 'app-heroe-cine',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @let perfil = heroe();
    @let gesto = postura();
    <div
      class="hero"
      [class.is-speaking]="hablando()"
      [class.power-on]="poderActivo()"
      [class.is-facing-left]="mirada() === 'izquierda'"
      [class.is-leaning]="gesto === 'inclinado_adelante' || gesto === 'senalar_orden'"
      [class.is-listening]="gesto === 'escucha_empatica'"
      [class.is-tense]="gesto === 'retroceso_tension'"
      [class.is-steady]="gesto === 'decidido' || gesto === 'defensa_abierta'"
      [attr.data-power]="perfil.efectoPoder"
      [style.--hero-energy]="perfil.colorEnergia"
      [style.--breath-delay]="retrasoRespiracionMs() + 'ms'"
      [style.--gesture-delay]="retrasoGestoMs() + 'ms'"
    >
      <span class="hero-halo" aria-hidden="true"></span>
      @if (poderActivo()) {
        <span class="hero-effect" aria-hidden="true"></span>
      }
      <div class="hero-pose">
        @for (avatar of [perfil]; track avatar.id) {
          <img
            class="hero-portrait"
            [src]="'simulador/heroes/' + avatar.id + '.png'"
            [alt]="etiqueta() + ' como ' + avatar.nombre"
            width="384"
            height="384"
            decoding="async"
            draggable="false"
          />
        }
        @if (gesto === 'brazo_levantado') {
          <img class="hero-gesture hero-vote" src="simulador/heroes/voto.png" alt="" aria-hidden="true" />
        }
        @if (gesto === 'senalar_orden') {
          <img class="hero-gesture hero-point" src="simulador/heroes/senal.png" alt="" aria-hidden="true" />
        }
      </div>
    </div>
  `,
  styles: [`
    :host {
      display: block;
      width: 100%;
      height: 100%;
    }

    .hero, .hero-pose {
      position: relative;
      width: 100%;
      height: 100%;
    }

    .hero {
      --facing: 1;
      isolation: isolate;
    }

    .hero.is-facing-left {
      --facing: -1;
    }

    .hero-pose {
      transform-origin: 50% 91%;
      transition: transform 460ms cubic-bezier(0.22, 1, 0.36, 1);
    }

    .hero-portrait {
      display: block;
      width: 100%;
      height: 100%;
      object-fit: contain;
      transform-origin: 50% 91%;
      filter: drop-shadow(0 8px 10px #05080ec7);
      animation: heroIdle 5.6s ease-in-out var(--breath-delay) infinite;
    }

    .hero-halo {
      position: absolute;
      inset: 8% 4% 10%;
      border-radius: 48%;
      background: radial-gradient(ellipse, color-mix(in srgb, var(--hero-energy) 44%, transparent), transparent 71%);
      opacity: 0.24;
      transition: opacity 380ms ease;
      pointer-events: none;
    }

    .hero.is-speaking .hero-halo { opacity: 0.65; }
    .hero.power-on .hero-halo { opacity: 0.96; }
    .hero.is-speaking .hero-portrait {
      animation: heroSpeak 2.85s ease-in-out infinite;
    }
    .hero.is-leaning .hero-pose {
      transform: translateX(calc(var(--facing) * 3%)) rotate(calc(var(--facing) * 3deg));
    }
    .hero.is-listening .hero-pose {
      transform: rotate(calc(var(--facing) * 1.5deg));
    }
    .hero.is-tense .hero-pose {
      transform: translateX(calc(var(--facing) * -2%)) rotate(calc(var(--facing) * -2.5deg));
    }
    .hero.is-steady .hero-pose, .hero.power-on .hero-pose {
      transform: translateY(-2%);
    }

    .hero-gesture {
      position: absolute;
      object-fit: contain;
      filter: drop-shadow(0 4px 5px #05080eda)
        drop-shadow(0 0 4px color-mix(in srgb, var(--hero-energy) 52%, transparent));
    }

    .hero-vote {
      --hand-angle: -15deg;
      inline-size: 26%;
      block-size: 54%;
      inset-block-end: 12%;
      inset-inline-start: 6%;
      transform-origin: 50% 91%;
      animation: raiseHand 520ms cubic-bezier(0.17, 1, 0.3, 1) var(--gesture-delay) both;
      rotate: var(--hand-angle);
    }

    .is-facing-left .hero-vote {
      --hand-angle: 15deg;
      inset-inline: auto 6%;
      scale: -1 1;
    }

    .hero-point {
      inline-size: 59%;
      block-size: 35%;
      inset-block-end: 15%;
      inset-inline-start: 55%;
      animation: pointHand 740ms cubic-bezier(0.17, 1, 0.3, 1) both;
    }

    .is-facing-left .hero-point {
      inset-inline: auto 55%;
      scale: -1 1;
    }

    .hero-effect {
      position: absolute;
      inset: 12% 7% 7%;
      border: 1px solid var(--hero-energy);
      border-radius: 50%;
      box-shadow: inset 0 0 18px color-mix(in srgb, var(--hero-energy) 64%, transparent);
      animation: energyPulse 950ms ease-out both;
    }

    [data-power="escudo"] .hero-effect {
      border-width: 2px;
      border-style: double;
      border-radius: 46% 46% 61% 61% / 38% 38% 72% 72%;
    }

    [data-power="destello"] .hero-effect {
      border-style: dashed;
      animation-name: energyFlash;
    }

    @keyframes heroIdle {
      0%, 100% { transform: translateY(0); }
      52% { transform: translateY(-1.8%); }
    }

    @keyframes heroSpeak {
      0%, 100% { transform: rotate(0); }
      24% { transform: translateY(-1%) rotate(-1deg); }
      59% { transform: rotate(0.7deg); }
    }

    @keyframes raiseHand {
      from { opacity: 0; transform: translateY(22%) rotate(18deg); }
      70% { opacity: 1; transform: translateY(-5%); }
      to { opacity: 1; transform: translateY(0); }
    }

    @keyframes pointHand {
      from { opacity: 0; transform: translateX(calc(var(--facing) * -20%)); }
      to { opacity: 1; transform: translateX(0); }
    }

    @keyframes energyPulse {
      0% { opacity: 0; transform: scale(0.63); }
      28% { opacity: 0.88; }
      100% { opacity: 0; transform: scale(1.21); }
    }

    @keyframes energyFlash {
      0% { opacity: 0; transform: rotate(-16deg) scale(0.76); }
      23% { opacity: 0.88; }
      100% { opacity: 0; transform: rotate(22deg) scale(1.11); }
    }

    @media (prefers-reduced-motion: reduce) {
      .hero-pose, .hero-halo { transition: none; }
      .hero .hero-portrait, .hero-gesture { animation: none; }
      .hero-effect { display: none; }
    }
  `],
})
export class HeroeCineComponent {
  readonly heroe = input.required<PerfilHeroe>();
  readonly etiqueta = input.required<string>();
  readonly postura = input<PosturaCorporal>('sentado_firme');
  readonly mirada = input<DireccionMirada>('centro');
  readonly hablando = input(false);
  readonly poderActivo = input(false);
  readonly retrasoRespiracionMs = input(120);
  readonly retrasoGestoMs = input(0);
}
