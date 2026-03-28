import { TestBed } from '@angular/core/testing';
import { CanActivateFn } from '@angular/router';

import { configuracionGuard } from './configuracion-guard';

describe('configuracionGuard', () => {
  const executeGuard: CanActivateFn = (...guardParameters) => 
      TestBed.runInInjectionContext(() => configuracionGuard(...guardParameters));

  beforeEach(() => {
    TestBed.configureTestingModule({});
  });

  it('should be created', () => {
    expect(executeGuard).toBeTruthy();
  });
});
