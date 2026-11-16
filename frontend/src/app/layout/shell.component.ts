import { Component, inject } from '@angular/core';
import { Router, RouterLink, RouterLinkActive, RouterOutlet, NavigationEnd } from '@angular/router';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { filter } from 'rxjs/operators';
import { AuthService } from '../core/auth.service';

@Component({
  selector: 'app-shell',
  standalone: true,
  imports: [
    CommonModule,
    RouterOutlet,
    RouterLink,
    RouterLinkActive,
    MatIconModule,
    MatButtonModule,
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
      .pipe(filter((event): event is NavigationEnd => event instanceof NavigationEnd))
      .subscribe((event) => {
        this.rutaActual = event.urlAfterRedirects;
      });
    this.rutaActual = this.router.url;
  }

  obtenerTituloVista(): string {
    if (this.rutaActual.startsWith('/casos')) return 'Gestión de Casos & Escenarios';
    if (this.rutaActual.startsWith('/programacion')) return 'Programación de Sesiones & Espacios';
    if (this.rutaActual.startsWith('/seguimiento')) return 'Auditoría & Seguimiento Académico';
    if (this.rutaActual.startsWith('/administracion')) return 'Gobernanza & Directorio Docente';
    if (this.rutaActual.startsWith('/estudiante')) return 'Portal de Simulación Estudiantil';
    return 'Consola Principal SPS';
  }

  obtenerInicial(): string {
    const usuario = this.auth.usuario();
    if (!usuario?.correo) return 'U';
    return usuario.correo.charAt(0).toUpperCase();
  }
}
