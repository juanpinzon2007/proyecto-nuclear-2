import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { AuthService } from '../../core/auth.service';
import { mensajeError } from '../../core/api-error';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
  ],
  template: `
    <main class="login-page scanlines">
      <div class="login-wrap stagger">
        <section class="brand-card">
          <div class="brand-emblem">
            <img class="brand-logo" src="/logo-sps.png" alt="Logo SPS" />
          </div>
          <div>
            <h1>SPS</h1>
            <small>Simulador de Psicología Social</small>
            <p class="brand-slogan">Aprender a comprender la sociedad.</p>
          </div>
        </section>

        <mat-card class="panel auth-card">
          @if (verificacionPendiente(); as verif) {
            <div class="otp-banner">
              <div class="otp-title">
                <mat-icon class="cyan">mark_email_read</mat-icon>
                <span>Verificación Única de Primer Ingreso</span>
              </div>
              <p>
                {{ verif.mensaje }}
                <br />
                Correo destino: <strong class="cyan">{{ verif.correo }}</strong>.
                <br />
                <small>Este código solo se solicita la primera vez que inicias sesión.</small>
              </p>
            </div>

            @if (infoVerificacion()) {
              <div class="info-box">{{ infoVerificacion() }}</div>
            }

            <form (ngSubmit)="confirmarCodigoPrimerIngreso()" class="login-form">
              <mat-form-field appearance="outline" class="full">
                <mat-label>Código de verificación (6 dígitos)</mat-label>
                <input
                  matInput
                  type="text"
                  [(ngModel)]="codigoVerificacion"
                  name="codigoVerificacion"
                  required
                  maxlength="12"
                  inputmode="numeric"
                  autocomplete="one-time-code"
                  placeholder="Ej. 482915"
                  class="otp-input"
                />
                <mat-icon matPrefix class="cyan">pin</mat-icon>
              </mat-form-field>

              @if (errorLogin()) {
                <div class="error-box">{{ errorLogin() }}</div>
              }

              <button mat-flat-button color="primary" class="full submit-btn" type="submit" [disabled]="cargando() || !codigoVerificacion.trim()">
                @if (cargando()) {
                  <mat-spinner diameter="20"></mat-spinner>
                } @else {
                  Verificar Código e Ingresar
                }
              </button>

              <div class="otp-actions">
                <button mat-stroked-button type="button" (click)="reenviarCodigo()" [disabled]="cargando()">
                  <mat-icon>send</mat-icon> Reenviar código
                </button>
                <button mat-button type="button" (click)="volverALogin()" [disabled]="cargando()">
                  Volver
                </button>
              </div>
            </form>
          } @else if (recuperacionPaso()) {
            <div class="otp-banner">
              <div class="otp-title">
                <mat-icon class="cyan">lock_reset</mat-icon>
                <span>Recuperación de Contraseña por Correo</span>
              </div>
              <p>
                @if (recuperacionPaso() === 'SOLICITAR') {
                  Ingresa tu correo registrado y te enviaremos un código temporal de 6 dígitos para crear una nueva contraseña.
                } @else {
                  Enviamos un código de recuperación a <strong class="cyan">{{ correoRecuperacion }}</strong>.
                  Ingrésalo abajo junto con tu nueva contraseña.
                }
              </p>
            </div>

            @if (infoVerificacion()) {
              <div class="info-box">{{ infoVerificacion() }}</div>
            }

            @if (recuperacionPaso() === 'SOLICITAR') {
              <form (ngSubmit)="enviarCodigoRecuperacion()" class="login-form">
                <mat-form-field appearance="outline" class="full">
                  <mat-label>Correo registrado</mat-label>
                  <input
                    matInput
                    type="email"
                    [(ngModel)]="correoRecuperacion"
                    name="correoRecuperacion"
                    required
                    autocomplete="email"
                    placeholder="usuario@correo.com"
                  />
                  <mat-icon matPrefix class="cyan">alternate_email</mat-icon>
                </mat-form-field>

                @if (errorLogin()) {
                  <div class="error-box">{{ errorLogin() }}</div>
                }

                <button mat-flat-button color="primary" class="full submit-btn" type="submit" [disabled]="cargando() || !correoRecuperacion.trim()">
                  @if (cargando()) {
                    <mat-spinner diameter="20"></mat-spinner>
                  } @else {
                    Enviar Código al Correo
                  }
                </button>

                <div class="otp-actions">
                  <button mat-button type="button" (click)="volverALogin()" [disabled]="cargando()">
                    Volver al inicio de sesión
                  </button>
                </div>
              </form>
            } @else {
              <form (ngSubmit)="confirmarRecuperacionClave()" class="login-form">
                <mat-form-field appearance="outline" class="full">
                  <mat-label>Código de recuperación (6 dígitos)</mat-label>
                  <input
                    matInput
                    type="text"
                    [(ngModel)]="codigoRecuperacion"
                    name="codigoRecuperacion"
                    required
                    maxlength="12"
                    inputmode="numeric"
                    autocomplete="one-time-code"
                    placeholder="Ej. 482915"
                    class="otp-input"
                  />
                  <mat-icon matPrefix class="cyan">pin</mat-icon>
                </mat-form-field>

                <mat-form-field appearance="outline" class="full">
                  <mat-label>Nueva contraseña (mín. 6 caracteres)</mat-label>
                  <input
                    matInput
                    [type]="mostrarNuevaClave ? 'text' : 'password'"
                    [(ngModel)]="nuevaClave"
                    name="nuevaClave"
                    required
                    minlength="6"
                    autocomplete="new-password"
                  />
                  <mat-icon matPrefix class="cyan">lock</mat-icon>
                  <button mat-icon-button matSuffix type="button" (click)="mostrarNuevaClave = !mostrarNuevaClave">
                    <mat-icon>{{ mostrarNuevaClave ? 'visibility_off' : 'visibility' }}</mat-icon>
                  </button>
                </mat-form-field>

                <mat-form-field appearance="outline" class="full">
                  <mat-label>Confirmar nueva contraseña</mat-label>
                  <input
                    matInput
                    [type]="mostrarNuevaClave ? 'text' : 'password'"
                    [(ngModel)]="confirmarNuevaClave"
                    name="confirmarNuevaClave"
                    required
                    autocomplete="new-password"
                  />
                  <mat-icon matPrefix class="cyan">verified_user</mat-icon>
                </mat-form-field>

                @if (errorLogin()) {
                  <div class="error-box">{{ errorLogin() }}</div>
                }

                <button mat-flat-button color="primary" class="full submit-btn" type="submit" [disabled]="cargando() || !codigoRecuperacion.trim() || nuevaClave.length < 6">
                  @if (cargando()) {
                    <mat-spinner diameter="20"></mat-spinner>
                  } @else {
                    Restablecer Contraseña
                  }
                </button>

                <div class="otp-actions">
                  <button mat-stroked-button type="button" (click)="enviarCodigoRecuperacion(true)" [disabled]="cargando()">
                    <mat-icon>send</mat-icon> Reenviar código
                  </button>
                  <button mat-button type="button" (click)="volverALogin()" [disabled]="cargando()">
                    Cancelar
                  </button>
                </div>
              </form>
            }
          } @else {
            <p class="auth-hint">Ingresa tu correo institucional y tu contraseña o código de convocatoria.</p>

            @if (infoVerificacion()) {
              <div class="info-box">{{ infoVerificacion() }}</div>
            }

            <form (ngSubmit)="iniciarSesion()" class="login-form">
              <mat-form-field appearance="outline" class="full">
                <mat-label>Correo institucional</mat-label>
                <input
                  matInput
                  type="email"
                  [(ngModel)]="correo"
                  name="correo"
                  required
                  autocomplete="username"
                  placeholder="usuario@universidad.edu.co"
                />
                <mat-icon matPrefix class="cyan">alternate_email</mat-icon>
              </mat-form-field>

              <mat-form-field appearance="outline" class="full">
                <mat-label>Contraseña o código de convocatoria</mat-label>
                <input
                  matInput
                  [type]="mostrarCredencial ? 'text' : 'password'"
                  [(ngModel)]="credencial"
                  name="credencial"
                  required
                  autocomplete="current-password"
                  placeholder="Clave institucional o código de sesión"
                />
                <mat-icon matPrefix class="cyan">lock</mat-icon>
                <button mat-icon-button matSuffix type="button" (click)="mostrarCredencial = !mostrarCredencial">
                  <mat-icon>{{ mostrarCredencial ? 'visibility_off' : 'visibility' }}</mat-icon>
                </button>
              </mat-form-field>

              @if (errorLogin()) {
                <div class="error-box">{{ errorLogin() }}</div>
              }

              <button mat-flat-button color="primary" class="full submit-btn" type="submit" [disabled]="cargando() || !correo.trim() || !credencial.trim()">
                @if (cargando()) {
                  <mat-spinner diameter="20"></mat-spinner>
                } @else {
                  Ingresar a la Plataforma
                }
              </button>

              <div class="forgot-row">
                <button mat-button type="button" class="forgot-btn" (click)="abrirRecuperacion()" [disabled]="cargando()">
                  <mat-icon>lock_reset</mat-icon> ¿Olvidaste tu contraseña? Recupérala por correo
                </button>
              </div>
            </form>
          }
        </mat-card>
      </div>
    </main>
  `,
  styles: [`
    .login-page {
      min-height: 100vh;
      display: grid;
      place-items: center;
      padding: 20px;
      background:
        radial-gradient(circle at 18% 18%, rgba(0, 229, 244, 0.14), transparent 42%),
        radial-gradient(circle at 82% 82%, rgba(0, 232, 148, 0.1), transparent 42%),
        linear-gradient(rgba(13, 30, 38, 0.22) 1px, transparent 1px),
        linear-gradient(90deg, rgba(13, 30, 38, 0.22) 1px, transparent 1px),
        var(--bg);
      background-size: auto, auto, 24px 24px, 24px 24px, auto;
    }
    .login-wrap {
      width: min(100%, 520px);
      position: relative;
      z-index: 4;
    }
    .brand-card {
      display: grid;
      grid-template-columns: 88px 1fr;
      gap: 18px;
      align-items: center;
      margin-bottom: 16px;
      padding: 18px 20px;
      border: 1px solid rgba(0, 229, 244, 0.45);
      border-bottom: 3px solid var(--cyan);
      background: rgba(255, 255, 255, 0.96);
      color: #10212a;
      box-shadow: 0 18px 44px rgba(0, 0, 0, 0.45);
    }
    .brand-emblem {
      width: 84px;
      height: 84px;
      display: grid;
      place-items: center;
      border: 2px solid #0b3b6e;
      border-radius: 14px;
      padding: 6px;
      background: #ffffff;
      box-shadow: 0 6px 18px rgba(11, 59, 110, 0.14);
    }
    .brand-logo {
      width: 100%;
      height: 100%;
      object-fit: contain;
      display: block;
    }
    .brand-card h1 {
      margin: 0;
      color: #0b3b6e;
      font-family: var(--display);
      font-size: 38px;
      font-weight: 800;
      line-height: 0.96;
      text-transform: uppercase;
      letter-spacing: 1px;
    }
    .brand-card small {
      display: block;
      margin-top: 4px;
      color: #1d2d3a;
      font-family: var(--body);
      font-weight: 600;
      font-size: 13px;
    }
    .brand-slogan {
      margin: 4px 0 0;
      color: #4a5e6d;
      font-family: var(--body);
      font-style: italic;
      font-size: 13px;
    }
    .auth-card {
      display: grid;
      gap: 14px;
      padding: 24px 26px !important;
      background: rgba(9, 15, 22, 0.96) !important;
      border: 1px solid var(--line-strong) !important;
      margin-bottom: 0 !important;
    }
    .auth-hint {
      margin: 0;
      font-size: 13px;
      color: var(--muted);
    }
    .login-form {
      padding: 18px 4px 6px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .submit-btn {
      height: 50px !important;
      font-size: 14px !important;
      letter-spacing: 1.5px !important;
      margin-top: 8px;
    }
    .otp-banner {
      background: rgba(0, 229, 244, 0.08);
      border: 1px solid rgba(0, 229, 244, 0.35);
      border-left: 4px solid var(--cyan);
      padding: 12px 14px;
      font-size: 13px;
      color: var(--text);
      line-height: 1.5;
    }
    .otp-banner p { margin: 6px 0 0; }
    .otp-banner small { color: var(--muted); }
    .otp-title {
      display: flex;
      align-items: center;
      gap: 8px;
      font-family: var(--mono);
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      color: var(--cyan);
    }
    .info-box {
      padding: 10px 12px;
      border: 1px solid rgba(0, 232, 148, 0.45);
      background: rgba(0, 232, 148, 0.1);
      color: var(--green);
      font-size: 12px;
    }
    .otp-input {
      font-family: var(--mono) !important;
      letter-spacing: 4px;
      font-size: 18px !important;
      font-weight: 700;
    }
    .otp-actions {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
      margin-top: 6px;
      flex-wrap: wrap;
    }
    .forgot-row {
      display: flex;
      justify-content: center;
      margin-top: 6px;
    }
    .forgot-btn {
      font-size: 12px !important;
      color: var(--cyan-soft) !important;
    }
    .secure {
      display: flex;
      justify-content: center;
      align-items: center;
      gap: 8px;
      padding-top: 10px;
      border-top: 1px solid rgba(184, 211, 214, 0.14);
      color: var(--dim);
      font-size: 10px;
      letter-spacing: 1px;
    }
    .secure i {
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: var(--green);
      box-shadow: 0 0 10px var(--green);
      animation: pulse 1.7s ease-in-out infinite;
    }
    @media (max-width: 520px) {
      .brand-card {
        grid-template-columns: 1fr;
        text-align: center;
        justify-items: center;
      }
      .auth-card {
        padding: 18px !important;
      }
    }
  `],
})
export class LoginComponent {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  mostrarCredencial = false;
  mostrarNuevaClave = false;
  correo = '';
  credencial = '';
  codigoVerificacion = '';
  correoRecuperacion = '';
  codigoRecuperacion = '';
  nuevaClave = '';
  confirmarNuevaClave = '';
  errorLogin = signal<string | null>(null);
  infoVerificacion = signal<string | null>(null);
  cargando = signal<boolean>(false);
  verificacionPendiente = signal<{ correo: string; mensaje: string; expiraEnSegundos: number } | null>(null);
  recuperacionPaso = signal<'SOLICITAR' | 'CONFIRMAR' | null>(null);

  async iniciarSesion(): Promise<void> {
    this.errorLogin.set(null);
    this.infoVerificacion.set(null);
    this.cargando.set(true);
    try {
      const res = await this.auth.loginUnificado(this.correo.trim(), this.credencial.trim());
      if (res.estado === 'VERIFICACION_REQUERIDA') {
        this.codigoVerificacion = '';
        this.verificacionPendiente.set({
          correo: res.correo,
          mensaje: res.mensaje,
          expiraEnSegundos: res.expiraEnSegundos,
        });
        return;
      }
      if (res.usuario) {
        this.credencial = '';
        this.codigoVerificacion = '';
        void this.router.navigateByUrl(this.auth.rutaInicio());
      } else {
        this.errorLogin.set('No se pudo obtener el perfil de usuario.');
      }
    } catch (err) {
      this.errorLogin.set(mensajeError(err));
    } finally {
      this.cargando.set(false);
    }
  }

  async confirmarCodigoPrimerIngreso(): Promise<void> {
    const verif = this.verificacionPendiente();
    if (!verif) return;
    this.errorLogin.set(null);
    this.infoVerificacion.set(null);
    this.cargando.set(true);
    try {
      const u = await this.auth.verificarPrimerIngreso(verif.correo, this.codigoVerificacion.trim());
      if (u) {
        this.credencial = '';
        this.codigoVerificacion = '';
        this.verificacionPendiente.set(null);
        void this.router.navigateByUrl(this.auth.rutaInicio());
      } else {
        this.errorLogin.set('No se pudo obtener el perfil de usuario.');
      }
    } catch (err) {
      this.errorLogin.set(mensajeError(err));
    } finally {
      this.cargando.set(false);
    }
  }

  async reenviarCodigo(): Promise<void> {
    const verif = this.verificacionPendiente();
    if (!verif) return;
    this.errorLogin.set(null);
    this.infoVerificacion.set(null);
    this.cargando.set(true);
    try {
      const r = await this.auth.loginEstudiantePorClave(verif.correo, this.credencial.trim());
      if (r.requiere_verificacion) {
        this.infoVerificacion.set(`Se envió un nuevo código de verificación a ${r.correo ?? verif.correo}.`);
      } else if (r.access_token) {
        this.verificacionPendiente.set(null);
        await this.iniciarSesion();
      }
    } catch (err) {
      this.errorLogin.set(mensajeError(err));
    } finally {
      this.cargando.set(false);
    }
  }

  volverALogin(): void {
    this.verificacionPendiente.set(null);
    this.recuperacionPaso.set(null);
    this.codigoVerificacion = '';
    this.codigoRecuperacion = '';
    this.nuevaClave = '';
    this.confirmarNuevaClave = '';
    this.errorLogin.set(null);
    this.infoVerificacion.set(null);
  }

  abrirRecuperacion(): void {
    this.errorLogin.set(null);
    this.infoVerificacion.set(null);
    this.verificacionPendiente.set(null);
    this.correoRecuperacion = this.correo.trim();
    this.codigoRecuperacion = '';
    this.nuevaClave = '';
    this.confirmarNuevaClave = '';
    this.recuperacionPaso.set('SOLICITAR');
  }

  async enviarCodigoRecuperacion(esReenvio = false): Promise<void> {
    const objetivo = this.correoRecuperacion.trim();
    if (!objetivo) return;
    this.errorLogin.set(null);
    this.infoVerificacion.set(null);
    this.cargando.set(true);
    try {
      const resp = await this.auth.solicitarRecuperacionContrasena(objetivo);
      this.recuperacionPaso.set('CONFIRMAR');
      this.infoVerificacion.set(esReenvio ? `Código reenviado a ${objetivo}.` : resp.mensaje);
    } catch (err) {
      this.errorLogin.set(mensajeError(err));
    } finally {
      this.cargando.set(false);
    }
  }

  async confirmarRecuperacionClave(): Promise<void> {
    if (this.nuevaClave !== this.confirmarNuevaClave) {
      this.errorLogin.set('Las contraseñas nuevas no coinciden.');
      return;
    }
    this.errorLogin.set(null);
    this.infoVerificacion.set(null);
    this.cargando.set(true);
    try {
      const resp = await this.auth.confirmarRecuperacionContrasena(
        this.correoRecuperacion.trim(),
        this.codigoRecuperacion.trim(),
        this.nuevaClave,
      );
      this.correo = this.correoRecuperacion.trim();
      this.credencial = '';
      this.recuperacionPaso.set(null);
      this.codigoRecuperacion = '';
      this.nuevaClave = '';
      this.confirmarNuevaClave = '';
      this.infoVerificacion.set(resp.mensaje);
    } catch (err) {
      this.errorLogin.set(mensajeError(err));
    } finally {
      this.cargando.set(false);
    }
  }
}

