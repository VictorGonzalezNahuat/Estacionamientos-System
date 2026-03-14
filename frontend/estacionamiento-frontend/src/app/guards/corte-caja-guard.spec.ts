import { TestBed } from '@angular/core/testing';
import { CanActivateFn } from '@angular/router';

import { corteCajaGuard } from './corte-caja-guard';

describe('corteCajaGuard', () => {
  const executeGuard: CanActivateFn = (...guardParameters) => 
      TestBed.runInInjectionContext(() => corteCajaGuard(...guardParameters));

  beforeEach(() => {
    TestBed.configureTestingModule({});
  });

  it('should be created', () => {
    expect(executeGuard).toBeTruthy();
  });
});
