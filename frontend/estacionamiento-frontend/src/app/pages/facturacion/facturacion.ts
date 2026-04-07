import { Component, OnDestroy, inject } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { FormsModule, NgForm } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { AlertService } from '../../core/services/alert';
import { EmitFacturaPayload, EmitFacturaResponse, FacturacionService, FiscalClientRegisterWithTicketPayload } from '../../services/facturacion.service';
import { RecaptchaService } from '../../services/recaptcha.service';

type TicketField = 'placa' | 'fecha_salida' | 'hora_salida' | 'importe' | 'history_estacionamiento_id';

const FLOW_CANCELLED = 'FLOW_CANCELLED';

@Component({
  selector: 'app-facturacion',
  imports: [RouterModule, FormsModule],
  templateUrl: './facturacion.html',
  styleUrl: './facturacion.css',
})
export class Facturacion implements OnDestroy {
  private readonly lastInvoiceRequestIdKey = 'facturacion_last_invoice_request_id';

  private facturacionService = inject(FacturacionService);
  private alert = inject(AlertService);
  private router = inject(Router);
  private recaptchaService = inject(RecaptchaService);

  private rateLimitTimer: ReturnType<typeof setInterval> | null = null;

  isSubmitting = false;
  rateLimitRemainingSeconds = 0;
  fieldErrors: Partial<Record<TicketField, string>> = {};

  form = {
    rfc: '',
    history_estacionamiento_id: '',
    placa: '',
    fecha_salida: '',
    hora_salida: '',
    importe: '',
    send_email: true,
    notes: '',
  };

  ngOnDestroy(): void {
    this.clearRateLimitTimer();
  }

  get isRateLimited(): boolean {
    return this.rateLimitRemainingSeconds > 0;
  }

  async onSubmit(formRef: NgForm): Promise<void> {
    if (this.isSubmitting || this.isRateLimited) return;

    this.fieldErrors = {};

    if (formRef.invalid) {
      this.alert.error('Completa correctamente todos los campos requeridos antes de emitir la factura.');
      return;
    }

    const rfc = this.normalizeRFC(this.form.rfc);
    const historyId = Number(this.form.history_estacionamiento_id);
    const importe = Number(this.form.importe);
    const importeNormalizado = Number(importe.toFixed(2));
    const fechaSalida = this.formatFechaForApi(this.form.fecha_salida);
    const horaSalida = this.formatHoraForApi(this.form.hora_salida);
    const placa = this.normalizePlate(this.form.placa);

    if (Number.isNaN(historyId) || historyId <= 0) {
      this.alert.error('El folio del ticket debe ser un numero valido mayor a 0.');
      return;
    }

    if (Number.isNaN(importe) || importe <= 0) {
      this.alert.error('El importe debe ser un numero valido mayor a 0.');
      return;
    }

    if (!fechaSalida) {
      this.alert.error('La fecha de salida es invalida. Usa el formato dd-mm-aaaa en vista y se enviara como yyyy-mm-dd.');
      return;
    }

    if (!horaSalida) {
      this.alert.error('La hora de salida es invalida. Se enviara al backend en formato HH:mm:ss.');
      return;
    }

    if (!placa) {
      this.alert.error('La placa es obligatoria y debe contener caracteres validos.');
      return;
    }

    this.isSubmitting = true;

    try {
      const fiscalCustomerId = await this.resolveFiscalCustomerId({
        rfc,
        history_estacionamiento_id: historyId,
        placa,
        fecha_salida: fechaSalida,
        hora_salida: horaSalida,
        importe: importeNormalizado,
      });

      const emitirRecaptchaToken = await this.recaptchaService.execute('emitir_factura');

      const payload: EmitFacturaPayload = {
        fiscal_customer_id: fiscalCustomerId,
        history_estacionamiento_id: historyId,
        placa,
        fecha_salida: fechaSalida,
        hora_salida: horaSalida,
        importe: importeNormalizado,
        send_email: this.form.send_email,
        notes: this.form.notes.trim(),
        recaptcha_token: emitirRecaptchaToken,
      };

      const response = await firstValueFrom(this.facturacionService.emitirFactura(payload));
      await this.handleEmitSuccess(response, formRef);
    } catch (error) {
      if (error instanceof Error && error.message === FLOW_CANCELLED) {
        return;
      }

      if (error instanceof HttpErrorResponse) {
        this.handleFacturacionError(error);
        return;
      }

      const message = error instanceof Error
        ? error.message
        : 'Ocurrio un error inesperado durante la emision de factura.';
      this.alert.error(message);
    } finally {
      this.isSubmitting = false;
    }
  }

  clearFieldError(field: TicketField): void {
    if (!this.fieldErrors[field]) {
      return;
    }

    this.fieldErrors = {
      ...this.fieldErrors,
      [field]: undefined,
    };
  }

  private async resolveFiscalCustomerId(ticket: {
    rfc: string;
    history_estacionamiento_id: number;
    placa: string;
    fecha_salida: string;
    hora_salida: string;
    importe: number;
  }): Promise<number> {
    try {
      const customer = await firstValueFrom(this.facturacionService.getFiscalCustomerByRFC(ticket.rfc));
      return customer.id;
    } catch (error) {
      if (!(error instanceof HttpErrorResponse) || !this.isFiscalCustomerNotFound(error)) {
        throw error;
      }

      const fiscalInput = await this.alert.requestFiscalCustomerInput({
        rfc: ticket.rfc,
        razon_social: '',
        codigo_postal: '',
        regimen_fiscal: '',
        uso_cfdi_receptor: 'G03',
        nombre_contacto: '',
        email: '',
        telefono: '',
        history_estacionamiento_id: String(ticket.history_estacionamiento_id),
        placa: ticket.placa,
        fecha_salida: ticket.fecha_salida,
        hora_salida: ticket.hora_salida,
        importe: ticket.importe.toFixed(2),
      });

      if (!fiscalInput) {
        throw new Error(FLOW_CANCELLED);
      }

      const registerRecaptchaToken = await this.recaptchaService.execute('registro_cliente_fiscal');

      const payload: FiscalClientRegisterWithTicketPayload = {
        rfc: this.normalizeRFC(fiscalInput.rfc),
        razon_social: this.normalizeSpaces(fiscalInput.razon_social),
        codigo_postal: this.onlyDigits(fiscalInput.codigo_postal).slice(0, 5),
        regimen_fiscal: this.normalizeSpaces(fiscalInput.regimen_fiscal),
        uso_cfdi_receptor: fiscalInput.uso_cfdi_receptor.trim().toUpperCase(),
        nombre_contacto: this.normalizeSpaces(fiscalInput.nombre_contacto),
        email: fiscalInput.email.trim().toLowerCase(),
        telefono: this.onlyDigits(fiscalInput.telefono).slice(0, 10),
        history_estacionamiento_id: Number(fiscalInput.history_estacionamiento_id),
        placa: this.normalizePlate(fiscalInput.placa),
        fecha_salida: this.formatFechaForApi(fiscalInput.fecha_salida) ?? ticket.fecha_salida,
        hora_salida: this.formatHoraForApi(fiscalInput.hora_salida) ?? ticket.hora_salida,
        importe: Number(Number(fiscalInput.importe).toFixed(2)),
        recaptcha_token: registerRecaptchaToken,
      };

      this.form.rfc = payload.rfc;
      this.form.history_estacionamiento_id = String(payload.history_estacionamiento_id);
      this.form.placa = payload.placa;
      this.form.fecha_salida = payload.fecha_salida;
      this.form.hora_salida = payload.hora_salida;
      this.form.importe = payload.importe.toFixed(2);

      const created = await firstValueFrom(this.facturacionService.createFiscalClientWithTicket(payload));
      return created.id;
    }
  }

  private async handleEmitSuccess(response: EmitFacturaResponse, formRef: NgForm): Promise<void> {
    this.saveLastInvoiceRequestId(response.invoice_request_id);
    this.facturacionService.saveInvoiceAccessToken(
      response.invoice_request_id,
      response.access_token,
      response.access_token_expires_at
    );

    const shouldDownloadDocs = await this.alert.confirm(
      `La factura se emitio correctamente. Solicitud #${response.invoice_request_id}. ¿Deseas descargar los documentos ahora?`,
      'Factura emitida',
      'Descargar documentos',
      'Finalizar'
    );

    this.resetForm(formRef);

    if (shouldDownloadDocs) {
      void this.router.navigate(['/facturacion/descarga-documentos'], {
        queryParams: { invoiceRequestId: response.invoice_request_id }
      });
    }
  }

  private isFiscalCustomerNotFound(err: HttpErrorResponse): boolean {
    const detail = err?.error?.detail;
    return err.status === 404 && detail?.code === 'FISCAL_CUSTOMER_NOT_FOUND';
  }

  private buildErrorMessage(err: HttpErrorResponse, fallback: string): string {
    const detail = err?.error?.detail;

    if (typeof detail === 'string' && detail.trim().length > 0) {
      return detail;
    }

    if (detail && typeof detail?.message === 'string' && detail.message.trim().length > 0) {
      return detail.message;
    }

    if (Array.isArray(detail) && detail.length > 0) {
      const lines = detail
        .map((item: any) => {
          const field = Array.isArray(item?.loc) ? item.loc[item.loc.length - 1] : 'campo';
          const msg = typeof item?.msg === 'string' ? item.msg : 'valor invalido';
          return `${field}: ${msg}`;
        })
        .join('\n');
      return `${fallback}\n${lines}`;
    }

    const message = err?.error?.message;
    if (typeof message === 'string' && message.trim().length > 0) {
      return message;
    }

    return fallback;
  }

  private handleFacturacionError(err: HttpErrorResponse): void {
    const code = this.extractDetailCode(err);

    if (err.status === 403 && (code === 'RECAPTCHA_LOW_SCORE' || code === 'RECAPTCHA_FAILED')) {
      this.alert.error('No pudimos validar la solicitud, intenta nuevamente.');
      return;
    }

    if (err.status === 429 && code === 'RATE_LIMITED') {
      const seconds = this.extractRetryAfterSeconds(err);
      this.startRateLimitCountdown(seconds);
      this.alert.error(`Demasiadas solicitudes. Intenta nuevamente en ${seconds} segundos.`);
      return;
    }

    if (err.status === 409 && code === 'TICKET_ALREADY_INVOICED') {
      this.alert.error('Este ticket ya tiene una factura emitida o en proceso.');
      return;
    }

    if (this.applyMismatchErrors(err)) {
      this.alert.error('Los datos del ticket no coinciden con una operacion pagada. Revisa los campos resaltados.');
      return;
    }

    this.alert.error(this.buildErrorMessage(err, 'No se pudo completar el proceso de facturacion.'));
  }

  private applyMismatchErrors(err: HttpErrorResponse): boolean {
    if (err.status !== 400) {
      return false;
    }

    const detail = err?.error?.detail;
    const mismatchFields = new Set<TicketField>();

    const addFieldIfTicket = (field: unknown) => {
      if (typeof field !== 'string') return;
      const normalized = field.trim().toLowerCase();
      if (normalized === 'placa') mismatchFields.add('placa');
      if (normalized === 'fecha_salida') mismatchFields.add('fecha_salida');
      if (normalized === 'hora_salida') mismatchFields.add('hora_salida');
      if (normalized === 'importe') mismatchFields.add('importe');
      if (normalized === 'history_estacionamiento_id') mismatchFields.add('history_estacionamiento_id');
    };

    if (Array.isArray(detail)) {
      detail.forEach((item: any) => {
        const loc = Array.isArray(item?.loc) ? item.loc[item.loc.length - 1] : undefined;
        addFieldIfTicket(loc);
      });
    }

    if (detail && typeof detail === 'object') {
      if (Array.isArray(detail?.fields)) {
        detail.fields.forEach((field: unknown) => addFieldIfTicket(field));
      }

      if (detail?.mismatches && typeof detail.mismatches === 'object') {
        Object.keys(detail.mismatches).forEach((field) => addFieldIfTicket(field));
      }

      addFieldIfTicket(detail?.field);
    }

    const message = typeof detail?.message === 'string' ? detail.message.toLowerCase() : '';
    if (!mismatchFields.size) {
      if (message.includes('placa')) mismatchFields.add('placa');
      if (message.includes('fecha')) mismatchFields.add('fecha_salida');
      if (message.includes('hora')) mismatchFields.add('hora_salida');
      if (message.includes('importe')) mismatchFields.add('importe');
      if (message.includes('ticket') || message.includes('history')) mismatchFields.add('history_estacionamiento_id');
    }

    if (!mismatchFields.size) {
      return false;
    }

    const errors: Partial<Record<TicketField, string>> = {};
    mismatchFields.forEach((field) => {
      errors[field] = 'Este valor no coincide con el ticket pagado.';
    });

    this.fieldErrors = errors;
    return true;
  }

  private extractDetailCode(err: HttpErrorResponse): string {
    const detail = err?.error?.detail;
    if (!detail) return '';
    if (typeof detail?.code === 'string') return detail.code;
    if (typeof err?.error?.code === 'string') return err.error.code;
    return '';
  }

  private extractRetryAfterSeconds(err: HttpErrorResponse): number {
    const detail = err?.error?.detail;
    const fromBody = Number(detail?.retry_after_seconds ?? err?.error?.retry_after_seconds ?? 0);
    if (Number.isFinite(fromBody) && fromBody > 0) {
      return Math.ceil(fromBody);
    }

    const fromHeader = Number(err.headers?.get('Retry-After'));
    if (Number.isFinite(fromHeader) && fromHeader > 0) {
      return Math.ceil(fromHeader);
    }

    return 30;
  }

  private startRateLimitCountdown(seconds: number): void {
    const safeSeconds = Math.max(1, Math.ceil(seconds));
    this.rateLimitRemainingSeconds = safeSeconds;
    this.clearRateLimitTimer();

    this.rateLimitTimer = setInterval(() => {
      this.rateLimitRemainingSeconds = Math.max(0, this.rateLimitRemainingSeconds - 1);
      if (this.rateLimitRemainingSeconds === 0) {
        this.clearRateLimitTimer();
      }
    }, 1000);
  }

  private clearRateLimitTimer(): void {
    if (!this.rateLimitTimer) {
      return;
    }

    clearInterval(this.rateLimitTimer);
    this.rateLimitTimer = null;
  }

  private normalizeRFC(value: string): string {
    return value.trim().toUpperCase().replace(/\s+/g, '');
  }

  private normalizePlate(value: string): string {
    return value.trim().toUpperCase().replace(/[^A-Z0-9]/g, '');
  }

  private normalizeSpaces(value: string): string {
    return value.trim().replace(/\s+/g, ' ');
  }

  private onlyDigits(value: string): string {
    return value.replace(/\D+/g, '');
  }

  private formatFechaForApi(value: string): string | null {
    const input = value.trim();

    if (/^\d{4}-\d{2}-\d{2}$/.test(input)) {
      return input;
    }

    const ddmmyyyy = input.match(/^(\d{2})-(\d{2})-(\d{4})$/);
    if (ddmmyyyy) {
      const [, day, month, year] = ddmmyyyy;
      return `${year}-${month}-${day}`;
    }

    return null;
  }

  private formatHoraForApi(value: string): string | null {
    const input = value.trim();

    if (/^\d{2}:\d{2}:\d{2}$/.test(input)) {
      return input;
    }

    if (/^\d{2}:\d{2}$/.test(input)) {
      return `${input}:00`;
    }

    const amPm = input.match(/^(\d{1,2}):(\d{2})(?::(\d{2}))?\s?(AM|PM)$/i);
    if (amPm) {
      let hour = Number(amPm[1]);
      const minutes = amPm[2];
      const seconds = amPm[3] ?? '00';
      const period = amPm[4].toUpperCase();

      if (hour < 1 || hour > 12) {
        return null;
      }

      if (period === 'AM') {
        hour = hour === 12 ? 0 : hour;
      } else {
        hour = hour === 12 ? 12 : hour + 12;
      }

      return `${String(hour).padStart(2, '0')}:${minutes}:${seconds}`;
    }

    return null;
  }

  get fechaSalidaDisplay(): string {
    if (!this.form.fecha_salida) return '--/--/----';

    const apiDate = this.formatFechaForApi(this.form.fecha_salida);
    if (!apiDate) return '--/--/----';

    const [year, month, day] = apiDate.split('-');
    return `${day}-${month}-${year}`;
  }

  get horaSalidaDisplay(): string {
    if (!this.form.hora_salida) return '--:--:-- --';

    const apiTime = this.formatHoraForApi(this.form.hora_salida);
    if (!apiTime) return '--:--:-- --';

    const [h, m, s] = apiTime.split(':').map(v => Number(v));
    const period = h >= 12 ? 'PM' : 'AM';
    const hour12 = h % 12 === 0 ? 12 : h % 12;
    return `${String(hour12).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')} ${period}`;
  }

  private resetForm(formRef: NgForm): void {
    formRef.resetForm({
      rfc: '',
      history_estacionamiento_id: '',
      placa: '',
      fecha_salida: '',
      hora_salida: '',
      importe: '',
      send_email: true,
      notes: '',
    });
  }

  private saveLastInvoiceRequestId(invoiceRequestId: number): void {
    localStorage.setItem(this.lastInvoiceRequestIdKey, String(invoiceRequestId));
  }

}
