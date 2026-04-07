import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { ConfigService } from './config.service';

export interface FiscalClientCreatePayload {
  rfc: string;
  razon_social: string;
  codigo_postal: string;
  regimen_fiscal: string;
  uso_cfdi_receptor: string;
  nombre_contacto: string;
  email: string;
  telefono: string;
}

export interface FiscalClientRegisterWithTicketPayload extends FiscalClientCreatePayload {
  history_estacionamiento_id: number;
  placa: string;
  fecha_salida: string;
  hora_salida: string;
  importe: number;
  recaptcha_token: string;
}

export interface FiscalClientResponse extends FiscalClientCreatePayload {
  id: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface EmitFacturaPayload {
  fiscal_customer_id: number;
  history_estacionamiento_id: number;
  placa: string;
  fecha_salida: string;
  hora_salida: string;
  importe: number;
  send_email: boolean;
  notes: string;
  recaptcha_token: string;
}

export interface EmitFacturaResponse {
  invoice_request_id: number;
  status: string;
  fiscal_customer_id: number;
  source_type: string;
  source_id: string;
  idempotency_key: string;
  created_at: string;
  message: string;
  access_token: string;
  access_token_expires_at: string;
}

export interface InvoiceRequestStatusResponse {
  invoice_request_id: number;
  status: string;
  total: number | null;
  currency: string | null;
  verification_url: string | null;
  issued_at: string | null;
  documents_ready: boolean;
  can_cancel: boolean;
  attempts: number;
  created_at: string;
  updated_at: string;
}

export interface StoredInvoiceAccess {
  accessToken: string;
  expiresAt: string;
}

@Injectable({
  providedIn: 'root'
})
export class FacturacionService {
  private readonly invoiceAccessTokenPrefix = 'facturacion_invoice_access_token_';
  private readonly invoiceAccessTokenExpiryPrefix = 'facturacion_invoice_access_token_exp_';

  private http = inject(HttpClient);
  private configService = inject(ConfigService);

  createFiscalClient(payload: FiscalClientCreatePayload) {
    return this.http.post<FiscalClientResponse>(
      `${this.configService.apiUrl}/facturacion/clientes-fiscales`,
      payload
    );
  }

  createFiscalClientWithTicket(payload: FiscalClientRegisterWithTicketPayload) {
    return this.http.post<FiscalClientResponse>(
      `${this.configService.apiUrl}/facturacion/clientes-fiscales`,
      payload
    );
  }

  getFiscalCustomerByRFC(rfc: string) {
    return this.http.get<FiscalClientResponse>(
      `${this.configService.apiUrl}/facturacion/clientes-fiscales/por-rfc/${encodeURIComponent(rfc)}`
    );
  }

  emitirFactura(payload: EmitFacturaPayload) {
    return this.http.post<EmitFacturaResponse>(
      `${this.configService.apiUrl}/facturacion/emitir`,
      payload
    );
  }

  getInvoiceRequestStatus(invoiceRequestId: number, accessToken: string) {
    return this.http.get<InvoiceRequestStatusResponse>(
      `${this.configService.apiUrl}/facturacion/solicitudes/${invoiceRequestId}`,
      { headers: this.buildInvoiceAccessHeaders(accessToken) }
    );
  }

  cancelInvoiceRequest(invoiceRequestId: number, accessToken: string) {
    return this.http.post(
      `${this.configService.apiUrl}/facturacion/solicitudes/${invoiceRequestId}/cancelar`,
      {},
      { headers: this.buildInvoiceAccessHeaders(accessToken) }
    );
  }

  downloadInvoiceXml(invoiceRequestId: number, accessToken: string) {
    return this.http.get(
      `${this.configService.apiUrl}/facturacion/solicitudes/${invoiceRequestId}/xml`,
      {
        headers: this.buildInvoiceAccessHeaders(accessToken),
        responseType: 'blob'
      }
    );
  }

  downloadInvoicePdf(invoiceRequestId: number, accessToken: string) {
    return this.http.get(
      `${this.configService.apiUrl}/facturacion/solicitudes/${invoiceRequestId}/pdf`,
      {
        headers: this.buildInvoiceAccessHeaders(accessToken),
        responseType: 'blob'
      }
    );
  }

  saveInvoiceAccessToken(invoiceRequestId: number, accessToken: string, expiresAt: string): void {
    if (!this.canUseStorage() || !accessToken || !expiresAt) {
      return;
    }

    sessionStorage.setItem(`${this.invoiceAccessTokenPrefix}${invoiceRequestId}`, accessToken);
    sessionStorage.setItem(`${this.invoiceAccessTokenExpiryPrefix}${invoiceRequestId}`, expiresAt);
  }

  getInvoiceAccessToken(invoiceRequestId: number): StoredInvoiceAccess | null {
    if (!this.canUseStorage()) {
      return null;
    }

    const accessToken = sessionStorage.getItem(`${this.invoiceAccessTokenPrefix}${invoiceRequestId}`);
    const expiresAt = sessionStorage.getItem(`${this.invoiceAccessTokenExpiryPrefix}${invoiceRequestId}`);

    if (!accessToken || !expiresAt) {
      return null;
    }

    if (this.isExpired(expiresAt)) {
      this.clearInvoiceAccessToken(invoiceRequestId);
      return null;
    }

    return { accessToken, expiresAt };
  }

  clearInvoiceAccessToken(invoiceRequestId: number): void {
    if (!this.canUseStorage()) {
      return;
    }

    sessionStorage.removeItem(`${this.invoiceAccessTokenPrefix}${invoiceRequestId}`);
    sessionStorage.removeItem(`${this.invoiceAccessTokenExpiryPrefix}${invoiceRequestId}`);
  }

  private buildInvoiceAccessHeaders(accessToken: string): Record<string, string> {
    return {
      'X-Invoice-Access-Token': accessToken
    };
  }

  private isExpired(expiresAt: string): boolean {
    const expiresAtDate = new Date(expiresAt);
    if (Number.isNaN(expiresAtDate.getTime())) {
      return true;
    }

    return Date.now() >= expiresAtDate.getTime();
  }

  private canUseStorage(): boolean {
    return typeof window !== 'undefined' && typeof sessionStorage !== 'undefined';
  }
}
