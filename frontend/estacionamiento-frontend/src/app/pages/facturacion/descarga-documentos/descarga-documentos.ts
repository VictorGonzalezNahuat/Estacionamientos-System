import { ChangeDetectorRef, Component, OnInit, inject } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { finalize } from 'rxjs/operators';
import { AlertService } from '../../../core/services/alert';
import { FacturacionService, InvoiceRequestStatusResponse } from '../../../services/facturacion.service';
import QRCode from 'qrcode';

@Component({
  selector: 'app-descarga-documentos',
  imports: [RouterModule],
  templateUrl: './descarga-documentos.html',
  styleUrl: './descarga-documentos.css',
})
export class DescargaDocumentos implements OnInit {
  private readonly lastInvoiceRequestIdKey = 'facturacion_last_invoice_request_id';
  private readonly dateFormatter = new Intl.DateTimeFormat('es-MX', {
    dateStyle: 'full',
    timeStyle: 'medium'
  });

  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private alert = inject(AlertService);
  private facturacionService = inject(FacturacionService);
  private cdr = inject(ChangeDetectorRef);

  invoiceRequestId: number | null = null;
  invoiceAccessToken: string | null = null;
  invoiceAccessTokenExpiresAt: string | null = null;
  statusInfo: InvoiceRequestStatusResponse | null = null;
  loadingStatus = false;
  downloadingXml = false;
  downloadingPdf = false;
  verificationQrDataUrl: string | null = null;
  generatingVerificationQr = false;

  ngOnInit(): void {
    this.invoiceRequestId = this.resolveInvoiceRequestId();

    if (!this.invoiceRequestId) {
      this.alert.error('No se encontro un invoice_request_id para descargar documentos.');
      void this.router.navigate(['/facturacion']);
      return;
    }

    const accessInfo = this.facturacionService.getInvoiceAccessToken(this.invoiceRequestId);
    if (!accessInfo) {
      this.alert.error('No se encontro un token de acceso vigente para esta solicitud. Emite la factura nuevamente para continuar.');
      void this.router.navigate(['/facturacion']);
      return;
    }

    this.invoiceAccessToken = accessInfo.accessToken;
    this.invoiceAccessTokenExpiresAt = accessInfo.expiresAt;

    this.loadStatus();
  }

  downloadXml(): void {
    if (!this.invoiceRequestId || !this.invoiceAccessToken || this.downloadingXml || !this.statusInfo?.documents_ready) return;

    this.downloadingXml = true;
    this.cdr.detectChanges();

    this.facturacionService.downloadInvoiceXml(this.invoiceRequestId, this.invoiceAccessToken)
      .pipe(finalize(() => {
        this.downloadingXml = false;
        this.cdr.detectChanges();
      }))
      .subscribe({
      next: (blob) => {
        this.downloadBlob(blob, `factura-${this.invoiceRequestId}.xml`);
      },
      error: (err: HttpErrorResponse) => {
        if (this.handleTokenAuthError(err, 'descargar XML')) {
          return;
        }
        this.alert.error(this.buildErrorMessage(err, 'No se pudo descargar el XML.'));
      }
    });
  }

  downloadPdf(): void {
    if (!this.invoiceRequestId || !this.invoiceAccessToken || this.downloadingPdf || !this.statusInfo?.documents_ready) return;

    this.downloadingPdf = true;
    this.cdr.detectChanges();

    this.facturacionService.downloadInvoicePdf(this.invoiceRequestId, this.invoiceAccessToken)
      .pipe(finalize(() => {
        this.downloadingPdf = false;
        this.cdr.detectChanges();
      }))
      .subscribe({
      next: (blob) => {
        this.downloadBlob(blob, `factura-${this.invoiceRequestId}.pdf`);
      },
      error: (err: HttpErrorResponse) => {
        if (this.handleTokenAuthError(err, 'descargar PDF')) {
          return;
        }
        this.alert.error(this.buildErrorMessage(err, 'No se pudo descargar el PDF.'));
      }
    });
  }

  private loadStatus(): void {
    if (!this.invoiceRequestId || !this.invoiceAccessToken) return;

    this.loadingStatus = true;
    this.cdr.detectChanges();

    this.facturacionService.getInvoiceRequestStatus(this.invoiceRequestId, this.invoiceAccessToken)
      .pipe(finalize(() => {
        this.loadingStatus = false;
        this.cdr.detectChanges();
      }))
      .subscribe({
      next: (statusInfo) => {
        this.statusInfo = statusInfo;
        void this.refreshVerificationQr(this.getVerificationUrl(statusInfo));
      },
      error: (err: HttpErrorResponse) => {
        if (this.handleTokenAuthError(err, 'consultar el estado de la solicitud')) {
          return;
        }

        this.alert.error(this.buildErrorMessage(err, 'No se pudo obtener el estado de la solicitud de factura.'));
        this.statusInfo = null;
        this.verificationQrDataUrl = null;
      }
    });
  }

  private async refreshVerificationQr(verificationUrl: string | null): Promise<void> {
    if (!verificationUrl) {
      this.verificationQrDataUrl = null;
      this.generatingVerificationQr = false;
      this.cdr.detectChanges();
      return;
    }

    this.generatingVerificationQr = true;
    this.verificationQrDataUrl = null;
    this.cdr.detectChanges();

    try {
      this.verificationQrDataUrl = await QRCode.toDataURL(verificationUrl, {
        errorCorrectionLevel: 'M',
        margin: 2,
        width: 320,
      });
    } catch {
      this.verificationQrDataUrl = null;
      this.alert.error('No se pudo generar el codigo QR de verificacion.');
    } finally {
      this.generatingVerificationQr = false;
      this.cdr.detectChanges();
    }
  }

  get verificationUrl(): string | null {
    return this.getVerificationUrl(this.statusInfo);
  }

  private getVerificationUrl(statusInfo: InvoiceRequestStatusResponse | null): string | null {
    if (!statusInfo) {
      return null;
    }

    const rawValue = (statusInfo as any).verification_url ?? (statusInfo as any).verificationUrl;
    if (typeof rawValue !== 'string') {
      return null;
    }

    const trimmed = rawValue.trim();
    return trimmed.length > 0 ? trimmed : null;
  }

  formatDateTime(value: string | null): string {
    if (!value) {
      return 'No disponible';
    }

    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return value;
    }

    return this.dateFormatter.format(date);
  }

  isCompletedStatus(value: string | null): boolean {
    if (!value) {
      return false;
    }

    const normalized = value.trim().toLowerCase();
    return ['timbrada', 'timbrado', 'completed', 'issued', 'success', 'finalizado', 'done'].includes(normalized);
  }

  displayStatusLabel(value: string | null): string {
    if (!value) {
      return 'No disponible';
    }

    const normalized = value.trim().toLowerCase();

    if (normalized === 'issued') {
      return 'EMITIDO';
    }

    return value;
  }

  private resolveInvoiceRequestId(): number | null {
    const queryValue = this.route.snapshot.queryParamMap.get('invoiceRequestId');
    const fromQuery = Number(queryValue);

    if (queryValue && !Number.isNaN(fromQuery) && fromQuery > 0) {
      localStorage.setItem(this.lastInvoiceRequestIdKey, String(fromQuery));
      return fromQuery;
    }

    const localValue = localStorage.getItem(this.lastInvoiceRequestIdKey);
    const fromLocal = Number(localValue);
    if (localValue && !Number.isNaN(fromLocal) && fromLocal > 0) {
      return fromLocal;
    }

    return null;
  }

  private handleTokenAuthError(err: HttpErrorResponse, actionLabel: string): boolean {
    if (!this.invoiceRequestId || (err.status !== 401 && err.status !== 403)) {
      return false;
    }

    this.facturacionService.clearInvoiceAccessToken(this.invoiceRequestId);
    this.statusInfo = null;
    this.invoiceAccessToken = null;
    this.invoiceAccessTokenExpiresAt = null;
    this.alert.error(`No fue posible ${actionLabel} porque el token de acceso expiro o no coincide con la solicitud. Emite la factura nuevamente para recuperar acceso.`);
    void this.router.navigate(['/facturacion']);
    return true;
  }

  private downloadBlob(blob: Blob, fileName: string): void {
    const blobUrl = window.URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = blobUrl;
    anchor.download = fileName;
    anchor.style.display = 'none';
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
    window.URL.revokeObjectURL(blobUrl);
  }

  private buildErrorMessage(err: HttpErrorResponse, fallback: string): string {
    const detail = err?.error?.detail;

    if (typeof detail === 'string' && detail.trim().length > 0) {
      return detail;
    }

    if (detail && typeof detail?.message === 'string' && detail.message.trim().length > 0) {
      return detail.message;
    }

    const message = err?.error?.message;
    if (typeof message === 'string' && message.trim().length > 0) {
      return message;
    }

    return fallback;
  }

}
