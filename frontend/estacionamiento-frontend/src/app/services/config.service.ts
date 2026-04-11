import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom, Observable } from 'rxjs';
import { inject } from '@angular/core';

export interface SystemConfigResponse {
  DATABASE_CLOUD_USER: string;
  DATABASE_CLOUD_HOST: string;
  DATABASE_CLOUD_PORT: number;
  DATABASE_CLOUD_NAME: string;
  SYNC_AUTO_ENABLED: boolean;
  MOBILE_PRINT: boolean;
  SYNC_INTERVAL_MINUTES: number;
  ENTRY_TICKET_CODE_TYPE: string;
  PUBLIC_STATUS_BASE_URL: string;
  AVISO_ENTRADA: string;
  AVISO_SALIDA: string;
}

export interface GeneralConfigUpdate {
  SYNC_AUTO_ENABLED?: boolean;
  MOBILE_PRINT?: boolean;
  SYNC_INTERVAL_MINUTES?: number;
  ENTRY_TICKET_CODE_TYPE?: string;
  PUBLIC_STATUS_BASE_URL?: string;
  AVISO_ENTRADA?: string;
  AVISO_SALIDA?: string;
}

export interface DatabaseConfigUpdate {
  DATABASE_CLOUD_USER: string;
  DATABASE_CLOUD_PASSWORD: string;
  DATABASE_CLOUD_HOST: string;
  DATABASE_CLOUD_PORT: number;
  DATABASE_CLOUD_NAME: string;
}

export interface SystemConfigUpdate extends GeneralConfigUpdate, DatabaseConfigUpdate {}

export interface CortesConfigResponse {
  AUTOSEND_REPORT: boolean;
  SMTP_HOST: string;
  SMTP_PORT: number;
  SMTP_USERNAME: string;
  SMTP_USE_TLS: boolean;
  SMTP_TIMEOUT_SECONDS: number;
  REPORT_FROM_NAME: string;
  REPORT_SUBJECT_TEMPLATE: string;
}

export interface CortesConfigUpdate extends CortesConfigResponse {
  SMTP_PASSWORD: string;
}

export interface PrinterNetworkConfig {
  host: string;
  port: number;
  timeout: number;
}

export interface PrinterUsbConfig {
  mode: string;
  printer_name: string;
}

export interface PrinterConfigResponse {
  method: string;
  network: PrinterNetworkConfig;
  usb: PrinterUsbConfig;
}

export interface PrinterConfigUpdate {
  method: string;
  network: PrinterNetworkConfig;
  usb: PrinterUsbConfig;
}

export interface RuntimeConfig {
  apiUrl: string;
  RECAPTCHA_SITE_KEY?: string;
  speech?: {
    voiceName?: string;
    lang?: string;
    rate?: number;
    pitch?: number;
    volume?: number;
  };
}

@Injectable({
  providedIn: 'root'
})
export class ConfigService {

  private config: RuntimeConfig | null = null;
  private http = inject(HttpClient);

  constructor() {}

  async loadConfig(): Promise<void> {
    this.config = await firstValueFrom(
      this.http.get<RuntimeConfig>('/config.json')
    );
  }

  get apiUrl(): string {
    return this.config?.apiUrl ?? '';
  }

  get speechVoiceName(): string | undefined {
    return this.config?.speech?.voiceName;
  }

  get speechLang(): string {
    return this.config?.speech?.lang ?? 'es-MX';
  }

  get speechRate(): number {
    return this.config?.speech?.rate ?? 1;
  }

  get speechPitch(): number {
    return this.config?.speech?.pitch ?? 1;
  }

  get speechVolume(): number {
    return this.config?.speech?.volume ?? 1;
  }

  get recaptchaSiteKey(): string {
    return this.config?.RECAPTCHA_SITE_KEY?.trim() ?? '';
  }

  // Métodos para la configuración del sistema
  getSystemConfig(): Observable<SystemConfigResponse> {
    return this.http.get<SystemConfigResponse>(`${this.apiUrl}/config`);
  }

  updateGeneralConfig(config: GeneralConfigUpdate): Observable<SystemConfigResponse> {
    return this.http.patch<SystemConfigResponse>(`${this.apiUrl}/config`, config);
  }

  updateDatabaseConfig(config: DatabaseConfigUpdate): Observable<SystemConfigResponse> {
    return this.http.patch<SystemConfigResponse>(`${this.apiUrl}/config/base-datos`, config);
  }

  updateSystemConfig(config: SystemConfigUpdate): Observable<SystemConfigResponse> {
    return this.http.patch<SystemConfigResponse>(`${this.apiUrl}/config`, config);
  }

  getCortesConfig(): Observable<CortesConfigResponse> {
    return this.http.get<CortesConfigResponse>(`${this.apiUrl}/config/cortes`);
  }

  updateCortesConfig(config: CortesConfigUpdate): Observable<CortesConfigResponse> {
    return this.http.patch<CortesConfigResponse>(`${this.apiUrl}/config/cortes`, config);
  }

  getPrinterConfig(): Observable<PrinterConfigResponse> {
    return this.http.get<PrinterConfigResponse>(`${this.apiUrl}/config/printer`);
  }

  updatePrinterConfig(config: PrinterConfigUpdate): Observable<PrinterConfigResponse> {
    return this.http.patch<PrinterConfigResponse>(`${this.apiUrl}/config/printer`, config);
  }
}
