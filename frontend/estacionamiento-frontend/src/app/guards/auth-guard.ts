// auth.guard.ts
import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { map, catchError, of } from 'rxjs';
import { ConfigService } from '../services/config.service';

export const authGuard: CanActivateFn = () => {

  const http = inject(HttpClient);
  const router = inject(Router);
  const configService = inject(ConfigService);

  return http.get<{ id: number, nombre: string, codigo: number }>(
    `${configService.apiUrl}/auth/me`
  ).pipe(
    map(() => {
      return true;
    }),
    catchError(error => {
      console.error('ERROR DEL AUTH GUARD:', error);
      router.navigate(['/login']);
      return of(false);
    })
  );
};
