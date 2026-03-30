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
}

export interface GeneralConfigUpdate {
  SYNC_AUTO_ENABLED?: boolean;
  MOBILE_PRINT?: boolean;
  SYNC_INTERVAL_MINUTES?: number;
  ENTRY_TICKET_CODE_TYPE?: string;
  PUBLIC_STATUS_BASE_URL?: string;
}

export interface DatabaseConfigUpdate {
  DATABASE_CLOUD_USER: string;
  DATABASE_CLOUD_PASSWORD: string;
  DATABASE_CLOUD_HOST: string;
  DATABASE_CLOUD_PORT: number;
  DATABASE_CLOUD_NAME: string;
}

export interface SystemConfigUpdate extends GeneralConfigUpdate, DatabaseConfigUpdate {}

@Injectable({
  providedIn: 'root'
})
export class ConfigService {

  private config: any;
  private http = inject(HttpClient);

  constructor() {}

  async loadConfig(): Promise<void> {
    this.config = await firstValueFrom(
      this.http.get('/config.json')
    );
  }

  get apiUrl(): string {
    return this.config?.apiUrl;
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

  // Métodos para la configuración del sistema
  getSystemConfig(): Observable<SystemConfigResponse> {
    return this.http.get<SystemConfigResponse>(`${this.apiUrl}/config/`);
  }

  updateGeneralConfig(config: GeneralConfigUpdate): Observable<SystemConfigResponse> {
    return this.http.patch<SystemConfigResponse>(`${this.apiUrl}/config/`, config);
  }

  updateDatabaseConfig(config: DatabaseConfigUpdate): Observable<SystemConfigResponse> {
    return this.http.patch<SystemConfigResponse>(`${this.apiUrl}/config/base-datos`, config);
  }

  updateSystemConfig(config: SystemConfigUpdate): Observable<SystemConfigResponse> {
    return this.http.patch<SystemConfigResponse>(`${this.apiUrl}/config/`, config);
  }
}
