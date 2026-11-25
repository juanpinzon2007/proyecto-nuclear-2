import { HttpErrorResponse } from '@angular/common/http';
import { describe, expect, it } from 'vitest';
import { mensajeError, mensajeErrorAsync } from './api-error';

describe('mensajes de solicitud', () => {
  it('explica una desconexión con una acción para el usuario', () => {
    expect(mensajeError(new HttpErrorResponse({ status: 0 }))).toContain('Revisa tu conexión');
  });

  it('presenta una única instrucción cuando hay demasiados intentos', () => {
    const respuesta = new HttpErrorResponse({ status: 429, error: { detail: 'Detalle del servidor' } });
    const mensaje = mensajeError(respuesta);
    expect(mensaje).toContain('Espera un momento');
    expect(mensaje).not.toContain('Detalle del servidor');
  });

  it('muestra el motivo específico cuando falla el envío del código', () => {
    const mensaje = 'No pudimos enviar el código de verificación. Inténtalo más tarde.';
    const respuesta = new HttpErrorResponse({ status: 503, error: { detail: {
      codigo: 'CORREO_NO_DISPONIBLE', mensaje,
    } } });
    expect(mensajeError(respuesta)).toBe(mensaje);
  });

  it('informa campos inválidos y errores generales en el mismo mensaje', () => {
    const respuesta = new HttpErrorResponse({ status: 422, error: { detail: [
      { loc: ['body', 'correo'], msg: 'Revisa el formato.' },
      { loc: ['body'], msg: 'Hay un campo desconocido.' },
    ] } });
    expect(mensajeError(respuesta)).toBe('Datos inválidos: correo: Revisa el formato. · Hay un campo desconocido.');
  });

  it('recupera el mensaje de error de una descarga', async () => {
    const cuerpo = '{"detail":"Informe no encontrado."}';
    const blob = new Blob([cuerpo]);
    // jsdom 26 todavía no implementa Blob.text() en su entorno DOM.
    Object.defineProperty(blob, 'text', { value: async () => cuerpo });
    const respuesta = new HttpErrorResponse({ status: 404, error: blob });
    expect(await mensajeErrorAsync(respuesta)).toContain('Informe no encontrado.');
  });
});
