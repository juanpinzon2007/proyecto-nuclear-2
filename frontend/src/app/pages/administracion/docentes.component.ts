import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatTabsModule } from '@angular/material/tabs';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTableModule } from '@angular/material/table';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { IdentityService } from '../../core/identity.service';
import { CuentaDocenteRespuesta, PerfilPermisosDocentesRespuesta, Rol } from '../../core/api.models';
import { mensajeError } from '../../core/api-error';

@Component({
  selector: 'app-docentes',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
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
          <h1>Administración de Identidad y Roles</h1>
          <p class="muted">Gestión de usuarios docentes, permisos institucionales y excepciones académicas</p>
        </div>
      </div>

      @if (error()) {
        <div class="error-box">{{ error() }}</div>
      }
      @if (mensajeExito()) {
        <div class="success-box">{{ mensajeExito() }}</div>
      }

      <mat-tab-group mat-stretch-tabs="false">
        <!-- Pestaña 1: Cuentas Docentes -->
        <mat-tab label="Cuentas Docentes">
          <div style="padding-top: 16px;">
            <!-- Formulario crear docente -->
            <mat-card style="margin-bottom: 24px;">
              <mat-card-header>
                <mat-card-title>Crear Nueva Cuenta Docente</mat-card-title>
              </mat-card-header>
              <mat-card-content style="padding-top: 16px;">
                <form (ngSubmit)="crearDocente()" class="row">
                  <mat-form-field appearance="outline">
                    <mat-label>Nombre Completo</mat-label>
                    <input matInput [(ngModel)]="nuevoDocenteNombre" name="nuevoDocenteNombre" required placeholder="Prof. Carlos Mendoza" />
                  </mat-form-field>

                  <mat-form-field appearance="outline">
                    <mat-label>Correo Institucional</mat-label>
                    <input matInput type="email" [(ngModel)]="nuevoDocenteCorreo" name="nuevoDocenteCorreo" required placeholder="carlos@universidad.edu.co" />
                  </mat-form-field>

                  <mat-form-field appearance="outline">
                    <mat-label>Contraseña Inicial</mat-label>
                    <input matInput type="password" [(ngModel)]="nuevoDocenteClave" name="nuevoDocenteClave" required />
                  </mat-form-field>

                  <div style="display: flex; align-items: center;">
                    <button mat-flat-button color="primary" type="submit" style="height: 56px;" [disabled]="guardando()">
                      @if (guardando()) {
                        <mat-spinner diameter="18"></mat-spinner>
                      } @else {
                        <span>Registrar Docente</span>
                      }
                    </button>
                  </div>
                </form>
              </mat-card-content>
            </mat-card>

            @if (cargando()) {
              <div style="display: flex; justify-content: center; padding: 40px;">
                <mat-spinner diameter="40"></mat-spinner>
              </div>
            } @else {
              <table mat-table [dataSource]="docentes()" class="mat-elevation-z1">
                <ng-container matColumnDef="nombre">
                  <th mat-header-cell *matHeaderCellDef>Nombre</th>
                  <td mat-cell *matCellDef="let d"><strong>{{ d.nombre }}</strong></td>
                </ng-container>

                <ng-container matColumnDef="correo">
                  <th mat-header-cell *matHeaderCellDef>Correo</th>
                  <td mat-cell *matCellDef="let d">{{ d.correo }}</td>
                </ng-container>

                <ng-container matColumnDef="id">
                  <th mat-header-cell *matHeaderCellDef>ID Usuario</th>
                  <td mat-cell *matCellDef="let d"><span class="mono">{{ d.id_usuario }}</span></td>
                </ng-container>

                <ng-container matColumnDef="estado">
                  <th mat-header-cell *matHeaderCellDef>Estado</th>
                  <td mat-cell *matCellDef="let d">
                    <span class="chip" [class.ok]="d.activo" [class.bad]="!d.activo">
                      {{ d.activo ? 'ACTIVO' : 'INACTIVO' }}
                    </span>
                  </td>
                </ng-container>

                <tr mat-header-row *matHeaderRowDef="columnasDocentes"></tr>
                <tr mat-row *matRowDef="let row; columns: columnasDocentes;"></tr>
              </table>
            }
          </div>
        </mat-tab>

        <!-- Pestaña 2: Permisos Globales del Rol Docente -->
        <mat-tab label="Permisos del Rol Docente">
          <div style="padding-top: 16px; max-width: 700px;">
            <mat-card>
              <mat-card-header>
                <mat-card-title>Configuración Institucional del Rol Docente</mat-card-title>
                <mat-card-subtitle>
                  Alcance: {{ perfilPermisos()?.alcance || 'Global' }} · Docentes vinculados: {{ perfilPermisos()?.docentes_afectados || 0 }}
                </mat-card-subtitle>
              </mat-card-header>
              <mat-card-content style="padding-top: 16px;">
                <p>Permisos actualmente asignados a la plantilla docente:</p>
                <div class="stack" style="margin: 12px 0;">
                  @for (permiso of permisosDisponibles(); track permiso) {
                    <div style="display: flex; align-items: center; justify-content: space-between; padding: 8px 12px; background: var(--mat-sys-surface-container-low); border-radius: 6px;">
                      <span class="mono">{{ permiso }}</span>
                      <button mat-stroked-button [color]="tienePermiso(permiso) ? 'warn' : 'primary'" (click)="togglePermiso(permiso)">
                        {{ tienePermiso(permiso) ? 'Revocar' : 'Otorgar' }}
                      </button>
                    </div>
                  }
                </div>
                <div style="text-align: right; margin-top: 16px;">
                  <button mat-flat-button color="primary" (click)="guardarPermisosRol()" [disabled]="guardando()">
                    Guardar Cambios de Permisos
                  </button>
                </div>
              </mat-card-content>
            </mat-card>
          </div>
        </mat-tab>

        <!-- Pestaña 3: Excepciones de Repetición -->
        <mat-tab label="Excepción de Repetición">
          <div style="padding-top: 16px; max-width: 600px;">
            <mat-card>
              <mat-card-header>
                <mat-card-title>Autorizar Repetición Excepcional</mat-card-title>
              </mat-card-header>
              <mat-card-content style="padding-top: 16px;">
                <p class="muted">Habilita a un estudiante para presentar nuevamente un intento en una sesión con restricciones.</p>
                <form (ngSubmit)="autorizarRepeticion()" class="stack">
                  <mat-form-field appearance="outline" class="full">
                    <mat-label>UUID de la Sesión</mat-label>
                    <input matInput [(ngModel)]="repeticionSesionId" name="repeticionSesionId" required />
                  </mat-form-field>

                  <mat-form-field appearance="outline" class="full">
                    <mat-label>ID / UUID del Estudiante</mat-label>
                    <input matInput [(ngModel)]="repeticionEstudianteId" name="repeticionEstudianteId" required />
                  </mat-form-field>

                  <div style="display: flex; justify-content: flex-end;">
                    <button mat-flat-button color="primary" type="submit" [disabled]="guardando()">
                      Emitir Autorización de Repetición
                    </button>
                  </div>
                </form>
              </mat-card-content>
            </mat-card>
          </div>
        </mat-tab>
      </mat-tab-group>
    </div>
  `,
})
export class DocentesComponent implements OnInit {
  private readonly identityService = inject(IdentityService);

  readonly columnasDocentes = ['nombre', 'correo', 'id', 'estado'];
  readonly docentes = signal<CuentaDocenteRespuesta[]>([]);
  readonly perfilPermisos = signal<PerfilPermisosDocentesRespuesta | null>(null);
  readonly permisosAsignados = signal<string[]>([]);
  readonly permisosDisponibles = signal<string[]>([]);

  readonly cargando = signal<boolean>(true);
  readonly guardando = signal<boolean>(false);
  readonly error = signal<string | null>(null);
  readonly mensajeExito = signal<string | null>(null);

  // Crear docente
  nuevoDocenteNombre = '';
  nuevoDocenteCorreo = '';
  nuevoDocenteClave = '';

  // Excepción
  repeticionSesionId = '';
  repeticionEstudianteId = '';

  ngOnInit(): void {
    this.cargarDatos();
  }

  cargarDatos(): void {
    this.cargando.set(true);
    this.error.set(null);

    this.identityService.listarDocentes().subscribe({
      next: (res) => this.docentes.set(res.docentes),
      error: (err) => this.error.set(mensajeError(err)),
      complete: () => this.cargando.set(false),
    });

    this.identityService.permisosRolDocente().subscribe({
      next: (res) => {
        this.perfilPermisos.set(res);
        this.permisosAsignados.set([...res.permisos]);
        this.permisosDisponibles.set([...res.permisos_disponibles]);
      },
      error: () => {},
    });
  }

  crearDocente(): void {
    if (!this.nuevoDocenteCorreo || !this.nuevoDocenteClave) return;
    this.guardando.set(true);
    this.error.set(null);

    this.identityService.crearDocente({
      nombre: this.nuevoDocenteNombre,
      correo: this.nuevoDocenteCorreo,
      clave: this.nuevoDocenteClave,
      roles: ['DOCENTE' as Rol],
    }).subscribe({
      next: () => {
        this.mensajeExito.set('Docente registrado correctamente.');
        this.nuevoDocenteNombre = '';
        this.nuevoDocenteCorreo = '';
        this.nuevoDocenteClave = '';
        this.guardando.set(false);
        this.cargarDatos();
      },
      error: (err) => {
        this.error.set(mensajeError(err));
        this.guardando.set(false);
      },
    });
  }

  tienePermiso(p: string): boolean {
    return this.permisosAsignados().includes(p);
  }

  togglePermiso(p: string): void {
    const act = this.permisosAsignados();
    if (act.includes(p)) {
      this.permisosAsignados.set(act.filter((x) => x !== p));
    } else {
      this.permisosAsignados.set([...act, p]);
    }
  }

  guardarPermisosRol(): void {
    this.guardando.set(true);
    this.error.set(null);
    this.identityService.actualizarPermisosRolDocente(this.permisosAsignados()).subscribe({
      next: (res) => {
        this.perfilPermisos.set(res);
        this.permisosAsignados.set([...res.permisos]);
        this.mensajeExito.set('Permisos del rol docente actualizados institucionalmente.');
        this.guardando.set(false);
      },
      error: (err) => {
        this.error.set(mensajeError(err));
        this.guardando.set(false);
      },
    });
  }

  autorizarRepeticion(): void {
    if (!this.repeticionSesionId || !this.repeticionEstudianteId) return;
    this.guardando.set(true);
    this.error.set(null);

    this.identityService.autorizarRepeticion({
      id_sesion: this.repeticionSesionId.trim(),
      id_estudiante: this.repeticionEstudianteId.trim(),
    }).subscribe({
      next: () => {
        this.mensajeExito.set('Excepción de repetición concedida exitosamente.');
        this.repeticionSesionId = '';
        this.repeticionEstudianteId = '';
        this.guardando.set(false);
      },
      error: (err) => {
        this.error.set(mensajeError(err));
        this.guardando.set(false);
      },
    });
  }
}

