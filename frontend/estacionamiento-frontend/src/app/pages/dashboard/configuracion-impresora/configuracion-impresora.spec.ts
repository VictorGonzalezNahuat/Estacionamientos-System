import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of } from 'rxjs';

import { ConfiguracionImpresora } from './configuracion-impresora';
import { ConfigService } from '../../../services/config.service';
import { AlertService } from '../../../core/services/alert';
import { AuthService } from '../../../services/auth.service';

const configServiceMock = {
  getPrinterConfig: () => of({
    method: 'NETWORK',
    network: {
      host: '192.168.1.130',
      port: 9100,
      timeout: 10,
    },
    usb: {
      mode: 'WINDOWS_DEFAULT',
      printer_name: '',
    },
  }),
};

const alertServiceMock = {
  error: () => {},
  success: () => {},
  requestPassword: async () => null,
};

const authServiceMock = {
  getCurrentUser: () => of({ codigo: 'admin' }),
  login: () => of({}),
};

describe('ConfiguracionImpresora', () => {
  let component: ConfiguracionImpresora;
  let fixture: ComponentFixture<ConfiguracionImpresora>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ConfiguracionImpresora],
      providers: [
        { provide: ConfigService, useValue: configServiceMock },
        { provide: AlertService, useValue: alertServiceMock },
        { provide: AuthService, useValue: authServiceMock },
      ],
    })
    .compileComponents();

    fixture = TestBed.createComponent(ConfiguracionImpresora);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
