import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { firstValueFrom, Observable, of } from 'rxjs';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { CasesService } from './cases.service';
import { CasoDetalleResponse, GrafoResponse, VersionResponse } from './api.models';

let api: CasesService;
let http: HttpTestingController;
beforeEach(() => {
  TestBed.configureTestingModule({providers:[provideHttpClient(),provideHttpClientTesting()]});
  api=TestBed.inject(CasesService);
  http=TestBed.inject(HttpTestingController);
});
afterEach(() => http.verify());

function caso(): CasoDetalleResponse {
  return { id:'v', caso_id:'c', numero:1, nombre:'Asch', desarrollo_situacional:'grupo', contexto_historia:'aula',
    tiempo_estimado_min:20, estado:'BORRADOR', escenarios:['e1','e2'].map((id,i)=>({
      id,orden:i+1,contexto_situacional:'aula',preguntas:[{id:id+'p',orden:1,enunciado:'¿Qué eliges?',
        opciones:[true,false].map((correcta,j)=>({id:id+j,orden:j+1,texto:'opción '+j,es_correcta:correcta,
          justificacion:'Se explica la consecuencia',valoraciones:{}}))}]})),
    rubrica:{id:'r',nombre:'Análisis',version_regla:'v1',criterios:[{id:'cr',nombre:'Decisión',peso:'100',
      niveles:[{id:'n',nombre:'Alto',puntaje:'100',descriptor:'Argumenta'}]}]} };
}

const cuerpo={case:{nombre:'Asch',desarrolloSituacional:'grupo',contextoHistoria:'aula',tiempoEstimadoMin:20}};
const grafo={escenario_inicial_id:'e1',transiciones:[]};
const peticiones: [string,string,unknown,()=>Observable<unknown>][]=[
  ['GET','',null,()=>api.listar()],['GET','/v',null,()=>api.obtener('v')],
  ['POST','',cuerpo,()=>api.crear(cuerpo)],['DELETE','/v',null,()=>api.eliminarBorrador('v')],
  ['PUT','/v',cuerpo,()=>api.actualizar('v',cuerpo)],['POST','/v/publish',{},()=>api.publicar('v')],
  ['POST','/v/archive',{},()=>api.archivar('v')],['POST','/v/republish',{},()=>api.republicar('v')],
  ['POST','/v/clone',{},()=>api.clonar('v')],['GET','/v/graph',null,()=>api.grafo('v')],
  ['PUT','/v/graph',grafo,()=>api.guardarGrafo('v',grafo)],
];
it.each(peticiones)('%s /cases%s usa el contrato del backend', async(method,ruta,body,fn)=>{
  const resp=firstValueFrom(fn());
  const req=http.expectOne({method,url:'/api/v1/cases'+ruta});
  expect(req.request.body).toEqual(body);
  req.flush(null);
  expect(await resp).toBeNull();
});

it('conecta todas las opciones al escenario siguiente y cierra el recorrido',()=>{
  const detalle=caso();
  expect(api.erroresPublicacion(detalle)).toEqual([]);
  expect(api.construirGrafoLineal(detalle)).toEqual({escenario_inicial_id:'e1',transiciones:[
    {opcion_id:'e10',tipo:'ESCENA',destino_id:'e2'},{opcion_id:'e11',tipo:'ESCENA',destino_id:'e2'},
    {opcion_id:'e20',tipo:'FIN',destino_id:null},{opcion_id:'e21',tipo:'FIN',destino_id:null},
  ]});
});

it('detecta datos básicos ausentes y descarta un recorrido sin escenarios',()=>{
  const detalle={...caso(),nombre:' ',tiempo_estimado_min:0,escenarios:[],rubrica:null};
  expect(api.erroresPublicacion(detalle)).toHaveLength(4);
  expect(api.construirGrafoLineal(detalle)).toBeNull();
});

it('localiza preguntas, opciones y criterios incompletos',()=>{
  const detalle=caso();
  const pregunta=detalle.escenarios[1].preguntas[0];
  detalle.escenarios[0].preguntas=[];
  pregunta.opciones=pregunta.opciones.slice(0,1);
  pregunta.opciones[0].justificacion=' ';
  detalle.escenarios[1].preguntas.push({...pregunta,orden:2,opciones:[{...pregunta.opciones[0],es_correcta:false}]});
  const criterio=detalle.rubrica!.criterios[0];
  criterio.peso='42'; criterio.niveles=[];
  const errores=api.erroresPublicacion(detalle).join('\n');
  for(const frase of ['no tiene preguntas','exactamente 1','al menos 2','una opción correcta','una opción incorrecta',
    'falta justificación','42%','no tiene niveles']) expect(errores).toContain(frase);
  expect(api.construirGrafoLineal(detalle)).toBeNull();
  detalle.rubrica!.criterios=[];
  expect(api.erroresPublicacion(detalle)).toContain('La rúbrica no tiene criterios.');
});

it.each(['completo','sin inicio','sin transición','inválido'])('publica el borrador con grafo %s',async modo=>{
  const detalle=caso();
  if(modo==='inválido') detalle.nombre='';
  const existente:GrafoResponse={version_id:'v',escenas:[{id:'e1',contexto:'aula',inicial:modo!=='sin inicio',
    preguntas:[{id:'p',enunciado:'?',opciones:[{opcion_id:'o',tipo:modo==='sin transición'?null:'FIN',destino_id:null,texto:'fin'}]}]}]};
  const publicada:VersionResponse={caso_id:'c',version_id:'v',estado:'PUBLICADO'};
  vi.spyOn(api,'obtener').mockReturnValue(of(detalle));
  const leer=vi.spyOn(api,'grafo').mockReturnValue(of(existente));
  const guardar=vi.spyOn(api,'guardarGrafo').mockReturnValue(of(existente));
  const publicar=vi.spyOn(api,'publicar').mockReturnValue(of(publicada));
  expect(await api.publicarInteligente('v')).toEqual(publicada);
  expect(leer).toHaveBeenCalledTimes(modo==='inválido'?0:1);
  if(modo==='sin inicio'||modo==='sin transición'){
    expect(guardar).toHaveBeenCalledWith('v',api.construirGrafoLineal(detalle));
  }else expect(guardar).not.toHaveBeenCalled();
  expect(publicar).toHaveBeenCalledWith('v');
});
