import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { ResultadoIntentoDetalle } from '../../core/api.models';

@Component({
  selector: 'app-simulador-resultado',
  standalone: true,
  imports: [CommonModule, RouterLink, MatButtonModule, MatCardModule, MatIconModule],
  template: `
    <div class="res-header">
      <a mat-stroked-button routerLink="/estudiante">
        <mat-icon>arrow_back</mat-icon> Volver al Portal
      </a>
      <span class="tag green">{{ res.estado_intento }} · {{ res.modalidad }}</span>
    </div>

    <mat-card class="panel result-head stagger">
      <mat-card-content>
        <div class="spread head-top">
          <div>
            <p class="eyebrow green">Estado: Simulación Finalizada (RF-13 · RF-14)</p>
            <h1>{{ res.caso_nombre }}</h1>
          </div>
          <span class="ref mono">{{ res.rubrica_nombre }}</span>
        </div>

        <div class="score-layout">
          <div class="score-ring" [style.--score]="res.nota_final + '%'">
            <div class="score-value">
              <span>{{ res.nota_final | number:'1.1-2' }}</span>
              <small>/ 100 PTS</small>
            </div>
          </div>

          <div class="score-copy">
            <div class="spread mono">
              <span>ÍNDICE DE DESEMPEÑO GLOBAL</span>
              <b class="green">{{ res.nota_final | number:'1.1-2' }} / 100</b>
            </div>
            <div class="meter">
              <span [style.width.%]="res.nota_final" style="--meter-color: var(--green)"></span>
            </div>
            <div class="stats-row mono">
              <span>ACIERTOS: <strong class="cyan">{{ res.aciertos }} / {{ res.total_preguntas }}</strong></span>
              <span>RESPONDIDAS: <strong class="cyan">{{ res.respondidas }} / {{ res.total_preguntas }}</strong></span>
            </div>
            <p class="summary">{{ res.comentario_automatico }}</p>
          </div>
        </div>
      </mat-card-content>
    </mat-card>

    @if (res.retroalimentacion_docente) {
      <mat-card class="panel fb-card">
        <mat-card-header>
          <mat-card-title>Retroalimentación General del Docente (RF-26)</mat-card-title>
          <mat-card-subtitle>{{ res.fecha_retroalimentacion | date:'medium' }}</mat-card-subtitle>
        </mat-card-header>
        <mat-card-content style="padding-top:14px; font-size:15px; line-height:1.6;">
          {{ res.retroalimentacion_docente }}
        </mat-card-content>
      </mat-card>
    }

    @if (res.criterios.length) {
      <section class="panel panel-pad chart-card">
        <div class="spread">
          <div>
            <p class="eyebrow green">Desglose de Evaluación</p>
            <h2 class="section-heading">Criterios de Rúbrica (RF-17)</h2>
          </div>
          <span class="tag green">RÚBRICA</span>
        </div>

        <div class="chart-bars">
          @for (c of res.criterios; track c.id_criterio) {
            <div class="chart-row">
              <span>{{ c.nombre }} ({{ c.peso }}%)</span>
              <i><b [style.width.%]="c.puntaje_obtenido"></b></i>
              <strong>{{ c.puntaje_obtenido | number:'1.1-2' }}</strong>
            </div>
          }
        </div>

        <div class="criterios-grid stagger">
          @for (c of res.criterios; track c.id_criterio) {
            <article class="crit-card">
              <div class="crit-top">
                <strong>{{ c.nombre }}</strong>
                <span class="tag amber">PESO {{ c.peso }}%</span>
              </div>
              <div class="crit-score mono">
                <span>{{ c.puntaje_obtenido | number:'1.1-2' }}<small>/100</small></span>
                <span class="tag green">{{ c.nivel_nombre }}</span>
              </div>
              <div class="meter" style="height: 8px;">
                <span [style.width.%]="c.puntaje_obtenido"></span>
              </div>
              <p class="muted crit-desc">{{ c.nivel_descriptor }}</p>
            </article>
          }
        </div>
      </section>
    }

    <section class="panel events">
      <div class="events-head spread">
        <div>
          <p class="eyebrow">Bitácora de Decisiones (RF-08 · RF-14)</p>
          <h3>Justificaciones Teóricas por Pregunta</h3>
        </div>
        <span class="tag">{{ res.preguntas.length }} ITEMS</span>
      </div>

      <div class="q-review-list">
        @for (q of res.preguntas; track q.pregunta_id; let qi = $index) {
          <div class="event-row" [class.q-ok]="q.es_correcta" [class.q-bad]="!q.es_correcta">
            <div class="event-top">
              <b class="event-badge" [class.amber]="!q.es_correcta">{{ q.es_correcta ? '✓' : '!' }}</b>
              <span class="mono cyan">ESC-{{ q.escenario_orden }} · P{{ qi + 1 }}</span>
              <strong class="q-title-txt">{{ q.enunciado }}</strong>
              <span class="chip" [class.ok]="q.es_correcta" [class.bad]="!q.es_correcta">
                {{ !q.respondida ? 'SIN RESPONDER (0 PTS)' : (q.es_correcta ? 'CORRECTA' : 'INCORRECTA') }}
              </span>
            </div>

            <div class="event-body">
              <div class="q-ans"><strong>Tu selección:</strong> {{ q.opcion_elegida_texto }}</div>
              <div class="q-just"><strong>Justificación:</strong> {{ q.justificacion_elegida }}</div>
              @if (!q.es_correcta && q.opcion_correcta_texto) {
                <div class="q-corr">
                  <strong>Respuesta esperada:</strong> {{ q.opcion_correcta_texto }}
                  @if (q.justificacion_correcta) {
                    <div style="margin-top:4px;"><em>Fundamento:</em> {{ q.justificacion_correcta }}</div>
                  }
                </div>
              }
              @if (q.reflexion_estudiante) {
                <div class="q-refl"><strong>Tu reflexión:</strong> {{ q.reflexion_estudiante }}</div>
              }
            </div>
          </div>
        }
      </div>
    </section>
  `,
  styles: [`
    :host { display: grid; gap: 16px; }
    .res-header { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; }
    .result-head { padding: 22px !important; margin-bottom: 0 !important; }
    .head-top { margin-bottom: 16px; }
    .head-top h1 { margin: 4px 0 0; font-family: var(--display); font-size: clamp(28px, 4.5vw, 38px); text-transform: uppercase; color: var(--text); }
    .ref { padding: 8px 12px; border: 1px solid rgba(184, 211, 214, 0.3); background: #232a34; color: var(--text) !important; }
    .score-layout { display: grid; grid-template-columns: 150px 1fr; gap: 20px; align-items: center; }
    .score-ring { --score: 76%; width: 142px; height: 142px; display: grid; place-items: center; position: relative; border-radius: 50%; background: conic-gradient(var(--green) var(--score), rgba(184, 211, 214, 0.14) 0); box-shadow: 0 0 28px rgba(0, 232, 148, 0.16); }
    .score-ring::after { content: ''; position: absolute; inset: 14px; border-radius: 50%; background: #0d1219; border: 1px solid rgba(184, 211, 214, 0.14); }
    .score-value { position: relative; z-index: 1; display: grid; place-items: center; line-height: 1; text-align: center; font-family: var(--mono); }
    .score-value span { color: var(--green); font-size: 30px; font-weight: 700; }
    .score-value small { margin-top: 4px; color: var(--muted); font-size: 11px; }
    .score-copy { display: grid; gap: 10px; }
    .stats-row { display: flex; gap: 18px; flex-wrap: wrap; color: var(--muted); }
    .summary { margin: 0; padding-top: 10px; border-top: 1px solid rgba(184, 211, 214, 0.14); color: var(--text); font-size: 14px; line-height: 1.55; }
    .fb-card { border-left: 4px solid var(--amber) !important; margin-bottom: 0 !important; }
    .chart-card { display: grid; gap: 16px; background: linear-gradient(145deg, rgba(0, 229, 244, 0.06), rgba(0, 232, 148, 0.04)), rgba(16, 20, 27, 0.94); }
    .section-heading { margin: 4px 0 0; font-family: var(--display); font-size: 26px; text-transform: uppercase; }
    .chart-bars { display: grid; gap: 12px; }
    .chart-row { display: grid; grid-template-columns: 1.1fr 1.6fr 56px; gap: 10px; align-items: center; }
    .chart-row span { font: 12px var(--mono); text-transform: uppercase; color: #cbd6d8; }
    .chart-row i { height: 14px; border: 1px solid rgba(184, 211, 214, 0.2); background: #05080d; overflow: hidden; }
    .chart-row b { display: block; height: 100%; background: var(--cyan); box-shadow: 0 0 14px var(--cyan); }
    .chart-row strong { color: var(--cyan); font: 15px var(--mono); text-align: right; }
    .criterios-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 12px; }
    .crit-card { display: grid; gap: 10px; padding: 16px; background: #0b1017; border: 1px solid var(--line); border-left: 4px solid var(--cyan); }
    .crit-top, .crit-score { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
    .crit-score { font-size: 22px; color: var(--cyan); }
    .crit-score small { font-size: 12px; color: var(--muted); }
    .crit-desc { margin: 0; font-size: 12px; }
    .events-head { padding: 18px 20px; border-bottom: 1px solid var(--line); }
    .events-head h3 { margin: 4px 0 0; font-family: var(--display); font-size: 24px; text-transform: uppercase; }
    .q-review-list { display: grid; }
    .event-row { padding: 16px 20px; border-top: 1px solid rgba(184, 211, 214, 0.12); display: grid; gap: 8px; }
    .event-row.q-ok { border-left: 4px solid var(--green); }
    .event-row.q-bad { border-left: 4px solid var(--red); }
    .event-top { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
    .event-badge { display: grid; place-items: center; width: 26px; height: 26px; border-radius: 50%; border: 1px solid rgba(0, 232, 148, 0.55); color: var(--green); font: 700 14px var(--mono); }
    .event-badge.amber { border-color: rgba(255, 184, 0, 0.65); color: var(--amber); }
    .q-title-txt { flex: 1; color: var(--text); font-size: 15px; }
    .event-body { display: grid; gap: 6px; padding-left: 36px; font-size: 13px; color: var(--muted); }
    .q-corr { background: rgba(0, 232, 148, 0.08); border: 1px solid rgba(0, 232, 148, 0.3); padding: 8px 12px; color: #a7f3d0; }
    .q-refl { background: #0b1017; border: 1px solid rgba(184, 211, 214, 0.16); padding: 8px 12px; color: var(--text); }
    @media (max-width: 780px) {
      .score-layout, .chart-row { grid-template-columns: 1fr; }
      .score-ring { margin: auto; }
      .chart-row strong { text-align: left; }
      .event-body { padding-left: 0; }
    }
  `],
})
export class SimuladorResultadoComponent {
  @Input({ required: true }) res!: ResultadoIntentoDetalle;
}

