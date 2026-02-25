import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EntradasSalidas } from './entradas-salidas';

describe('EntradasSalidas', () => {
  let component: EntradasSalidas;
  let fixture: ComponentFixture<EntradasSalidas>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EntradasSalidas]
    })
    .compileComponents();

    fixture = TestBed.createComponent(EntradasSalidas);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
