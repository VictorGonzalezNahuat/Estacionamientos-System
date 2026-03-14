import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class ConfigService {

  private config: any;

  constructor(private http: HttpClient) {}

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
}
