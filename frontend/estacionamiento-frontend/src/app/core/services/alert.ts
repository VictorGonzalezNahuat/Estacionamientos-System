import { Injectable, signal } from '@angular/core';

export interface AlertMessage {
  type: 'success' | 'error' | 'info';
  message?: string;

  // NUEVO
  title?: string;
  data?: any;
  persistent?: boolean; // si no se debe cerrar sola
}


@Injectable({
  providedIn: 'root'
})
export class AlertService {

  alertState = signal<AlertMessage | null>(null);

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

  close() {
    this.alertState.set(null);
  }

  private show(config: AlertMessage) {
    this.alertState.set({
      ...config,
      persistent: true
    });
  }
}

