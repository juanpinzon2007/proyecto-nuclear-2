import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { Rol } from './api.models';
import { AuthService } from './auth.service';

/** Exige sesión válida. */
export const authGuard: CanActivateFn = async () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  const u = await auth.asegurarPerfil();
  return u ? true : router.createUrlTree(['/login']);
};

/** Exige alguno de los roles indicados. */
export function rolGuard(...roles: Rol[]): CanActivateFn {
  return async () => {
    const auth = inject(AuthService);
    const router = inject(Router);
    const u = await auth.asegurarPerfil();
    if (!u) return router.createUrlTree(['/login']);
    return u.roles.some((r) => roles.includes(r)) ? true : router.createUrlTree(['/sin-permiso']);
  };
}

/** Exige alguno de los permisos indicados. */
export function permisoGuard(...permisos: string[]): CanActivateFn {
  return async () => {
    const auth = inject(AuthService);
    const router = inject(Router);
    const u = await auth.asegurarPerfil();
    if (!u) return router.createUrlTree(['/login']);
    return permisos.some((p) => u.permisos.includes(p)) ? true : router.createUrlTree(['/sin-permiso']);
  };
}

/** Si ya hay sesión, redirige al inicio según el rol. */
export const invitadoGuard: CanActivateFn = async () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  const u = await auth.asegurarPerfil();
  return u ? router.createUrlTree([auth.rutaInicio()]) : true;
};

/** Redirige la ruta raíz directamente al módulo principal de cada rol (RF-02). */
export const inicioGuard: CanActivateFn = async () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  await auth.asegurarPerfil();
  return router.createUrlTree([auth.rutaInicio()]);
};

