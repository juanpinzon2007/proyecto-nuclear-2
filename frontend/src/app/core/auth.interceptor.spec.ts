import { HttpErrorResponse, HttpEvent, HttpHandlerFn, HttpRequest } from '@angular/common/http';
import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { Subject } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { authInterceptor } from './auth.interceptor';
import { AuthService } from './auth.service';

describe('token de la sesión', () => {
  const token = signal<string | null>('sesion-anterior');
  const logout = vi.fn();

  beforeEach(() => {
    token.set('sesion-anterior');
    logout.mockClear();
    TestBed.configureTestingModule({ providers: [{ provide: AuthService, useValue: { token, logout } }] });
  });

  function enviar(url: string) {
    const respuesta = new Subject<HttpEvent<unknown>>();
    const siguiente = vi.fn<HttpHandlerFn>(() => respuesta);
    TestBed.runInInjectionContext(() => authInterceptor(new HttpRequest('GET', url), siguiente))
      .subscribe({ error: () => undefined });
    return { cabeceras: siguiente.mock.calls[0][0].headers, respuesta };
  }

  it('adjunta el token solo a la API autenticada de SPS', () => {
    expect(enviar('/api/v1/identity/me').cabeceras.get('Authorization')).toBe('Bearer sesion-anterior');
    expect(enviar('/api/v1/identity/auth/personal').cabeceras.has('Authorization')).toBe(false);
    expect(enviar('https://example.test/api/v1/identity/me').cabeceras.has('Authorization')).toBe(false);
  });

  it('cierra la sesión cuando la API rechaza el token vigente', () => {
    const { respuesta } = enviar('/api/v1/identity/me');
    respuesta.error(new HttpErrorResponse({ status: 401 }));
    expect(logout).toHaveBeenCalledOnce();
  });

  it('conserva una sesión nueva cuando la respuesta pertenece al token anterior', () => {
    const { respuesta } = enviar('/api/v1/identity/me');
    token.set('sesion-nueva');
    respuesta.error(new HttpErrorResponse({ status: 401 }));
    expect(logout).not.toHaveBeenCalled();
  });
});
