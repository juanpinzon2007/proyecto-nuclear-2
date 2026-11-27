import { TestBed } from '@angular/core/testing';
import { ActivatedRoute } from '@angular/router';
import { MatSnackBar } from '@angular/material/snack-bar';
import { of, throwError } from 'rxjs';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ParticipationService } from '../../core/participation.service';
import { UiDialogService } from '../../core/ui-dialog.service';
import { SimuladorComponent } from './simulador.component';

describe('Entrega de una simulacion', () => {
  const carga = vi.fn();
  const enviar = vi.fn();
  const confirmar = vi.fn();
  const aviso = vi.fn();
  const resultado = { puntaje: 75 };
  let pantalla: SimuladorComponent;

  beforeEach(() => {
    vi.resetAllMocks();
    TestBed.configureTestingModule({ providers: [
      { provide: ActivatedRoute, useValue: {} },
      { provide: ParticipationService, useValue: { obtenerWorkspace: carga, enviarSimulacion: enviar } },
      { provide: UiDialogService, useValue: { confirmar } },
      { provide: MatSnackBar, useValue: { open: aviso } },
    ] });
    pantalla = TestBed.runInInjectionContext(() => new SimuladorComponent());
    pantalla.idIntento = 42;
  });

  afterEach(() => pantalla.ngOnDestroy());

  it.each([true, false])('solicita confirmacion y entrega con listo_para_enviar=%s', async listo => {
    carga.mockReturnValue(of({ escenarios: [], listo_para_enviar: listo, respondidas: 1, total_preguntas: 2 }));
    enviar.mockReturnValue(of(resultado));
    confirmar.mockResolvedValue(true);
    await pantalla.cargarEstado();
    await pantalla.entregarSimulacion();
    expect(confirmar).toHaveBeenCalledWith(expect.objectContaining({ tono: listo ? 'green' : 'amber' }));
    expect(enviar).toHaveBeenCalledWith(42, !listo);
    expect(pantalla.resultado()).toEqual(resultado);
    expect(pantalla.workspace()).toBeNull();
  });

  it.each([true, false])('conserva el intento al cancelar con listo_para_enviar=%s', async listo => {
    const estado = { escenarios: [], listo_para_enviar: listo };
    carga.mockReturnValue(of(estado));
    confirmar.mockResolvedValue(false);
    await pantalla.cargarEstado();
    await pantalla.entregarSimulacion();
    expect(enviar).not.toHaveBeenCalled();
    expect(pantalla.workspace()).toEqual(estado);
    expect(pantalla.guardando()).toBe(false);
  });

  it('recupera el resultado cuando el intento se cierra antes de confirmar', async () => {
    carga.mockReturnValueOnce(of({ escenarios: [] })).mockReturnValueOnce(of({ cerrado: true, resultado }));
    await pantalla.cargarEstado();
    await pantalla.entregarSimulacion();
    expect(confirmar).not.toHaveBeenCalled();
    expect(enviar).not.toHaveBeenCalled();
    expect(pantalla.resultado()).toEqual(resultado);
  });

  it('permite reintentar una carga fallida y muestra el resultado existente', async () => {
    carga.mockReturnValueOnce(throwError(() => new Error('sin red')))
      .mockReturnValueOnce(of({ cerrado: true, resultado }));
    await pantalla.cargarEstado();
    expect(aviso).toHaveBeenCalled();
    expect(pantalla.cargando()).toBe(false);
    await pantalla.cargarEstado();
    expect(pantalla.resultado()).toEqual(resultado);
    await pantalla.entregarSimulacion();
    expect(enviar).not.toHaveBeenCalled();
  });
});
