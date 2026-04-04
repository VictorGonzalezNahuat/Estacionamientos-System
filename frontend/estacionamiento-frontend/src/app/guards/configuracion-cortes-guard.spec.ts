import { TestBed } from '@angular/core/testing';
import { CanActivateFn } from '@angular/router';

import { configuracionCortesGuard } from './configuracion-cortes-guard';

describe('configuracionCortesGuard', () => {
  const executeGuard: CanActivateFn = (...guardParameters) => 
      TestBed.runInInjectionContext(() => configuracionCortesGuard(...guardParameters));

  beforeEach(() => {
    TestBed.configureTestingModule({});
  });

  it('should be created', () => {
    expect(executeGuard).toBeTruthy();
  });
});
