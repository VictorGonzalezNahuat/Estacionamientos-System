import { Component, HostListener, inject, OnInit, OnDestroy, ChangeDetectionStrategy, signal } from '@angular/core';
import { Router, RouterOutlet, RouterLink } from "@angular/router";
import { HttpClient } from '@angular/common/http';
import { Subscription, of, timer } from 'rxjs';
import { catchError, map, switchMap } from 'rxjs/operators';
import { AuthService } from '../../services/auth.service';
import { TariffService } from '../../services/tariff.service';
import { AlertService } from '../../core/services/alert';
import { ConfigService } from '../../services/config.service';

interface PendingMessage {
  id: number;
  contenido: string;
}

@Component({
  selector: 'app-dashboard',
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.css',
  imports: [RouterOutlet, RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Dashboard implements OnInit, OnDestroy {

  private router = inject(Router);
  private authService = inject(AuthService);
  private tariffService = inject(TariffService);
  private alertService = inject(AlertService);
  private http = inject(HttpClient);
  private configService = inject(ConfigService);

  private readonly messagesPollIntervalMs = 10000;
  private readonly speechRepeatIntervalMs = 8000;
  private pollingSubscription?: Subscription;
  private speechIntervalId: ReturnType<typeof setInterval> | null = null;
  private acknowledgedMessageBatches = new Set<string>();
  private activeMessagesKey: string | null = null;

  openMenu = signal<string | null>(null);
  currentUser = signal<any>(null);
  currentTariff = signal<any>(null);
  userInitials = signal('');

  ngOnInit(): void {
    this.loadUserData();
    this.loadTariffData();
    this.startPendingMessagesPolling();
  }

  ngOnDestroy(): void {
    this.pollingSubscription?.unsubscribe();
    this.stopSpeechLoop();
  }

  loadUserData(): void {
    this.authService.getCurrentUser().subscribe({
      next: (response: any) => {
        this.currentUser.set({
          codigo: response.codigo,
          nombre: response.nombre
        });
        this.generateInitials();
      },
      error: (error) => {
        console.error('Error cargando usuario:', error);
        this.currentUser.set({ codigo: 'N/A', nombre: 'Usuario' });
      }
    });
  }

  loadTariffData(): void {
    this.tariffService.getDefaultTariff().subscribe({
      next: (response: any) => {
        this.currentTariff.set({
          hora: response.hora,
          medio_dia: response.medio_dia,
          fraccion: response.fraccion,
          diario: response.diario,
          tipo_vehiculo: response.tipo_vehiculo
        });
      },
      error: (error) => {
        console.error('Error cargando tarifa:', error);
        this.currentTariff.set({
          hora: 'N/A',
          medio_dia: 'N/A',
          fraccion: 'N/A',
          diario: 'N/A',
          tipo_vehiculo: 'N/A'
        });
      }
    });
  }

  generateInitials(): void {
    const user = this.currentUser();
    if (user?.nombre) {
      const names = user.nombre.split(' ');
      this.userInitials.set(names.map((n: string) => n.charAt(0).toUpperCase()).join(''));
    }
  }

  toggleMenu(menu: string): void {
    this.openMenu.set(this.openMenu() === menu ? null : menu);
  }

  navigate(): void {
    this.openMenu.set(null);
  }

  @HostListener('document:click')
  closeMenu(): void {
    this.openMenu.set(null);
  }

  logout(): void {
    const message = '¿Deseas cerrar tu sesión?\n\nEsta acción no sustituye el cierre de turno';
    this.alertService.confirm(
      message,
      'Cerrar Sesión',
      'Cerrar Sesión',
      'Cancelar'
    ).then((confirmed) => {
      if (confirmed) {
        localStorage.removeItem('token');
        this.router.navigate(['/login']);
      }
    });
  }

  private startPendingMessagesPolling(): void {
    this.pollingSubscription = timer(0, this.messagesPollIntervalMs).pipe(
      switchMap(() => this.fetchPendingMessages()),
    ).subscribe((pendingMessages) => {
      if (!pendingMessages.length) {
        return;
      }

      const messagesKey = this.buildMessagesKey(pendingMessages);
      if (this.acknowledgedMessageBatches.has(messagesKey) || this.activeMessagesKey === messagesKey) {
        return;
      }

      const activeAlert = this.alertService.alertState();
      if (activeAlert && activeAlert.type !== 'pending-messages') {
        return;
      }

      this.activeMessagesKey = messagesKey;
      const messagesContent = pendingMessages.map((message) => message.contenido);
      this.startSpeechLoop(messagesContent);

      this.alertService.pendingMessages(
        messagesContent,
        () => {
          this.activeMessagesKey = null;
          this.stopSpeechLoop();

          this.markMessagesAsRead(pendingMessages.map((message) => message.id)).then((wasMarked) => {
            if (wasMarked) {
              this.acknowledgedMessageBatches.add(messagesKey);
            }
          });
        },
        () => {
          this.activeMessagesKey = null;
          this.stopSpeechLoop();
        }
      );
    });
  }

  private fetchPendingMessages() {
    return this.http.get<any>(`${this.configService.apiUrl}/turnos/mi-turno`).pipe(
      catchError(() => of(null)),
      switchMap((turno) => {
        if (turno?.abierto !== true) {
          return of<PendingMessage[]>([]);
        }

        return this.http.get<any>(`${this.configService.apiUrl}/mensajes/pendientes`).pipe(
          map((response) => this.normalizeMessages(response)),
          catchError((error) => {
            console.error('Error consultando mensajes pendientes:', error);
            return of<PendingMessage[]>([]);
          })
        );
      })
    );
  }

  private normalizeMessages(response: unknown): PendingMessage[] {
    const rawItems = Array.isArray(response)
      ? response
      : Array.isArray((response as { mensajes?: unknown[] })?.mensajes)
        ? (response as { mensajes: unknown[] }).mensajes
        : [];

    return rawItems
      .map((item) => this.extractPendingMessage(item))
      .filter((message): message is PendingMessage => !!message);
  }

  private extractPendingMessage(item: unknown): PendingMessage | null {
    if (item && typeof item === 'object') {
      const candidate = item as { id?: unknown; mensaje?: string; texto?: string; contenido?: string };
      const messageId = typeof candidate.id === 'number' ? candidate.id : null;
      const messageCandidate = candidate.mensaje ?? candidate.texto ?? candidate.contenido;

      if (messageId !== null && typeof messageCandidate === 'string') {
        const trimmed = messageCandidate.trim();
        if (trimmed.length) {
          return { id: messageId, contenido: trimmed };
        }
      }
    }

    return null;
  }

  private buildMessagesKey(messages: PendingMessage[]): string {
    return messages
      .map((message) => message.id)
      .sort((a, b) => a - b)
      .join('|');
  }

  private markMessagesAsRead(ids: number[]) {
    if (!ids.length) {
      return Promise.resolve(true);
    }

    return new Promise<boolean>((resolve) => {
      this.http.patch(`${this.configService.apiUrl}/mensajes/marcar-leidos`, { ids }).subscribe({
        next: () => resolve(true),
        error: (error) => {
          console.error('Error al marcar mensajes como leidos:', error);
          resolve(false);
        },
      });
    });
  }

  private startSpeechLoop(messages: string[]): void {
    this.stopSpeechLoop();

    const speechText = messages.length === 1
      ? `Mensaje pendiente: ${messages[0]}`
      : `Tienes ${messages.length} mensajes pendientes. ${messages.join('. ')}`;

    this.speak(speechText);
    this.speechIntervalId = setInterval(() => {
      this.speak(speechText);
    }, this.speechRepeatIntervalMs);
  }

  private stopSpeechLoop(): void {
    if (this.speechIntervalId) {
      clearInterval(this.speechIntervalId);
      this.speechIntervalId = null;
    }
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
  }

  private speak(text: string): void {
    if (!('speechSynthesis' in window)) {
      return;
    }

    const synth = window.speechSynthesis;
    const utterance = new SpeechSynthesisUtterance(text);
    const preferredName = this.configService.speechVoiceName;
    const preferredLang = this.configService.speechLang;

    utterance.lang = preferredLang;
    utterance.rate = this.configService.speechRate;
    utterance.pitch = this.configService.speechPitch;
    utterance.volume = this.configService.speechVolume;

    const selectVoice = () => {
      const voices = synth.getVoices();
      if (!voices.length) {
        return;
      }

      const selectedVoice =
        (preferredName ? voices.find((voice) => voice.name === preferredName) : undefined)
        ?? voices.find((voice) => voice.lang === preferredLang)
        ?? voices.find((voice) => voice.lang.startsWith('es'));

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
