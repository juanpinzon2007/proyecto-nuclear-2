import { Component, inject } from '@angular/core';
import { Router } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { AuthService } from '../../core/auth.service';

@Component({
  selector: 'app-forbidden',
  standalone: true,
  imports: [MatButtonModule, MatCardModule, MatIconModule],
  template: `
    <main class="screen scanlines warn-screen">
      <div class="content narrow">
        <mat-card class="panel warn-card">
          <div class="warn-icon pulse">
            <mat-icon>lock</mat-icon>
          </div>
          <p class="eyebrow amber">Protocolo de Seguridad // Código 403</p>
          <h1>Acceso Denegado</h1>
          <p class="warn-copy">
            No cuentas con las credenciales o permisos activos para operar en este módulo del Simulador SPS.
          </p>
          <div class="warn-actions">
            <button mat-flat-button color="accent" (click)="irInicio()">Volver al inicio</button>
            <button mat-stroked-button (click)="logout()">Cerrar sesión</button>
          </div>
          <div class="spectrum" aria-hidden="true">
            <span></span><span></span><span></span>
          </div>
        </mat-card>
      </div>
    </main>
  `,
  styles: [`
    .warn-screen {
      display: grid;
      place-items: center;
      padding: 24px 16px;
    }
    .warn-card {
      display: grid;
      gap: 14px;
      padding: 28px !important;
      text-align: center;
      border-top: 4px solid var(--amber) !important;
      border-color: rgba(255, 184, 0, 0.5) !important;
      background: rgba(16, 20, 27, 0.96) !important;
    }
    .warn-icon {
      width: 68px;
      height: 68px;
      margin: 0 auto 4px;
      display: grid;
      place-items: center;
      border: 1px solid rgba(255, 184, 0, 0.55);
      background: rgba(255, 184, 0, 0.1);
      color: var(--amber);
    }
    .warn-icon mat-icon {
      font-size: 36px;
      width: 36px;
      height: 36px;
    }
    h1 {
      margin: 0;
      font-family: var(--display);
      font-size: 38px;
      color: var(--text);
    }
    .warn-copy {
      color: var(--muted);
      font-size: 14px;
      line-height: 1.55;
      margin: 0;
    }
    .warn-actions {
      display: flex;
      gap: 12px;
      justify-content: center;
      flex-wrap: wrap;
      margin-top: 6px;
    }
    .spectrum {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 6px;
      margin-top: 10px;
    }
    .spectrum span {
      height: 5px;
      background: var(--cyan);
    }
    .spectrum span:nth-child(2) {
      background: var(--green);
    }
    .spectrum span:nth-child(3) {
      background: var(--amber);
    }
  `],
})
export class ForbiddenComponent {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  irInicio(): void {
    void this.router.navigateByUrl(this.auth.rutaInicio());
  }

  logout(): void {
    this.auth.logout();
  }
}

