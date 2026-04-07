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
    'corte-caja-preview': 'assets/alerts/confirm.svg',
    'corte-caja-status': 'assets/alerts/success.svg',
    'fiscal-customer-input': 'assets/alerts/secure.svg',
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

  isCorteCajaPreviewInputValid(alert: AlertMessage | null | undefined): boolean {
    const totalDeclarado = Number(alert?.inputValue ?? '');
    return Number.isFinite(totalDeclarado) && totalDeclarado >= 0;
  }

  getCorteCajaPreviewInputValue(alert: AlertMessage | null | undefined): number {
    return Number(alert?.inputValue ?? 0);
  }

  getCorteCajaPreviewTotalGeneral(alert: AlertMessage | null | undefined): number {
    return Number(alert?.data?.totalGeneral ?? 0);
  }

  getCorteCajaPreviewTotalDeclarado(alert: AlertMessage | null | undefined): number {
    return Number(alert?.data?.totalDeclarado ?? alert?.inputValue ?? 0);
  }

  getCorteCajaPreviewDifference(alert: AlertMessage | null | undefined): number {
    return this.getCorteCajaPreviewTotalDeclarado(alert) - this.getCorteCajaPreviewTotalGeneral(alert);
  }

  getCorteCajaPreviewDifferenceLabel(alert: AlertMessage | null | undefined): string {
    const difference = this.getCorteCajaPreviewDifference(alert);

    if (difference === 0) {
      return 'Corte cuadrado';
    }

    if (difference > 0) {
      return 'Sobra dinero';
    }

    return 'Falta dinero';
  }

  formatCurrency(value: number | string | null | undefined): string {
    const numberValue = Number(value ?? 0);
    return new Intl.NumberFormat('es-MX', {
      style: 'currency',
      currency: 'MXN',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(Number.isFinite(numberValue) ? numberValue : 0);
  }

  getAlertIconPath(type: AlertMessage['type']): string {
    if (type === 'corte-caja-status') {
      const stage = this.alertService.alertState()?.data?.stage;
      if (stage === 'error') {
        return 'assets/alerts/error.svg';
      }
      if (stage === 'processing') {
        return 'assets/alerts/interrogation.svg';
      }
      return 'assets/alerts/success.svg';
    }

    return this.alertIconByType[type] ?? 'assets/alerts/info.svg';
  }

  getAlertIconAlt(type: AlertMessage['type']): string {
    return `Icono de alerta ${type}`;
  }

  isFiscalCustomerInputValid(alert: AlertMessage | null | undefined): boolean {
    const form = alert?.data?.form;
    if (!form) {
      return false;
    }

    const hasRequiredText = [
      form.rfc,
      form.razon_social,
      form.codigo_postal,
      form.regimen_fiscal,
      form.uso_cfdi_receptor,
      form.nombre_contacto,
      form.email,
      form.telefono,
      form.history_estacionamiento_id,
      form.placa,
      form.fecha_salida,
      form.hora_salida,
      form.importe,
    ].every((value: string) => typeof value === 'string' && value.trim().length > 0);

    if (!hasRequiredText) {
      return false;
    }

    const fechaValida = /^\d{4}-\d{2}-\d{2}$/.test(form.fecha_salida.trim());
    const horaValida = /^\d{2}:\d{2}(:\d{2})?$/.test(form.hora_salida.trim());
    const importe = Number(form.importe);
    const historyId = Number(form.history_estacionamiento_id);
    const emailValido = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim());

    return (
      fechaValida
      && horaValida
      && Number.isFinite(importe)
      && importe > 0
      && Number.isFinite(historyId)
      && historyId > 0
      && emailValido
    );
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

  formatAlertDate(value: string | undefined | null): string {
    if (!value) return '';

    const parsed = this.parseDateValue(value);
    if (!parsed) return value;

    const day = String(parsed.getDate()).padStart(2, '0');
    const month = new Intl.DateTimeFormat('es-MX', { month: 'long' }).format(parsed);
    const year = parsed.getFullYear();

    return `${day} de ${month}, ${year}`;
  }

  formatAlertTime(value: string | undefined | null): string {
    if (!value) return '';

    const timeOnlyMatch = value.trim().match(/^(\d{1,2}):(\d{2})(?::(\d{2})(?:\.\d+)?)?$/);
    if (timeOnlyMatch) {
      const [, hourRaw, minute, secondRaw] = timeOnlyMatch;
      const hour24 = Number(hourRaw);
      if (!Number.isInteger(hour24) || hour24 < 0 || hour24 > 23) return value;

      const second = secondRaw ?? '00';
      const hour12 = hour24 % 12 || 12;
      const suffix = hour24 >= 12 ? 'pm' : 'am';

      return `${String(hour12).padStart(2, '0')}:${minute}:${second} ${suffix}`;
    }

    const parsedDateTime = this.parseDateValue(value);
    if (!parsedDateTime) return value;

    const hour24 = parsedDateTime.getHours();
    const minute = String(parsedDateTime.getMinutes()).padStart(2, '0');
    const second = String(parsedDateTime.getSeconds()).padStart(2, '0');
    const hour12 = hour24 % 12 || 12;
    const suffix = hour24 >= 12 ? 'pm' : 'am';

    return `${String(hour12).padStart(2, '0')}:${minute}:${second} ${suffix}`;
  }

  private parseDateValue(value: string): Date | null {
    const dateOnlyMatch = value.match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (dateOnlyMatch) {
      const year = Number(dateOnlyMatch[1]);
      const month = Number(dateOnlyMatch[2]);
      const day = Number(dateOnlyMatch[3]);
      const parsedDate = new Date(year, month - 1, day);
      return Number.isNaN(parsedDate.getTime()) ? null : parsedDate;
    }

    const parsed = new Date(value);
    return Number.isNaN(parsed.getTime()) ? null : parsed;
  }

}
