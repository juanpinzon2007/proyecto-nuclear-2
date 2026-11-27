import { TestBed } from '@angular/core/testing';
import { MAT_DIALOG_DATA, MatDialog, MatDialogRef } from '@angular/material/dialog';
import { of } from 'rxjs';
import { expect, it, vi } from 'vitest';
import { NeuroDialogComponent, NeuroDialogData, UiDialogService } from './ui-dialog.service';

const basico={titulo:'Publicar resultado',mensaje:'¿Confirmas la publicación?'};
const opciones={...basico,tono:'warn' as const,eyebrow:'Revisión',botonConfirmar:'Aceptar',botonCancelar:'Volver'};

function servicioConRespuesta(respuesta:unknown) {
  const abrir=vi.fn().mockReturnValue({afterClosed:()=>of(respuesta)});
  TestBed.configureTestingModule({providers:[{provide:MatDialog,useValue:{open:abrir}}]});
  return {servicio:TestBed.inject(UiDialogService),abrir};
}

it.each([true,false])('devuelve la confirmación %s y configura los botones',async confirma=>{
  const {servicio,abrir}=servicioConRespuesta(confirma);
  expect(await servicio.confirmar(confirma?opciones:basico)).toBe(confirma);
  expect(abrir).toHaveBeenCalledWith(NeuroDialogComponent,expect.objectContaining({
    ariaLabel:basico.titulo,data:{...basico,modo:'confirm',tono:confirma?'warn':'cyan',
      eyebrow:confirma?'Revisión':'Confirmación',botonConfirmar:confirma?'Aceptar':'Confirmar',botonCancelar:confirma?'Volver':'Cancelar'},
  }));
});

it.each([['  motivo  ','motivo'],['   ',null],[undefined,null]])('normaliza la respuesta de texto %s',async (entrada,esperado)=>{
  const {servicio,abrir}=servicioConRespuesta(entrada);
  const personalizar=esperado!==null;
  expect(await servicio.solicitarTexto(personalizar?{...opciones,etiquetaCampo:'Razón',placeholder:'Detalle'}:basico)).toBe(esperado);
  expect(abrir.mock.calls[0][1].data).toEqual({...basico,modo:'prompt',tono:personalizar?'warn':'amber',
    eyebrow:personalizar?'Revisión':'Registro Académico',etiquetaCampo:personalizar?'Razón':'Motivo académico',
    placeholder:personalizar?'Detalle':'Describe brevemente el motivo...',botonConfirmar:personalizar?'Aceptar':'Registrar',
    botonCancelar:personalizar?'Volver':'Cancelar'});
});

const tonos: [NeuroDialogData['tono'],string][]=[['cyan','verified_user'],['amber','help_outline'],['green','task_alt'],['warn','warning_amber']];
it.each(tonos)('muestra el icono del tono %s y valida la respuesta', (tono,icono)=>{
  const modo=tono==='cyan'?'confirm':'prompt';
  const cerrar=vi.fn();
  TestBed.configureTestingModule({providers:[{provide:MAT_DIALOG_DATA,useValue:{...opciones,modo,tono}},
    {provide:MatDialogRef,useValue:{close:cerrar}}]});
  const componente=TestBed.runInInjectionContext(()=>new NeuroDialogComponent());
  expect(componente.iconoPorTono()).toBe(icono);
  componente.cancelar();
  expect(cerrar).toHaveBeenCalledWith(modo==='confirm'?false:null);
  cerrar.mockClear();
  componente.aceptar();
  if(modo==='confirm') expect(cerrar).toHaveBeenCalledWith(true);
  else {
    expect(cerrar).not.toHaveBeenCalled();
    expect(componente.errorRequerido).toBe(true);
    componente.texto='  motivo  ';
    componente.aceptar();
    expect(cerrar).toHaveBeenCalledWith('motivo');
  }
});

it.each(['confirm','prompt','prompt personalizado'])('permite operar el diálogo visible %s',async variante=>{
  const prompt=variante!=='confirm';
  const personalizado=variante==='prompt personalizado';
  const cerrar=vi.fn();
  TestBed.configureTestingModule({imports:[NeuroDialogComponent],providers:[
    {provide:MAT_DIALOG_DATA,useValue:{...opciones,modo:prompt?'prompt':'confirm',tono:prompt?'warn':'cyan',
      etiquetaCampo:personalizado?'Detalle':undefined,placeholder:personalizado?'Indica el motivo':undefined}},
    {provide:MatDialogRef,useValue:{close:cerrar}},
  ]});
  const fixture=TestBed.createComponent(NeuroDialogComponent);
  fixture.detectChanges();
  await fixture.whenStable();
  const elemento:HTMLElement=fixture.nativeElement;
  expect(elemento.querySelector('h2')?.textContent).toContain(basico.titulo);
  const [cancelar,aceptar]=Array.from(elemento.querySelectorAll('button'));
  cancelar.click();
  expect(cerrar).toHaveBeenCalledWith(prompt?null:false);
  cerrar.mockClear();
  aceptar.click();
  fixture.detectChanges();
  const campo=elemento.querySelector('textarea');
  if(prompt){
    expect(elemento.querySelector('.nd-err')?.textContent).toContain('Debes ingresar un texto');
    expect(campo?.placeholder).toBe(personalizado?'Indica el motivo':'Escribe aquí...');
    campo!.value=' justificación ';
    campo!.dispatchEvent(new Event('input'));
    campo!.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',ctrlKey:true,bubbles:true}));
    expect(cerrar).toHaveBeenCalledWith('justificación');
  }else{
    expect(campo).toBeNull();
    expect(cerrar).toHaveBeenCalledWith(true);
  }
});
