import { TestBed } from '@angular/core/testing';
import { CanActivateFn } from '@angular/router';

import { entradasSalidasGuard } from './entradas-salidas-guard';

describe('entradasSalidasGuard', () => {
  const executeGuard: CanActivateFn = (...guardParameters) => 
      TestBed.runInInjectionContext(() => entradasSalidasGuard(...guardParameters));

  beforeEach(() => {
    TestBed.configureTestingModule({});
  });

  it('should be created', () => {
    expect(executeGuard).toBeTruthy();
  });
});
