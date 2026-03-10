import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { ConfigService } from './config.service';

@Injectable({
  providedIn: 'root'
})
export class TariffService {

  private http = inject(HttpClient);
  private configService = inject(ConfigService);

  getDefaultTariff() {
    return this.http.get<any>(`${this.configService.apiUrl}/tarifas/default`);
  }
}
