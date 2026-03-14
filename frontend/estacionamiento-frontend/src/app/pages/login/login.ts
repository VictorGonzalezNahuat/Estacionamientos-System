import { Component, ChangeDetectionStrategy, inject, ElementRef, ViewChild, AfterViewInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../services/auth.service';
import { Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { ConfigService } from '../../services/config.service';
import { forkJoin, of } from 'rxjs';
import { catchError } from 'rxjs/operators';

@Component({
  selector: 'app-login',
  templateUrl: './login.html',
  styleUrl: './login.css',
  imports: [FormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Login implements AfterViewInit {

  @ViewChild('usernameInput') private usernameInput?: ElementRef<HTMLInputElement>;

  private authService = inject(AuthService);
  private router = inject(Router);
  private http = inject(HttpClient);
  private config = inject(ConfigService);

  username = '';
  password = '';
  errorMessage = '';

  ngAfterViewInit(): void {
    // Ensure the user field is focused and its content selected after view render.
    queueMicrotask(() => {
      const input = this.usernameInput?.nativeElement;
      if (!input) return;
      input.focus();
      input.select();
    });
  }

  onLogin() {
    this.authService.login({
      username: this.username,
      password: this.password
    }).subscribe({
      next: (response) => {
        this.authService.saveToken(response.access_token);
        this.anunciarBienvenida();
        this.router.navigate(['/dashboard']);
      },
      error: () => {
        this.errorMessage = 'Credenciales incorrectas';
      }
    });
  }

  private anunciarBienvenida() {
    forkJoin({
      user: this.http.get<any>(`${this.config.apiUrl}/auth/me`),
      turno: this.http.get<any>(`${this.config.apiUrl}/turnos/mi-turno`).pipe(catchError(() => of(null)))
    }).subscribe({
      next: ({ user, turno }) => {
        const nombre = user?.nombre ?? 'usuario';
        const msg = turno?.abierto === true
          ? `Bienvenido ${nombre}, actualmente cuentas con un turno abierto`
          : `Bienvenido ${nombre}, actualmente no tienes turno abierto`;
        this.speak(msg);
      }
    });
  }

  private speak(text: string) {
    if (!('speechSynthesis' in window)) return;

    const synth = window.speechSynthesis;
    const utterance = new SpeechSynthesisUtterance(text);
    const preferredName = this.config.speechVoiceName;
    const preferredLang = this.config.speechLang;

    utterance.lang = preferredLang;
    utterance.rate = this.config.speechRate;
    utterance.pitch = this.config.speechPitch;
    utterance.volume = this.config.speechVolume;

    const selectVoice = () => {
      const voices = synth.getVoices();
      if (!voices.length) return;

      const selectedVoice =
        (preferredName ? voices.find(v => v.name === preferredName) : undefined) ??
        voices.find(v => v.lang === preferredLang) ??
        voices.find(v => v.lang.startsWith('es'));

      if (selectedVoice) {
        utterance.voice = selectedVoice;
        utterance.lang = selectedVoice.lang;
      }
    };

    selectVoice();
    synth.cancel();
    synth.speak(utterance);
  }
}