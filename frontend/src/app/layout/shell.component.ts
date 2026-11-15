import { Component, inject } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { CommonModule } from '@angular/common';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { MatDividerModule } from '@angular/material/divider';
import { AuthService } from '../core/auth.service';

@Component({
  selector: 'app-shell',
  standalone: true,
  imports: [
    CommonModule,
    RouterOutlet,
    RouterLink,
    RouterLinkActive,
    MatToolbarModule,
    MatButtonModule,
    MatIconModule,
    MatMenuModule,
    MatDividerModule,
  ],
  template: `
    <mat-toolbar color="primary" class="main-toolbar">
      <div class="brand" routerLink="/">
        <mat-icon>psychology</mat-icon>
        <span class="title">SPS</span>
        <span class="subtitle">Simulador de Psicología Social</span>
      </div>

      <nav class="nav-links">
        @if (auth.esDocente() || auth.esAdmin()) {
          <a mat-button routerLink="/casos" routerLinkActive="active-link">
            <mat-icon>folder_special</mat-icon> Casos
          </a>
          <a mat-button routerLink="/programacion" routerLinkActive="active-link">
            <mat-icon>event</mat-icon> Programación
          </a>
          <a mat-button routerLink="/seguimiento" routerLinkActive="active-link">
            <mat-icon>insights</mat-icon> Seguimiento
          </a>
        }
        @if (auth.esAdmin()) {
          <a mat-button routerLink="/administracion/docentes" routerLinkActive="active-link">
            <mat-icon>admin_panel_settings</mat-icon> Administración
          </a>
        }
        @if (auth.esEstudiante()) {
          <a mat-button routerLink="/estudiante" routerLinkActive="active-link">
            <mat-icon>school</mat-icon> Mi Convocatoria
          </a>
        }
      </nav>

      <div class="spacer"></div>

      <div class="user-section">
        @if (auth.usuario(); as u) {
          <div class="user-meta">
            <span class="user-email">{{ u.correo }}</span>
            <div class="roles-badges">
              @for (r of u.roles; track r) {
                <span class="chip-sm" [class.admin]="r === 'ADMINISTRADOR'" [class.doc]="r === 'DOCENTE'" [class.est]="r === 'ESTUDIANTE'">
                  {{ r }}
                </span>
              }
            </div>
          </div>
          <button mat-icon-button (click)="auth.logout()" title="Cerrar sesión">
            <mat-icon>logout</mat-icon>
          </button>
        }
      </div>
    </mat-toolbar>

    <main class="main-content">
      <router-outlet></router-outlet>
    </main>
  `,
  styles: [`
    .main-toolbar {
      display: flex;
      align-items: center;
      gap: 16px;
      position: sticky;
      top: 0;
      z-index: 1000;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 8px;
      cursor: pointer;
      user-select: none;
      text-decoration: none;
      color: inherit;
    }
    .title {
      font-weight: 700;
      font-size: 20px;
      letter-spacing: 0.5px;
    }
    .subtitle {
      font-size: 13px;
      opacity: 0.85;
      display: none;
    }
    @media (min-width: 768px) {
      .subtitle { display: inline; }
    }
    .nav-links {
      display: flex;
      gap: 4px;
      align-items: center;
    }
    .nav-links a {
      color: inherit;
      border-radius: 4px;
      display: inline-flex;
      align-items: center;
      gap: 4px;
    }
    .active-link {
      background: rgba(255, 255, 255, 0.2);
      font-weight: 600;
    }
    .user-section {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .user-meta {
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      line-height: 1.2;
    }
    .user-email {
      font-size: 13px;
      font-weight: 500;
    }
    .roles-badges {
      display: flex;
      gap: 4px;
      margin-top: 2px;
    }
    .chip-sm {
      font-size: 10px;
      padding: 1px 6px;
      border-radius: 8px;
      font-weight: 600;
      text-transform: uppercase;
      background: rgba(255, 255, 255, 0.25);
    }
    .main-content {
      min-height: calc(100vh - 64px);
    }
  `],
})
export class ShellComponent {
  readonly auth = inject(AuthService);
}

