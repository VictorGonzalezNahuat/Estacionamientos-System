import { Component, inject, ChangeDetectionStrategy, signal, effect } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AlertService, type AlertMessage } from '../../../core/services/alert';

@Component({
  selector: 'app-global-alert',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './global-alert.html',
  styleUrls: ['./global-alert.css'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class GlobalAlert {

  alertService = inject(AlertService);

  private readonly alertIconByType: Record<AlertMessage['type'], string> = {
    success: 'assets/alerts/success.svg',
    error: 'assets/alerts/error.svg',
    info: 'assets/alerts/info.svg',
    confirm: 'assets/alerts/confirm.svg',
    'session-restart': 'assets/alerts/interrogation.svg',
    'password-input': 'assets/alerts/secure.svg',
    'reset-password-step1': 'assets/alerts/secure.svg',
    'reset-password-step2': 'assets/alerts/secure.svg',
    'pending-messages': 'assets/alerts/interrogation.svg',
    'payment-method-select': 'assets/alerts/interrogation.svg',
  };

  mostrarNuevaPass = signal(false);
  mostrarConfirmarNuevaPass = signal(false);
  mostrarAdminPass = signal(false);

  constructor() {
    effect(() => {
      const type = this.alertService.alertState()?.type;
      if (type === 'reset-password-step1') {
        this.mostrarNuevaPass.set(false);
        this.mostrarConfirmarNuevaPass.set(false);
      } else if (type === 'reset-password-step2') {
        this.mostrarAdminPass.set(false);
      }
    });
  }

  get resetStep1Valid(): boolean {
    const a = this.alertService.alertState();
    return !!(a?.inputValue && a?.inputValue2 && a.inputValue === a.inputValue2);
  }

  getAlertIconPath(type: AlertMessage['type']): string {
    return this.alertIconByType[type] ?? 'assets/alerts/info.svg';
  }

  getAlertIconAlt(type: AlertMessage['type']): string {
    return `Icono de alerta ${type}`;
  }

  handleIconError(event: Event): void {
    const img = event.target as HTMLImageElement | null;
    if (!img) return;

    const fallbackPath = 'assets/alerts/info.svg';
    if (!img.src.endsWith(fallbackPath)) {
      img.src = fallbackPath;
    }
  }

  toggleNuevaPass() { this.mostrarNuevaPass.update(v => !v); }
  toggleConfirmarNuevaPass() { this.mostrarConfirmarNuevaPass.update(v => !v); }
  toggleAdminPass() { this.mostrarAdminPass.update(v => !v); }

}
