import { TestBed } from '@angular/core/testing';
import { CanActivateFn } from '@angular/router';

import { cancelacionTicketsGuard } from './cancelacion-tickets-guard';

describe('cancelacionTicketsGuard', () => {
  const executeGuard: CanActivateFn = (...guardParameters) => 
      TestBed.runInInjectionContext(() => cancelacionTicketsGuard(...guardParameters));

  beforeEach(() => {
    TestBed.configureTestingModule({});
  });

  it('should be created', () => {
    expect(executeGuard).toBeTruthy();
  });
});
