import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Router } from '@angular/router';
import { ConfigService } from './config.service';

@Injectable({
  providedIn: 'root'
})
export class AuthService {

  private http = inject(HttpClient);
  private router = inject(Router);
  private configService = inject(ConfigService);

  login(credentials: { username: string; password: string }) {
    const body = new URLSearchParams();
    body.set('username', credentials.username);
    body.set('password', credentials.password);

    return this.http.post<any>(
      `${this.configService.apiUrl}/auth/login`,
      body.toString(),
      {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        }
      }
    );
  }

  saveToken(token: string) {
    localStorage.setItem('token', token);
  }

  logout() {
    localStorage.removeItem('token');
    this.router.navigate(['/auth/login']);
  }

  isAuthenticated(): boolean {
    return !!localStorage.getItem('token');
  }

  getCurrentUser() {
    return this.http.get<any>(`${this.configService.apiUrl}/auth/me`);
  }

  verifyAdmin() {
    return this.http.get<{ admin: boolean }>(`${this.configService.apiUrl}/auth/verify-admin`);
  }

  verifyEncargado() {
    return this.http.get<{ encargado: boolean }>(`${this.configService.apiUrl}/auth/verify-encargado`);
  }
}
