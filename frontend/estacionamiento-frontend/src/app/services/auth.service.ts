import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Router } from '@angular/router';

@Injectable({
  providedIn: 'root'
})
export class AuthService {

  private apiUrl = 'http://localhost:8000'; // cambia si es necesario

  constructor(private http: HttpClient, private router: Router) {}

  login(credentials: { username: string; password: string }) {
    const body = new URLSearchParams();
    body.set('username', credentials.username);
    body.set('password', credentials.password);

    return this.http.post<any>(
        `${this.apiUrl}/auth/login`,
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
}
