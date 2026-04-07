import { ComponentFixture, TestBed } from '@angular/core/testing';

import { Facturacion } from './facturacion';

describe('Facturacion', () => {
  let component: Facturacion;
  let fixture: ComponentFixture<Facturacion>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Facturacion]
    })
    .compileComponents();

    fixture = TestBed.createComponent(Facturacion);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
