import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { firstValueFrom, Observable } from 'rxjs';
import { beforeEach, afterEach, expect, it } from 'vitest';
import { IdentityService } from './identity.service';
import { CrearUsuarioAdminSolicitud } from './api.models';

let api: IdentityService;
let http: HttpTestingController;
const base='/api/v1/identity/';
beforeEach(() => {
  TestBed.configureTestingModule({providers:[provideHttpClient(),provideHttpClientTesting()]});
  api=TestBed.inject(IdentityService);
  http=TestBed.inject(HttpTestingController);
});
afterEach(() => http.verify());

const docente={correo:'docente@example.test'};
const usuario: CrearUsuarioAdminSolicitud={nombre:'Alumno',correo:'alumno@example.test',rol:'ESTUDIANTE'};
const permiso={permisos:['CREAR_CASOS']};
const repeticion={id_sesion:'s1',id_estudiante:'e1'};
const consentimiento={id_version_documento:3,referencia:'doc',huella:'abc',acepta:true};
const id='uno/dos';
const operaciones: [string,string,unknown,()=>Observable<unknown>][]=[
  ['GET','docentes?limite=50&desplazamiento=0',null,()=>api.listarDocentes()],
  ['GET','docentes?limite=2&desplazamiento=4',null,()=>api.listarDocentes(2,4)],
  ['POST','docentes',docente,()=>api.crearDocente(docente)],
  ['PUT','docentes/uno%2Fdos/autorizaciones',permiso,()=>api.actualizarAutorizaciones(id,permiso)],
  ['GET','roles/docente/permisos',null,()=>api.permisosRolDocente()],
  ['PUT','roles/docente/permisos',permiso,()=>api.actualizarPermisosRolDocente(permiso.permisos)],
  ['GET','usuarios',null,()=>api.listarUsuarios()],
  ['GET','usuarios/pagina?pagina=2&tamano=4&buscar=Ana',null,()=>api.paginarUsuarios(2,4,'Ana')],
  ['POST','usuarios',usuario,()=>api.crearUsuario(usuario)],
  ['PATCH','usuarios/uno%2Fdos',{activo:false},()=>api.actualizarUsuario(id,{activo:false})],
  ['POST','usuarios/uno%2Fdos/identidades-academicas',{},()=>api.asegurarIdentidades(id)],
  ['POST','excepciones/repeticiones',repeticion,()=>api.autorizarRepeticion(repeticion)],
  ['GET','convocatorias/c/asignaciones/4/consentimiento',null,()=>api.documentoConsentimiento('c',4)],
  ['GET','convocatorias/c/asignaciones/4/consentimiento/aceptacion',null,()=>api.consultarAceptacion('c',4)],
  ['POST','convocatorias/c/asignaciones/4/consentimiento/aceptacion',consentimiento,()=>api.aceptarConsentimiento('c',4,consentimiento)],
  ['GET','seguimiento/casos',null,()=>api.casosSeguimiento()],
  ['GET','seguimiento/casos/uno%2Fdos/participaciones',null,()=>api.participacionesCaso(id)],
  ['GET','seguimiento/participaciones/uno%2Fdos',null,()=>api.detalleParticipacion(id)],
  ['GET','seguimiento/participaciones/uno%2Fdos/feedback',null,()=>api.feedback(id)],
  ['POST','seguimiento/participaciones/uno%2Fdos/feedback',{texto:'Bien argumentado'},()=>api.enviarFeedback(id,'Bien argumentado')],
];
it.each(operaciones)('%s %s conserva el cuerpo y entrega la respuesta', async (method,ruta,body,enviar) => {
  const respuesta=firstValueFrom(enviar());
  const req=http.expectOne({method,url:base+ruta});
  expect(req.request.body).toEqual(body);
  req.flush({ok:true});
  expect(await respuesta).toEqual({ok:true});
});

it('exporta el reporte con un filtro por estudiante y omite los filtros vacíos', async () => {
  const filtros={formato:'pdf' as const,id_estudiante:[7,9],id_grupo:null,version_publicacion:undefined};
  const respuesta=firstValueFrom(api.reporteSesion(id,filtros));
  const req=http.expectOne(r=>r.url===base+'seguimiento/sesiones/uno%2Fdos/reporte');
  expect(req.request.params.keys().sort()).toEqual(['formato','id_estudiante']);
  expect(req.request.params.getAll('id_estudiante')).toEqual(['7','9']);
  expect(req.request.responseType).toBe('blob');
  const pdf=new Blob(['%PDF'],{type:'application/pdf'});
  req.flush(pdf);
  expect(await respuesta).toBe(pdf);
});

it('solicita el archivo provisional de la sesión en el formato elegido', async () => {
  const respuesta=firstValueFrom(api.reporteProvisionalSesion(id,'xlsx'));
  const req=http.expectOne({method:'GET',url:base+'seguimiento/sesiones/uno%2Fdos/reporte-provisional?formato=xlsx'});
  expect(req.request.responseType).toBe('blob');
  const archivo=new Blob(['xlsx']);
  req.flush(archivo);
  expect(await respuesta).toBe(archivo);
});
