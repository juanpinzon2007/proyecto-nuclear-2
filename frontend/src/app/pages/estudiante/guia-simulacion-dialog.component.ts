import { DatePipe } from '@angular/common';
import { Component, inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MiConvocatoriaItem } from '../../core/api.models';

@Component({
  selector: 'app-guia-simulacion-dialog',
  standalone: true,
  imports: [DatePipe, MatButtonModule, MatDialogModule, MatIconModule],
  template: `
    <header class="guide-header">
      <span class="guide-icon"><mat-icon aria-hidden="true">explore</mat-icon></span>
      <div>
        <h2 mat-dialog-title>Antes de empezar</h2>
        <p>{{ convocatoria.caso_nombre }}</p>
      </div>
    </header>

    <mat-dialog-content>
      <div class="time-note" id="guia-tiempo">
        <mat-icon aria-hidden="true">timer</mat-icon>
        <div>
          <strong>Hasta {{ convocatoria.tiempo_maximo_minutos }} min por intento</strong>
          <p>El cronómetro empieza al pulsar «Empezar intento».</p>
          <p>Confirma tu ingreso antes del {{ convocatoria.fecha_limite_mitad_tiempo | date:'dd/MM/yyyy · HH:mm' }}.</p>
        </div>
      </div>

      @if (contexto || rol) {
        <section class="case-brief" aria-labelledby="guia-contexto">
          <h3 id="guia-contexto">Contexto del caso</h3>
          @if (contexto) {
            <p>{{ contexto }}</p>
          }
          @if (rol) {
            <p>{{ rol }}</p>
          }
        </section>
      }

      <h3 class="steps-heading">Cómo jugar</h3>
      <ol class="guide-steps">
        <li><strong>Lee la escena.</strong> Fíjate en qué ocurre y qué te preguntan.</li>
        <li><strong>Elige una carta.</strong> Cada carta es una respuesta. Usa el Joker para comparar opciones si está disponible.</li>
        <li><strong>Pulsa «Lanzar carta».</strong> Puedes explicar tu elección antes de pulsar el botón, que guarda tu respuesta.</li>
        <li><strong>Entrega la simulación.</strong> Revisa tus respuestas, pulsa «Entregar simulación» y confirma.</li>
      </ol>
    </mat-dialog-content>

    <mat-dialog-actions align="end">
      <button mat-stroked-button type="button" [mat-dialog-close]="false">Volver al portal</button>
      <button mat-flat-button color="primary" type="button" [mat-dialog-close]="true">
        <mat-icon aria-hidden="true">play_arrow</mat-icon> Empezar intento
      </button>
    </mat-dialog-actions>
  `,
  styles: `
    :host {
      display: flex;
      flex-direction: column;
      min-height: 0;
      background: var(--surface-raised);
      color: var(--text);
    }
    .guide-header {
      display: flex;
      align-items: center;
      gap: 14px;
      padding: clamp(14px, 4vw, 24px);
      border-bottom: 1px solid var(--line);
      background: radial-gradient(ellipse at top left, #29627852, transparent 72%);
    }
    .guide-icon {
      display: grid;
      place-items: center;
      flex: 0 0 44px;
      height: 44px;
      border-radius: var(--control-radius);
      border: 1px solid var(--line-strong);
      background: var(--panel);
      color: var(--cyan);
    }
    .guide-header h2 {
      margin: 0;
      padding: 0;
      font: 700 clamp(26px, 5vw, 36px)/1.1 var(--display);
      color: var(--text);
    }
    .guide-header h2::before { display: none; }
    .guide-header p { margin: 4px 0 0; color: var(--muted); font-size: var(--type-control); }
    mat-dialog-content {
      min-height: 0;
      padding: 16px clamp(14px, 4vw, 24px);
      font: 400 var(--type-control)/1.55 var(--body);
      color: var(--muted);
    }
    .time-note {
      display: flex;
      align-items: flex-start;
      gap: 9px;
      padding: 10px 12px;
      border: 1px solid var(--line-strong);
      border-radius: var(--control-radius);
      background: var(--panel);
    }
    .time-note mat-icon { flex: none; color: var(--amber); }
    .time-note strong, .guide-steps strong, h3 { color: var(--text); }
    .time-note p { margin: 3px 0 0; }
    .case-brief { margin: 16px 0; }
    h3 { margin: 0 0 4px; font-size: var(--type-control); }
    .case-brief p { margin: 0; white-space: pre-line; overflow-wrap: anywhere; }
    .case-brief p + p { margin-top: 6px; }
    .steps-heading { margin-top: 16px; }
    .guide-steps { display: grid; gap: 8px; margin: 6px 0 0; padding-inline-start: 24px; }
    .guide-steps li::marker { color: var(--cyan-soft); font-weight: 700; }
    mat-dialog-actions {
      gap: 8px;
      margin: 0;
      padding: 12px clamp(14px, 4vw, 24px);
      border-top: 1px solid var(--line);
      background: var(--panel);
    }
    @media (max-width: 420px) {
      .guide-icon { display: none; }
      mat-dialog-actions > button { flex: 1 1 124px; padding-inline: 8px; }
    }
  `,
})
export class GuiaSimulacionDialogComponent {
  readonly convocatoria = inject<MiConvocatoriaItem>(MAT_DIALOG_DATA);
  readonly contexto = this.convocatoria.contexto_historia?.trim();
  readonly rol = this.convocatoria.desarrollo_situacional?.trim();
}
