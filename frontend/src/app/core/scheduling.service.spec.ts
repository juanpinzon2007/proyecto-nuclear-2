import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { firstValueFrom, Observable } from 'rxjs';
import { afterEach, beforeEach, expect, it } from 'vitest';
import { SchedulingService } from './scheduling.service';

let api: SchedulingService;
let http: HttpTestingController;
beforeEach(() => {
  TestBed.configureTestingModule({providers:[provideHttpClient(),provideHttpClientTesting()]});
  api=TestBed.inject(SchedulingService);
  http=TestBed.inject(HttpTestingController);
});
afterEach(()=>http.verify());

const sesion={espacio_academico_id:'a',version_caso_id:'v',fecha_inicio:'2026-11-27T13:00:00Z',
  fecha_fin:'2026-11-27T14:00:00Z',tiempo_maximo_minutos:30};
const grupo={nombre:'Laboratorio',periodo:'2026-2'};
const evaluacion='sesiones/s/evaluacion/';
const solicitudes: [string,string,unknown,()=>Observable<unknown>][]=[
  ['GET','espacios',null,()=>api.espacios()],
  ['POST','espacios',{nombre:'Social'},()=>api.crearEspacio('Social')],
  ['GET','sesiones',null,()=>api.sesiones()],
  ['GET','sesiones?docente_id=d&espacio_id=a',null,()=>api.sesiones({docente_id:'d',espacio_id:'a'})],
  ['GET','sesiones/s',null,()=>api.sesion('s')],
  ['POST','sesiones',sesion,()=>api.programar(sesion)],
  ['POST','sesiones/s/estado',{accion:'finalizar'},()=>api.cambiarEstado('s','finalizar')],
  ['GET','sesiones/s/convocatorias',null,()=>api.convocatorias('s')],
  ['POST','sesiones/s/convocatorias',{estudiante_id:'e'},()=>api.crearConvocatoria('s','e')],
  ['DELETE','sesiones/s/convocatorias/c',null,()=>api.retirarConvocatoria('s','c')],
  ['GET','convocatorias/c/admision',null,()=>api.admision('c')],
  ['POST','convocatorias/c/espera',{codigo_acceso:'012345'},()=>api.solicitarEspera('c','012345')],
  ['POST','validar-ingreso',{convocatoria_id:'c',estudiante_id:'e',codigo_acceso:'012345'},()=>api.validarIngreso('c','e','012345')],
  ['GET','notificaciones?destinatario_id=e',null,()=>api.notificaciones('e')],
  ['GET',evaluacion+'preparacion',null,()=>api.preparacion('s')],
  ['GET',evaluacion+'intentos/4/resultado-tecnico',null,()=>api.resultadoTecnico('s',4)],
  ['POST',evaluacion+'intentos/4/resultado-tecnico',{},()=>api.calcularResultadoTecnico('s',4)],
  ['GET',evaluacion+'consolidacion',null,()=>api.consolidacion('s')],
  ['POST',evaluacion+'convocatorias/c/ausencia',{motivo:'Sin ingreso'},()=>api.registrarAusencia('s','c','Sin ingreso')],
  ['POST',evaluacion+'convocatorias/c/ausencia/rectificacion',{motivo:'Corrección',id_confirmacion:'r'},()=>api.rectificarAusencia('s','c','Corrección','r')],
  ['GET',evaluacion+'publicaciones',null,()=>api.publicaciones('s')],
  ['POST',evaluacion+'publicaciones',{revision_sha256:'sha'},()=>api.publicar('s','sha')],
  ['PUT',evaluacion+'visibilidad',{mostrar_provisional:false},()=>api.visibilidad('s',false)],
  ['POST','calificaciones/notificar',{estudiante_id:'e',participacion_id:'p'},()=>api.notificarCalificacion('e','p')],
  ['GET','espacios/todos',null,()=>api.todosEspacios()],
  ['POST','espacios/a/autorizar',{},()=>api.autorizarEspacio('a')],
  ['POST','espacios/a/autorizar',{id_docente:3},()=>api.autorizarEspacio('a',3)],
  ['GET','docentes',null,()=>api.docentes()],
  ['GET','estudiantes',null,()=>api.estudiantes()],
  ['GET','grupos',null,()=>api.grupos()],
  ['POST','grupos',grupo,()=>api.crearGrupo(grupo.nombre,grupo.periodo)],
  ['POST','grupos',{...grupo,id_profesor:3},()=>api.crearGrupo(grupo.nombre,grupo.periodo,3)],
  ['POST','grupos/2/estudiantes',{id_usuario:7},()=>api.matricularEstudiante(2,7)],
  ['DELETE','grupos/2/estudiantes/7',null,()=>api.retirarEstudiante(2,7)],
  ['PATCH','sesiones/s',{lugar:'Aula 3'},()=>api.actualizarSesion('s',{lugar:'Aula 3'})],
  ['GET','mis-convocatorias',null,()=>api.misConvocatorias()],
  ['GET','convocatorias/c/resultado',null,()=>api.resultadoEstudiante('c')],
];
it.each(solicitudes)('%s /scheduling/%s envía los parámetros solicitados', async(method,ruta,cuerpo,enviar)=>{
  const respuesta=firstValueFrom(enviar());
  const req=http.expectOne({method,url:'/scheduling/'+ruta});
  expect(req.request.body).toEqual(cuerpo);
  req.flush({id:'prueba'});
  expect(await respuesta).toEqual({id:'prueba'});
});
