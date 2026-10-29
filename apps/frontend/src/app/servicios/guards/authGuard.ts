import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../AuthService';


export const authGuard: CanActivateFn = async (route, state) => {
  const authService = inject(AuthService);
  const router = inject(Router);

  try {
    // obtiene la sesion de Supabase de forma asincrona
    const { data } = await authService.session;

    if (data.session) {
      // elusuario tiene una sesion activa?si -> permite el acceso a la ruta
      return true;

    } else {
      // no hay sesion, se bloquea la navegacion y se redirige al inicio
      return router.createUrlTree(['/']);
    }
  } catch (error) {
    console.error('Error verificando la sesion en el Guard:', error);
    return router.createUrlTree(['/']);
  }
};