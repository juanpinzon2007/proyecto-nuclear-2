import { Component, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Router, RouterLink, RouterLinkActive, RouterOutlet, NavigationEnd } from '@angular/router';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { filter } from 'rxjs/operators';
import { AuthService } from '../core/auth.service';
import { avatarUsuario } from '../core/user-avatar';

@Component({
  selector: 'app-shell',
  standalone: true,
  imports: [
    CommonModule,
    RouterOutlet,
    RouterLink,
    RouterLinkActive,
    MatIconModule,
  ],
  templateUrl: './shell.component.html',
  styleUrls: ['./shell.component.scss'],
})
export class ShellComponent {
  readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  rutaActual = '';

  constructor() {
    this.router.events
      .pipe(filter((event): event is NavigationEnd => event instanceof NavigationEnd), takeUntilDestroyed())
      .subscribe((event) => {
        this.rutaActual = event.urlAfterRedirects;
      });
    this.rutaActual = this.router.url;
  }

  obtenerTituloVista(): string {
    if (this.rutaActual.startsWith('/casos')) return 'Casos de estudio';
    if (this.rutaActual.startsWith('/programacion')) return 'Sesiones y grupos';
    if (this.rutaActual.startsWith('/seguimiento')) return 'Seguimiento académico';
    if (this.rutaActual.startsWith('/administracion')) return 'Administración';
    if (this.rutaActual.startsWith('/estudiante')) return 'Portal del estudiante';
    return 'Simulador de Psicología Social';
  }

  obtenerAvatar(): string {
    const u = this.auth.usuario();
    return avatarUsuario({
      id_usuario: u?.id_usuario,
      correo: u?.correo,
      rol: u?.roles?.[0],
    });
  }
}
