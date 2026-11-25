import { signal } from '@angular/core';
import { describe, expect, it } from 'vitest';
import { etiquetaEstado, ListaPaginada, paginadorEnEspanol } from './lista-paginada';

describe('paginación de registros académicos', () => {
  it('busca por texto sin depender de tildes y vuelve a la primera página', () => {
    const filas = signal(['Sofía Gómez', 'Carlos Pinzón', 'Sara Nieto']);
    const lista = new ListaPaginada(filas, (nombre) => nombre);
    lista.cambiar({ pageIndex: 2, pageSize: 1, length: 3 });
    expect(lista.visibles()).toEqual(['Sara Nieto']);

    lista.buscar('  SOFIA  ');
    expect(lista.pagina()).toBe(0);
    expect(lista.visibles()).toEqual(['Sofía Gómez']);
  });

  it('muestra la última página disponible cuando se reduce la lista', () => {
    const filas = signal(Array.from({ length: 21 }, (_, i) => `Estudiante ${i + 1}`));
    const lista = new ListaPaginada(filas, (nombre) => nombre);
    lista.cambiar({ pageIndex: 2, pageSize: 10, length: 21 });
    expect(lista.visibles()).toEqual(['Estudiante 21']);

    filas.update((datos) => datos.slice(0, 12));
    expect(lista.pagina()).toBe(1);
    expect(lista.visibles()).toEqual(['Estudiante 11', 'Estudiante 12']);
  });

  it('describe en español el rango visible y los estados', () => {
    const textos = paginadorEnEspanol();
    expect(textos.getRangeLabel(1, 10, 12)).toBe('11–12 de 12');
    expect(textos.getRangeLabel(0, 10, 0)).toBe('0 de 0');
    expect(etiquetaEstado('SIN_INICIAR')).toBe('Sin iniciar');
    expect(etiquetaEstado('TECNICO')).toBe('Técnico');
  });
});
