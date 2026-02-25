import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { map, catchError, of } from 'rxjs';
import { ConfigService } from '../services/config.service';
import { AlertService } from '../core/services/alert';

export const turnoGuard: CanActivateFn = () => {

  const http = inject(HttpClient);
  const router = inject(Router);
  const configService = inject(ConfigService);
  const alertService = inject(AlertService);

  return http.get<{ abierto: boolean }>(
    `${configService.apiUrl}/turnos/mi-turno`
  ).pipe(
    map(response => {

      if (response.abierto === false) {
        return true;
      }

      alertService.error('Ya existe un turno abierto para este usuario.');

      return router.createUrlTree(['/dashboard']);
    }),
    catchError((error) => {

      console.error('ERROR DEL GUARD:', error);

      alertService.error('Error verificando el turno.');

      return of(router.createUrlTree(['/login']));
    })
  );
};

