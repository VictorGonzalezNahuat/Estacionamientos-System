import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { catchError, map, of } from 'rxjs';
import { AlertService } from '../core/services/alert';
import { AuthService } from '../services/auth.service';

export const configuracionCortesGuard: CanActivateFn = () => {
  const authService = inject(AuthService);
  const router = inject(Router);
  const alertService = inject(AlertService);

  return authService.verifyAdmin().pipe(
    map(response => {
      if (response.admin === true) {
        return true;
      }

      alertService.error('Debes ser administrador para acceder a la configuración de cortes');
      return router.createUrlTree(['/dashboard']);
    }),
    catchError(error => {
      console.error('ERROR DEL GUARD DE CONFIGURACIÓN DE CORTES:', error);
      alertService.error('No fue posible validar permisos de administrador.');
      return of(router.createUrlTree(['/login']));
    })
  );
};
