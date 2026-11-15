import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';
import { AuthService } from './auth.service';

/** Añade `Authorization: Bearer` a las llamadas al backend y cierra sesión ante un 401. */
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);
  const esApi = req.url.startsWith('/api/') || req.url.startsWith('/scheduling');
  const esLogin = req.url.includes('/identity/auth/');
  const token = auth.token();
  const peticion = esApi && token && !esLogin
    ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } })
    : req;
  return next(peticion).pipe(
    catchError((err: unknown) => {
      if (err instanceof HttpErrorResponse && err.status === 401 && esApi && !esLogin && token) {
        auth.logout();
      }
      return throwError(() => err);
    }),
  );
};

