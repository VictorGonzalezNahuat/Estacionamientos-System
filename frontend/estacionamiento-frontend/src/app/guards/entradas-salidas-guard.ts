import { HttpClient } from '@angular/common/http';
import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { ConfigService } from '../services/config.service';
import { AlertService } from '../core/services/alert';
import { catchError, map, of } from 'rxjs';

export const entradasSalidasGuard: CanActivateFn = () => {
  const http = inject(HttpClient);
  const router = inject(Router);
  const configService = inject(ConfigService);
  const alertService = inject(AlertService);

  return http.get<{ abierto: boolean }>(
    `${configService.apiUrl}/turnos/mi-turno`
  ).pipe(
    map(response => {

      if (response.abierto === true) {
        return true;
      }

      alertService.error('No hay turno abierto');
      return router.createUrlTree(['/dashboard']);
    }),
    catchError(error => {
      console.error(error);
      alertService.error('Error verificando el turno.');
      return of(router.createUrlTree(['/login']));
    })
  );
};
