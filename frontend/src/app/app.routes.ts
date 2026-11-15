import { Routes } from '@angular/router';
import { authGuard, invitadoGuard, rolGuard } from './core/auth.guards';
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
      // Casos
      {
        path: 'casos',
        loadComponent: () => import('./pages/casos/casos-lista.component').then((m) => m.CasosListaComponent),
        canActivate: [rolGuard('DOCENTE', 'ADMINISTRADOR')],
      },
      {
        path: 'casos/:id',
        loadComponent: () => import('./pages/casos/caso-detalle.component').then((m) => m.CasoDetalleComponent),
        canActivate: [rolGuard('DOCENTE', 'ADMINISTRADOR')],
      },
      {
        path: 'casos/:id/grafo',
        loadComponent: () => import('./pages/casos/caso-grafo.component').then((m) => m.CasoGrafoComponent),
        canActivate: [rolGuard('DOCENTE', 'ADMINISTRADOR')],
      },

      // Programación & Evaluación
      {
        path: 'programacion',
        loadComponent: () => import('./pages/programacion/programacion.component').then((m) => m.ProgramacionComponent),
        canActivate: [rolGuard('DOCENTE', 'ADMINISTRADOR')],
      },
      {
        path: 'programacion/:id/convocatorias',
        loadComponent: () => import('./pages/programacion/convocatorias.component').then((m) => m.ConvocatoriasComponent),
        canActivate: [rolGuard('DOCENTE', 'ADMINISTRADOR')],
      },
      {
        path: 'programacion/:id/evaluacion',
        loadComponent: () => import('./pages/programacion/evaluacion-sesion.component').then((m) => m.EvaluacionSesionComponent),
        canActivate: [rolGuard('DOCENTE', 'ADMINISTRADOR')],
      },

      // Seguimiento Docente
      {
        path: 'seguimiento',
        loadComponent: () => import('./pages/seguimiento/seguimiento.component').then((m) => m.SeguimientoComponent),
        canActivate: [rolGuard('DOCENTE', 'ADMINISTRADOR')],
      },
      {
        path: 'seguimiento/participaciones/:id',
        loadComponent: () => import('./pages/seguimiento/participacion-detalle.component').then((m) => m.ParticipacionDetalleComponent),
        canActivate: [rolGuard('DOCENTE', 'ADMINISTRADOR')],
      },

      // Administración
      {
        path: 'administracion/docentes',
        loadComponent: () => import('./pages/administracion/docentes.component').then((m) => m.DocentesComponent),
        canActivate: [rolGuard('ADMINISTRADOR')],
      },

      // Portal Estudiante y Simulador
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
        redirectTo: 'casos',
      },
    ],
  },
  {
    path: '**',
    redirectTo: '',
  },
];
