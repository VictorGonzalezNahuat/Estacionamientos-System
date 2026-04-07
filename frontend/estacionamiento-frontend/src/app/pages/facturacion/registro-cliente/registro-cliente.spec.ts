import { ComponentFixture, TestBed } from '@angular/core/testing';

import { RegistroCliente } from './registro-cliente';

describe('RegistroCliente', () => {
  let component: RegistroCliente;
  let fixture: ComponentFixture<RegistroCliente>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [RegistroCliente]
    })
    .compileComponents();

    fixture = TestBed.createComponent(RegistroCliente);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
