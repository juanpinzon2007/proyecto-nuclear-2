import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatTabsModule } from '@angular/material/tabs';
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
    MatTabsModule,
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
            <mat-icon>psychology</mat-icon>
          </div>
          <div>
            <p class="module">Módulo de Acceso · NeuroCommand</p>
            <h1>Simulador SPS</h1>
            <small>Plataforma Académica de Psicología Social</small>
          </div>
        </section>

        <mat-card class="panel auth-card">
          <span class="tag green">Protocolo autenticado · Acceso seguro</span>
          <p class="auth-hint">Selecciona tu perfil e ingresa tus credenciales institucionales o código de convocatoria.</p>

          <mat-tab-group mat-stretch-tabs="false" mat-align-tabs="center" [(selectedIndex)]="tabSeleccionada">
            <!-- Login Personal Docente / Admin -->
            <mat-tab label="Personal Docente / Admin">
              <form (ngSubmit)="loginPersonal()" class="login-form">
                <mat-form-field appearance="outline" class="full">
                  <mat-label>Correo electrónico</mat-label>
                  <input matInput type="email" [(ngModel)]="correoPersonal" name="correoPersonal" required autocomplete="username" placeholder="docente@universidad.edu.co" />
                  <mat-icon matPrefix class="cyan">email</mat-icon>
                </mat-form-field>

                <mat-form-field appearance="outline" class="full">
                  <mat-label>Contraseña</mat-label>
                  <input matInput [type]="mostrarClave ? 'text' : 'password'" [(ngModel)]="clavePersonal" name="clavePersonal" required autocomplete="current-password" />
                  <mat-icon matPrefix class="cyan">lock</mat-icon>
                  <button mat-icon-button matSuffix type="button" (click)="mostrarClave = !mostrarClave">
                    <mat-icon>{{ mostrarClave ? 'visibility_off' : 'visibility' }}</mat-icon>
                  </button>
                </mat-form-field>

                @if (errorPersonal()) {
                  <div class="error-box">{{ errorPersonal() }}</div>
                }

                <button mat-flat-button color="primary" class="full submit-btn" type="submit" [disabled]="cargando()">
                  @if (cargando()) {
                    <mat-spinner diameter="20"></mat-spinner>
                  } @else {
                    Ingresar como Personal
                  }
                </button>
              </form>
            </mat-tab>

            <!-- Login Estudiante -->
            <mat-tab label="Estudiante">
              <form (ngSubmit)="loginEstudiante()" class="login-form">
                <div class="info-box">
                  Ingresa con tu correo y el <strong>código de acceso de convocatoria</strong> emitido por tu docente.
                </div>

                <mat-form-field appearance="outline" class="full">
                  <mat-label>Correo del estudiante</mat-label>
                  <input matInput type="email" [(ngModel)]="correoEstudiante" name="correoEstudiante" required placeholder="estudiante@universidad.edu.co" />
                  <mat-icon matPrefix class="cyan">school</mat-icon>
                </mat-form-field>

                <mat-form-field appearance="outline" class="full">
                  <mat-label>Código de Convocatoria</mat-label>
                  <input matInput type="password" [(ngModel)]="codigoConvocatoria" name="codigoConvocatoria" required placeholder="Código seguro de la sesión" />
                  <mat-icon matPrefix class="cyan">key</mat-icon>
                </mat-form-field>

                @if (errorEstudiante()) {
                  <div class="error-box">{{ errorEstudiante() }}</div>
                }

                <button mat-flat-button color="primary" class="full submit-btn" type="submit" [disabled]="cargando()">
                  @if (cargando()) {
                    <mat-spinner diameter="20"></mat-spinner>
                  } @else {
                    Ingresar al Simulador
                  }
                </button>
              </form>
            </mat-tab>
          </mat-tab-group>

          <div class="secure mono">
            <i></i>
            <span>CONEXIÓN SEGURA · NODO POSTGRESQL ACTIVO</span>
          </div>
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
      width: 78px;
      height: 78px;
      display: grid;
      place-items: center;
      border: 2px solid #00a7b8;
      background: radial-gradient(circle, rgba(0, 229, 244, 0.22), #0a1b24 78%);
      color: var(--cyan);
    }
    .brand-emblem mat-icon {
      font-size: 42px;
      width: 42px;
      height: 42px;
    }
    .module {
      margin: 0 0 4px;
      color: #00727e;
      font-family: var(--mono);
      font-size: 11px;
      letter-spacing: 2px;
      text-transform: uppercase;
    }
    .brand-card h1 {
      margin: 0;
      color: #0d3038;
      font-family: var(--display);
      font-size: 36px;
      font-weight: 700;
      line-height: 0.96;
      text-transform: uppercase;
    }
    .brand-card small {
      display: block;
      margin-top: 5px;
      color: #536069;
      font-family: var(--mono);
      font-size: 11px;
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

  tabSeleccionada = 0;
  mostrarClave = false;

  correoPersonal = '';
  clavePersonal = '';
  errorPersonal = signal<string | null>(null);

  correoEstudiante = '';
  codigoConvocatoria = '';
  errorEstudiante = signal<string | null>(null);

  cargando = signal<boolean>(false);

  async loginPersonal(): Promise<void> {
    this.errorPersonal.set(null);
    this.cargando.set(true);
    try {
      const u = await this.auth.loginPersonal(this.correoPersonal, this.clavePersonal);
      if (u) {
        void this.router.navigateByUrl(this.auth.rutaInicio());
      } else {
        this.errorPersonal.set('No se pudo obtener el perfil de usuario.');
      }
    } catch (err) {
      this.errorPersonal.set(mensajeError(err));
    } finally {
      this.cargando.set(false);
    }
  }

  async loginEstudiante(): Promise<void> {
    this.errorEstudiante.set(null);
    this.cargando.set(true);
    try {
      const u = await this.auth.loginEstudiante(this.correoEstudiante, this.codigoConvocatoria);
      if (u) {
        void this.router.navigateByUrl('/estudiante');
      } else {
        this.errorEstudiante.set('No se pudo verificar la credencial de estudiante.');
      }
    } catch (err) {
      this.errorEstudiante.set(mensajeError(err));
    } finally {
      this.cargando.set(false);
    }
  }
}

