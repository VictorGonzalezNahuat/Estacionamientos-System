import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';

import { Estacionados } from './estacionados';

describe('Estacionados', () => {
  let component: Estacionados;
  let fixture: ComponentFixture<Estacionados>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Estacionados],
      providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()]
    })
    .compileComponents();

    fixture = TestBed.createComponent(Estacionados);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
