import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { map, catchError, of } from 'rxjs';

export const turnoGuard: CanActivateFn = () => {

  const http = inject(HttpClient);
  const router = inject(Router);

  return http.get<{ abierto: boolean }>('http://localhost:8000/turnos/mi-turno')
.pipe(
    map(response => {

      if (response.abierto === false) {
        return true;
      } else {
        alert('Ya existe un turno abierto.');
        return false;
      }

    }),
    catchError((error) => {
      console.error('ERROR DEL GUARD:', error);
      alert('Error verificando el turno.');
      router.navigate(['/login'])
      return of(false);
    })
  );
};
