import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideRouter } from '@angular/router';

import { Encargados } from './encargados';
import { ConfigService } from '../../../services/config.service';
import { AlertService } from '../../../core/services/alert';

describe('Encargados', () => {
  let component: Encargados;
  let fixture: ComponentFixture<Encargados>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Encargados],
      providers: [
        provideHttpClient(),
        provideRouter([]),
        {
          provide: ConfigService,
          useValue: { apiUrl: 'http://localhost:8000' },
        },
        {
          provide: AlertService,
          useValue: {
            error: () => undefined,
            success: () => undefined,
          },
        },
      ],
    })
    .compileComponents();

    fixture = TestBed.createComponent(Encargados);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
