import { TestBed } from '@angular/core/testing';
import { CanActivateFn } from '@angular/router';

import { tarifasGuard } from './tarifas-guard';

describe('tarifasGuard', () => {
  const executeGuard: CanActivateFn = (...guardParameters) => 
      TestBed.runInInjectionContext(() => tarifasGuard(...guardParameters));

  beforeEach(() => {
    TestBed.configureTestingModule({});
  });

  it('should be created', () => {
    expect(executeGuard).toBeTruthy();
  });
});
