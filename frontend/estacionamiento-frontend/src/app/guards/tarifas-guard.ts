import { CanActivateFn } from '@angular/router';

export const tarifasGuard: CanActivateFn = (route, state) => {
  return true;
};
