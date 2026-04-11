import { CanActivateFn } from '@angular/router';

export const cancelacionTicketsGuard: CanActivateFn = (route, state) => {
  return true;
};
