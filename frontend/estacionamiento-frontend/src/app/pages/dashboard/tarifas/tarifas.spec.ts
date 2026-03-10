import { ComponentFixture, TestBed } from '@angular/core/testing';

import { Tarifas } from './tarifas';

describe('Tarifas', () => {
  let component: Tarifas;
  let fixture: ComponentFixture<Tarifas>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Tarifas]
    })
    .compileComponents();

    fixture = TestBed.createComponent(Tarifas);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
