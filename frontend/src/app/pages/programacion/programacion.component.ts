import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatTabsModule } from '@angular/material/tabs';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTableModule } from '@angular/material/table';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { SchedulingService } from '../../core/scheduling.service';
import { CasesService } from '../../core/cases.service';
import { CasoResumenResponse, EspacioAcademicoResponse, ProgramarSesionRequest, SesionResponse } from '../../core/api.models';
import { mensajeError } from '../../core/api-error';

@Component({
  selector: 'app-programacion',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterLink,
    MatCardModule,
    MatTabsModule,
    MatButtonModule,
    MatIconModule,
    MatTableModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatProgressSpinnerModule,
  ],
  template: `
    <div class="page">
      <div class="page-header">
        <div>
          <h1>Programación Académica</h1>
          <p class="muted">Gestión de sesiones de simulación, espacios físicos/virtuales y convocatorias de estudiantes</p>
        </div>
      </div>

      @if (error()) {
        <div class="error-box">{{ error() }}</div>
      }
      @if (mensajeExito()) {
        <div class="success-box">{{ mensajeExito() }}</div>
      }

      <mat-tab-group mat-stretch-tabs="false">
        <!-- Pestaña 1: Sesiones -->
        <mat-tab label="Sesiones Programadas">
          <div style="padding-top: 16px;">
            @if (cargando()) {
              <div style="display: flex; justify-content: center; padding: 40px;">
                <mat-spinner diameter="40"></mat-spinner>
              </div>
            } @else if (sesiones().length === 0) {
              <mat-card style="text-align: center; padding: 32px;">
                <mat-icon style="font-size: 48px; width: 48px; height: 48px; opacity: 0.5;">event_busy</mat-icon>
                <h3>No hay sesiones programadas</h3>
                <p class="muted">Utiliza la pestaña "Programar Nueva Sesión" para planificar una sesión con un caso de estudio.</p>
              </mat-card>
            } @else {
              <table mat-table [dataSource]="sesiones()" class="mat-elevation-z1">
                <ng-container matColumnDef="estado">
                  <th mat-header-cell *matHeaderCellDef>Estado</th>
                  <td mat-cell *matCellDef="let s">
                    <span class="chip" [class.ok]="s.estado === 'FINALIZADO'" [class.warn]="s.estado === 'EN_CURSO'">
                      {{ s.estado }}
                    </span>
                  </td>
                </ng-container>

                <ng-container matColumnDef="inicio">
                  <th mat-header-cell *matHeaderCellDef>Fecha y Horario</th>
                  <td mat-cell *matCellDef="let s">
                    <div><strong>Inicio:</strong> {{ s.fecha_inicio | date:'short' }}</div>
                    <div><strong>Fin:</strong> {{ s.fecha_fin | date:'short' }} ({{ s.tiempo_maximo_minutos }} min max)</div>
                    @if (s.lugar) {
                      <div class="muted">Lugar: {{ s.lugar }}</div>
                    }
                  </td>
                </ng-container>

                <ng-container matColumnDef="caso">
                  <th mat-header-cell *matHeaderCellDef>Versión Caso</th>
                  <td mat-cell *matCellDef="let s">
                    <span class="mono" style="font-size: 12px;">{{ s.version_caso_id }}</span>
                  </td>
                </ng-container>

                <ng-container matColumnDef="acciones">
                  <th mat-header-cell *matHeaderCellDef style="text-align: right;">Acciones</th>
                  <td mat-cell *matCellDef="let s" style="text-align: right;">
                    <a mat-button color="primary" [routerLink]="['/programacion', s.id, 'convocatorias']" title="Gestionar convocatorias de estudiantes">
                      <mat-icon>people</mat-icon> Convocatorias
                    </a>
                    <a mat-button color="accent" [routerLink]="['/programacion', s.id, 'evaluacion']" title="Evaluación técnica y consolidación">
                      <mat-icon>assessment</mat-icon> Evaluación
                    </a>
                    @if (s.estado === 'SIN_INICIAR') {
                      <button mat-button color="primary" (click)="cambiarEstadoSesion(s.id, 'iniciar')" title="Iniciar sesión">
                        <mat-icon>play_arrow</mat-icon> Iniciar
                      </button>
                    }
                    @if (s.estado === 'EN_CURSO') {
                      <button mat-button color="warn" (click)="cambiarEstadoSesion(s.id, 'finalizar')" title="Finalizar sesión">
                        <mat-icon>stop</mat-icon> Finalizar
                      </button>
                    }
                  </td>
                </ng-container>

                <tr mat-header-row *matHeaderRowDef="columnasSesiones"></tr>
                <tr mat-row *matRowDef="let row; columns: columnasSesiones;"></tr>
              </table>
            }
          </div>
        </mat-tab>

        <!-- Pestaña 2: Programar Nueva Sesión -->
        <mat-tab label="Programar Nueva Sesión">
          <div style="padding-top: 16px; max-width: 800px;">
            <mat-card>
              <mat-card-header>
                <mat-card-title>Configurar Sesión Académica</mat-card-title>
              </mat-card-header>
              <mat-card-content style="padding-top: 16px;">
                <form (ngSubmit)="programarSesion()" class="stack">
                  <div class="row">
                    <mat-form-field appearance="outline">
                      <mat-label>Espacio Académico</mat-label>
                      <mat-select [(ngModel)]="nuevaSesionEspacioId" name="nuevaSesionEspacioId" required>
                        @for (esp of espacios(); track esp.id) {
                          <mat-option [value]="esp.id">{{ esp.nombre }}</mat-option>
                        }
                      </mat-select>
                    </mat-form-field>

                    <mat-form-field appearance="outline">
                      <mat-label>Versión del Caso de Estudio</mat-label>
                      <mat-select [(ngModel)]="nuevaSesionVersionCasoId" name="nuevaSesionVersionCasoId" required>
                        @for (c of casos(); track c.version_id) {
                          <mat-option [value]="c.version_id">
                            {{ c.nombre }} ({{ c.estado }})
                          </mat-option>
                        }
                      </mat-select>
                    </mat-form-field>
                  </div>

                  <div class="row">
                    <mat-form-field appearance="outline">
                      <mat-label>Fecha y Hora de Inicio</mat-label>
                      <input matInput type="datetime-local" [(ngModel)]="nuevaSesionInicio" name="nuevaSesionInicio" required />
                    </mat-form-field>

                    <mat-form-field appearance="outline">
                      <mat-label>Fecha y Hora de Fin</mat-label>
                      <input matInput type="datetime-local" [(ngModel)]="nuevaSesionFin" name="nuevaSesionFin" required />
                    </mat-form-field>

                    <mat-form-field appearance="outline" style="max-width: 180px;">
                      <mat-label>Tiempo Máx (min)</mat-label>
                      <input matInput type="number" [(ngModel)]="nuevaSesionTiempo" name="nuevaSesionTiempo" required min="10" />
                    </mat-form-field>
                  </div>

                  <mat-form-field appearance="outline" class="full">
                    <mat-label>Lugar / Enlace de la sesión (Opcional)</mat-label>
                    <input matInput [(ngModel)]="nuevaSesionLugar" name="nuevaSesionLugar" placeholder="Laboratorio 302 o Sala Virtual" />
                  </mat-form-field>

                  <mat-form-field appearance="outline" class="full">
                    <mat-label>Mensaje Personalizado para los estudiantes (Opcional)</mat-label>
                    <textarea matInput rows="2" [(ngModel)]="nuevaSesionMensaje" name="nuevaSesionMensaje" placeholder="Instrucciones previas a la simulación..."></textarea>
                  </mat-form-field>

                  <div style="display: flex; justify-content: flex-end;">
                    <button mat-flat-button color="primary" type="submit" [disabled]="guardando()">
                      @if (guardando()) {
                        <mat-spinner diameter="18"></mat-spinner>
                      } @else {
                        Crear Sesión
                      }
                    </button>
                  </div>
                </form>
              </mat-card-content>
            </mat-card>
          </div>
        </mat-tab>

        <!-- Pestaña 3: Espacios Académicos -->
        <mat-tab label="Espacios Académicos">
          <div style="padding-top: 16px; max-width: 600px;">
            <mat-card style="margin-bottom: 16px;">
              <mat-card-header>
                <mat-card-title>Crear Espacio</mat-card-title>
              </mat-card-header>
              <mat-card-content style="padding-top: 16px;">
                <form (ngSubmit)="crearEspacio()" style="display: flex; gap: 8px;">
                  <mat-form-field appearance="outline" style="flex: 1;">
                    <mat-label>Nombre del Espacio</mat-label>
                    <input matInput [(ngModel)]="nuevoEspacioNombre" name="nuevoEspacioNombre" required placeholder="Ej: Laboratorio de Conducta Social A" />
                  </mat-form-field>
                  <button mat-flat-button color="primary" type="submit" style="height: 56px;" [disabled]="guardando()">
                    Agregar
                  </button>
                </form>
              </mat-card-content>
            </mat-card>

            <mat-card>
              <mat-card-header>
                <mat-card-title>Espacios Registrados</mat-card-title>
              </mat-card-header>
              <mat-card-content style="padding-top: 16px;">
                @if (espacios().length === 0) {
                  <p class="muted">No hay espacios creados aún.</p>
                } @else {
                  <div class="stack">
                    @for (esp of espacios(); track esp.id) {
                      <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; background: var(--mat-sys-surface-container-low); border-radius: 6px;">
                        <span style="font-weight: 500;">{{ esp.nombre }}</span>
                        <span class="mono muted" style="font-size: 11px;">{{ esp.id }}</span>
                      </div>
                    }
                  </div>
                }
              </mat-card-content>
            </mat-card>
          </div>
        </mat-tab>
      </mat-tab-group>
    </div>
  `,
})
export class ProgramacionComponent implements OnInit {
  private readonly schedulingService = inject(SchedulingService);
  private readonly casesService = inject(CasesService);

  readonly columnasSesiones = ['estado', 'inicio', 'caso', 'acciones'];
  readonly sesiones = signal<SesionResponse[]>([]);
  readonly espacios = signal<EspacioAcademicoResponse[]>([]);
  readonly casos = signal<CasoResumenResponse[]>([]);

  readonly cargando = signal<boolean>(true);
  readonly guardando = signal<boolean>(false);
  readonly error = signal<string | null>(null);
  readonly mensajeExito = signal<string | null>(null);

  // Nueva sesión
  nuevaSesionEspacioId = '';
  nuevaSesionVersionCasoId = '';
  nuevaSesionInicio = '';
  nuevaSesionFin = '';
  nuevaSesionTiempo = 45;
  nuevaSesionLugar = '';
  nuevaSesionMensaje = '';

  // Nuevo espacio
  nuevoEspacioNombre = '';

  ngOnInit(): void {
    this.cargarDatos();
  }

  cargarDatos(): void {
    this.cargando.set(true);
    this.error.set(null);

    this.schedulingService.sesiones().subscribe({
      next: (s) => this.sesiones.set(s),
      error: (err) => this.error.set(mensajeError(err)),
    });

    this.schedulingService.espacios().subscribe({
      next: (esp) => this.espacios.set(esp),
      error: () => {},
    });

    this.casesService.listar().subscribe({
      next: (c) => this.casos.set(c),
      error: () => {},
      complete: () => this.cargando.set(false),
    });
  }

  programarSesion(): void {
    if (!this.nuevaSesionEspacioId || !this.nuevaSesionVersionCasoId || !this.nuevaSesionInicio || !this.nuevaSesionFin) {
      this.error.set('Por favor completa todos los campos requeridos para la sesión.');
      return;
    }
    this.guardando.set(true);
    this.error.set(null);
    this.mensajeExito.set(null);

    const req: ProgramarSesionRequest = {
      espacio_academico_id: this.nuevaSesionEspacioId,
      version_caso_id: this.nuevaSesionVersionCasoId,
      fecha_inicio: new Date(this.nuevaSesionInicio).toISOString(),
      fecha_fin: new Date(this.nuevaSesionFin).toISOString(),
      tiempo_maximo_minutos: this.nuevaSesionTiempo,
      lugar: this.nuevaSesionLugar || null,
      mensaje_personalizado: this.nuevaSesionMensaje || null,
    };

    this.schedulingService.programar(req).subscribe({
      next: () => {
        this.guardando.set(false);
        this.mensajeExito.set('Sesión programada correctamente.');
        this.nuevaSesionLugar = '';
        this.nuevaSesionMensaje = '';
        this.cargarDatos();
      },
      error: (err) => {
        this.error.set(mensajeError(err));
        this.guardando.set(false);
      },
    });
  }

  crearEspacio(): void {
    if (!this.nuevoEspacioNombre.trim()) return;
    this.guardando.set(true);
    this.error.set(null);

    this.schedulingService.crearEspacio(this.nuevoEspacioNombre.trim()).subscribe({
      next: (esp) => {
        this.espacios.update((list) => [...list, esp]);
        this.nuevoEspacioNombre = '';
        this.guardando.set(false);
        this.mensajeExito.set('Espacio académico creado.');
      },
      error: (err) => {
        this.error.set(mensajeError(err));
        this.guardando.set(false);
      },
    });
  }

  cambiarEstadoSesion(id: string, accion: 'iniciar' | 'finalizar'): void {
    this.error.set(null);
    this.schedulingService.cambiarEstado(id, accion).subscribe({
      next: () => {
        this.mensajeExito.set(`Sesión marcada como ${accion === 'iniciar' ? 'EN CURSO' : 'FINALIZADA'}.`);
        this.cargarDatos();
      },
      error: (err) => this.error.set(mensajeError(err)),
    });
  }
}

