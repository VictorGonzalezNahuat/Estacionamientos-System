import { TestBed } from '@angular/core/testing';
import { CanActivateFn } from '@angular/router';

import { configuracionImpresoraGuard } from './configuracion-impresora-guard';

describe('configuracionImpresoraGuard', () => {
  const executeGuard: CanActivateFn = (...guardParameters) => 
      TestBed.runInInjectionContext(() => configuracionImpresoraGuard(...guardParameters));

  beforeEach(() => {
    TestBed.configureTestingModule({});
  });

  it('should be created', () => {
    expect(executeGuard).toBeTruthy();
  });
});
