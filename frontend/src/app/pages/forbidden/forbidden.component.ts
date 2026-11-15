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
    <div class="page" style="max-width: 500px; margin-top: 80px; text-align: center;">
      <mat-card>
        <mat-card-header style="justify-content: center; padding-top: 16px;">
          <mat-icon style="font-size: 64px; height: 64px; width: 64px; color: var(--mat-sys-error);">lock</mat-icon>
        </mat-card-header>
        <mat-card-content style="padding: 24px;">
          <h2>Acceso Denegado</h2>
          <p class="muted">No tienes los permisos necesarios para acceder a esta sección del Simulador.</p>
          <div style="margin-top: 24px; display: flex; gap: 12px; justify-content: center;">
            <button mat-flat-button color="primary" (click)="irInicio()">Volver al inicio</button>
            <button mat-stroked-button (click)="logout()">Cerrar sesión</button>
          </div>
        </mat-card-content>
      </mat-card>
    </div>
  `,
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

