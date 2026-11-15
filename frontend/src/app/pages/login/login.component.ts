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
    <div class="login-wrapper">
      <mat-card class="login-card">
        <div class="login-header">
          <div class="icon-circle">
            <mat-icon>psychology</mat-icon>
          </div>
          <h1>Simulador SPS</h1>
          <p class="muted">Plataforma Académica de Psicología Social</p>
        </div>

        <mat-tab-group mat-stretch-tabs="false" mat-align-tabs="center" [(selectedIndex)]="tabSeleccionada">
          <!-- Login Personal Docente / Admin -->
          <mat-tab label="Personal Docente / Admin">
            <form (ngSubmit)="loginPersonal()" class="login-form">
              <mat-form-field appearance="outline" class="full">
                <mat-label>Correo electrónico</mat-label>
                <input matInput type="email" [(ngModel)]="correoPersonal" name="correoPersonal" required autocomplete="username" placeholder="docente@universidad.edu.co" />
                <mat-icon matPrefix>email</mat-icon>
              </mat-form-field>

              <mat-form-field appearance="outline" class="full">
                <mat-label>Contraseña</mat-label>
                <input matInput [type]="mostrarClave ? 'text' : 'password'" [(ngModel)]="clavePersonal" name="clavePersonal" required autocomplete="current-password" />
                <mat-icon matPrefix>lock</mat-icon>
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
              <div class="info-box" style="margin-bottom: 16px; font-size: 13px;">
                Ingresa con tu correo y el <strong>código de acceso de convocatoria</strong> asignado por tu docente.
              </div>

              <mat-form-field appearance="outline" class="full">
                <mat-label>Correo del estudiante</mat-label>
                <input matInput type="email" [(ngModel)]="correoEstudiante" name="correoEstudiante" required placeholder="estudiante@universidad.edu.co" />
                <mat-icon matPrefix>school</mat-icon>
              </mat-form-field>

              <mat-form-field appearance="outline" class="full">
                <mat-label>Código de Convocatoria</mat-label>
                <input matInput type="password" [(ngModel)]="codigoConvocatoria" name="codigoConvocatoria" required placeholder="Código seguro de la sesión" />
                <mat-icon matPrefix>key</mat-icon>
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
      </mat-card>
    </div>
  `,
  styles: [`
    .login-wrapper {
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 16px;
      background: linear-gradient(135deg, #0d47a1 0%, #1976d2 50%, #42a5f5 100%);
    }
    .login-card {
      width: 100%;
      max-width: 460px;
      padding: 24px 20px;
      border-radius: 16px;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.25);
    }
    .login-header {
      text-align: center;
      margin-bottom: 20px;
    }
    .icon-circle {
      width: 64px;
      height: 64px;
      border-radius: 50%;
      background: var(--mat-sys-primary-container);
      color: var(--mat-sys-on-primary-container);
      display: inline-flex;
      align-items: center;
      justify-content: center;
      margin-bottom: 12px;
    }
    .icon-circle mat-icon {
      font-size: 36px;
      width: 36px;
      height: 36px;
    }
    .login-header h1 {
      margin: 0;
      font-size: 24px;
      font-weight: 700;
    }
    .login-form {
      padding: 20px 8px 8px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .submit-btn {
      height: 48px;
      font-size: 15px;
      font-weight: 600;
      margin-top: 8px;
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

