import { TestBed } from '@angular/core/testing';
import { CanActivateFn } from '@angular/router';

import { turnoGuard } from './turno-guard';

describe('turnoGuard', () => {
  const executeGuard: CanActivateFn = (...guardParameters) => 
      TestBed.runInInjectionContext(() => turnoGuard(...guardParameters));

  beforeEach(() => {
    TestBed.configureTestingModule({});
  });

  it('should be created', () => {
    expect(executeGuard).toBeTruthy();
  });
});
