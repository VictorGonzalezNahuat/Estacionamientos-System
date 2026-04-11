import { TestBed } from '@angular/core/testing';
import { CanActivateFn } from '@angular/router';

import { reimpresionTicketsGuard } from './reimpresion-tickets-guard';

describe('reimpresionTicketsGuard', () => {
  const executeGuard: CanActivateFn = (...guardParameters) => 
      TestBed.runInInjectionContext(() => reimpresionTicketsGuard(...guardParameters));

  beforeEach(() => {
    TestBed.configureTestingModule({});
  });

  it('should be created', () => {
    expect(executeGuard).toBeTruthy();
  });
});
