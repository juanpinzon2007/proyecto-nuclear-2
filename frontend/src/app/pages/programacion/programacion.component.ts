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
import { MatTableModule } from '@angular/material/table';
import { MatTabsModule } from '@angular/material/tabs';
import { firstValueFrom } from 'rxjs';
import { mensajeError } from '../../core/api-error';
import {
  CasoResumenResponse,
  ConvocatoriaAsignadaResponse,
  EspacioAcademicoResponse,
  EstudianteDisponibleItem,
  GrupoResponse,
  SesionConAsignacionResponse,
  SesionResponse,
} from '../../core/api.models';
import { CasesService } from '../../core/cases.service';
import { SchedulingService } from '../../core/scheduling.service';

@Component({
  selector: 'app-programacion',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterLink,
    MatCardModule,
    MatTabsModule,
    MatTableModule,
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
          <p class="eyebrow">Despliegue de Misiones</p>
          <h2>Programación de Sesiones, Espacios y Grupos</h2>
          <p class="subtitle">
            Organiza cohortes estudiantiles, autoriza espacios académicos y agenda sesiones con generación automática de códigos.
          </p>
        </div>
        <button mat-stroked-button (click)="cargarTodo()" [disabled]="cargando()">
          <mat-icon>refresh</mat-icon> Actualizar
        </button>
      </div>

      @if (codigosGenerados().length) {
        <div class="codes-banner">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; gap:10px; flex-wrap:wrap;">
            <strong class="mono green">BÓVEDA DE CÓDIGOS INDIVIDUALES EMITIDOS (COMPARTIR CON CADA ESTUDIANTE):</strong>
            <button mat-button type="button" (click)="codigosGenerados.set([])">Ocultar</button>
          </div>
          <div class="codes-list">
            @for (c of codigosGenerados(); track c.convocatoria_id) {
              <div class="code-chip">
                <span>{{ nombreEstudiantePorUuid(c.estudiante_id) }}</span>
                <span class="mono gold-code">{{ c.codigo_acceso }}</span>
              </div>
            }
          </div>
        </div>
      }

      <mat-tab-group animationDuration="200ms">
        <!-- TAB 1: Sesiones Programadas y Nueva Programación -->
        <mat-tab label="Sesiones Académicas">
          <div class="tab-grid">
            <!-- Formulario Crear Sesión / Editar Sesión -->
            <mat-card class="panel panel-cyan-left">
              <mat-card-header>
                <mat-card-title>{{ sesionEditando() ? 'Editar Horario & Notificar Cambios' : 'Programar Nueva Sesión' }}</mat-card-title>
                <mat-card-subtitle>Solo aparecen casos en estado PUBLICADO y espacios autorizados</mat-card-subtitle>
              </mat-card-header>
              <mat-card-content>
                <form class="form-stack" (ngSubmit)="sesionEditando() ? guardarEdicionSesion() : crearSesion()">
                  @if (!sesionEditando()) {
                    <div class="inline-space">
                      <mat-form-field appearance="outline" style="flex:1;">
                        <mat-label>Espacio académico autorizado</mat-label>
                        <mat-select [(ngModel)]="formSes.espacioId" name="espId" required>
                          @for (e of espacios(); track e.id) {
                            <mat-option [value]="e.id">{{ e.nombre }}</mat-option>
                          }
                        </mat-select>
                      </mat-form-field>
                      <button mat-stroked-button type="button" (click)="mostrarCrearEspacio = !mostrarCrearEspacio" title="Crear nuevo espacio académico">
                        <mat-icon>add</mat-icon>
                      </button>
                    </div>

                    @if (mostrarCrearEspacio) {
                      <div class="mini-create">
                        <input class="dark-input" [(ngModel)]="nuevoEspacioNombre" name="newEsp" placeholder="Nombre del nuevo espacio..." />
                        <button mat-flat-button color="primary" type="button" (click)="crearYAutorizarEspacio()">Crear</button>
                      </div>
                    }

                    <mat-form-field appearance="outline">
                      <mat-label>Versión de caso PUBLICADO</mat-label>
                      <mat-select [(ngModel)]="formSes.versionCasoId" name="casoId" (ngModelChange)="alCambiarCaso($event)" required>
                        @for (c of casosPublicados(); track c.version_id) {
                          <mat-option [value]="c.version_id">{{ c.nombre }} (v{{ c.numero }} · máx {{ c.tiempo_estimado_min }}m)</mat-option>
                        }
                      </mat-select>
                    </mat-form-field>
                  }

                  <mat-form-field appearance="outline">
                    <mat-label>Fecha y hora de inicio</mat-label>
                    <input matInput type="datetime-local" [(ngModel)]="formSes.inicioLocal" name="inicio" required />
                  </mat-form-field>

                  <mat-form-field appearance="outline">
                    <mat-label>Fecha y hora de finalización</mat-label>
                    <input matInput type="datetime-local" [(ngModel)]="formSes.finLocal" name="fin" required />
                  </mat-form-field>

                  <mat-form-field appearance="outline">
                    <mat-label>Tiempo máximo del intento (minutos)</mat-label>
                    <input matInput type="number" min="1" [(ngModel)]="formSes.tiempoMax" name="tmax" required />
                  </mat-form-field>

                  <mat-form-field appearance="outline">
                    <mat-label>Lugar físico o enlace virtual</mat-label>
                    <input matInput [(ngModel)]="formSes.lugar" name="lugar" placeholder="Ej: Sala de Simulación 2 / Zoom" />
                  </mat-form-field>

                  <mat-form-field appearance="outline">
                    <mat-label>Mensaje personalizado de convocatoria</mat-label>
                    <textarea matInput rows="2" [(ngModel)]="formSes.mensaje" name="msg"></textarea>
                  </mat-form-field>

                  @if (!sesionEditando()) {
                    <mat-form-field appearance="outline">
                      <mat-label>Grupo académico (opcional para convocar ahora)</mat-label>
                      <mat-select [(ngModel)]="formSes.grupoId" name="grpId" (ngModelChange)="alCambiarGrupo($event)">
                        <mat-option [value]="null">-- Convocar manualmente después --</mat-option>
                        @for (g of grupos(); track g.id_grupo) {
                          <mat-option [value]="g.id_grupo">{{ g.nombre }} ({{ g.periodo }} · {{ g.estudiantes.length }} est.)</mat-option>
                        }
                      </mat-select>
                    </mat-form-field>

                    @if (formSes.grupoId) {
                      <mat-form-field appearance="outline">
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

                  <div class="actions-row">
                    <button mat-flat-button color="primary" type="submit" [disabled]="guardando()">
                      <mat-icon>{{ sesionEditando() ? 'notifications_active' : 'event_available' }}</mat-icon>
                      {{ sesionEditando() ? 'Guardar y Notificar Cambios' : 'Programar Sesión' }}
                    </button>
                    @if (sesionEditando()) {
                      <button mat-button type="button" (click)="cancelarEdicionSesion()">Cancelar</button>
                    }
                  </div>
                </form>
              </mat-card-content>
            </mat-card>

            <!-- Tabla de Sesiones -->
            <mat-card class="panel">
              <mat-card-header>
                <mat-card-title>Sesiones Programadas ({{ sesiones().length }})</mat-card-title>
              </mat-card-header>
              <mat-card-content>
                <div class="table-scroll">
                  <table mat-table [dataSource]="sesiones()" class="full-table">
                    <ng-container matColumnDef="caso">
                      <th mat-header-cell *matHeaderCellDef>Caso & Espacio</th>
                      <td mat-cell *matCellDef="let s">
                        <div class="cell-main">{{ nombreCaso(s.version_caso_id) }}</div>
                        <div class="cell-sub">{{ nombreEspacio(s.espacio_academico_id) }} · {{ s.lugar || 'Virtual' }}</div>
                      </td>
                    </ng-container>

                    <ng-container matColumnDef="horario">
                      <th mat-header-cell *matHeaderCellDef>Ventana</th>
                      <td mat-cell *matCellDef="let s">
                        <div class="mono">{{ s.fecha_inicio | date:'short' }}</div>
                        <div class="cell-sub">hasta {{ s.fecha_fin | date:'short' }} ({{ s.tiempo_maximo_minutos }}m)</div>
                      </td>
                    </ng-container>

                    <ng-container matColumnDef="estado">
                      <th mat-header-cell *matHeaderCellDef>Estado</th>
                      <td mat-cell *matCellDef="let s">
                        <span class="state-pill" [class]="'st-' + s.estado.toLowerCase()">{{ s.estado }}</span>
                      </td>
                    </ng-container>

                    <ng-container matColumnDef="acciones">
                      <th mat-header-cell *matHeaderCellDef>Operaciones</th>
                      <td mat-cell *matCellDef="let s">
                        <div class="btn-wrap">
                          @if (s.estado === 'SIN_INICIAR') {
                            <button mat-flat-button color="primary" type="button" (click)="cambiarEstado(s.id, 'iniciar')">
                              Iniciar
                            </button>
                          }
                          @if (s.estado === 'EN_CURSO') {
                            <button mat-flat-button color="warn" type="button" (click)="cambiarEstado(s.id, 'finalizar')">
                              Finalizar
                            </button>
                          }
                          @if (s.estado !== 'FINALIZADO') {
                            <button mat-stroked-button type="button" (click)="iniciarEdicionSesion(s)" title="Editar fechas/lugar y notificar cambios">
                              Editar
                            </button>
                          }
                          <a mat-stroked-button [routerLink]="['/programacion', s.id, 'convocatorias']">Convocatorias</a>
                          <a mat-stroked-button [routerLink]="['/programacion', s.id, 'evaluacion']">Evaluación</a>
                        </div>
                      </td>
                    </ng-container>

                    <tr mat-header-row *matHeaderRowDef="['caso', 'horario', 'estado', 'acciones']"></tr>
                    <tr mat-row *matRowDef="let row; columns: ['caso', 'horario', 'estado', 'acciones']"></tr>
                  </table>
                </div>
              </mat-card-content>
            </mat-card>
          </div>
        </mat-tab>

        <!-- TAB 2: Grupos Académicos y Matrículas RF-04 -->
        <mat-tab label="Grupos & Estudiantes">
          <div class="tab-grid">
            <mat-card class="panel panel-amber-left">
              <mat-card-header>
                <mat-card-title>Crear Grupo Académico</mat-card-title>
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
                  <button mat-flat-button color="primary" type="submit" [disabled]="guardando()">
                    <mat-icon>group_add</mat-icon> Crear grupo
                  </button>
                </form>
              </mat-card-content>
            </mat-card>

            <mat-card class="panel">
              <mat-card-header>
                <mat-card-title>Grupos y Matrículas ({{ grupos().length }})</mat-card-title>
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
                        <span class="mono cyan">{{ g.estudiantes.length }} ESTUDIANTE(S)</span>
                      </div>

                      <div class="enroll-bar">
                        <select class="dark-sel" [(ngModel)]="matricularPorGrupo[g.id_grupo]" [name]="'m_' + g.id_grupo">
                          <option [ngValue]="null">Seleccionar estudiante registrado...</option>
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
    .prog-wrap { padding: 4px 0 36px; max-width: 1160px; margin: 0 auto; }
    .subtitle { margin: 4px 0 0; color: var(--muted); font-size: 13px; }
    .tab-grid { display: grid; grid-template-columns: 400px 1fr; gap: 20px; margin-top: 16px; align-items: start; }
    @media (max-width: 1120px) { .tab-grid { grid-template-columns: 1fr; } }
    .form-stack { display: flex; flex-direction: column; gap: 12px; padding-top: 14px; }
    .inline-space { display: flex; gap: 8px; align-items: center; }
    .mini-create { display: flex; gap: 8px; padding: 10px; background: #070a10; border: 1px solid var(--line); }
    .dark-input { flex: 1; background: #10141b; color: var(--text); border: 1px solid var(--line-strong); padding: 6px 10px; }
    .students-check { background: #070a10; border: 1px solid var(--line); padding: 12px; display: flex; flex-direction: column; gap: 4px; }
    .check-title { font-family: var(--mono); font-size: 11px; color: var(--cyan); text-transform: uppercase; margin-bottom: 4px; }
    .actions-row { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
    .table-scroll { overflow-x: auto; }
    .full-table { width: 100%; }
    .cell-main { font-weight: 600; color: var(--text); }
    .cell-sub { font-size: 12px; color: var(--muted); }
    .state-pill { padding: 3px 9px; border: 1px solid rgba(184, 211, 214, 0.25); font-family: var(--mono); font-size: 11px; font-weight: 700; text-transform: uppercase; }
    .st-sin_iniciar { border-color: rgba(255, 184, 0, 0.55); background: rgba(255, 184, 0, 0.12); color: var(--amber); }
    .st-en_curso { border-color: rgba(0, 232, 148, 0.55); background: rgba(0, 232, 148, 0.12); color: var(--green); }
    .st-finalizado { border-color: rgba(169, 181, 184, 0.35); background: rgba(169, 181, 184, 0.1); color: var(--muted); }
    .btn-wrap { display: flex; gap: 6px; flex-wrap: wrap; }
    .codes-banner { background: rgba(0, 232, 148, 0.08); border: 1px solid rgba(0, 232, 148, 0.5); border-left: 4px solid var(--green); padding: 14px 16px; margin-bottom: 16px; }
    .codes-list { display: flex; flex-wrap: wrap; gap: 10px; }
    .code-chip { background: #070a10; border: 1px solid var(--line-strong); padding: 8px 12px; display: flex; gap: 12px; align-items: center; }
    .gold-code { color: var(--amber) !important; font-weight: 700; font-size: 14px; letter-spacing: 1px; }
    .group-card { background: #0b1017; border: 1px solid var(--line); border-left: 4px solid var(--cyan); padding: 14px; }
    .group-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; gap: 10px; flex-wrap: wrap; }
    .period-tag { margin-left: 8px; border: 1px solid rgba(255, 184, 0, 0.5); background: rgba(255, 184, 0, 0.1); color: var(--amber); padding: 2px 8px; font-family: var(--mono); font-size: 11px; font-weight: 700; }
    .enroll-bar { display: flex; gap: 8px; align-items: center; margin-bottom: 10px; flex-wrap: wrap; }
    .dark-sel { flex: 1; background: #070a10; color: var(--text); border: 1px solid var(--line-strong); padding: 8px 10px; font-family: var(--mono); font-size: 12px; }
    .enrolled-list { display: flex; flex-direction: column; gap: 6px; }
    .enrolled-item { display: flex; justify-content: space-between; align-items: center; padding: 6px 10px; background: #070a10; border: 1px solid rgba(184, 211, 214, 0.12); font-size: 13px; flex-wrap: wrap; gap: 8px; }
    @media (max-width: 640px) {
      .inline-space, .mini-create, .enroll-bar { flex-wrap: wrap; }
      .mini-create button, .enroll-bar button { width: 100%; }
      .btn-wrap a, .btn-wrap button { flex: 1 1 auto; }
    }
  `],
})
export class ProgramacionComponent implements OnInit {
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
  readonly codigosGenerados = signal<ConvocatoriaAsignadaResponse[]>([]);
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
      if ('convocatorias' in res && res.convocatorias.length) {
        this.codigosGenerados.set((res as SesionConAsignacionResponse).convocatorias);
      }
      this.snack.open('Sesión programada con éxito.', 'OK', { duration: 3000 });
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
      this.snack.open(`Sesión ${accion === 'iniciar' ? 'INICIADA' : 'FINALIZADA'}.`, 'OK', { duration: 3000 });
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

  nombreEstudiantePorUuid(uuid: string): string {
    const est = this.estudiantesDisponibles().find((e) => e.uuid_scheduling === uuid);
    return est ? `${est.nombre} (${est.correo})` : uuid.slice(0, 8);
  }
}
