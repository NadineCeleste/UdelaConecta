import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';
import { AuthService } from '../AuthService';
import { environment } from '../../environments/environment';

// Adjunta el token JWT a las llamadas a la API y cierra la sesión si el backend responde 401
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const authService = inject(AuthService);
  const router = inject(Router);
  const esApi = req.url.startsWith(environment.apiUrl);
  const token = esApi ? authService.getToken() : null;

  const authReq = token
    ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } })
    : req;

  return next(authReq).pipe(
    catchError((error: HttpErrorResponse) => {
      // Token vencido o inválido: limpiamos la sesión para no dejar al usuario trabado
      if (error.status === 401 && token) {
        authService.signOut();
        router.navigate(['/']);
      }
      return throwError(() => error);
    })
  );
};
