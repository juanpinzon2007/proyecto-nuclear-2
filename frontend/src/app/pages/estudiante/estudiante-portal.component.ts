import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { firstValueFrom } from 'rxjs';
import { mensajeError } from '../../core/api-error';
import { ConsentimientoEstado, MiConvocatoriaItem } from '../../core/api.models';
import { AuthService } from '../../core/auth.service';
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
    <div class="portal-wrap content">
      <!-- HERO TELEMETRY PANEL -->
      <section class="panel panel-pad hero stagger">
        <div class="spread">
          <div>
            <p class="eyebrow">Estación Estudiantil // Misiones Asignadas</p>
            <h1>Portal del Estudiante</h1>
            <p class="hero-sub">
              Operador: <strong class="cyan">{{ auth.usuario()?.correo }}</strong>. Revisa el briefing de tus convocatorias, firma el consentimiento informado e inicia tu simulación.
            </p>
          </div>
          <div class="hero-right">
            <div class="level-box">
              <small>ACTIVOS</small>
              <b>{{ convocatorias().length }}</b>
            </div>
            <button mat-stroked-button (click)="cargarPortal()" [disabled]="cargando()">
              <mat-icon>refresh</mat-icon> Actualizar
            </button>
          </div>
        </div>

        <div class="meter segmented" aria-hidden="true">
          @for (seg of [1,2,3,4,5,6,7,8,9,10]; track seg) {
            <i [class.on]="seg <= convocatorias().length * 3 || seg <= 4"></i>
          }
        </div>
      </section>

      @if (consentimientoActivo(); as cons) {
        <mat-card class="panel consent-card">
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

      <div class="spread section-head-row">
        <h2 class="section-title">Convocatorias & Casos</h2>
        <span class="mono">BRIEFING DE MISIÓN</span>
      </div>

      @if (cargando()) {
        <div class="center-spin"><mat-spinner diameter="42"></mat-spinner></div>
      } @else if (!convocatorias().length) {
        <mat-card class="panel empty-panel">
          <mat-icon class="empty-ico">event_busy</mat-icon>
          <h3>Sin convocatorias registradas</h3>
          <p class="muted">No se encontraron sesiones asociadas a tu cuenta actualmente.</p>
        </mat-card>
      } @else {
        <div class="stack stagger">
          @for (c of convocatorias(); track c.convocatoria_id; let ci = $index) {
            <mat-card class="panel conv-card" [class.conv-live]="c.estado_sesion === 'EN_CURSO'">
              <!-- Header Visual Tactico del Caso -->
              <div class="case-banner">
                <div class="case-art" [class.alt]="ci % 2 === 1">
                  <span>CASO 0{{ ci + 1 }}</span>
                </div>
                <div class="case-head-meta">
                  <div class="spread">
                    <span class="state-pill" [class]="'st-' + c.estado_sesion.toLowerCase()">
                      SESIÓN {{ c.estado_sesion }}
                    </span>
                    @if (c.nota_visible !== null && c.nota_visible !== undefined) {
                      <span class="score-pill">NOTA: {{ c.nota_visible | number:'1.1-2' }} / 100</span>
                    }
                  </div>
                  <h2 class="case-title">{{ c.caso_nombre }}</h2>
                  <p class="case-sub">
                    {{ c.espacio_nombre }} · Docente: {{ c.docente_nombre }} · {{ c.lugar || 'Modalidad virtual' }}
                  </p>
                  <div class="complexity-row mono">
                    <span>ESCENARIOS:</span>
                    <span class="blocks" aria-hidden="true">■ ■ ■ · {{ c.escenarios_count }}</span>
                    <span>· TIEMPO MÁX: {{ c.tiempo_maximo_minutos }} MIN</span>
                  </div>
                </div>
              </div>

              <mat-card-content style="padding-top:16px;">
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

                <!-- Objetivos Numerados Estilo Briefing -->
                <div class="briefing-grid">
                  <div class="objective-card">
                    <span class="obj-num">01</span>
                    <div>
                      <div class="story-lbl">Contexto del caso</div>
                      <p>{{ c.contexto_historia }}</p>
                    </div>
                  </div>
                  <div class="objective-card">
                    <span class="obj-num">02</span>
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

                <div class="card-actions">
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
              </mat-card-content>
            </mat-card>
          }
        </div>
      }
    </div>
  `,
  styles: [`
    .portal-wrap {
      padding: 4px 0 36px;
      max-width: 900px;
    }
    .hero {
      display: grid;
      gap: 16px;
      margin-bottom: 20px;
      border-left: 4px solid var(--cyan);
      background:
        radial-gradient(circle at top right, rgba(0, 229, 244, 0.12), transparent 48%),
        rgba(16, 20, 27, 0.95);
    }
    h1 {
      margin: 4px 0 6px;
      font-family: var(--display);
      font-size: clamp(32px, 5vw, 44px);
      line-height: 0.98;
      text-transform: uppercase;
      color: var(--text);
    }
    .hero-sub {
      margin: 0;
      color: var(--muted);
      font-size: 14px;
      line-height: 1.5;
    }
    .hero-right {
      display: flex;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
    }
    .level-box {
      min-width: 98px;
      padding: 10px 16px;
      border: 1px solid rgba(184, 211, 214, 0.35);
      background: #232932;
      font-family: var(--mono);
      text-align: left;
    }
    .level-box small {
      display: block;
      font-size: 10px;
      letter-spacing: 1.2px;
      color: var(--cyan);
    }
    .level-box b {
      display: block;
      font-size: 24px;
      line-height: 1.1;
      color: var(--text);
    }
    .section-head-row {
      margin-bottom: 12px;
    }
    .empty-panel {
      text-align: center;
      padding: 42px 24px !important;
    }
    .empty-ico {
      font-size: 48px;
      width: 48px;
      height: 48px;
      color: var(--dim);
      margin-bottom: 8px;
    }
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
    .conv-card {
      margin-bottom: 0 !important;
    }
    .conv-card.conv-live {
      border-left: 4px solid var(--green) !important;
      box-shadow: inset 0 0 28px rgba(0, 232, 148, 0.04), 0 12px 28px rgba(0, 0, 0, 0.45) !important;
    }
    .case-banner {
      display: grid;
      grid-template-columns: 120px 1fr;
      gap: 18px;
      padding-bottom: 16px;
      border-bottom: 1px solid var(--line);
      align-items: center;
    }
    .case-art {
      height: 112px;
      display: grid;
      place-items: center;
      border: 1px solid var(--line-strong);
      background: radial-gradient(circle, #036875, #041a24 38%, #060c12 75%);
      color: var(--cyan);
      font-family: var(--display);
      font-size: 26px;
      font-weight: 700;
      letter-spacing: 1px;
      text-transform: uppercase;
    }
    .case-art.alt {
      border-color: rgba(255, 184, 0, 0.45);
      background: radial-gradient(circle, #673f20, #10202b 32%, #060c12 75%);
      color: var(--amber);
    }
    .case-head-meta {
      display: grid;
      gap: 6px;
      min-width: 0;
    }
    .case-title {
      margin: 0;
      font-family: var(--display);
      font-size: 28px;
      line-height: 1.05;
      text-transform: uppercase;
      color: var(--text);
    }
    .case-sub {
      margin: 0;
      color: var(--muted);
      font-size: 13px;
    }
    .complexity-row {
      display: flex;
      gap: 8px;
      align-items: center;
      font-size: 11px;
      color: var(--dim);
      flex-wrap: wrap;
    }
    .blocks {
      color: var(--green);
      letter-spacing: 1.5px;
    }
    .state-pill {
      padding: 3px 9px;
      border: 1px solid rgba(184, 211, 214, 0.25);
      font-family: var(--mono);
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.8px;
      text-transform: uppercase;
    }
    .st-sin_iniciar {
      border-color: rgba(255, 184, 0, 0.55);
      background: rgba(255, 184, 0, 0.12);
      color: var(--amber);
    }
    .st-en_curso {
      border-color: rgba(0, 232, 148, 0.55);
      background: rgba(0, 232, 148, 0.12);
      color: var(--green);
    }
    .st-finalizado {
      border-color: rgba(169, 181, 184, 0.35);
      background: rgba(169, 181, 184, 0.1);
      color: var(--muted);
    }
    .score-pill {
      background: rgba(255, 184, 0, 0.14);
      border: 1px solid rgba(255, 184, 0, 0.55);
      color: var(--amber);
      padding: 4px 10px;
      font-family: var(--mono);
      font-size: 12px;
      font-weight: 700;
    }
    .fact-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
      margin-bottom: 14px;
    }
    .fact-tile {
      padding: 10px 12px;
      border: 1px solid rgba(0, 229, 244, 0.18);
      background: #0b1017;
      display: grid;
      gap: 4px;
    }
    .fact-tile small {
      font-family: var(--mono);
      font-size: 10px;
      letter-spacing: 0.8px;
      color: var(--dim);
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
      background: rgba(8, 12, 18, 0.88);
    }
    .obj-num {
      width: 36px;
      height: 36px;
      display: grid;
      place-items: center;
      border: 1px solid var(--line-strong);
      background: rgba(0, 229, 244, 0.08);
      color: var(--cyan);
      font-family: var(--mono);
      font-size: 14px;
      font-weight: 700;
    }
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
    .card-actions {
      display: flex;
      gap: 12px;
      margin-top: 16px;
      flex-wrap: wrap;
    }
    .ok-txt { color: var(--green); font-weight: 700; }
    .bad-txt { color: var(--coral); font-weight: 700; }
    .gold-tag { color: var(--amber); font-weight: 700; }
    @media (max-width: 780px) {
      .fact-grid, .briefing-grid { grid-template-columns: 1fr; }
      .case-banner { grid-template-columns: 1fr; }
      .case-art { height: 74px; }
    }
  `],
})
export class EstudiantePortalComponent implements OnInit, OnDestroy {
  readonly auth = inject(AuthService);
  private readonly scheduling = inject(SchedulingService);
  private readonly participation = inject(ParticipationService);
  private readonly router = inject(Router);
  private readonly snack = inject(MatSnackBar);

  readonly cargando = signal(false);
  readonly operando = signal(false);
  readonly convocatorias = signal<MiConvocatoriaItem[]>([]);
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
