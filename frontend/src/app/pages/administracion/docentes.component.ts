import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
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
    FormsModule,
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
    <div class="page role-dashboard" [attr.aria-busy]="cargando()">
      <header class="panel dashboard-hero dashboard-cover-administracion">
        <div class="dashboard-copy">
          <p class="eyebrow">Consola de administración</p>
          <h1>Administración</h1>
          <p class="dashboard-description">Gestiona las cuentas, sus permisos y las autorizaciones de los espacios académicos.</p>
          <div class="dashboard-actions">
            <button mat-stroked-button type="button" (click)="cargarTodo()" [disabled]="cargando()">
              <mat-icon aria-hidden="true">refresh</mat-icon> Actualizar datos
            </button>
          </div>
        </div>
      </header>

      <dl class="dashboard-summary" aria-label="Resumen de administración">
        <div class="dashboard-stat">
          <dt><span class="dashboard-stat-icon"><mat-icon aria-hidden="true">groups</mat-icon></span> Usuarios</dt>
          <dd>{{ usuarios().length }}</dd>
        </div>
        <div class="dashboard-stat dashboard-tone-green">
          <dt><span class="dashboard-stat-icon"><mat-icon aria-hidden="true">how_to_reg</mat-icon></span> Cuentas activas</dt>
          <dd>{{ cuentasActivas() }}</dd>
        </div>
        <div class="dashboard-stat dashboard-tone-amber">
          <dt><span class="dashboard-stat-icon"><mat-icon aria-hidden="true">school</mat-icon></span> Espacios</dt>
          <dd>{{ espacios().length }}</dd>
        </div>
      </dl>

      <mat-tab-group animationDuration="0ms">
        <!-- TAB 1: Usuarios, Roles y Permisos Individuales -->
        <mat-tab label="Usuarios & Permisos">
          <div class="tab-grid">
            <mat-card class="panel panel-card dashboard-enter" id="admin-user-editor">
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
                    <mat-label>{{ usuarioEditando() ? 'Nueva contraseña (opcional)' : 'Contraseña inicial' }}</mat-label>
                    <input matInput type="password" [(ngModel)]="formUser.clave" name="clave"
                           [required]="!usuarioEditando()" />
                  </mat-form-field>

                  @if (formUser.rol === 'ESTUDIANTE' && !usuarioEditando()) {
                    <div class="role-hint">
                      El estudiante iniciará sesión con este correo y contraseña. Únicamente la primera vez recibirá un código de verificación en su correo.
                    </div>
                  }

                  @if (formUser.rol === 'ESTUDIANTE' && usuarioEditando()) {
                    <mat-checkbox [(ngModel)]="formUser.exigirPrimerIngreso" name="exigirPrimerIngreso">
                      Exigir código por correo en el próximo inicio de sesión
                    </mat-checkbox>
                  }

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

            <section class="directory" aria-labelledby="directory-title">
              <div class="dashboard-heading">
                <h2 id="directory-title">Directorio de usuarios</h2>
                <span>{{ usuarios().length }} {{ usuarios().length === 1 ? 'cuenta' : 'cuentas' }}</span>
              </div>

              <div class="dashboard-grid">
                @for (u of usuarios(); track u.id_usuario) {
                  <article class="panel dashboard-card directory-card"
                    [class.dashboard-tone-green]="u.rol === 'DOCENTE'"
                    [class.dashboard-tone-amber]="u.rol === 'ADMINISTRADOR'"
                    [attr.aria-labelledby]="'admin-user-' + u.id_usuario">
                    <div class="dashboard-card-content">
                      <div class="dashboard-card-top">
                        <img class="directory-avatar" [src]="avatarUsuario({ id_usuario: u.id_usuario, nombre: u.nombre, correo: u.correo, rol: u.rol })" alt="" width="46" height="46" />
                        <span class="dashboard-badge">{{ u.rol }}</span>
                      </div>

                      <h3 [id]="'admin-user-' + u.id_usuario">{{ u.nombre }}</h3>
                      <p class="directory-email">{{ u.correo }}</p>

                      <div class="directory-details">
                        <div>
                          <h4>Permisos efectivos</h4>
                          @if (u.permisos_efectivos.length) {
                            <div class="chips-inline">
                              @for (p of u.permisos_efectivos; track p) {
                                <span class="mini-chip">{{ p }}</span>
                              }
                            </div>
                          } @else {
                            <p class="cell-sub">Sin permisos efectivos</p>
                          }
                        </div>

                        <div>
                          <h4>Vínculos académicos</h4>
                          @if (u.identidad_cases && u.identidad_scheduling) {
                            <span class="dashboard-badge dashboard-tone-green">CASES + SCHEDULING</span>
                          } @else if (u.rol === 'ADMINISTRADOR') {
                            <p class="cell-sub">No aplica</p>
                          } @else {
                            <button mat-stroked-button type="button" (click)="generarIdentidades(u)">
                              <mat-icon aria-hidden="true">link</mat-icon> Generar UUID
                            </button>
                          }
                        </div>

                        @if (u.rol === 'ESTUDIANTE') {
                          <span class="dashboard-badge" [class.dashboard-tone-amber]="u.primer_ingreso_verificado === false">
                            {{ u.primer_ingreso_verificado === false ? 'Primer ingreso pendiente' : 'Primer ingreso verificado' }}
                          </span>
                        }
                      </div>
                    </div>

                    <div class="dashboard-card-actions" role="group" [attr.aria-label]="'Acciones de ' + u.nombre">
                      <button mat-stroked-button type="button" (click)="editarUsuario(u)">
                        <mat-icon aria-hidden="true">edit</mat-icon> Editar
                      </button>
                      <button mat-button type="button" (click)="alternarEstado(u)"
                        [class.btn-active]="u.activo" [class.btn-inactive]="!u.activo"
                        [attr.aria-label]="(u.activo ? 'Desactivar cuenta de ' : 'Activar cuenta de ') + u.nombre">
                        <mat-icon aria-hidden="true">{{ u.activo ? 'toggle_on' : 'toggle_off' }}</mat-icon>
                        {{ u.activo ? 'Activa' : 'Inactiva' }}
                      </button>
                    </div>
                  </article>
                } @empty {
                  @if (!cargando()) {
                    <div class="panel dashboard-empty"><p>No hay cuentas para mostrar.</p></div>
                  }
                }
              </div>
            </section>
          </div>
        </mat-tab>

        <!-- TAB 2: Perfil Global del Rol DOCENTE -->
        <mat-tab label="Permisos Globales Docentes">
          <mat-card class="panel panel-card dashboard-enter">
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
            <mat-card class="panel panel-card dashboard-enter">
              <mat-card-header>
                <mat-card-title>Crear Espacio Académico</mat-card-title>
                <mat-card-subtitle>Registra asignaturas o módulos y autoriza docentes titulares</mat-card-subtitle>
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

            <section class="directory" aria-labelledby="spaces-title">
              <div class="dashboard-heading">
                <h2 id="spaces-title">Espacios registrados</h2>
                <span>{{ espacios().length }} {{ espacios().length === 1 ? 'espacio' : 'espacios' }}</span>
              </div>
              <div class="dashboard-grid">
                @for (e of espacios(); track e.id) {
                  <article class="panel dashboard-card dashboard-tone-amber" [attr.aria-labelledby]="'admin-space-' + e.id">
                    <div class="dashboard-card-content">
                      <span class="dashboard-icon"><mat-icon aria-hidden="true">school</mat-icon></span>
                      <h3 [id]="'admin-space-' + e.id">{{ e.nombre }}</h3>
                      <p class="cell-sub mono">ID: {{ e.id }}</p>
                      <div class="chips-inline space-docentes">
                        @for (d of e.docentes_autorizados; track d.id_usuario) {
                          <span class="mini-chip">{{ d.nombre }}</span>
                        }
                        @if (!e.docentes_autorizados.length) {
                          <span class="muted">Sin docentes autorizados aún</span>
                        }
                      </div>
                    </div>
                    <div class="dashboard-card-actions grant-box">
                      <select class="perm-select" [(ngModel)]="asignacionDocentePorEspacio[e.id]" [name]="'grant_' + e.id"
                        [attr.aria-label]="'Docente a autorizar en ' + e.nombre">
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
                  </article>
                } @empty {
                  @if (!cargando()) {
                    <div class="panel dashboard-empty"><p>No hay espacios registrados.</p></div>
                  }
                }
              </div>
            </section>
          </div>
        </mat-tab>
      </mat-tab-group>
    </div>
  `,
  styles: [`
    mat-tab-group { min-width: 0; }
    .tab-grid {
      display: grid;
      grid-template-columns: minmax(250px, 0.9fr) minmax(0, 2fr);
      align-items: start;
      gap: 16px;
      padding-top: 16px;
    }
    .directory { min-width: 0; }
    .panel-card { margin-top: 16px; border-top: 2px solid #507e9f !important; }
    .tab-grid .panel-card { margin-top: 0; }
    #admin-user-editor { scroll-margin-top: 87px; }
    .form-stack { display: flex; flex-direction: column; gap: 10px; padding-top: 16px; }
    .actions-row { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
    .perm-box {
      display: grid;
      gap: 8px;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #0a1422;
    }
    .perm-label { font-family: var(--mono); font-size: 11px; color: var(--cyan-soft); font-weight: 600; }
    .perm-row { display: flex; justify-content: space-between; align-items: center; gap: 8px; flex-wrap: wrap; }
    .perm-code { color: var(--text); font: 12px var(--mono); overflow-wrap: anywhere; }
    .perm-select {
      min-width: 0;
      max-width: 100%;
      padding: 8px 10px;
      border: 1px solid #547e9e;
      border-radius: 8px;
      background: #0a1422;
      color: var(--text);
      font: 13px var(--mono);
    }
    .directory-avatar {
      width: 46px;
      height: 46px;
      object-fit: cover;
      border: 1px solid var(--dashboard-tone, var(--cyan-soft));
      border-radius: 10px;
      background: #0a1422;
    }
    .directory-card h3 { margin-bottom: 5px; }
    .directory-email, .cell-sub { margin: 0; color: #acbfd4; font-size: 13px; }
    .directory-details { display: grid; justify-items: start; gap: 12px; margin-top: 15px; }
    .directory-details h4 { margin: 0 0 6px; color: #c5d6e9; font: 13px var(--mono); }
    .directory-details .dashboard-badge { display: inline-block; }
    .chips-inline { display: flex; flex-wrap: wrap; gap: 4px; }
    .mini-chip {
      padding: 3px 7px;
      border: 1px solid #385470;
      border-radius: 5px;
      background: #101b2f;
      color: var(--cyan-soft);
      font: 11px var(--mono);
    }
    .btn-active { color: var(--green) !important; }
    .btn-inactive { color: var(--coral) !important; }
    .role-hint { font-size: 12px; color: var(--cyan-soft); background: #123647; border-radius: 7px; padding: 8px 10px; line-height: 1.45; }
    .perm-list { display: flex; flex-direction: column; gap: 10px; padding-top: 12px; }
    .space-docentes { margin-top: 9px; }
    .grant-box .perm-select { flex: 1 1 140px; margin: 2px 5px 2px 0; }
    @media (max-width: 960px) { .tab-grid { grid-template-columns: minmax(0, 1fr); } }
    @media (max-width: 540px) { .grant-box button { flex: 1 1 auto; } }
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
  readonly cuentasActivas = computed(() => this.usuarios().filter((usuario) => usuario.activo).length);
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
    exigirPrimerIngreso: false,
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
      exigirPrimerIngreso: u.primer_ingreso_verificado === false,
      permisosIndividuales: { ...u.permisos_individuales },
    };
    document.getElementById('admin-user-editor')?.scrollIntoView({ block: 'start' });
  }

  cancelarEdicion(): void {
    this.usuarioEditando.set(null);
    this.formUser = {
      nombre: '',
      correo: '',
      rol: 'DOCENTE',
      clave: '',
      activo: true,
      exigirPrimerIngreso: false,
      permisosIndividuales: {},
    };
  }

  async guardarUsuario(): Promise<void> {
    const editando = this.usuarioEditando();
    if (!editando && !this.formUser.clave.trim()) {
      this.snack.open('Ingresa una contraseña inicial de al menos 6 caracteres.', 'Cerrar', { duration: 4000 });
      return;
    }
    this.guardando.set(true);
    try {
      if (editando) {
        await firstValueFrom(
          this.identity.actualizarUsuario(editando.id_usuario, {
            nombre: this.formUser.nombre.trim(),
            correo: this.formUser.correo.trim(),
            rol: this.formUser.rol,
            activo: this.formUser.activo,
            clave: this.formUser.clave.trim() || null,
            permisos_individuales: this.formUser.permisosIndividuales,
            primer_ingreso_verificado: this.formUser.rol === 'ESTUDIANTE' ? !this.formUser.exigirPrimerIngreso : null,
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
