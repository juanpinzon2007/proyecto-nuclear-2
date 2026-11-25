import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTabsModule } from '@angular/material/tabs';
import { firstValueFrom } from 'rxjs';
import { mensajeError } from '../../core/api-error';
import {
  CasoResumenResponse,
  EspacioAcademicoResponse,
  EstudianteDisponibleItem,
  GrupoResponse,
  SesionResponse,
} from '../../core/api.models';
import { CasesService } from '../../core/cases.service';
import { SchedulingService } from '../../core/scheduling.service';

import { etiquetaEstado } from '../../core/lista-paginada';

@Component({
  selector: 'app-programacion',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterLink,
    MatCardModule,
    MatTabsModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatCheckboxModule,
    MatButtonModule,
    MatIconModule,
    MatSnackBarModule,
  ],
  template: `
    <div class="prog-wrap">
      <div class="page-header">
        <div>
          <h1>Sesiones y grupos</h1>
          <p class="subtitle">
            Programa una sesión para tu clase, organiza tus grupos y consulta sus convocatorias.
          </p>
        </div>
        <button mat-stroked-button type="button" (click)="cargarTodo()" [disabled]="cargando()">
          <mat-icon>refresh</mat-icon> {{ cargando() ? 'Actualizando…' : 'Actualizar' }}
        </button>
      </div>

      <mat-tab-group animationDuration="200ms" [disablePagination]="true">
        <!-- TAB 1: Sesiones programadas y Nueva Programación -->
        <mat-tab label="Sesiones académicas">
          @if (sesiones().length) {
            <button class="session-shortcut" mat-stroked-button type="button"
                    (click)="sesionesProgramadas.focus({ preventScroll: true }); sesionesProgramadas.scrollIntoView({ block: 'start' })">
              <mat-icon>arrow_downward</mat-icon> Ver sesiones programadas
            </button>
          }
          <div class="tab-grid">
            <!-- Formulario Crear Sesión / Editar Sesión -->
            <mat-card class="panel panel-cyan-left">
              <mat-card-header>
                <mat-card-title>{{ sesionEditando() ? 'Editar horario y notificar cambios' : 'Programar sesión' }}</mat-card-title>
                <mat-card-subtitle>Selecciona un caso publicado y un espacio autorizado.</mat-card-subtitle>
              </mat-card-header>
              <mat-card-content>
                <form class="form-stack" (ngSubmit)="sesionEditando() ? guardarEdicionSesion() : crearSesion()">
                  @if (!sesionEditando()) {
                    <div class="inline-space">
                      <mat-form-field appearance="outline" subscriptSizing="dynamic">
                        <mat-label>Espacio académico</mat-label>
                        <mat-select [(ngModel)]="formSes.espacioId" name="espId" required>
                          @for (e of espacios(); track e.id) {
                            <mat-option [value]="e.id">{{ e.nombre }}</mat-option>
                          }
                        </mat-select>
                      </mat-form-field>
                      <button mat-stroked-button type="button" (click)="mostrarCrearEspacio = !mostrarCrearEspacio"
                              [attr.aria-expanded]="mostrarCrearEspacio" aria-label="Crear espacio académico" title="Crear espacio académico">
                        <mat-icon>add</mat-icon>
                      </button>
                    </div>

                    @if (mostrarCrearEspacio) {
                      <div class="mini-create">
                        <input class="dark-input" [(ngModel)]="nuevoEspacioNombre" name="newEsp" placeholder="Nombre del nuevo espacio..." />
                        <button mat-flat-button color="primary" type="button" (click)="crearYAutorizarEspacio()">Crear</button>
                      </div>
                    }

                    <mat-form-field appearance="outline" subscriptSizing="dynamic">
                      <mat-label>Caso publicado</mat-label>
                      <mat-select [(ngModel)]="formSes.versionCasoId" name="casoId" (ngModelChange)="alCambiarCaso($event)" required>
                        @for (c of casosPublicados(); track c.version_id) {
                          <mat-option [value]="c.version_id">{{ c.nombre }} (v{{ c.numero }} · máx {{ c.tiempo_estimado_min }}m)</mat-option>
                        }
                      </mat-select>
                    </mat-form-field>
                  }

                  <mat-form-field appearance="outline" subscriptSizing="dynamic">
                    <mat-label>Fecha y hora de inicio</mat-label>
                    <input matInput type="datetime-local" [(ngModel)]="formSes.inicioLocal" name="inicio" required />
                  </mat-form-field>

                  <mat-form-field appearance="outline" subscriptSizing="dynamic">
                    <mat-label>Fecha y hora de finalización</mat-label>
                    <input matInput type="datetime-local" [(ngModel)]="formSes.finLocal" name="fin" required />
                  </mat-form-field>

                  <mat-form-field appearance="outline" subscriptSizing="dynamic">
                    <mat-label>Duración del intento (min)</mat-label>
                    <input matInput type="number" min="1" [(ngModel)]="formSes.tiempoMax" name="tmax" required />
                  </mat-form-field>

                  <mat-form-field appearance="outline" subscriptSizing="dynamic">
                    <mat-label>Lugar físico o enlace virtual</mat-label>
                    <input matInput [(ngModel)]="formSes.lugar" name="lugar" placeholder="Ej: Sala de Simulación 2 / Zoom" />
                  </mat-form-field>

                  <mat-form-field appearance="outline" subscriptSizing="dynamic">
                    <mat-label>Mensaje para los estudiantes</mat-label>
                    <textarea matInput rows="2" [(ngModel)]="formSes.mensaje" name="msg"></textarea>
                  </mat-form-field>

                  @if (!sesionEditando()) {
                    <mat-form-field appearance="outline" subscriptSizing="dynamic">
                      <mat-label>Grupo académico (opcional)</mat-label>
                      <mat-select [(ngModel)]="formSes.grupoId" name="grpId" (ngModelChange)="alCambiarGrupo($event)">
                        <mat-option [value]="null">-- Convocar manualmente después --</mat-option>
                        @for (g of grupos(); track g.id_grupo) {
                          <mat-option [value]="g.id_grupo">{{ g.nombre }} ({{ g.periodo }} · {{ g.estudiantes.length }} est.)</mat-option>
                        }
                      </mat-select>
                    </mat-form-field>

                    @if (formSes.grupoId) {
                      <mat-form-field appearance="outline" subscriptSizing="dynamic">
                        <mat-label>Fecha límite explícita de ingreso</mat-label>
                        <input matInput type="datetime-local" [(ngModel)]="formSes.limiteIngresoLocal" name="limIng" required />
                      </mat-form-field>

                      <div class="students-check">
                        <span class="check-title">Estudiantes matriculados a convocar ({{ seleccionadosCount() }}):</span>
                        @for (est of estudiantesGrupoSeleccionado(); track est.id_usuario) {
                          @if (est.uuid_scheduling) {
                            <mat-checkbox [checked]="estudiantesSeleccionados.has(est.uuid_scheduling)"
                                          (change)="toggleEstudianteSesion(est.uuid_scheduling, $event.checked)">
                              {{ est.nombre }} <span class="muted">({{ est.correo }})</span>
                            </mat-checkbox>
                          }
                        }
                      </div>
                    }
                  }

                  <div class="action-group form-actions">
                    <button mat-flat-button color="primary" type="submit" [disabled]="guardando()">
                      <mat-icon>{{ sesionEditando() ? 'notifications_active' : 'event_available' }}</mat-icon>
                      {{ sesionEditando() ? 'Guardar y notificar cambios' : 'Programar sesión' }}
                    </button>
                    @if (sesionEditando()) {
                      <button mat-button type="button" (click)="cancelarEdicionSesion()">Cancelar</button>
                    }
                  </div>
                </form>
              </mat-card-content>
            </mat-card>

            <mat-card class="panel session-panel">
              <mat-card-header>
                <h2 mat-card-title #sesionesProgramadas tabindex="-1">Sesiones programadas ({{ sesiones().length }})</h2>
              </mat-card-header>
              <mat-card-content>
                @if (sesiones().length) {
                  <div class="session-grid session-head" aria-hidden="true">
                    <span>Caso y espacio</span><span>Horario</span><span>Estado</span><span>Acciones</span>
                  </div>
                  <ul class="session-list" role="list" aria-label="Sesiones programadas">
                    @for (s of sesiones(); track s.id) {
                      <li class="session-grid session-row">
                        <div class="session-case">
                          <strong>{{ nombreCaso(s.version_caso_id) }}</strong>
                          <span>{{ nombreEspacio(s.espacio_academico_id) }} · {{ s.lugar || 'Virtual' }}</span>
                        </div>
                        <div class="session-time">
                          <time [attr.datetime]="s.fecha_inicio">{{ s.fecha_inicio | date:'dd/MM/yy · HH:mm' }}</time>
                          <time [attr.datetime]="s.fecha_fin">Hasta {{ s.fecha_fin | date:'dd/MM/yy · HH:mm' }}</time>
                          <span>{{ s.tiempo_maximo_minutos }} min por intento</span>
                        </div>
                        <span class="state-pill" [class]="'st-' + s.estado.toLowerCase()">{{ etiquetaEstado(s.estado) }}</span>
                        <div class="session-actions" role="group" [attr.aria-label]="'Acciones de la sesión del ' + (s.fecha_inicio | date:'dd/MM/yy · HH:mm')">
                          <a mat-stroked-button [routerLink]="['/programacion', s.id, 'convocatorias']">Convocatorias</a>
                          <a mat-stroked-button [routerLink]="['/programacion', s.id, 'evaluacion']">Evaluación</a>
                          @if (s.estado !== 'FINALIZADO') {
                            <button mat-stroked-button type="button" (click)="iniciarEdicionSesion(s)">Editar</button>
                          }
                          @if (s.estado === 'SIN_INICIAR') {
                            <button mat-flat-button color="primary" type="button" (click)="cambiarEstado(s.id, 'iniciar')">Iniciar</button>
                          }
                          @if (s.estado === 'EN_CURSO') {
                            <button mat-stroked-button class="session-end" type="button" (click)="cambiarEstado(s.id, 'finalizar')">Finalizar</button>
                          }
                        </div>
                      </li>
                    }
                  </ul>
                } @else if (cargando()) {
                  <p class="muted empty-sessions" role="status">Cargando sesiones…</p>
                } @else {
                  <p class="muted empty-sessions">Todavía no hay sesiones programadas.</p>
                }
              </mat-card-content>
            </mat-card>
          </div>
        </mat-tab>

        <!-- TAB 2: Grupos Académicos y Matrículas RF-04 -->
        <mat-tab label="Grupos y estudiantes">
          <div class="tab-grid">
            <mat-card class="panel panel-amber-left">
              <mat-card-header>
                <mat-card-title>Crear grupo académico</mat-card-title>
                <mat-card-subtitle>Agrupa estudiantes por cohorte o curso para programar sesiones</mat-card-subtitle>
              </mat-card-header>
              <mat-card-content>
                <form class="form-stack" (ngSubmit)="crearGrupo()">
                  <mat-form-field appearance="outline">
                    <mat-label>Nombre del grupo</mat-label>
                    <input matInput [(ngModel)]="nuevoGrupoNombre" name="gNom" placeholder="Ej: Bioética Grupo A" required />
                  </mat-form-field>
                  <mat-form-field appearance="outline">
                    <mat-label>Periodo académico</mat-label>
                    <input matInput [(ngModel)]="nuevoGrupoPeriodo" name="gPer" placeholder="Ej: 2026-2" required />
                  </mat-form-field>
                  <div class="action-group form-actions">
                    <button mat-flat-button color="primary" type="submit" [disabled]="guardando()">
                      <mat-icon>group_add</mat-icon> Crear grupo
                    </button>
                  </div>
                </form>
              </mat-card-content>
            </mat-card>

            <mat-card class="panel">
              <mat-card-header>
                <mat-card-title>Grupos y matrículas ({{ grupos().length }})</mat-card-title>
              </mat-card-header>
              <mat-card-content>
                @if (!grupos().length) {
                  <p class="muted">No tienes grupos creados todavía.</p>
                }
                <div class="stack stagger">
                  @for (g of grupos(); track g.id_grupo) {
                    <div class="group-card">
                      <div class="group-head">
                        <div>
                          <strong style="font-size:15px;">{{ g.nombre }}</strong>
                          <span class="period-tag">{{ g.periodo }}</span>
                        </div>
                        <span class="mono cyan">{{ g.estudiantes.length }} {{ g.estudiantes.length === 1 ? 'estudiante' : 'estudiantes' }}</span>
                      </div>

                      <div class="enroll-bar">
                        <select class="dark-sel" [(ngModel)]="matricularPorGrupo[g.id_grupo]" [name]="'m_' + g.id_grupo"
                                [attr.aria-label]="'Estudiante para matricular en ' + g.nombre">
                          <option [ngValue]="null">Seleccionar estudiante</option>
                          @for (est of estudiantesDisponibles(); track est.id_usuario) {
                            <option [ngValue]="est.id_usuario">{{ est.nombre }} ({{ est.correo }})</option>
                          }
                        </select>
                        <button mat-flat-button color="primary" type="button"
                                (click)="matricular(g.id_grupo)"
                                [disabled]="!matricularPorGrupo[g.id_grupo] || guardando()">
                          Matricular
                        </button>
                      </div>

                      @if (g.estudiantes.length) {
                        <div class="enrolled-list">
                          @for (m of g.estudiantes; track m.id_usuario) {
                            <div class="enrolled-item">
                              <span>{{ m.nombre }} <span class="muted">({{ m.correo }})</span></span>
                              <button mat-button color="warn" type="button" (click)="retirarMatricula(g.id_grupo, m.id_usuario)">
                                Retirar
                              </button>
                            </div>
                          }
                        </div>
                      }
                    </div>
                  }
                </div>
              </mat-card-content>
            </mat-card>
          </div>
        </mat-tab>
      </mat-tab-group>
    </div>
  `,
  styles: [`
    .prog-wrap { padding: 4px 0 24px; max-width: 1240px; margin: 0 auto; }
    .subtitle { margin: 6px 0 0; color: var(--muted); max-width: 66ch; }
    .tab-grid {
      display: grid;
      grid-template-columns: minmax(0, 21rem) minmax(0, 1fr);
      gap: 20px;
      margin-top: 16px;
      align-items: start;
    }
    .session-shortcut { display: none; }
    @media (max-width: 920px) {
      .tab-grid { grid-template-columns: minmax(0, 1fr); gap: 0; }
      .session-shortcut { display: inline-flex; margin-top: 14px; }
    }
    .form-stack { display: flex; flex-direction: column; gap: 12px; padding-top: 14px; }
    .inline-space, .mini-create, .enroll-bar {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 8px;
      align-items: stretch;
    }
    .inline-space > button { width: 48px; height: auto; padding: 0; min-width: 0; }
    .inline-space mat-icon { margin: 0; }
    .mini-create { padding: 10px; background: var(--panel); border: 1px solid var(--line); border-radius: 8px; }
    .dark-input { min-width: 0; background: #10141b; color: var(--text); border: 1px solid var(--line-strong); border-radius: 8px; padding: 6px 10px; }
    .students-check { background: #070a10; border: 1px solid var(--line); padding: 12px; display: flex; flex-direction: column; gap: 4px; }
    .check-title { font-family: var(--mono); font-size: 11px; color: var(--cyan); margin-bottom: 4px; }
    .session-panel { container-type: inline-size; min-width: 0; }
    .session-panel h2 { margin: 0; }
    .session-list { margin: 0; padding: 0; list-style: none; }
    .session-grid {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(9rem, .7fr) 6.2rem minmax(15.5rem, 1fr);
      gap: 12px;
      align-items: center;
      padding-inline: 12px;
    }
    .session-head {
      padding-block: 11px;
      background: var(--bg);
      color: var(--cyan-soft);
      font-size: var(--type-small);
      font-weight: 650;
    }
    .session-row { padding-block: 14px; border-bottom: 1px solid var(--line); }
    .session-list > :last-child { border-bottom: 0; }
    .session-case, .session-time { display: grid; gap: 3px; min-width: 0; }
    .session-case { overflow-wrap: anywhere; }
    .session-case strong { font-size: 14px; line-height: 1.4; }
    .session-case span, .session-time span, .session-time time + time { color: var(--muted); }
    .session-case span, .session-time span { font-size: var(--type-small); }
    .session-time time { color: var(--text); font-size: var(--type-small); font-variant-numeric: tabular-nums; }
    .state-pill { justify-self: start; padding: 3px 8px; border: 1px solid var(--line-strong); border-radius: 5px; font-size: var(--type-meta); font-weight: 650; white-space: nowrap; }
    .st-sin_iniciar { border-color: rgba(255, 184, 0, 0.55); background: rgba(255, 184, 0, 0.12); color: var(--amber); }
    .st-en_curso { border-color: rgba(0, 232, 148, 0.55); background: rgba(0, 232, 148, 0.12); color: var(--green); }
    .st-finalizado { border-color: rgba(169, 181, 184, 0.35); background: rgba(169, 181, 184, 0.1); color: var(--muted); }
    .session-actions { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 6px; }
    .session-actions > :is(a, button) { min-width: 0; padding-inline: 6px; }
    .session-end.mat-mdc-outlined-button:not(:disabled) {
      color: #ffacb4 !important;
      border-color: #9f575f !important;
      background: #51273140 !important;
    }
    .session-end.mat-mdc-outlined-button:hover:not(:disabled) { background: #512731 !important; box-shadow: none !important; }
    .empty-sessions { margin: 0; padding-block: 20px; }
    @container (max-width: 710px) {
      .session-head { display: none; }
      .session-row {
        grid-template-columns: minmax(0, 1fr) auto;
        gap: 8px 12px;
        padding-inline: 0;
      }
      .session-time { grid-row: 2; grid-column: 1 / -1; }
      .session-row > .state-pill { grid-area: 1 / 2; align-self: start; }
      .session-actions { grid-column: 1 / -1; margin-top: 4px; }
    }
    .group-card { background: #0b1017; border: 1px solid var(--line); border-left: 4px solid var(--cyan); padding: 14px; }
    .group-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; gap: 10px; flex-wrap: wrap; }
    .period-tag { margin-left: 8px; border: 1px solid rgba(255, 184, 0, 0.5); background: rgba(255, 184, 0, 0.1); color: var(--amber); padding: 2px 8px; font-family: var(--mono); font-size: 11px; font-weight: 700; }
    .enroll-bar { margin-bottom: 10px; }
    .dark-sel { min-width: 0; background: #070a10; color: var(--text); border: 1px solid var(--line-strong); border-radius: 8px; padding: 8px 10px; font-family: var(--mono); font-size: 12px; }
    .enrolled-list { display: flex; flex-direction: column; gap: 6px; }
    .enrolled-item { display: flex; justify-content: space-between; align-items: center; padding: 6px 10px; background: #070a10; border: 1px solid rgba(184, 211, 214, 0.12); font-size: 13px; flex-wrap: wrap; gap: 8px; overflow-wrap: anywhere; }
    @media (max-width: 480px) {
      .mini-create, .enroll-bar { grid-template-columns: minmax(0, 1fr); }
    }
  `],
})
export class ProgramacionComponent implements OnInit {
  readonly etiquetaEstado = etiquetaEstado;
  private readonly scheduling = inject(SchedulingService);
  private readonly cases = inject(CasesService);
  private readonly snack = inject(MatSnackBar);

  readonly cargando = signal(false);
  readonly guardando = signal(false);
  readonly espacios = signal<EspacioAcademicoResponse[]>([]);
  readonly casosTodos = signal<CasoResumenResponse[]>([]);
  readonly casosPublicados = signal<CasoResumenResponse[]>([]);
  readonly sesiones = signal<SesionResponse[]>([]);
  readonly grupos = signal<GrupoResponse[]>([]);
  readonly estudiantesDisponibles = signal<EstudianteDisponibleItem[]>([]);
  readonly sesionEditando = signal<SesionResponse | null>(null);

  mostrarCrearEspacio = false;
  nuevoEspacioNombre = '';
  nuevoGrupoNombre = '';
  nuevoGrupoPeriodo = '2026-2';
  matricularPorGrupo: Record<number, number | null> = {};
  estudiantesSeleccionados = new Set<string>();

  formSes = {
    espacioId: '',
    versionCasoId: '',
    inicioLocal: this.isoLocal(0),
    finLocal: this.isoLocal(120),
    tiempoMax: 30,
    lugar: '',
    mensaje: '',
    grupoId: null as number | null,
    limiteIngresoLocal: this.isoLocal(15),
  };

  ngOnInit(): void {
    void this.cargarTodo();
  }

  private isoLocal(offsetMin: number): string {
    const d = new Date(Date.now() + offsetMin * 60_000);
    d.setSeconds(0, 0);
    const pad = (n: number) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  }

  private aIsoUtc(localStr: string): string {
    return new Date(localStr).toISOString();
  }

  async cargarTodo(): Promise<void> {
    this.cargando.set(true);
    try {
      const [esp, cas, ses, grps, ests] = await Promise.all([
        firstValueFrom(this.scheduling.espacios()),
        firstValueFrom(this.cases.listar()),
        firstValueFrom(this.scheduling.sesiones()),
        firstValueFrom(this.scheduling.grupos()),
        firstValueFrom(this.scheduling.estudiantes()),
      ]);
      this.espacios.set(esp);
      this.casosTodos.set(cas);
      this.casosPublicados.set(cas.filter((c) => c.estado === 'PUBLICADO'));
      this.sesiones.set(ses);
      this.grupos.set(grps);
      this.estudiantesDisponibles.set(ests);

      if (!this.formSes.espacioId && esp.length) this.formSes.espacioId = esp[0].id;
      if (!this.formSes.versionCasoId && this.casosPublicados().length) {
        const primero = this.casosPublicados()[0];
        this.formSes.versionCasoId = primero.version_id;
        this.formSes.tiempoMax = primero.tiempo_estimado_min;
      }
    } catch (e) {
      this.snack.open(mensajeError(e), 'Cerrar', { duration: 4500 });
    } finally {
      this.cargando.set(false);
    }
  }

  alCambiarCaso(versionId: string): void {
    const caso = this.casosPublicados().find((c) => c.version_id === versionId);
    if (caso) this.formSes.tiempoMax = caso.tiempo_estimado_min;
  }

  alCambiarGrupo(grupoId: number | null): void {
    this.estudiantesSeleccionados.clear();
    if (!grupoId) return;
    const g = this.grupos().find((x) => x.id_grupo === grupoId);
    if (g) {
      for (const e of g.estudiantes) {
        if (e.uuid_scheduling && e.activo !== false) this.estudiantesSeleccionados.add(e.uuid_scheduling);
      }
    }
  }

  estudiantesGrupoSeleccionado() {
    const lista = this.grupos().find((g) => g.id_grupo === this.formSes.grupoId)?.estudiantes ?? [];
    return lista.filter((e) => e.activo !== false);
  }

  seleccionadosCount(): number {
    return this.estudiantesSeleccionados.size;
  }

  toggleEstudianteSesion(uuid: string, checked: boolean): void {
    if (checked) this.estudiantesSeleccionados.add(uuid);
    else this.estudiantesSeleccionados.delete(uuid);
  }

  async crearYAutorizarEspacio(): Promise<void> {
    if (!this.nuevoEspacioNombre.trim()) return;
    this.guardando.set(true);
    try {
      const esp = await firstValueFrom(this.scheduling.crearEspacio(this.nuevoEspacioNombre.trim()));
      await firstValueFrom(this.scheduling.autorizarEspacio(esp.id));
      this.nuevoEspacioNombre = '';
      this.mostrarCrearEspacio = false;
      await this.cargarTodo();
      this.formSes.espacioId = esp.id;
      this.snack.open('Espacio creado y autorizado.', 'OK', { duration: 2500 });
    } catch (e) {
      this.snack.open(mensajeError(e), 'Cerrar', { duration: 4000 });
    } finally {
      this.guardando.set(false);
    }
  }

  async crearSesion(): Promise<void> {
    if (!this.formSes.espacioId || !this.formSes.versionCasoId) {
      this.snack.open('Selecciona un espacio académico y un caso publicado antes de programar.', 'OK', { duration: 3500 });
      return;
    }
    this.guardando.set(true);
    try {
      const payload: any = {
        espacio_academico_id: this.formSes.espacioId,
        version_caso_id: this.formSes.versionCasoId,
        fecha_inicio: this.aIsoUtc(this.formSes.inicioLocal),
        fecha_fin: this.aIsoUtc(this.formSes.finLocal),
        tiempo_maximo_minutos: Number(this.formSes.tiempoMax),
        lugar: this.formSes.lugar.trim() || null,
        mensaje_personalizado: this.formSes.mensaje.trim() || null,
      };
      if (this.formSes.grupoId) {
        if (!this.estudiantesSeleccionados.size) {
          this.snack.open('Selecciona al menos un estudiante del grupo.', 'OK', { duration: 3500 });
          this.guardando.set(false);
          return;
        }
        payload.grupo_id = this.formSes.grupoId;
        payload.estudiantes_ids = [...this.estudiantesSeleccionados];
        payload.fecha_limite_ingreso = this.aIsoUtc(this.formSes.limiteIngresoLocal);
      }
      const res = await firstValueFrom(this.scheduling.programar(payload));
      const mensaje = 'convocatorias' in res && res.convocatorias.length
        ? 'Sesión programada. Los códigos quedaron en cola para enviarse por correo.'
        : 'Sesión programada con éxito.';
      this.snack.open(mensaje, 'Cerrar', { duration: 4000 });
      await this.cargarTodo();
    } catch (e) {
      this.snack.open(mensajeError(e), 'Cerrar', { duration: 4500 });
    } finally {
      this.guardando.set(false);
    }
  }

  iniciarEdicionSesion(s: SesionResponse): void {
    this.sesionEditando.set(s);
    const toLocal = (iso: string) => {
      const d = new Date(iso);
      const pad = (n: number) => String(n).padStart(2, '0');
      return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
    };
    this.formSes.inicioLocal = toLocal(s.fecha_inicio);
    this.formSes.finLocal = toLocal(s.fecha_fin);
    this.formSes.tiempoMax = s.tiempo_maximo_minutos;
    this.formSes.lugar = s.lugar ?? '';
    this.formSes.mensaje = s.mensaje_personalizado ?? '';
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  cancelarEdicionSesion(): void {
    this.sesionEditando.set(null);
  }

  async guardarEdicionSesion(): Promise<void> {
    const s = this.sesionEditando();
    if (!s) return;
    this.guardando.set(true);
    try {
      await firstValueFrom(
        this.scheduling.actualizarSesion(s.id, {
          fecha_inicio: this.aIsoUtc(this.formSes.inicioLocal),
          fecha_fin: this.aIsoUtc(this.formSes.finLocal),
          tiempo_maximo_minutos: Number(this.formSes.tiempoMax),
          lugar: this.formSes.lugar.trim() || null,
          mensaje_personalizado: this.formSes.mensaje.trim() || null,
        }),
      );
      this.sesionEditando.set(null);
      this.snack.open('Sesión actualizada y cambios notificados a los estudiantes.', 'OK', { duration: 3500 });
      await this.cargarTodo();
    } catch (e) {
      this.snack.open(mensajeError(e), 'Cerrar', { duration: 4500 });
    } finally {
      this.guardando.set(false);
    }
  }

  async cambiarEstado(sesionId: string, accion: 'iniciar' | 'finalizar'): Promise<void> {
    this.guardando.set(true);
    try {
      await firstValueFrom(this.scheduling.cambiarEstado(sesionId, accion));
      this.snack.open(`Sesión ${accion === 'iniciar' ? 'iniciada' : 'finalizada'}.`, 'Cerrar', { duration: 3000 });
      await this.cargarTodo();
    } catch (e) {
      this.snack.open(mensajeError(e), 'Cerrar', { duration: 4500 });
    } finally {
      this.guardando.set(false);
    }
  }

  async crearGrupo(): Promise<void> {
    if (!this.nuevoGrupoNombre.trim() || !this.nuevoGrupoPeriodo.trim()) return;
    this.guardando.set(true);
    try {
      await firstValueFrom(this.scheduling.crearGrupo(this.nuevoGrupoNombre.trim(), this.nuevoGrupoPeriodo.trim()));
      this.nuevoGrupoNombre = '';
      this.snack.open('Grupo académico creado.', 'OK', { duration: 2500 });
      await this.cargarTodo();
    } catch (e) {
      this.snack.open(mensajeError(e), 'Cerrar', { duration: 4000 });
    } finally {
      this.guardando.set(false);
    }
  }

  async matricular(grupoId: number): Promise<void> {
    const idUsuario = this.matricularPorGrupo[grupoId];
    if (!idUsuario) return;
    this.guardando.set(true);
    try {
      await firstValueFrom(this.scheduling.matricularEstudiante(grupoId, idUsuario));
      this.matricularPorGrupo[grupoId] = null;
      this.snack.open('Estudiante matriculado en el grupo.', 'OK', { duration: 2500 });
      await this.cargarTodo();
    } catch (e) {
      this.snack.open(mensajeError(e), 'Cerrar', { duration: 4000 });
    } finally {
      this.guardando.set(false);
    }
  }

  async retirarMatricula(grupoId: number, idUsuario: number): Promise<void> {
    this.guardando.set(true);
    try {
      await firstValueFrom(this.scheduling.retirarEstudiante(grupoId, idUsuario));
      this.snack.open('Estudiante retirado del grupo.', 'OK', { duration: 2500 });
      await this.cargarTodo();
    } catch (e) {
      this.snack.open(mensajeError(e), 'Cerrar', { duration: 4000 });
    } finally {
      this.guardando.set(false);
    }
  }

  nombreCaso(versionId: string): string {
    return this.casosTodos().find((c) => c.version_id === versionId)?.nombre ?? versionId.slice(0, 8);
  }

  nombreEspacio(espId: string): string {
    return this.espacios().find((e) => e.id === espId)?.nombre ?? espId.slice(0, 8);
  }

}
