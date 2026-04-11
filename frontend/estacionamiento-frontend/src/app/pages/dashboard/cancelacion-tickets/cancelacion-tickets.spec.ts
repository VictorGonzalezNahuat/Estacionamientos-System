import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';

import { CancelacionTickets } from './cancelacion-tickets';

describe('CancelacionTickets', () => {
  let component: CancelacionTickets;
  let fixture: ComponentFixture<CancelacionTickets>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CancelacionTickets],
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    })
    .compileComponents();

    fixture = TestBed.createComponent(CancelacionTickets);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
