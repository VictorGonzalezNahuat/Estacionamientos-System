import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AccesoMovil } from './acceso-movil';

describe('AccesoMovil', () => {
  let component: AccesoMovil;
  let fixture: ComponentFixture<AccesoMovil>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AccesoMovil]
    })
    .compileComponents();

    fixture = TestBed.createComponent(AccesoMovil);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
