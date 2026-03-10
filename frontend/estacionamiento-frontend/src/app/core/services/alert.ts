import { Injectable, signal, inject } from '@angular/core';
import { Router } from '@angular/router';

export interface AlertMessage {
  type: 'success' | 'error' | 'info' | 'confirm' | 'session-restart' | 'password-input';
  message?: string;

  // NUEVO
  title?: string;
  data?: any;
  persistent?: boolean; // si no se debe cerrar sola
  onConfirm?: () => void;
  onCancel?: () => void;
  confirmText?: string;
  cancelText?: string;
  inputValue?: string;
}


@Injectable({
  providedIn: 'root'
})
export class AlertService {

  private router = inject(Router);

  alertState = signal<AlertMessage | null>(null);
  private confirmResolve: ((value: boolean) => void) | null = null;
  private passwordResolve: ((value: string | null) => void) | null = null;

  success(message: string) {
    this.show({ type: 'success', message });
  }

  error(message: string) {
    this.show({ type: 'error', message });
  }

  info(title: string, data: any) {
    this.show({
      type: 'info',
      title,
      data,
      persistent: true
    });
  }

  confirm(message: string, title: string = '¿Confirmar?', confirmText: string = 'Aceptar', cancelText: string = 'Cancelar'): Promise<boolean> {
    return new Promise((resolve) => {
      this.confirmResolve = resolve;
      this.show({
        type: 'confirm',
        message,
        title,
        confirmText,
        cancelText,
        persistent: true,
        onConfirm: () => this.handleConfirm(true),
        onCancel: () => this.handleConfirm(false),
      });
    });
  }

  sessionRestartRequired(message: string = 'Es necesario volver a iniciar sesión para aplicar los cambios') {
    this.show({
      type: 'session-restart',
      message,
      title: 'Reiniciar sesión',
      confirmText: 'Aceptar',
      persistent: true,
      onConfirm: () => this.handleSessionRestart(),
    });
  }

  requestPassword(title: string = 'Ingresar contraseña', message: string = 'Por favor ingresa tu contraseña para confirmar'): Promise<string | null> {
    return new Promise((resolve) => {
      this.passwordResolve = resolve;
      this.show({
        type: 'password-input',
        message,
        title,
        inputValue: '',
        confirmText: 'Aceptar',
        cancelText: 'Cancelar',
        persistent: true,
        onConfirm: () => this.handlePasswordConfirm(true),
        onCancel: () => this.handlePasswordConfirm(false),
      });
    });
  }

  handlePasswordConfirm(confirmed: boolean) {
    if (this.passwordResolve) {
      const passwordValue = confirmed ? this.alertState()?.inputValue || null : null;
      this.passwordResolve(passwordValue);
      this.passwordResolve = null;
    }
    this.close();
  }

  handleConfirm(confirmed: boolean) {
    if (this.confirmResolve) {
      this.confirmResolve(confirmed);
      this.confirmResolve = null;
    }
    this.close();
  }

  handleSessionRestart() {
    localStorage.removeItem('token');
    this.alertState.set(null);
    // Usar window.location.href para una redirección forzada y completamente segura
    setTimeout(() => {
      window.location.href = '/login';
    }, 300);
  }

  close() {
    this.alertState.set(null);
  }

  private show(config: AlertMessage) {
    this.alertState.set({
      ...config,
      persistent: config.persistent !== false
    });
  }
}

