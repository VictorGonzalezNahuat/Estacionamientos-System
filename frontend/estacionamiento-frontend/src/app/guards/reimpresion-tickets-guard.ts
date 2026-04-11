import { CanActivateFn } from '@angular/router';

export const reimpresionTicketsGuard: CanActivateFn = (route, state) => {
  return true;
};
