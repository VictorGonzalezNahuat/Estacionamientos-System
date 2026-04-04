import { Component, ChangeDetectionStrategy, inject, ElementRef, ViewChild, AfterViewInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../services/auth.service';
import { Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { ConfigService } from '../../services/config.service';
import { AlertService } from '../../core/services/alert';
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
  private alert = inject(AlertService);

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
        void this.handleSuccessfulLogin(response.access_token);
      },
      error: () => {
        this.errorMessage = 'Credenciales incorrectas';
      }
    });
  }

  private async handleSuccessfulLogin(token: string): Promise<void> {
    this.authService.saveToken(token);
    this.anunciarBienvenida();

    const targetRoute = this.isMobileDevice() ? '/acceso-movil' : '/dashboard';
    await this.router.navigate([targetRoute]);
  }

  private isMobileDevice(): boolean {
    const nav = navigator as Navigator & { userAgentData?: { mobile?: boolean } };
    const byClientHint = nav.userAgentData?.mobile === true;
    const byUserAgent = /android|iphone|ipod|windows phone|blackberry|opera mini|mobile/i.test(nav.userAgent);
    const byViewport = window.matchMedia('(max-width: 768px)').matches && window.matchMedia('(pointer: coarse)').matches;

    return byClientHint || byUserAgent || byViewport;
  }

  private anunciarBienvenida() {
    forkJoin({
      user: this.http.get<any>(`${this.config.apiUrl}/auth/me`),
      turno: this.http.get<any>(`${this.config.apiUrl}/turnos/mi-turno`).pipe(catchError(() => of(null)))
    }).subscribe({
      next: ({ user, turno }) => {
        const nombre = user?.nombre ?? 'usuario';
        const msg = turno?.estado === 'abierto'
          ? `Bienvenido ${nombre}, actualmente cuentas con un turno abierto`
          : turno?.estado === 'pendiente-corte'
            ? `Bienvenido ${nombre}, actualmente tu turno está pendiente de corte de caja`
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