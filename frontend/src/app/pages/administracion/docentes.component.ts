import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatChipsModule } from '@angular/material/chips';
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
  DocenteBreve,
  EspacioConAutorizaciones,
  PerfilPermisosDocentesRespuesta,
  Rol,
  UsuarioGestionItem,
} from '../../core/api.models';
import { IdentityService } from '../../core/identity.service';
import { SchedulingService } from '../../core/scheduling.service';
import { avatarUsuario } from '../../core/user-avatar';

@Component({
  selector: 'app-docentes',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatTabsModule,
    MatTableModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatCheckboxModule,
    MatButtonModule,
    MatIconModule,
    MatChipsModule,
    MatSnackBarModule,
  ],
  template: `
    <div class="admin-wrap">
      <div class="page-header">
        <div>
          <p class="eyebrow amber">Consola de Gobernanza // RF-03</p>
          <h2>Administración de Usuarios, Roles y Permisos</h2>
          <p class="subtitle">
            Control integral de cuentas, excepciones por permiso, vínculos de identidad y autorización de espacios académicos.
          </p>
        </div>
        <button mat-stroked-button (click)="cargarTodo()" [disabled]="cargando()">
          <mat-icon>refresh</mat-icon> Actualizar
        </button>
      </div>

      <mat-tab-group animationDuration="200ms">
        <!-- TAB 1: Usuarios, Roles y Permisos Individuales -->
        <mat-tab label="Usuarios & Permisos">
          <div class="tab-grid">
            <mat-card class="panel panel-cyan-left panel-card">
              <mat-card-header>
                <mat-card-title>{{ usuarioEditando() ? 'Editar Usuario #' + usuarioEditando()!.id_usuario : 'Registrar Nueva Cuenta' }}</mat-card-title>
                <mat-card-subtitle>Docentes, Estudiantes y Administradores con vínculo CASES/SCHEDULING</mat-card-subtitle>
              </mat-card-header>
              <mat-card-content>
                <form class="form-stack" (ngSubmit)="guardarUsuario()">
                  <mat-form-field appearance="outline">
                    <mat-label>Nombre completo</mat-label>
                    <input matInput [(ngModel)]="formUser.nombre" name="nombre" required />
                  </mat-form-field>

                  <mat-form-field appearance="outline">
                    <mat-label>Correo institucional</mat-label>
                    <input matInput type="email" [(ngModel)]="formUser.correo" name="correo" required />
                  </mat-form-field>

                  <mat-form-field appearance="outline">
                    <mat-label>Rol asignado</mat-label>
                    <mat-select [(ngModel)]="formUser.rol" name="rol" required>
                      <mat-option value="DOCENTE">DOCENTE</mat-option>
                      <mat-option value="ESTUDIANTE">ESTUDIANTE</mat-option>
                      <mat-option value="ADMINISTRADOR">ADMINISTRADOR</mat-option>
                    </mat-select>
                  </mat-form-field>

                  <mat-form-field appearance="outline">
                    <mat-label>{{ usuarioEditando() ? 'Nueva contraseña (opcional)' : (formUser.rol === 'ESTUDIANTE' ? 'Clave interna opcional (estudiante accede con código)' : 'Contraseña') }}</mat-label>
                    <input matInput type="password" [(ngModel)]="formUser.clave" name="clave"
                           [required]="!usuarioEditando() && formUser.rol !== 'ESTUDIANTE'" />
                  </mat-form-field>

                  <mat-checkbox [(ngModel)]="formUser.activo" name="activo">Cuenta activa</mat-checkbox>

                  @if (permisosDisponibles().length) {
                    <div class="perm-box">
                      <span class="perm-label">Excepciones de permisos individuales (sobreescriben el rol):</span>
                      @for (p of permisosDisponibles(); track p) {
                        <div class="perm-row">
                          <span class="perm-code">{{ p }}</span>
                          <select class="perm-select"
                                  [ngModel]="estadoPermisoIndividual(p)"
                                  (ngModelChange)="cambiarPermisoIndividual(p, $event)"
                                  [name]="'perm_' + p">
                            <option value="HEREDADO">Heredar del rol</option>
                            <option value="CONCEDIDO">Conceder</option>
                            <option value="REVOCADO">Revocar</option>
                          </select>
                        </div>
                      }
                    </div>
                  }

                  <div class="actions-row">
                    <button mat-flat-button color="primary" type="submit" [disabled]="guardando()">
                      <mat-icon>{{ usuarioEditando() ? 'save' : 'person_add' }}</mat-icon>
                      {{ usuarioEditando() ? 'Guardar cambios' : 'Crear usuario' }}
                    </button>
                    @if (usuarioEditando()) {
                      <button mat-button type="button" (click)="cancelarEdicion()">Cancelar</button>
                    }
                  </div>
                </form>
              </mat-card-content>
            </mat-card>

            <mat-card class="panel table-card">
              <mat-card-header>
                <mat-card-title>Directorio Completo ({{ usuarios().length }})</mat-card-title>
                <mat-card-subtitle>Visualiza roles, estado, permisos efectivos y UUID académicos</mat-card-subtitle>
              </mat-card-header>
              <mat-card-content>
                <div class="table-scroll">
                  <table mat-table [dataSource]="usuarios()" class="full-table">
                    <ng-container matColumnDef="usuario">
                      <th mat-header-cell *matHeaderCellDef>Usuario</th>
                      <td mat-cell *matCellDef="let u">
                        <div class="user-inline">
                          <img class="game-avatar" [src]="avatarUsuario({ id_usuario: u.id_usuario, nombre: u.nombre, correo: u.correo, rol: u.rol })" [alt]="u.nombre" />
                          <div>
                            <div class="cell-main">{{ u.nombre }}</div>
                            <div class="cell-sub">{{ u.correo }}</div>
                          </div>
                        </div>
                      </td>
                    </ng-container>

                    <ng-container matColumnDef="rol">
                      <th mat-header-cell *matHeaderCellDef>Rol</th>
                      <td mat-cell *matCellDef="let u">
                        <span class="role-badge" [class]="'role-' + u.rol.toLowerCase()">{{ u.rol }}</span>
                      </td>
                    </ng-container>

                    <ng-container matColumnDef="permisos">
                      <th mat-header-cell *matHeaderCellDef>Permisos</th>
                      <td mat-cell *matCellDef="let u">
                        <div class="chips-inline">
                          @for (p of u.permisos_efectivos; track p) {
                            <span class="mini-chip">{{ p }}</span>
                          }
                          @if (!u.permisos_efectivos.length) {
                            <span class="muted">Sin permisos extra</span>
                          }
                        </div>
                      </td>
                    </ng-container>

                    <ng-container matColumnDef="identidades">
                      <th mat-header-cell *matHeaderCellDef>Vínculos</th>
                      <td mat-cell *matCellDef="let u">
                        @if (u.identidad_cases && u.identidad_scheduling) {
                          <span class="ok-badge">CASES + SCHEDULING</span>
                        } @else if (u.rol === 'ADMINISTRADOR') {
                          <span class="muted">N/A (Admin)</span>
                        } @else {
                          <button mat-stroked-button type="button" (click)="generarIdentidades(u)">
                            Generar UUID
                          </button>
                        }
                      </td>
                    </ng-container>

                    <ng-container matColumnDef="estado">
                      <th mat-header-cell *matHeaderCellDef>Estado</th>
                      <td mat-cell *matCellDef="let u">
                        <button mat-button type="button" (click)="alternarEstado(u)"
                                [class]="u.activo ? 'btn-active' : 'btn-inactive'">
                          {{ u.activo ? 'ACTIVO' : 'INACTIVO' }}
                        </button>
                      </td>
                    </ng-container>

                    <ng-container matColumnDef="acciones">
                      <th mat-header-cell *matHeaderCellDef>Acciones</th>
                      <td mat-cell *matCellDef="let u">
                        <button mat-icon-button type="button" (click)="editarUsuario(u)" title="Editar usuario y permisos">
                          <mat-icon>edit</mat-icon>
                        </button>
                      </td>
                    </ng-container>

                    <tr mat-header-row *matHeaderRowDef="['usuario', 'rol', 'permisos', 'identidades', 'estado', 'acciones']"></tr>
                    <tr mat-row *matRowDef="let row; columns: ['usuario', 'rol', 'permisos', 'identidades', 'estado', 'acciones']"></tr>
                  </table>
                </div>
              </mat-card-content>
            </mat-card>
          </div>
        </mat-tab>

        <!-- TAB 2: Perfil Global del Rol DOCENTE -->
        <mat-tab label="Permisos Globales Docentes">
          <mat-card class="panel panel-green-left panel-card">
            <mat-card-header>
              <mat-card-title>Perfil Base del Rol DOCENTE</mat-card-title>
              <mat-card-subtitle>
                Aplica por defecto a todos los docentes ({{ perfilDocentes()?.docentes_afectados ?? 0 }} cuentas),
                salvo excepciones individuales asignadas en la pestaña anterior.
              </mat-card-subtitle>
            </mat-card-header>
            <mat-card-content>
              @if (perfilDocentes(); as perfil) {
                <div class="perm-list">
                  @for (perm of perfil.permisos_disponibles; track perm) {
                    <mat-checkbox [checked]="permisosGlobalesSeleccionados.has(perm)"
                                  (change)="togglePermisoGlobal(perm, $event.checked)">
                      <strong class="mono">{{ perm }}</strong>
                    </mat-checkbox>
                  }
                </div>
                <div class="actions-row" style="margin-top: 16px;">
                  <button mat-flat-button color="primary" (click)="guardarPerfilGlobal()" [disabled]="guardando()">
                    <mat-icon>verified_user</mat-icon> Guardar permisos globales docentes
                  </button>
                </div>
              }
            </mat-card-content>
          </mat-card>
        </mat-tab>

        <!-- TAB 3: Espacios Académicos -->
        <mat-tab label="Espacios Académicos">
          <div class="tab-grid">
            <mat-card class="panel panel-amber-left panel-card">
              <mat-card-header>
                <mat-card-title>Crear Espacio Académico</mat-card-title>
                <mat-card-subtitle>Registra asignaturas o módulos y autoriza docentes titulares (RF-04)</mat-card-subtitle>
              </mat-card-header>
              <mat-card-content>
                <form class="form-stack" (ngSubmit)="crearYAutorizarEspacio()">
                  <mat-form-field appearance="outline">
                    <mat-label>Nombre del espacio académico</mat-label>
                    <input matInput [(ngModel)]="nuevoEspacioNombre" name="espNombre" required />
                  </mat-form-field>
                  <mat-form-field appearance="outline">
                    <mat-label>Autorizar inicialmente al docente (opcional)</mat-label>
                    <mat-select [(ngModel)]="espacioDocenteInicial" name="espDoc">
                      <mat-option [value]="null">-- Ninguno por ahora --</mat-option>
                      @for (d of docentesList(); track d.id_usuario) {
                        <mat-option [value]="d.id_usuario">{{ d.nombre }} ({{ d.correo }})</mat-option>
                      }
                    </mat-select>
                  </mat-form-field>
                  <button mat-flat-button color="primary" type="submit" [disabled]="guardando()">
                    <mat-icon>add_business</mat-icon> Crear espacio
                  </button>
                </form>
              </mat-card-content>
            </mat-card>

            <mat-card class="panel table-card">
              <mat-card-header>
                <mat-card-title>Espacios Registrados ({{ espacios().length }})</mat-card-title>
              </mat-card-header>
              <mat-card-content>
                @for (e of espacios(); track e.id) {
                  <div class="space-row">
                    <div>
                      <div class="cell-main">{{ e.nombre }}</div>
                      <div class="cell-sub mono">ID: {{ e.id }}</div>
                      <div class="chips-inline" style="margin-top: 6px;">
                        @for (d of e.docentes_autorizados; track d.id_usuario) {
                          <span class="mini-chip">{{ d.nombre }}</span>
                        }
                        @if (!e.docentes_autorizados.length) {
                          <span class="muted">Sin docentes autorizados aún</span>
                        }
                      </div>
                    </div>
                    <div class="grant-box">
                      <select class="perm-select" [(ngModel)]="asignacionDocentePorEspacio[e.id]" [name]="'grant_' + e.id">
                        <option [ngValue]="null">Seleccionar docente...</option>
                        @for (d of docentesList(); track d.id_usuario) {
                          <option [ngValue]="d.id_usuario">{{ d.nombre }}</option>
                        }
                      </select>
                      <button mat-stroked-button type="button" (click)="autorizarDocenteEspacio(e.id)"
                              [disabled]="!asignacionDocentePorEspacio[e.id] || guardando()">
                        Autorizar
                      </button>
                    </div>
                  </div>
                }
              </mat-card-content>
            </mat-card>
          </div>
        </mat-tab>
      </mat-tab-group>
    </div>
  `,
  styles: [`
    .admin-wrap { padding: 4px 0 36px; max-width: 1160px; margin: 0 auto; }
    .subtitle { margin: 4px 0 0; color: var(--muted); font-size: 13px; }
    .tab-grid { display: grid; grid-template-columns: 380px 1fr; gap: 20px; margin-top: 16px; align-items: start; }
    @media (max-width: 1080px) { .tab-grid { grid-template-columns: 1fr; } }
    .panel-card, .table-card { margin-top: 12px; }
    .form-stack { display: flex; flex-direction: column; gap: 12px; padding-top: 14px; }
    .actions-row { display: flex; gap: 10px; align-items: center; }
    .perm-box { background: #070a10; border: 1px solid var(--line); padding: 12px; display: flex; flex-direction: column; gap: 8px; }
    .perm-label { font-family: var(--mono); font-size: 11px; color: var(--cyan); font-weight: 600; text-transform: uppercase; }
    .perm-row { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
    .perm-code { font-size: 12px; font-family: var(--mono); color: var(--text); }
    .perm-select { background: #070a10; color: var(--text); border: 1px solid var(--line-strong); padding: 6px 10px; font-family: var(--mono); font-size: 12px; }
    .table-scroll { overflow-x: auto; }
    .full-table { width: 100%; }
    .cell-main { font-weight: 600; color: var(--text); }
    .cell-sub { font-size: 12px; color: var(--muted); }
    .role-badge { padding: 3px 9px; font-family: var(--mono); font-size: 11px; font-weight: 700; letter-spacing: 0.7px; }
    .role-administrador { background: rgba(255, 184, 0, 0.14); color: var(--amber); border: 1px solid rgba(255, 184, 0, 0.5); }
    .role-docente { background: rgba(0, 232, 148, 0.12); color: var(--green); border: 1px solid rgba(0, 232, 148, 0.48); }
    .role-estudiante { background: rgba(0, 229, 244, 0.12); color: var(--cyan); border: 1px solid rgba(0, 229, 244, 0.45); }
    .chips-inline { display: flex; flex-wrap: wrap; gap: 4px; }
    .mini-chip { background: #070a10; border: 1px solid var(--line); padding: 2px 7px; font-family: var(--mono); font-size: 11px; color: var(--cyan-soft); }
    .ok-badge { color: var(--green); font-family: var(--mono); font-size: 11px; font-weight: 700; }
    .btn-active { color: var(--green) !important; font-weight: 700; font-size: 11px; }
    .btn-inactive { color: var(--coral) !important; font-weight: 700; font-size: 11px; }
    .perm-list { display: flex; flex-direction: column; gap: 10px; padding-top: 12px; }
    .space-row { display: flex; justify-content: space-between; align-items: center; gap: 12px; padding: 14px 0; border-bottom: 1px solid var(--line); flex-wrap: wrap; }
    .grant-box { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
    @media (max-width: 640px) {
      .actions-row, .grant-box { flex-wrap: wrap; width: 100%; }
      .grant-box .perm-select, .grant-box button { width: 100%; }
    }
  `],
})
export class DocentesComponent implements OnInit {
  private readonly identity = inject(IdentityService);
  private readonly scheduling = inject(SchedulingService);
  private readonly snack = inject(MatSnackBar);
  readonly avatarUsuario = avatarUsuario;

  readonly cargando = signal(false);
  readonly guardando = signal(false);
  readonly usuarios = signal<UsuarioGestionItem[]>([]);
  readonly permisosDisponibles = signal<string[]>([]);
  readonly perfilDocentes = signal<PerfilPermisosDocentesRespuesta | null>(null);
  readonly espacios = signal<EspacioConAutorizaciones[]>([]);
  readonly docentesList = signal<DocenteBreve[]>([]);
  readonly usuarioEditando = signal<UsuarioGestionItem | null>(null);

  permisosGlobalesSeleccionados = new Set<string>();
  nuevoEspacioNombre = '';
  espacioDocenteInicial: number | null = null;
  asignacionDocentePorEspacio: Record<string, number | null> = {};

  formUser = {
    nombre: '',
    correo: '',
    rol: 'DOCENTE' as Rol,
    clave: '',
    activo: true,
    permisosIndividuales: {} as Record<string, boolean>,
  };

  ngOnInit(): void {
    void this.cargarTodo();
  }

  async cargarTodo(): Promise<void> {
    this.cargando.set(true);
    try {
      const [cat, perfil, esp, docs] = await Promise.all([
        firstValueFrom(this.identity.listarUsuarios()),
        firstValueFrom(this.identity.permisosRolDocente()),
        firstValueFrom(this.scheduling.todosEspacios()),
        firstValueFrom(this.scheduling.docentes()),
      ]);
      this.usuarios.set(cat.usuarios);
      this.permisosDisponibles.set(cat.permisos_disponibles);
      this.perfilDocentes.set(perfil);
      this.permisosGlobalesSeleccionados = new Set(perfil.permisos);
      this.espacios.set(esp);
      this.docentesList.set(docs);
    } catch (e) {
      this.snack.open(mensajeError(e), 'Cerrar', { duration: 4500 });
    } finally {
      this.cargando.set(false);
    }
  }

  estadoPermisoIndividual(codigo: string): 'HEREDADO' | 'CONCEDIDO' | 'REVOCADO' {
    if (!(codigo in this.formUser.permisosIndividuales)) return 'HEREDADO';
    return this.formUser.permisosIndividuales[codigo] ? 'CONCEDIDO' : 'REVOCADO';
  }

  cambiarPermisoIndividual(codigo: string, valor: 'HEREDADO' | 'CONCEDIDO' | 'REVOCADO'): void {
    if (valor === 'HEREDADO') {
      delete this.formUser.permisosIndividuales[codigo];
    } else {
      this.formUser.permisosIndividuales[codigo] = valor === 'CONCEDIDO';
    }
  }

  editarUsuario(u: UsuarioGestionItem): void {
    this.usuarioEditando.set(u);
    this.formUser = {
      nombre: u.nombre,
      correo: u.correo,
      rol: u.rol as Rol,
      clave: '',
      activo: u.activo,
      permisosIndividuales: { ...u.permisos_individuales },
    };
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  cancelarEdicion(): void {
    this.usuarioEditando.set(null);
    this.formUser = {
      nombre: '',
      correo: '',
      rol: 'DOCENTE',
      clave: '',
      activo: true,
      permisosIndividuales: {},
    };
  }

  async guardarUsuario(): Promise<void> {
    this.guardando.set(true);
    try {
      const editando = this.usuarioEditando();
      if (editando) {
        await firstValueFrom(
          this.identity.actualizarUsuario(editando.id_usuario, {
            nombre: this.formUser.nombre.trim(),
            correo: this.formUser.correo.trim(),
            rol: this.formUser.rol,
            activo: this.formUser.activo,
            clave: this.formUser.clave.trim() || null,
            permisos_individuales: this.formUser.permisosIndividuales,
          }),
        );
        this.snack.open('Usuario actualizado correctamente.', 'OK', { duration: 3000 });
      } else {
        await firstValueFrom(
          this.identity.crearUsuario({
            nombre: this.formUser.nombre.trim(),
            correo: this.formUser.correo.trim(),
            rol: this.formUser.rol,
            clave: this.formUser.clave.trim() || null,
            activo: this.formUser.activo,
            permisos_individuales: this.formUser.permisosIndividuales,
            crear_identidades_academicas: true,
          }),
        );
        this.snack.open('Usuario creado con identidades académicas listas.', 'OK', { duration: 3000 });
      }
      this.cancelarEdicion();
      await this.cargarTodo();
    } catch (e) {
      this.snack.open(mensajeError(e), 'Cerrar', { duration: 5000 });
    } finally {
      this.guardando.set(false);
    }
  }

  async alternarEstado(u: UsuarioGestionItem): Promise<void> {
    this.guardando.set(true);
    try {
      await firstValueFrom(this.identity.actualizarUsuario(u.id_usuario, { activo: !u.activo }));
      this.snack.open(`Cuenta ${!u.activo ? 'activada' : 'desactivada'}.`, 'OK', { duration: 2500 });
      await this.cargarTodo();
    } catch (e) {
      this.snack.open(mensajeError(e), 'Cerrar', { duration: 4000 });
    } finally {
      this.guardando.set(false);
    }
  }

  async generarIdentidades(u: UsuarioGestionItem): Promise<void> {
    this.guardando.set(true);
    try {
      await firstValueFrom(this.identity.asegurarIdentidades(u.id_usuario));
      this.snack.open('Vínculos CASES y SCHEDULING generados.', 'OK', { duration: 2500 });
      await this.cargarTodo();
    } catch (e) {
      this.snack.open(mensajeError(e), 'Cerrar', { duration: 4000 });
    } finally {
      this.guardando.set(false);
    }
  }

  togglePermisoGlobal(perm: string, checked: boolean): void {
    if (checked) this.permisosGlobalesSeleccionados.add(perm);
    else this.permisosGlobalesSeleccionados.delete(perm);
  }

  async guardarPerfilGlobal(): Promise<void> {
    this.guardando.set(true);
    try {
      const resp = await firstValueFrom(
        this.identity.actualizarPermisosRolDocente([...this.permisosGlobalesSeleccionados]),
      );
      this.perfilDocentes.set(resp);
      this.snack.open('Perfil global docente actualizado.', 'OK', { duration: 3000 });
      await this.cargarTodo();
    } catch (e) {
      this.snack.open(mensajeError(e), 'Cerrar', { duration: 4000 });
    } finally {
      this.guardando.set(false);
    }
  }

  async crearYAutorizarEspacio(): Promise<void> {
    if (!this.nuevoEspacioNombre.trim()) return;
    this.guardando.set(true);
    try {
      const espacio = await firstValueFrom(this.scheduling.crearEspacio(this.nuevoEspacioNombre.trim()));
      if (this.espacioDocenteInicial) {
        await firstValueFrom(this.scheduling.autorizarEspacio(espacio.id, this.espacioDocenteInicial));
      }
      this.nuevoEspacioNombre = '';
      this.espacioDocenteInicial = null;
      this.snack.open('Espacio académico creado.', 'OK', { duration: 3000 });
      await this.cargarTodo();
    } catch (e) {
      this.snack.open(mensajeError(e), 'Cerrar', { duration: 4000 });
    } finally {
      this.guardando.set(false);
    }
  }

  async autorizarDocenteEspacio(espacioId: string): Promise<void> {
    const idDocente = this.asignacionDocentePorEspacio[espacioId];
    if (!idDocente) return;
    this.guardando.set(true);
    try {
      await firstValueFrom(this.scheduling.autorizarEspacio(espacioId, idDocente));
      this.snack.open('Docente autorizado sobre el espacio.', 'OK', { duration: 2500 });
      await this.cargarTodo();
    } catch (e) {
      this.snack.open(mensajeError(e), 'Cerrar', { duration: 4000 });
    } finally {
      this.guardando.set(false);
    }
  }
}
