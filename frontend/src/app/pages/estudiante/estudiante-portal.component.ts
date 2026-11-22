import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { firstValueFrom } from 'rxjs';
import { mensajeError } from '../../core/api-error';
import { ConsentimientoEstado, MiConvocatoriaItem } from '../../core/api.models';
import { ParticipationService } from '../../core/participation.service';
import { SchedulingService } from '../../core/scheduling.service';

@Component({
  selector: 'app-estudiante-portal',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
  ],
  template: `
    <div class="page role-dashboard">
      <header class="panel dashboard-hero dashboard-cover-estudiante">
        <div class="dashboard-copy">
          <p class="eyebrow">Misiones asignadas</p>
          <h1>Portal del Estudiante</h1>
          <p class="dashboard-description">Revisa tu convocatoria, entra a la simulación y consulta tus resultados.</p>
          <div class="dashboard-actions">
            <button mat-stroked-button type="button" (click)="cargarPortal()" [disabled]="cargando()">
              <mat-icon aria-hidden="true">refresh</mat-icon> Actualizar convocatorias
            </button>
          </div>
        </div>
      </header>

      <dl class="dashboard-summary" aria-label="Resumen de convocatorias">
        <div class="dashboard-stat">
          <dt><span class="dashboard-stat-icon"><mat-icon aria-hidden="true">assignment</mat-icon></span> Convocatorias</dt>
          <dd>{{ convocatorias().length }}</dd>
        </div>
        <div class="dashboard-stat dashboard-tone-green">
          <dt><span class="dashboard-stat-icon"><mat-icon aria-hidden="true">play_circle_outline</mat-icon></span> En curso</dt>
          <dd>{{ resumen().enCurso }}</dd>
        </div>
        <div class="dashboard-stat dashboard-tone-slate">
          <dt><span class="dashboard-stat-icon"><mat-icon aria-hidden="true">assessment</mat-icon></span> Con resultados</dt>
          <dd>{{ resumen().conResultados }}</dd>
        </div>
      </dl>

      @if (consentimientoActivo(); as cons) {
        <mat-card class="panel consent-card dashboard-enter">
          <mat-card-header>
            <mat-card-title>Consentimiento Informado Institucional (v{{ cons.doc.version }})</mat-card-title>
            <mat-card-subtitle>{{ cons.doc.autoridad_aprobadora }} · Lectura obligatoria previa al intento</mat-card-subtitle>
          </mat-card-header>
          <mat-card-content style="padding-top:16px;">
            <div class="ethical-note">
              <span class="tag amber">PROTOCOLO OBLIGATORIO</span>
              <pre class="consent-text">{{ cons.doc.texto }}</pre>
            </div>
            <div class="consent-actions">
              <button mat-button type="button" (click)="consentimientoActivo.set(null)">Cerrar</button>
              <button mat-flat-button color="primary" type="button" (click)="aceptarConsentimiento(cons.convocatoriaId)" [disabled]="operando()">
                <mat-icon>verified</mat-icon> Acepto los términos y deseo continuar
              </button>
            </div>
          </mat-card-content>
        </mat-card>
      }

      <section aria-labelledby="mission-library-title" [attr.aria-busy]="cargando()">
        <div class="dashboard-heading">
          <h2 id="mission-library-title">Convocatorias y casos</h2>
        </div>

      @if (cargando()) {
        <div class="panel dashboard-empty" role="status"><mat-spinner diameter="32" aria-hidden="true" /><p>Cargando convocatorias…</p></div>
      } @else if (!convocatorias().length) {
        <div class="panel dashboard-empty">
          <mat-icon aria-hidden="true">event_busy</mat-icon>
          <h3>Sin convocatorias registradas</h3>
        </div>
      } @else {
        <div class="dashboard-grid mission-grid">
          @for (c of convocatorias(); track c.convocatoria_id) {
            <article class="panel dashboard-card" [class.dashboard-tone-green]="c.estado_sesion === 'EN_CURSO'"
              [class.dashboard-tone-amber]="c.estado_sesion === 'SIN_INICIAR'"
              [class.dashboard-tone-slate]="c.estado_sesion === 'FINALIZADO'"
              [attr.aria-labelledby]="'mision-' + c.convocatoria_id">
              <div class="dashboard-card-content">
                <div class="dashboard-card-top">
                  <span class="dashboard-icon"><mat-icon aria-hidden="true">alt_route</mat-icon></span>
                  <div class="mission-badges">
                    <span class="dashboard-badge">{{ c.estado_sesion.replaceAll('_', ' ') }}</span>
                    @if (c.nota_visible !== null && c.nota_visible !== undefined) {
                      <span class="dashboard-badge dashboard-tone-amber">Nota {{ c.nota_visible | number:'1.1-2' }} / 100</span>
                    }
                  </div>
                </div>
                <h3 [id]="'mision-' + c.convocatoria_id">{{ c.caso_nombre }}</h3>
                <p class="case-sub">
                  {{ c.espacio_nombre }} · Docente: {{ c.docente_nombre }} · {{ c.lugar || 'Modalidad virtual' }}
                </p>
                <div class="mission-meta">
                  @if (c.escenarios_count) {
                    <span><mat-icon aria-hidden="true">account_tree</mat-icon> {{ c.escenarios_count }} {{ c.escenarios_count === 1 ? 'escenario' : 'escenarios' }}</span>
                  }
                  <span><mat-icon aria-hidden="true">schedule</mat-icon> {{ c.tiempo_maximo_minutos }} min</span>
                </div>

                <!-- Fact Grid Telemetrico -->
                <div class="fact-grid">
                  <div class="fact-tile">
                    <small>INICIO DE VENTANA</small>
                    <b>{{ c.fecha_inicio | date:'short' }}</b>
                  </div>
                  <div class="fact-tile">
                    <small>CIERRE DE VENTANA</small>
                    <b>{{ c.fecha_fin | date:'short' }}</b>
                  </div>
                  <div class="fact-tile">
                    <small>LÍMITE DE INGRESO</small>
                    <b [class.ok-txt]="!ingresoExpirado(c)" [class.bad-txt]="ingresoExpirado(c)">
                      {{ c.fecha_limite_mitad_tiempo | date:'short' }}
                    </b>
                  </div>
                  <div class="fact-tile">
                    <small>INTENTOS / EXTRA</small>
                    <b>
                      {{ c.intentos_realizados }}
                      @if (c.permisos_extra_disponibles > 0) {
                        <span class="gold-tag"> (+{{ c.permisos_extra_disponibles }} auth)</span>
                      }
                    </b>
                  </div>
                </div>

                <div class="briefing-grid">
                  <div class="objective-card">
                    <span class="objective-icon"><mat-icon aria-hidden="true">history_edu</mat-icon></span>
                    <div>
                      <div class="story-lbl">Contexto del caso</div>
                      <p>{{ c.contexto_historia }}</p>
                    </div>
                  </div>
                  <div class="objective-card">
                    <span class="objective-icon"><mat-icon aria-hidden="true">psychology</mat-icon></span>
                    <div>
                      <div class="story-lbl">Desarrollo situacional / Rol</div>
                      <p>{{ c.desarrollo_situacional }}</p>
                    </div>
                  </div>
                </div>

                @if (c.mensaje_personalizado) {
                  <div class="msg-docente">
                    <strong>Mensaje del docente:</strong> {{ c.mensaje_personalizado }}
                  </div>
                }

                @if (c.es_ausente) {
                  <div class="alert-warn">Se registró ausencia confirmada para esta sesión (calificación 0.00).</div>
                }

                @if (c.estado_sesion === 'SIN_INICIAR') {
                  <div class="msg-docente">
                    <strong>Sesión programada:</strong> La simulación se habilitará el {{ c.fecha_inicio | date:'short' }}.
                  </div>
                } @else if (c.consentimiento_aceptado && c.estado_sesion === 'EN_CURSO' && !(c.intento_id && c.intento_estado === 'EN_CURSO') && !puedeIniciarNuevoIntento(c)) {
                  @if (ingresoExpirado(c)) {
                    <div class="alert-warn">
                      La ventana de ingreso oportuno cerró el {{ c.fecha_limite_mitad_tiempo | date:'short' }}. No es posible iniciar un nuevo intento.
                    </div>
                  } @else if (c.intentos_realizados > 0 && c.permisos_extra_disponibles <= 0) {
                    <div class="msg-docente">
                      <strong>Intento completado:</strong> Ya agotaste tu intento regular. Si necesitas repetir por fuerza mayor, solicita autorización excepcional al docente.
                    </div>
                  }
                }

                @if (c.tiene_retroalimentacion) {
                  <div class="msg-docente" style="border-left-color: var(--green);">
                    <strong>Retroalimentación docente disponible:</strong> Abre el detalle de tu resultado para leer los comentarios de tu docente.
                  </div>
                }

                @if (c.notificaciones_recientes.length) {
                  <div class="notif-box">
                    <strong><mat-icon style="font-size:16px; width:16px; height:16px; vertical-align:middle;">notifications</mat-icon> Avisos recientes:</strong>
                    <ul>
                      @for (n of c.notificaciones_recientes; track $index) {
                        <li>{{ n }}</li>
                      }
                    </ul>
                  </div>
                }

              </div>
              <div class="dashboard-card-actions mission-actions">
                  @if (!c.consentimiento_aceptado) {
                    <button mat-flat-button color="accent" type="button" (click)="abrirConsentimiento(c.convocatoria_id)" [disabled]="operando()">
                      <mat-icon>assignment</mat-icon> Leer y Aceptar Consentimiento
                    </button>
                  }

                  @if (c.intento_id && c.intento_estado === 'EN_CURSO') {
                    <button mat-flat-button color="primary" type="button" (click)="irAlSimulador(c.intento_id!)" [disabled]="operando()">
                      <mat-icon>play_arrow</mat-icon> Retomar Simulación en Curso
                    </button>
                  } @else if (c.consentimiento_aceptado && c.estado_sesion === 'EN_CURSO' && puedeIniciarNuevoIntento(c)) {
                    <button mat-flat-button color="primary" type="button" (click)="iniciarSimulacion(c.convocatoria_id)" [disabled]="operando()">
                      <mat-icon>rocket_launch</mat-icon> Iniciar Simulación Ahora
                    </button>
                  }

                  @if (c.intento_id && c.intento_estado !== 'EN_CURSO') {
                    <button mat-stroked-button color="primary" type="button" (click)="irAlSimulador(c.intento_id!)">
                      <mat-icon>grading</mat-icon> Ver Resultado, Rúbrica y Justificaciones
                    </button>
                  }
              </div>
            </article>
          }
        </div>
      }
      </section>
    </div>
  `,
  styles: [`
    .consent-card {
      border: 1px solid rgba(255, 184, 0, 0.55) !important;
      border-left: 4px solid var(--amber) !important;
      margin-bottom: 20px;
    }
    .ethical-note {
      display: grid;
      gap: 10px;
      padding: 14px;
      border: 1px solid rgba(255, 184, 0, 0.3);
      background: rgba(255, 184, 0, 0.05);
    }
    .consent-text {
      white-space: pre-wrap;
      font-family: var(--body);
      background: #070a10;
      padding: 14px;
      border: 1px solid rgba(184, 211, 214, 0.16);
      color: var(--text);
      margin: 0;
      line-height: 1.55;
      font-size: 13px;
    }
    .consent-actions {
      display: flex;
      gap: 10px;
      justify-content: flex-end;
      margin-top: 14px;
      flex-wrap: wrap;
    }
    .mission-grid { grid-template-columns: minmax(0, 1fr); }
    .mission-badges, .mission-meta { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; }
    .mission-badges { justify-content: flex-end; }
    .mission-meta { gap: 8px 16px; margin-bottom: 15px; color: #c6d7e9; font-size: 13px; }
    .mission-meta span { display: inline-flex; align-items: center; gap: 5px; }
    .mission-meta mat-icon { width: 18px; height: 18px; font-size: 18px; color: #8bbbd8; }
    .case-sub { margin: -3px 0 11px; color: var(--muted); font-size: 13px; }
    .mission-actions:empty { display: none; }
    .mission-actions button { white-space: normal; max-width: 100%; }
    .fact-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
      margin-bottom: 14px;
    }
    .fact-tile {
      padding: 10px 12px;
      border: 1px solid rgba(0, 229, 244, 0.18);
      border-radius: 8px;
      background: #0b1017;
      display: grid;
      gap: 4px;
    }
    .fact-tile small {
      font-family: var(--mono);
      font-size: 10px;
      letter-spacing: 0.8px;
      color: #a3b7cb;
    }
    .fact-tile b {
      font-size: 13px;
      color: var(--text);
    }
    .briefing-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }
    .objective-card {
      display: grid;
      grid-template-columns: 38px 1fr;
      gap: 12px;
      padding: 12px 14px;
      border: 1px solid rgba(184, 211, 214, 0.16);
      border-radius: 9px;
      background: rgba(8, 12, 18, 0.88);
    }
    .objective-icon {
      width: 36px;
      height: 36px;
      display: grid;
      place-items: center;
      border: 1px solid var(--line-strong);
      border-radius: 7px;
      background: rgba(0, 229, 244, 0.08);
      color: var(--cyan);
    }
    .objective-icon mat-icon { width: 20px; height: 20px; font-size: 20px; }
    .story-lbl {
      font-family: var(--mono);
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 1px;
      color: var(--cyan);
      margin-bottom: 4px;
    }
    .objective-card p {
      margin: 0;
      line-height: 1.5;
      color: var(--muted);
      font-size: 13px;
    }
    .msg-docente {
      margin-top: 12px;
      background: rgba(0, 232, 148, 0.08);
      border: 1px solid rgba(0, 232, 148, 0.35);
      border-left: 4px solid var(--green);
      padding: 10px 12px;
      font-size: 13px;
      color: var(--text);
    }
    .notif-box {
      margin-top: 12px;
      background: #0b1017;
      border: 1px solid rgba(0, 229, 244, 0.22);
      padding: 10px 14px;
      font-size: 12px;
    }
    .notif-box ul {
      margin: 6px 0 0 18px;
      padding: 0;
      color: var(--muted);
    }
    .alert-warn {
      margin-top: 12px;
      background: rgba(232, 67, 81, 0.14);
      border: 1px solid rgba(232, 67, 81, 0.5);
      border-left: 4px solid var(--red);
      color: var(--coral);
      padding: 10px 14px;
      font-family: var(--mono);
      font-size: 12px;
    }
    .ok-txt { color: var(--green); font-weight: 700; }
    .bad-txt { color: var(--coral); font-weight: 700; }
    .gold-tag { color: var(--amber); font-weight: 700; }
    @media (max-width: 780px) { .fact-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
    @media (max-width: 540px) { .briefing-grid { grid-template-columns: minmax(0, 1fr); } }
  `],
})
export class EstudiantePortalComponent implements OnInit, OnDestroy {
  private readonly scheduling = inject(SchedulingService);
  private readonly participation = inject(ParticipationService);
  private readonly router = inject(Router);
  private readonly snack = inject(MatSnackBar);

  readonly cargando = signal(false);
  readonly operando = signal(false);
  readonly convocatorias = signal<MiConvocatoriaItem[]>([]);
  readonly resumen = computed(() => {
    const convocatorias = this.convocatorias();
    return {
      enCurso: convocatorias.filter((c) => c.estado_sesion === 'EN_CURSO').length,
      conResultados: convocatorias.filter((c) => c.intento_id && c.intento_estado !== 'EN_CURSO').length,
    };
  });
  readonly consentimientoActivo = signal<{ convocatoriaId: string; doc: ConsentimientoEstado } | null>(null);

  private refreshHandle: ReturnType<typeof setInterval> | null = null;

  ngOnInit(): void {
    void this.cargarPortal();
    this.refreshHandle = setInterval(() => void this.cargarPortal(true), 30_000);
  }

  ngOnDestroy(): void {
    if (this.refreshHandle) clearInterval(this.refreshHandle);
  }

  async cargarPortal(silencioso = false): Promise<void> {
    if (!silencioso) this.cargando.set(true);
    try {
      const lista = await firstValueFrom(this.scheduling.misConvocatorias());
      this.convocatorias.set(lista);
    } catch (e) {
      if (!silencioso) this.snack.open(mensajeError(e), 'Cerrar', { duration: 4500 });
    } finally {
      if (!silencioso) this.cargando.set(false);
    }
  }

  ingresoExpirado(c: MiConvocatoriaItem): boolean {
    return Date.now() > new Date(c.fecha_limite_mitad_tiempo).getTime();
  }

  puedeIniciarNuevoIntento(c: MiConvocatoriaItem): boolean {
    if (this.ingresoExpirado(c)) return false;
    return c.intentos_realizados === 0 || c.permisos_extra_disponibles > 0;
  }

  async abrirConsentimiento(convocatoriaId: string): Promise<void> {
    this.operando.set(true);
    try {
      const doc = await firstValueFrom(this.participation.consultarConsentimiento(convocatoriaId));
      this.consentimientoActivo.set({ convocatoriaId, doc });
    } catch (e) {
      this.snack.open(mensajeError(e), 'Cerrar', { duration: 4000 });
    } finally {
      this.operando.set(false);
    }
  }

  async aceptarConsentimiento(convocatoriaId: string): Promise<void> {
    this.operando.set(true);
    try {
      await firstValueFrom(this.participation.aceptarConsentimiento(convocatoriaId));
      this.consentimientoActivo.set(null);
      this.snack.open('Consentimiento informado registrado.', 'OK', { duration: 3000 });
      await this.cargarPortal();
    } catch (e) {
      this.snack.open(mensajeError(e), 'Cerrar', { duration: 4000 });
    } finally {
      this.operando.set(false);
    }
  }

  async iniciarSimulacion(convocatoriaId: string): Promise<void> {
    this.operando.set(true);
    try {
      const res = await firstValueFrom(this.participation.iniciarSimulacion(convocatoriaId));
      await this.router.navigate(['/estudiante/simulador', res.id_intento]);
    } catch (e) {
      this.snack.open(mensajeError(e), 'Cerrar', { duration: 5000 });
      await this.cargarPortal();
    } finally {
      this.operando.set(false);
    }
  }

  irAlSimulador(intentoId: number): void {
    void this.router.navigate(['/estudiante/simulador', intentoId]);
  }
}
