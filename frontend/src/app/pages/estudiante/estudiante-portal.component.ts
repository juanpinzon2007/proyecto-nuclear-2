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
    <div class="portal-wrap">
      <div class="header-bar">
        <div>
          <h2>Portal del Estudiante</h2>
          <p class="subtitle">
            Bienvenido, <strong>{{ auth.usuario()?.correo }}</strong>. Revisa tus sesiones convocadas, acepta el consentimiento e inicia tu simulación.
          </p>
        </div>
        <button mat-stroked-button (click)="cargarPortal()" [disabled]="cargando()">
          <mat-icon>refresh</mat-icon> Actualizar
        </button>
      </div>

      @if (consentimientoActivo(); as cons) {
        <mat-card class="consent-card">
          <mat-card-header>
            <mat-card-title>Consentimiento Informado Institucional (v{{ cons.doc.version }})</mat-card-title>
            <mat-card-subtitle>{{ cons.doc.autoridad_aprobadora }} · Lectura obligatoria previa al intento</mat-card-subtitle>
          </mat-card-header>
          <mat-card-content style="padding-top:14px;">
            <pre class="consent-text">{{ cons.doc.texto }}</pre>
            <div style="display:flex; gap:10px; justify-content:flex-end; margin-top:14px;">
              <button mat-button type="button" (click)="consentimientoActivo.set(null)">Cerrar</button>
              <button mat-flat-button color="primary" type="button" (click)="aceptarConsentimiento(cons.convocatoriaId)" [disabled]="operando()">
                <mat-icon>verified</mat-icon> Acepto los términos y deseo continuar
              </button>
            </div>
          </mat-card-content>
        </mat-card>
      }

      @if (cargando()) {
        <div class="center-spin"><mat-spinner diameter="42"></mat-spinner></div>
      } @else if (!convocatorias().length) {
        <mat-card style="text-align:center; padding:36px;">
          <mat-icon style="font-size:48px; width:48px; height:48px; opacity:0.5;">event_busy</mat-icon>
          <h3>Sin convocatorias registradas</h3>
          <p class="muted">No se encontraron sesiones asociadas a tu cuenta actualmente.</p>
        </mat-card>
      } @else {
        @for (c of convocatorias(); track c.convocatoria_id) {
          <mat-card class="conv-card" [class.conv-live]="c.estado_sesion === 'EN_CURSO'">
            <mat-card-header>
              <mat-card-title style="display:flex; justify-content:space-between; align-items:center; width:100%; flex-wrap:wrap; gap:8px;">
                <span>{{ c.caso_nombre }}</span>
                <div style="display:flex; gap:8px; align-items:center;">
                  <span class="state-pill" [class]="'st-' + c.estado_sesion.toLowerCase()">Sesión {{ c.estado_sesion }}</span>
                  @if (c.nota_visible !== null && c.nota_visible !== undefined) {
                    <span class="score-pill">Nota: {{ c.nota_visible | number:'1.1-2' }} / 100</span>
                  }
                </div>
              </mat-card-title>
              <mat-card-subtitle>{{ c.espacio_nombre }} · Docente: {{ c.docente_nombre }} · {{ c.lugar || 'Modalidad virtual' }}</mat-card-subtitle>
            </mat-card-header>

            <mat-card-content style="padding-top:16px;">
              <div class="intro-grid">
                <div class="meta-box">
                  <div><strong>Inicio sesión:</strong> {{ c.fecha_inicio | date:'short' }}</div>
                  <div><strong>Cierre sesión:</strong> {{ c.fecha_fin | date:'short' }}</div>
                  <div>
                    <strong>Límite ingreso tardío (RF-22):</strong>
                    <span [class.ok-txt]="!ingresoExpirado(c)" [class.bad-txt]="ingresoExpirado(c)">
                      {{ c.fecha_limite_mitad_tiempo | date:'short' }}
                    </span>
                  </div>
                  <div><strong>Tiempo máximo:</strong> {{ c.tiempo_maximo_minutos }} minutos ({{ c.escenarios_count }} escenarios)</div>
                  <div><strong>Intentos realizados:</strong> {{ c.intentos_realizados }}
                    @if (c.permisos_extra_disponibles > 0) {
                      <span class="gold-tag"> · +{{ c.permisos_extra_disponibles }} repetición autorizada</span>
                    }
                  </div>
                </div>

                <div class="story-box">
                  <div class="story-lbl">Contexto del caso</div>
                  <p>{{ c.contexto_historia }}</p>
                  <div class="story-lbl">Desarrollo situacional / Rol</div>
                  <p>{{ c.desarrollo_situacional }}</p>
                  @if (c.mensaje_personalizado) {
                    <div class="msg-docente">
                      <strong>Mensaje del docente:</strong> {{ c.mensaje_personalizado }}
                    </div>
                  }
                </div>
              </div>

              @if (c.es_ausente) {
                <div class="alert-warn">Se registró ausencia confirmada para esta sesión (calificación 0.00).</div>
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
                    <mat-icon>grading</mat-icon> Ver Resultado, Rúbrica y Justificaciones (RF-14)
                  </button>
                }
              </div>
            </mat-card-content>
          </mat-card>
        }
      }
    </div>
  `,
  styles: [`
    .portal-wrap { padding: 8px 0 40px; }
    .header-bar { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; margin-bottom: 18px; }
    h2 { margin: 0; font-size: 22px; font-weight: 700; color: #f8fafc; }
    .subtitle { margin: 4px 0 0; color: #94a3b8; font-size: 13px; }
    .center-spin { display: flex; justify-content: center; padding: 48px; }
    .consent-card { border: 1px solid rgba(245, 158, 11, 0.5) !important; margin-bottom: 20px; }
    .consent-text { white-space: pre-wrap; font-family: inherit; background: rgba(6,11,22,0.75); padding: 14px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1); color: #e2e8f0; margin: 0; line-height: 1.5; }
    .conv-card { margin-bottom: 18px; }
    .conv-card.conv-live { border-left: 4px solid #10b981 !important; }
    .state-pill { padding: 3px 10px; border-radius: 999px; font-size: 11px; font-weight: 700; }
    .st-sin_iniciar { background: rgba(245,158,11,0.18); color: #fbbf24; }
    .st-en_curso { background: rgba(16,185,129,0.2); color: #34d399; }
    .st-finalizado { background: rgba(148,163,184,0.2); color: #cbd5e1; }
    .score-pill { background: rgba(245,158,11,0.2); border: 1px solid rgba(245,158,11,0.45); color: #fbbf24; padding: 4px 10px; border-radius: 999px; font-size: 12px; font-weight: 700; }
    .intro-grid { display: grid; grid-template-columns: 320px 1fr; gap: 16px; }
    @media (max-width: 900px) { .intro-grid { grid-template-columns: 1fr; } }
    .meta-box, .story-box { background: rgba(6,11,22,0.65); border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 14px; font-size: 13px; display: flex; flex-direction: column; gap: 8px; }
    .story-lbl { font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; color: #94a3b8; font-weight: 700; }
    .story-box p { margin: 0 0 6px; line-height: 1.5; color: #e2e8f0; }
    .msg-docente { background: rgba(16,185,129,0.1); border-left: 3px solid #10b981; padding: 8px 10px; border-radius: 6px; }
    .notif-box { margin-top: 12px; background: rgba(15,23,42,0.75); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; padding: 10px 14px; font-size: 12px; }
    .notif-box ul { margin: 6px 0 0 18px; padding: 0; color: #cbd5e1; }
    .alert-warn { margin-top: 12px; background: rgba(239,68,68,0.15); border: 1px solid rgba(239,68,68,0.4); color: #fecaca; padding: 10px 14px; border-radius: 8px; }
    .card-actions { display: flex; gap: 12px; margin-top: 16px; flex-wrap: wrap; }
    .ok-txt { color: #34d399; font-weight: 600; }
    .bad-txt { color: #f87171; font-weight: 600; }
    .gold-tag { color: #fbbf24; font-weight: 700; }
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
    if (c.intentos_realizados === 0) return true;
    return c.permisos_extra_disponibles > c.intentos_realizados - 1;
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
