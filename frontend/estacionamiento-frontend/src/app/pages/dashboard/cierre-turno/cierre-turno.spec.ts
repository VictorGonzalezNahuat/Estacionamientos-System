import { ComponentFixture, TestBed } from '@angular/core/testing';

import { CierreTurno } from './cierre-turno';

describe('CierreTurno', () => {
  let component: CierreTurno;
  let fixture: ComponentFixture<CierreTurno>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CierreTurno]
    })
    .compileComponents();

    fixture = TestBed.createComponent(CierreTurno);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
