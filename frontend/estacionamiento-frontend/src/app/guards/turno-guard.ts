import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { map, catchError, of, switchMap } from 'rxjs';
import { ConfigService } from '../services/config.service';
import { AlertService } from '../core/services/alert';
import { AuthService } from '../services/auth.service';

type MiTurnoEstado = 'sin-turno' | 'abierto' | 'pendiente-corte';
type MiTurnoResponse = {
  estado: MiTurnoEstado;
  turno_id?: number;
  hora_apertura?: string;
};

export const turnoGuard: CanActivateFn = () => {

  const http = inject(HttpClient);
  const router = inject(Router);
  const configService = inject(ConfigService);
  const alertService = inject(AlertService);
  const authService = inject(AuthService);

  return authService.verifyEncargado().pipe(
    switchMap(encargadoResponse => {

      if (encargadoResponse.encargado !== true) {
        alertService.error('No tienes permisos de encargado.');
        return of(router.createUrlTree(['/dashboard']));
      }

      return http.get<MiTurnoResponse>(
        `${configService.apiUrl}/turnos/mi-turno`
      ).pipe(
        map(response => {

          if (response.estado === 'sin-turno') {
            return true;
          }

          if (response.estado === 'pendiente-corte') {
            alertService.error('El turno actual debe ser cortado antes de iniciar uno nuevo.');
            return router.createUrlTree(['/dashboard']);
          }

          alertService.error('Ya existe un turno abierto para este usuario.');

          return router.createUrlTree(['/dashboard']);
        })
      );
    }),
    catchError((error) => {

      console.error('ERROR DEL GUARD:', error);

      alertService.error('Error verificando el turno.');

      return of(router.createUrlTree(['/login']));
    })
  );
};

