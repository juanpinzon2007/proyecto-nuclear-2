import { Component } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { MatDialog } from '@angular/material/dialog';
import { provideRouter, Router } from '@angular/router';
import { expect, it, vi } from 'vitest';
import { App } from './app';

@Component({ template: '' })
class VistaDePrueba {}

it('cierra los diálogos de la sesión al volver al inicio de sesión', async () => {
  const cerrar = vi.fn();
  TestBed.configureTestingModule({
    imports: [App],
    providers: [
      { provide: MatDialog, useValue: { closeAll: cerrar } },
      provideRouter([
        { path: 'simulacion', component: VistaDePrueba },
        { path: 'login', component: VistaDePrueba },
      ]),
    ],
  });
  TestBed.createComponent(App).detectChanges();
  const router = TestBed.inject(Router);
  await router.navigateByUrl('/simulacion');
  expect(cerrar).not.toHaveBeenCalled();

  await router.navigateByUrl('/login?sesion=expirada');
  expect(cerrar).toHaveBeenCalledOnce();
});
