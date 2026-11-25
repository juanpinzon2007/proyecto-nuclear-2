import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import axe from 'axe-core';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AuthService } from '../../core/auth.service';
import { LoginComponent } from './login.component';

describe('acceso a SPS', () => {
  const loginUnificado = vi.fn();
  const loginEstudiante = vi.fn();

  beforeEach(() => {
    loginUnificado.mockReset();
    loginEstudiante.mockReset();
    TestBed.configureTestingModule({
      imports: [LoginComponent],
      providers: [provideRouter([]), { provide: AuthService, useValue: { loginUnificado, loginEstudiante } }],
    });
  });

  it('expone nombre accesible para el formulario y sus controles', async () => {
    const fixture = TestBed.createComponent(LoginComponent);
    fixture.detectChanges();
    await fixture.whenStable();
    const pagina: HTMLElement = fixture.nativeElement;
    expect(pagina.querySelectorAll('h1')).toHaveLength(1);
    const resultados = await axe.run(pagina, {
      runOnly: { type: 'rule', values: ['label', 'button-name', 'landmark-unique', 'aria-valid-attr-value'] },
    });
    expect(resultados.violations.map(({ id, nodes }) => ({ id, elementos: nodes.map((nodo) => nodo.target) }))).toEqual([]);
  });

  it('presenta el título y un campo etiquetado al recuperar la contraseña', async () => {
    const fixture = TestBed.createComponent(LoginComponent);
    fixture.detectChanges();
    fixture.componentInstance.abrirRecuperacion();
    fixture.detectChanges();
    await fixture.whenStable();
    const pagina: HTMLElement = fixture.nativeElement;
    expect(pagina.querySelector('h1')?.textContent).toContain('Recuper');
    expect(document.activeElement).toBe(pagina.querySelector('h1'));
    const correo = pagina.querySelector<HTMLInputElement>('input[type="email"]');
    expect(correo?.labels?.[0]?.textContent).toContain('Correo');
  });

  it('envía un código de convocatoria por la ruta directa sin solicitar otro correo', async () => {
    const fixture = TestBed.createComponent(LoginComponent);
    const login = fixture.componentInstance;
    fixture.detectChanges();
    login.correo = 'estudiante@universidad.test';
    login.credencial = 'contraseña introducida antes';
    login.cambiarModoAcceso();
    fixture.detectChanges();
    await fixture.whenStable();
    expect(login.credencial).toBe('');
    expect(document.activeElement?.id).toBe('login-credential');

    login.credencial = ' CODIGO-PRUEBA ';
    loginEstudiante.mockResolvedValue(null);
    await login.iniciarSesion();
    expect(loginEstudiante).toHaveBeenCalledWith('estudiante@universidad.test', 'CODIGO-PRUEBA');
    expect(loginUnificado).not.toHaveBeenCalled();
  });
});
