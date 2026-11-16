import { Routes } from '@angular/router';
import { authGuard, inicioGuard, invitadoGuard, permisoGuard, rolGuard } from './core/auth.guards';
import { ShellComponent } from './layout/shell.component';

export const routes: Routes = [
  {
    path: 'login',
    loadComponent: () => import('./pages/login/login.component').then((m) => m.LoginComponent),
    canActivate: [invitadoGuard],
  },
  {
    path: 'sin-permiso',
    loadComponent: () => import('./pages/forbidden/forbidden.component').then((m) => m.ForbiddenComponent),
  },
  {
    path: '',
    component: ShellComponent,
    canActivate: [authGuard],
    children: [
      // Casos (Exclusivo DOCENTE; autoría protegida con permiso CREAR_CASOS RF-02)
      {
        path: 'casos',
        loadComponent: () => import('./pages/casos/casos-lista.component').then((m) => m.CasosListaComponent),
        canActivate: [rolGuard('DOCENTE')],
      },
      {
        path: 'casos/nuevo',
        loadComponent: () => import('./pages/casos/caso-editor.component').then((m) => m.CasoEditorComponent),
        canActivate: [rolGuard('DOCENTE'), permisoGuard('CREAR_CASOS')],
      },
      {
        path: 'casos/:id/editar',
        loadComponent: () => import('./pages/casos/caso-editor.component').then((m) => m.CasoEditorComponent),
        canActivate: [rolGuard('DOCENTE'), permisoGuard('CREAR_CASOS')],
      },
      {
        path: 'casos/:id',
        loadComponent: () => import('./pages/casos/caso-detalle.component').then((m) => m.CasoDetalleComponent),
        canActivate: [rolGuard('DOCENTE')],
      },
      {
        path: 'casos/:id/grafo',
        loadComponent: () => import('./pages/casos/caso-grafo.component').then((m) => m.CasoGrafoComponent),
        canActivate: [rolGuard('DOCENTE')],
      },

      // Programación & Evaluación (Exclusivo DOCENTE)
      {
        path: 'programacion',
        loadComponent: () => import('./pages/programacion/programacion.component').then((m) => m.ProgramacionComponent),
        canActivate: [rolGuard('DOCENTE')],
      },
      {
        path: 'programacion/:id/convocatorias',
        loadComponent: () => import('./pages/programacion/convocatorias.component').then((m) => m.ConvocatoriasComponent),
        canActivate: [rolGuard('DOCENTE')],
      },
      {
        path: 'programacion/:id/evaluacion',
        loadComponent: () => import('./pages/programacion/evaluacion-sesion.component').then((m) => m.EvaluacionSesionComponent),
        canActivate: [rolGuard('DOCENTE')],
      },

      // Seguimiento Docente (Exclusivo DOCENTE)
      {
        path: 'seguimiento',
        loadComponent: () => import('./pages/seguimiento/seguimiento.component').then((m) => m.SeguimientoComponent),
        canActivate: [rolGuard('DOCENTE')],
      },
      {
        path: 'seguimiento/participaciones/:id',
        loadComponent: () => import('./pages/seguimiento/participacion-detalle.component').then((m) => m.ParticipacionDetalleComponent),
        canActivate: [rolGuard('DOCENTE')],
      },

      // Administración (Exclusivo ADMINISTRADOR)
      {
        path: 'administracion/docentes',
        loadComponent: () => import('./pages/administracion/docentes.component').then((m) => m.DocentesComponent),
        canActivate: [rolGuard('ADMINISTRADOR')],
      },

      // Portal Estudiante y Simulador (Exclusivo ESTUDIANTE)
      {
        path: 'estudiante',
        loadComponent: () => import('./pages/estudiante/estudiante-portal.component').then((m) => m.EstudiantePortalComponent),
        canActivate: [rolGuard('ESTUDIANTE')],
      },
      {
        path: 'estudiante/simulador/:id',
        loadComponent: () => import('./pages/estudiante/simulador.component').then((m) => m.SimuladorComponent),
        canActivate: [rolGuard('ESTUDIANTE')],
      },

      {
        path: '',
        pathMatch: 'full',
        canActivate: [inicioGuard],
        children: [],
      },
    ],
  },
  {
    path: '**',
    redirectTo: '',
  },
];
