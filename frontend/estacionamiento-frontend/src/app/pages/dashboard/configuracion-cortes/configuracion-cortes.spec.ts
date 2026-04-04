import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of } from 'rxjs';

import { ConfiguracionCortes } from './configuracion-cortes';
import { ConfigService } from '../../../services/config.service';
import { AlertService } from '../../../core/services/alert';
import { AuthService } from '../../../services/auth.service';

const configServiceMock = {
  getCortesConfig: () => of({
    AUTOSEND_REPORT: true,
    SMTP_HOST: 'smtp.example.com',
    SMTP_PORT: 587,
    SMTP_USERNAME: 'user@example.com',
    SMTP_USE_TLS: true,
    SMTP_TIMEOUT_SECONDS: 30,
    REPORT_FROM_NAME: 'Sistema',
    REPORT_SUBJECT_TEMPLATE: 'Corte {fecha}',
  })
};

const alertServiceMock = {
  error: jasmine.createSpy('error'),
  success: jasmine.createSpy('success'),
  requestPassword: jasmine.createSpy('requestPassword').and.resolveTo(null),
};

const authServiceMock = {
  getCurrentUser: () => of({ codigo: 'admin' }),
  login: () => of({}),
};

describe('ConfiguracionCortes', () => {
  let component: ConfiguracionCortes;
  let fixture: ComponentFixture<ConfiguracionCortes>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ConfiguracionCortes],
      providers: [
        { provide: ConfigService, useValue: configServiceMock },
        { provide: AlertService, useValue: alertServiceMock },
        { provide: AuthService, useValue: authServiceMock },
      ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ConfiguracionCortes);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
