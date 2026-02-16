import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AperturaTurno } from './apertura-turno';

describe('AperturaTurno', () => {
  let component: AperturaTurno;
  let fixture: ComponentFixture<AperturaTurno>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AperturaTurno]
    })
    .compileComponents();

    fixture = TestBed.createComponent(AperturaTurno);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
