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
}
