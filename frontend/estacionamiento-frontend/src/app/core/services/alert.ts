import { Injectable, signal, inject } from '@angular/core';
import { Router } from '@angular/router';

export interface AlertMessage {
  type: 'success' | 'error' | 'info' | 'confirm' | 'session-restart' | 'password-input' | 'reset-password-step1' | 'reset-password-step2';
  message?: string;

  // NUEVO
  title?: string;
  data?: any;
  persistent?: boolean; // si no se debe cerrar sola
  onConfirm?: () => void;
  onCancel?: () => void;
  onClose?: () => void;
  confirmText?: string;
  cancelText?: string;
  inputValue?: string;
  inputValue2?: string;
}


@Injectable({
  providedIn: 'root'
})
export class AlertService {

  private router = inject(Router);

  alertState = signal<AlertMessage | null>(null);
  private confirmResolve: ((value: boolean) => void) | null = null;
  private passwordResolve: ((value: string | null) => void) | null = null;
  private resetPasswordResolve: ((value: { nueva: string; admin: string } | null) => void) | null = null;
  private _resetNuevaPassword = '';
  private _resetMessageTitle = '';

  success(message: string, onClose?: () => void) {
    this.show({ type: 'success', message, onClose });
  }

  error(message: string, onClose?: () => void) {
    this.show({ type: 'error', message, onClose });
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

  requestResetPassword(title: string = 'Restablecer contraseña'): Promise<{ nueva: string; admin: string } | null> {
    return new Promise((resolve) => {
      this.resetPasswordResolve = resolve;
      this._resetMessageTitle = title;
      this.show({
        type: 'reset-password-step1',
        title,
        inputValue: '',
        inputValue2: '',
        persistent: true,
      });
    });
  }

  handleResetGoStep2(): void {
    const state = this.alertState();
    if (!state) return;
    this._resetNuevaPassword = state.inputValue || '';
    this.show({
      type: 'reset-password-step2',
      title: 'Confirmar identidad',
      message: 'Ingresa tu contraseña de administrador para confirmar el cambio',
      inputValue: '',
      persistent: true,
    });
  }

  handleResetGoBack(): void {
    this.show({
      type: 'reset-password-step1',
      title: this._resetMessageTitle,
      inputValue: this._resetNuevaPassword,
      inputValue2: this._resetNuevaPassword,
      persistent: true,
    });
  }

  handleResetSubmit(): void {
    const adminPass = this.alertState()?.inputValue || '';
    if (this.resetPasswordResolve) {
      this.resetPasswordResolve({ nueva: this._resetNuevaPassword, admin: adminPass });
      this.resetPasswordResolve = null;
    }
    this._resetNuevaPassword = '';
    this.close();
  }

  handleResetCancel(): void {
    if (this.resetPasswordResolve) {
      this.resetPasswordResolve(null);
      this.resetPasswordResolve = null;
    }
    this._resetNuevaPassword = '';
    this.close();
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
    const currentAlert = this.alertState();
    this.alertState.set(null);
    currentAlert?.onClose?.();
  }

  private show(config: AlertMessage) {
    this.alertState.set({
      ...config,
      persistent: config.persistent !== false
    });
  }
}

