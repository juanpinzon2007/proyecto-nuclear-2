import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { RespuestaAccesoEstudiante, RespuestaMensajeOperacion, RespuestaToken, Rol, UsuarioPublico } from './api.models';

export type ResultadoLogin =
  | { estado: 'AUTENTICADO'; usuario: UsuarioPublico | null }
  | { estado: 'VERIFICACION_REQUERIDA'; correo: string; mensaje: string; expiraEnSegundos: number };

const TOKEN_KEY = 'sps.token';

interface ClaimsToken { sub: string; exp: number; convocatoria_id?: string; }

function decodificar(token: string): ClaimsToken | null {
  try {
    const payload = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
    const json = decodeURIComponent(
      atob(payload).split('').map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)).join(''),
    );
    return JSON.parse(json) as ClaimsToken;
  } catch {
    return null;
  }
}

/**
 * Autenticación contra Identity. El token JWT se guarda en sessionStorage
 * (se pierde al cerrar la pestaña) y el perfil se obtiene de GET /api/v1/identity/me.
 */
@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);

  private readonly _token = signal<string | null>(sessionStorage.getItem(TOKEN_KEY));
  private readonly _usuario = signal<UsuarioPublico | null>(null);
  private cargaPerfil: Promise<UsuarioPublico | null> | null = null;

  readonly token = this._token.asReadonly();
  readonly usuario = this._usuario.asReadonly();
  readonly claims = computed(() => { const t = this._token(); return t ? decodificar(t) : null; });
  /** Convocatoria vinculada al token de un estudiante (claim `convocatoria_id`). */
  readonly convocatoriaId = computed(() => this.claims()?.convocatoria_id ?? null);
  readonly roles = computed<Rol[]>(() => this._usuario()?.roles ?? []);
  readonly permisos = computed<string[]>(() => this._usuario()?.permisos ?? []);
  readonly esAdmin = computed(() => this.roles().includes('ADMINISTRADOR'));
  readonly esDocente = computed(() => this.roles().includes('DOCENTE'));
  readonly esEstudiante = computed(() => this.roles().includes('ESTUDIANTE'));

  tienePermiso(codigo: string): boolean {
    return this.permisos().includes(codigo);
  }

  tokenVigente(): boolean {
    const c = this.claims();
    return !!c && c.exp * 1000 > Date.now();
  }

  async loginPersonal(correo: string, clave: string): Promise<UsuarioPublico | null> {
    const r = await firstValueFrom(this.http.post<RespuestaToken>('/api/v1/identity/auth/personal', { correo, clave }));
    return this.iniciarSesion(r.access_token);
  }

  async loginEstudiante(correo: string, codigo_convocatoria: string): Promise<UsuarioPublico | null> {
    const r = await firstValueFrom(
      this.http.post<RespuestaToken>('/api/v1/identity/auth/estudiantes', { correo, codigo_convocatoria }),
    );
    return this.iniciarSesion(r.access_token);
  }

  async loginEstudiantePorClave(correo: string, clave: string): Promise<RespuestaAccesoEstudiante> {
    return firstValueFrom(
      this.http.post<RespuestaAccesoEstudiante>('/api/v1/identity/auth/estudiantes/acceso', { correo, clave }),
    );
  }

  async verificarPrimerIngreso(correo: string, codigo: string): Promise<UsuarioPublico | null> {
    const r = await firstValueFrom(
      this.http.post<RespuestaToken>('/api/v1/identity/auth/estudiantes/verificar-primer-ingreso', { correo, codigo }),
    );
    return this.iniciarSesion(r.access_token);
  }

  async solicitarRecuperacionContrasena(correo: string): Promise<RespuestaMensajeOperacion> {
    return firstValueFrom(
      this.http.post<RespuestaMensajeOperacion>('/api/v1/identity/auth/recuperar-contrasena/solicitar', { correo }),
    );
  }

  async confirmarRecuperacionContrasena(
    correo: string,
    codigo: string,
    nuevaClave: string,
  ): Promise<RespuestaMensajeOperacion> {
    return firstValueFrom(
      this.http.post<RespuestaMensajeOperacion>('/api/v1/identity/auth/recuperar-contrasena/confirmar', {
        correo,
        codigo,
        nueva_clave: nuevaClave,
      }),
    );
  }

  /**
   * Autentica docentes/administradores y estudiantes:
   * - Estudiantes con contraseña reciben OTP por correo únicamente en su primer inicio de sesión.
   * - También conserva el acceso directo por código de convocatoria cuando corresponda.
   */
  async loginUnificado(correo: string, credencial: string): Promise<ResultadoLogin> {
    try {
      const usuario = await this.loginPersonal(correo, credencial);
      return { estado: 'AUTENTICADO', usuario };
    } catch (errPersonal) {
      if (errPersonal instanceof HttpErrorResponse && errPersonal.status !== 401) {
        throw errPersonal;
      }
    }

    try {
      const acceso = await this.loginEstudiantePorClave(correo, credencial);
      if (acceso.requiere_verificacion) {
        return {
          estado: 'VERIFICACION_REQUERIDA',
          correo: acceso.correo ?? correo,
          mensaje:
            acceso.mensaje ??
            'Se envió un código de verificación a tu correo. Ingrésalo para completar tu primer acceso.',
          expiraEnSegundos: acceso.expira_en_segundos ?? 900,
        };
      }
      if (acceso.access_token) {
        const usuario = await this.iniciarSesion(acceso.access_token);
        return { estado: 'AUTENTICADO', usuario };
      }
    } catch (errEst) {
      if (errEst instanceof HttpErrorResponse && errEst.status !== 401) {
        throw errEst;
      }
    }

    const usuario = await this.loginEstudiante(correo, credencial);
    return { estado: 'AUTENTICADO', usuario };
  }

  private async iniciarSesion(token: string): Promise<UsuarioPublico | null> {
    sessionStorage.setItem(TOKEN_KEY, token);
    this._token.set(token);
    this._usuario.set(null);
    this.cargaPerfil = null;
    return this.asegurarPerfil();
  }

  /** Devuelve el perfil cargado (o lo consulta una sola vez). `null` si no hay sesión válida. */
  asegurarPerfil(): Promise<UsuarioPublico | null> {
    if (this._usuario()) return Promise.resolve(this._usuario());
    if (!this._token() || !this.tokenVigente()) {
      this.limpiar();
      return Promise.resolve(null);
    }
    this.cargaPerfil ??= firstValueFrom(this.http.get<UsuarioPublico>('/api/v1/identity/me'))
      .then((u) => { this._usuario.set(u); return u; })
      .catch(() => { this.limpiar(); return null; })
      .finally(() => { this.cargaPerfil = null; });
    return this.cargaPerfil;
  }

  rutaInicio(): string {
    if (this.esAdmin()) return '/administracion/docentes';
    if (this.esDocente()) return '/casos';
    if (this.esEstudiante()) return '/estudiante';
    return '/login';
  }

  logout(): void {
    this.limpiar();
    void this.router.navigateByUrl('/login');
  }

  private limpiar(): void {
    sessionStorage.removeItem(TOKEN_KEY);
    this._token.set(null);
    this._usuario.set(null);
  }
}

