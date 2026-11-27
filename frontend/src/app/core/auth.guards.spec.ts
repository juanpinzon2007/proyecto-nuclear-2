import { TestBed } from '@angular/core/testing';
import { ActivatedRouteSnapshot, CanActivateFn, provideRouter, Router, RouterStateSnapshot, UrlTree } from '@angular/router';
import { expect, it, vi } from 'vitest';
import { authGuard, inicioGuard, invitadoGuard, permisoGuard, rolGuard } from './auth.guards';
import { AuthService } from './auth.service';

const docente = { roles: ['DOCENTE'], permisos: ['CREAR_CASOS'] };
const escenarios: [string, CanActivateFn, typeof docente | null, true | string][] = [
  ['sesión vigente', authGuard, docente, true],
  ['sesión vencida', authGuard, null, '/login'],
  ['rol permitido', rolGuard('DOCENTE'), docente, true],
  ['rol distinto', rolGuard('ADMINISTRADOR'), docente, '/sin-permiso'],
  ['rol anónimo', rolGuard('DOCENTE'), null, '/login'],
  ['permiso concedido', permisoGuard('CREAR_CASOS'), docente, true],
  ['permiso ausente', permisoGuard('OTRO'), docente, '/sin-permiso'],
  ['permiso anónimo', permisoGuard('CREAR_CASOS'), null, '/login'],
  ['invitado', invitadoGuard, null, true],
  ['invitado con sesión', invitadoGuard, docente, '/docente'],
  ['inicio del docente', inicioGuard, docente, '/docente'],
];

it.each(escenarios)('%s', async (_, guard, perfil, esperado) => {
  TestBed.configureTestingModule({providers: [
    provideRouter([]),
    { provide: AuthService, useValue: { asegurarPerfil: vi.fn().mockResolvedValue(perfil), rutaInicio: () => '/docente' } },
  ]});
  const resultado = await TestBed.runInInjectionContext(() =>
    guard({} as ActivatedRouteSnapshot, {} as RouterStateSnapshot));
  expect(resultado instanceof UrlTree ? TestBed.inject(Router).serializeUrl(resultado) : resultado).toBe(esperado);
});
