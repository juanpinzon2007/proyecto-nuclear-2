import { HttpErrorResponse, provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { AuthService } from './auth.service';

const navegar = vi.fn();
const correo = 'persona@example.test';
const ruta = '/api/v1/identity/';
const token = 'prueba.' + btoa(JSON.stringify({exp: 4102444800, convocatoria_id: 'c1'})) + '.prueba';
let http: HttpTestingController;
beforeEach(() => {
  sessionStorage.removeItem('sps.token');
  navegar.mockClear();
  TestBed.configureTestingModule({providers: [provideHttpClient(), provideHttpClientTesting(),
    {provide: Router, useValue: { navigateByUrl: navegar }}]});
  http = TestBed.inject(HttpTestingController);
});
afterEach(() => {
  http.verify();
  sessionStorage.removeItem('sps.token');
});

it.each([null, 'malformado', 'x.' + btoa('{"exp":1}') + '.x'])('limpia la sesión no vigente %s', async t => {
  if (t) sessionStorage.setItem('sps.token', t);
  const auth = TestBed.inject(AuthService);
  expect(auth.tokenVigente()).toBe(false);
  expect(await auth.asegurarPerfil()).toBeNull();
  expect(auth.convocatoriaId()).toBeNull();
  expect(auth.rutaInicio()).toBe('/login');
  expect(auth.tienePermiso('CREAR_CASOS')).toBe(false);
  expect(sessionStorage.getItem('sps.token')).toBeNull();
});

it.each([['ADMINISTRADOR','/administracion/docentes'], ['DOCENTE','/casos'], ['ESTUDIANTE','/estudiante']])(
  'recupera el perfil %s una sola vez y cierra su sesión', async (rol, inicio) => {
    sessionStorage.setItem('sps.token', token);
    const auth = TestBed.inject(AuthService);
    const perfil = {correo, roles:[rol], permisos:['CREAR_CASOS']};
    expect(auth.convocatoriaId()).toBe('c1');
    const primera = auth.asegurarPerfil();
    expect(auth.asegurarPerfil()).toBe(primera);
    http.expectOne(ruta + 'me').flush(perfil);
    expect(await primera).toEqual(perfil);
    expect(await auth.asegurarPerfil()).toEqual(perfil);
    expect(auth.tienePermiso('CREAR_CASOS')).toBe(true);
    expect(auth.rutaInicio()).toBe(inicio);
    auth.logout();
    expect(auth.usuario()).toBeNull();
    expect(navegar).toHaveBeenCalledWith('/login');
});

it('descarta un token cuyo perfil es rechazado', async () => {
  sessionStorage.setItem('sps.token', token);
  const auth = TestBed.inject(AuthService);
  const perfil = auth.asegurarPerfil();
  http.expectOne(ruta + 'me').flush({}, {status:401,statusText:'Unauthorized'});
  expect(await perfil).toBeNull();
  expect(auth.token()).toBeNull();
});

it.each(['personal','estudiantes','estudiantes/verificar-primer-ingreso'])('establece la sesión por %s', async endpoint => {
  const auth=TestBed.inject(AuthService);
  const clave='clave-laboratorio';
  const acceso = endpoint==='personal' ? auth.loginPersonal(correo,clave)
    : endpoint==='estudiantes' ? auth.loginEstudiante(correo,clave) : auth.verificarPrimerIngreso(correo,clave);
  const req=http.expectOne({method:'POST',url:ruta+'auth/'+endpoint});
  const campo=endpoint==='personal' ? 'clave' : endpoint==='estudiantes' ? 'codigo_convocatoria' : 'codigo';
  expect(req.request.body).toEqual({correo,[campo]:clave});
  req.flush({access_token:token});
  await Promise.resolve();
  http.expectOne(ruta+'me').flush({correo});
  expect(await acceso).toEqual({correo});
  expect(sessionStorage.getItem('sps.token')).toBe(token);
});

it('solicita y confirma recuperación de contraseña mediante el código recibido', async () => {
  const auth=TestBed.inject(AuthService);
  const solicitud=auth.solicitarRecuperacionContrasena(correo);
  const req=http.expectOne({method:'POST',url:ruta+'auth/recuperar-contrasena/solicitar'});
  expect(req.request.body).toEqual({correo});
  req.flush({mensaje:'recibida'});
  expect(await solicitud).toEqual({mensaje:'recibida'});
  const confirmacion=auth.confirmarRecuperacionContrasena(correo,'123456','nueva');
  const cambio=http.expectOne({method:'POST',url:ruta+'auth/recuperar-contrasena/confirmar'});
  expect(cambio.request.body).toEqual({correo,codigo:'123456',nueva_clave:'nueva'});
  cambio.flush({mensaje:'actualizada'});
  expect(await confirmacion).toEqual({mensaje:'actualizada'});
});

it.each([true,false])('devuelve el desafío de primer ingreso con datos opcionales %s', async completos => {
  const auth=TestBed.inject(AuthService);
  const acceso=auth.loginUnificado(correo,'credencial');
  http.expectOne(ruta+'auth/personal').flush({}, {status:401,statusText:'Unauthorized'});
  await new Promise<void>(resolve => queueMicrotask(resolve));
  const req=http.expectOne(ruta+'auth/estudiantes/acceso');
  expect(req.request.body).toEqual({correo,clave:'credencial'});
  req.flush(completos ? {requiere_verificacion:true, correo:'otp@example.test', mensaje:'Verifica', expira_en_segundos:60}
    : {requiere_verificacion:true});
  const resultado=await acceso;
  expect(resultado.estado).toBe('VERIFICACION_REQUERIDA');
  if (resultado.estado==='VERIFICACION_REQUERIDA') {
    expect(resultado.correo).toBe(completos ? 'otp@example.test' : correo);
    expect(resultado.expiraEnSegundos).toBe(completos ? 60 : 900);
    expect(resultado.mensaje).toContain(completos ? 'Verifica' : 'correo');
  }
});


it('acepta la cuenta de personal en el primer paso del acceso unificado', async () => {
  const auth=TestBed.inject(AuthService);
  const perfil={correo,id_usuario:'7',roles:[],permisos:[]};
  vi.spyOn(auth,'loginPersonal').mockResolvedValue(perfil);
  expect(await auth.loginUnificado(correo,'clave')).toEqual({estado:'AUTENTICADO',usuario:perfil});
});

it('carga el perfil cuando el acceso por clave del estudiante emite un token', async () => {
  const auth=TestBed.inject(AuthService);
  vi.spyOn(auth,'loginPersonal').mockRejectedValue(new Error('Sin sesión de personal'));
  vi.spyOn(auth,'loginEstudiantePorClave').mockResolvedValue({requiere_verificacion:false,access_token:token});
  const acceso=auth.loginUnificado(correo,'clave');
  await new Promise<void>(resolve => setTimeout(resolve,0));
  http.expectOne(ruta+'me').flush({correo});
  expect(await acceso).toEqual({estado:'AUTENTICADO',usuario:{correo}});
});

it.each(['sin token','rechazo','error de transporte'])('intenta el código de convocatoria después de %s', async modo => {
  const auth=TestBed.inject(AuthService);
  vi.spyOn(auth,'loginPersonal').mockRejectedValue(new Error());
  const porClave=vi.spyOn(auth,'loginEstudiantePorClave');
  if (modo==='sin token') porClave.mockResolvedValue({requiere_verificacion:false});
  else porClave.mockRejectedValue(modo==='rechazo' ? new HttpErrorResponse({status:401}) : new Error());
  const porCodigo=vi.spyOn(auth,'loginEstudiante').mockResolvedValue(null);
  expect(await auth.loginUnificado(correo,'123456')).toEqual({estado:'AUTENTICADO',usuario:null});
  expect(porCodigo).toHaveBeenCalledWith(correo,'123456');
});

it.each(['personal','estudiante'])('propaga el fallo del servidor de %s', async origen => {
  const auth=TestBed.inject(AuthService);
  const fallo=new HttpErrorResponse({status:503});
  vi.spyOn(auth,'loginPersonal').mockRejectedValue(origen==='personal' ? fallo : new HttpErrorResponse({status:401}));
  vi.spyOn(auth,'loginEstudiantePorClave').mockRejectedValue(fallo);
  await expect(auth.loginUnificado(correo,'clave')).rejects.toBe(fallo);
});

