import { Injectable, signal, inject } from '@angular/core';
import { Router } from '@angular/router';

export interface AlertMessage {
  type: 'success' | 'error' | 'info' | 'confirm' | 'session-restart' | 'password-input' | 'reset-password-step1' | 'reset-password-step2' | 'pending-messages' | 'payment-method-select' | 'corte-caja-preview' | 'corte-caja-status' | 'fiscal-customer-input';
  message?: string;

  // NUEVO
  title?: string;
  data?: any;
  persistent?: boolean; // si no se debe cerrar sola
  onConfirm?: () => void | boolean | Promise<void | boolean>;
  onCancel?: () => void;
  onClose?: () => void;
  confirmText?: string;
  cancelText?: string;
  secondaryText?: string;
  inputValue?: string;
  inputValue2?: string;
}

export interface CorteCajaPreviewData {
  turnoId: number;
  totalGeneral: number;
  totalEfectivo: number;
  totalTarjeta: number;
  registros: number;
  fecha?: string;
  encargado?: string;
  totalDeclarado?: number;
  diferencia?: number;
  stage: 'input' | 'preview';
}

export interface CorteCajaStatusData {
  stage: 'processing' | 'success' | 'error';
  corteId?: number;
}

export interface FiscalCustomerInputData {
  rfc: string;
  razon_social: string;
  codigo_postal: string;
  regimen_fiscal: string;
  uso_cfdi_receptor: string;
  nombre_contacto: string;
  email: string;
  telefono: string;
  history_estacionamiento_id: string;
  placa: string;
  fecha_salida: string;
  hora_salida: string;
  importe: string;
}


@Injectable({
  providedIn: 'root'
})
export class AlertService {

  private router = inject(Router);

  alertState = signal<AlertMessage | null>(null);
  private confirmResolve: ((value: boolean) => void) | null = null;
  private paymentMethodResolve: ((value: 'efectivo' | 'tarjeta' | null) => void) | null = null;
  private passwordResolve: ((value: string | null) => void) | null = null;
  private resetPasswordResolve: ((value: { nueva: string; admin: string } | null) => void) | null = null;
  private corteCajaPreviewResolve: ((value: number | null) => void) | null = null;
  private fiscalCustomerInputResolve: ((value: FiscalCustomerInputData | null) => void) | null = null;
  private _resetNuevaPassword = '';
  private _resetMessageTitle = '';
  private _corteCajaTotalDeclarado = 0;

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

  pendingMessages(
    messages: string[],
    onConfirm: () => void,
    onClose?: () => void,
    title: string = 'Mensajes pendientes'
  ) {
    this.show({
      type: 'pending-messages',
      title,
      data: { messages },
      persistent: true,
      confirmText: 'Marcar como leido',
      onConfirm,
      onClose,
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

  selectPaymentMethod(
    message: string = 'Selecciona como deseas cobrar la salida del vehiculo.',
    title: string = 'Metodo de pago',
    efectivoText: string = 'Efectivo',
    tarjetaText: string = 'Tarjeta (Stripe)',
    cancelText: string = 'Cancelar'
  ): Promise<'efectivo' | 'tarjeta' | null> {
    return new Promise((resolve) => {
      this.paymentMethodResolve = resolve;
      this.show({
        type: 'payment-method-select',
        message,
        title,
        confirmText: efectivoText,
        secondaryText: tarjetaText,
        cancelText,
        persistent: true,
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

  requestCorteCajaPreview(data: Omit<CorteCajaPreviewData, 'stage' | 'totalDeclarado' | 'diferencia'>): Promise<number | null> {
    return new Promise((resolve) => {
      this.corteCajaPreviewResolve = resolve;
      this._corteCajaTotalDeclarado = 0;
      this.show({
        type: 'corte-caja-preview',
        title: 'Previsualización del corte',
        message: 'Ingresa el total declarado para revisar el corte antes de enviarlo al backend.',
        data: {
          ...data,
          stage: 'input',
        },
        inputValue: '',
        confirmText: 'Continuar',
        cancelText: 'Cancelar',
        persistent: true,
      });
    });
  }

  requestFiscalCustomerInput(defaults: FiscalCustomerInputData): Promise<FiscalCustomerInputData | null> {
    return new Promise((resolve) => {
      this.fiscalCustomerInputResolve = resolve;
      this.show({
        type: 'fiscal-customer-input',
        title: 'Registro fiscal requerido',
        message: 'El RFC no existe en sistema. Completa estos datos para registrar y continuar con la emision en un solo flujo.',
        data: {
          form: { ...defaults },
        },
        confirmText: 'Registrar y emitir',
        cancelText: 'Cancelar',
        persistent: true,
      });
    });
  }

  showCorteCajaProcessing(): void {
    this.show({
      type: 'corte-caja-status',
      title: 'Procesando corte',
      message: 'Espera un momento, estamos realizando el corte de caja.',
      data: { stage: 'processing' } satisfies CorteCajaStatusData,
      persistent: true,
    });
  }

  showCorteCajaSuccess(
    corteId: number,
    onDownload: () => void | Promise<void>,
    onClose?: () => void
  ): void {
    this.show({
      type: 'corte-caja-status',
      title: 'Corte realizado correctamente',
      message: 'El corte se guardo correctamente. Puedes descargar el reporte en PDF.',
      data: { stage: 'success', corteId } satisfies CorteCajaStatusData,
      confirmText: 'Descargar PDF',
      cancelText: 'Cerrar',
      onConfirm: onDownload,
      onClose,
      persistent: true,
    });
  }

  showCorteCajaError(message: string): void {
    this.show({
      type: 'corte-caja-status',
      title: 'No se pudo completar el corte',
      message,
      data: { stage: 'error' } satisfies CorteCajaStatusData,
      cancelText: 'Cerrar',
      persistent: true,
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

  handleCorteCajaPreviewContinue(): void {
    const state = this.alertState();
    if (!state || state.type !== 'corte-caja-preview') {
      return;
    }

    const totalDeclarado = Number(state.inputValue ?? '');
    if (!Number.isFinite(totalDeclarado) || totalDeclarado < 0) {
      return;
    }

    this._corteCajaTotalDeclarado = totalDeclarado;

    const totalGeneral = Number(state.data?.totalGeneral ?? 0);
    this.show({
      ...state,
      message: 'Revisa el resumen final del corte antes de confirmar.',
      data: {
        ...state.data,
        stage: 'preview',
        totalDeclarado,
        diferencia: totalDeclarado - totalGeneral,
      },
      confirmText: 'Aceptar',
      secondaryText: 'Editar total',
    });
  }

  handleCorteCajaPreviewBack(): void {
    const state = this.alertState();
    if (!state || state.type !== 'corte-caja-preview') {
      return;
    }

    this.show({
      ...state,
      message: 'Ingresa el total declarado para revisar el corte antes de enviarlo al backend.',
      data: {
        ...state.data,
        stage: 'input',
      },
      confirmText: 'Continuar',
      secondaryText: undefined,
    });
  }

  handleCorteCajaPreviewConfirm(): void {
    if (this.corteCajaPreviewResolve) {
      this.corteCajaPreviewResolve(this._corteCajaTotalDeclarado);
      this.corteCajaPreviewResolve = null;
    }
    this._corteCajaTotalDeclarado = 0;
    this.showCorteCajaProcessing();
  }

  handleCorteCajaPreviewCancel(): void {
    if (this.corteCajaPreviewResolve) {
      this.corteCajaPreviewResolve(null);
      this.corteCajaPreviewResolve = null;
    }
    this._corteCajaTotalDeclarado = 0;
    this.close();
  }

  async handleCorteCajaStatusDownload(): Promise<void> {
    const currentAlert = this.alertState();
    if (!currentAlert || currentAlert.type !== 'corte-caja-status' || !currentAlert.onConfirm) {
      return;
    }

    try {
      const result = await currentAlert.onConfirm();
      if (result === false) {
        return;
      }
    } catch (error) {
      console.error('Error descargando el reporte de corte:', error);
      this.show({
        ...currentAlert,
        message: 'No se pudo descargar el PDF del corte. Intenta nuevamente.',
      });
    }
  }

  handleCorteCajaStatusClose(): void {
    this.close();
  }

  handleFiscalCustomerInputConfirm(): void {
    if (!this.fiscalCustomerInputResolve) {
      this.close();
      return;
    }

    const state = this.alertState();
    if (!state || state.type !== 'fiscal-customer-input') {
      this.fiscalCustomerInputResolve(null);
      this.fiscalCustomerInputResolve = null;
      this.close();
      return;
    }

    const form = state.data?.form as FiscalCustomerInputData | undefined;
    if (!form) {
      this.fiscalCustomerInputResolve(null);
      this.fiscalCustomerInputResolve = null;
      this.close();
      return;
    }

    this.fiscalCustomerInputResolve({ ...form });
    this.fiscalCustomerInputResolve = null;
    this.close();
  }

  handleFiscalCustomerInputCancel(): void {
    if (this.fiscalCustomerInputResolve) {
      this.fiscalCustomerInputResolve(null);
      this.fiscalCustomerInputResolve = null;
    }
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

  handlePaymentMethodSelection(value: 'efectivo' | 'tarjeta' | null) {
    if (this.paymentMethodResolve) {
      this.paymentMethodResolve(value);
      this.paymentMethodResolve = null;
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

  markCurrentAlertAsRead() {
    const currentAlert = this.alertState();
    if (!currentAlert?.onConfirm) {
      this.close();
      return;
    }

    try {
      const result = currentAlert.onConfirm();
      if (result === false) {
        return;
      }
      this.close();
    } catch (error) {
      console.error('Error al marcar alerta como leida:', error);
    }
  }

  close() {
    const currentAlert = this.alertState();
    this.alertState.set(null);
    if (currentAlert?.type === 'corte-caja-preview' && this.corteCajaPreviewResolve) {
      this.corteCajaPreviewResolve(null);
      this.corteCajaPreviewResolve = null;
      this._corteCajaTotalDeclarado = 0;
    }
    if (currentAlert?.type === 'fiscal-customer-input' && this.fiscalCustomerInputResolve) {
      this.fiscalCustomerInputResolve(null);
      this.fiscalCustomerInputResolve = null;
    }
    currentAlert?.onClose?.();
  }

  private show(config: AlertMessage) {
    this.alertState.set({
      ...config,
      persistent: config.persistent !== false
    });
  }
}

