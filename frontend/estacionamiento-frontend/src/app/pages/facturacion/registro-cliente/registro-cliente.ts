import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, NgForm } from '@angular/forms';
import { Router } from '@angular/router';
import { HttpErrorResponse } from '@angular/common/http';
import { AlertService } from '../../../core/services/alert';
import { FacturacionService, FiscalClientCreatePayload } from '../../../services/facturacion.service';

@Component({
  selector: 'app-registro-cliente',
  imports: [CommonModule, FormsModule],
  templateUrl: './registro-cliente.html',
  styleUrl: './registro-cliente.css',
})
export class RegistroCliente {
  private facturacionService = inject(FacturacionService);
  private alert = inject(AlertService);
  private router = inject(Router);

  isSubmitting = false;

  readonly regimenFiscalOptions = [
    { code: '601', label: 'General de Ley Personas Morales' },
    { code: '603', label: 'Personas Morales con Fines no Lucrativos' },
    { code: '605', label: 'Sueldos y Salarios e Ingresos Asimilados a Salarios' },
    { code: '606', label: 'Arrendamiento' },
    { code: '612', label: 'Personas Fisicas con Actividades Empresariales y Profesionales' },
    { code: '614', label: 'Ingresos por intereses' },
    { code: '616', label: 'Sin obligaciones fiscales' },
    { code: '621', label: 'Incorporacion Fiscal' },
    { code: '625', label: 'Regimen de las Actividades Empresariales con ingresos a traves de plataformas tecnologicas' },
    { code: '626', label: 'Regimen Simplificado de Confianza' },
  ] as const;

  readonly usoCfdiReceptorOptions = [
    { code: 'G01', label: 'Adquisicion de mercancias' },
    { code: 'G02', label: 'Devoluciones, descuentos o bonificaciones' },
    { code: 'G03', label: 'Gastos en general' },
    { code: 'I01', label: 'Construcciones' },
    { code: 'I02', label: 'Mobiliario y equipo de oficina por inversiones' },
    { code: 'I03', label: 'Equipo de transporte' },
    { code: 'D01', label: 'Honorarios medicos, dentales y gastos hospitalarios' },
    { code: 'D02', label: 'Gastos medicos por incapacidad o discapacidad' },
    { code: 'S01', label: 'Sin efectos fiscales' },
  ] as const;

  form: FiscalClientCreatePayload = {
    rfc: '',
    razon_social: '',
    codigo_postal: '',
    regimen_fiscal: '',
    uso_cfdi_receptor: 'G03',
    nombre_contacto: '',
    email: '',
    telefono: '',
  };

  readonly requiredFieldsTotal = 8;

  onRFCChange(value: string): void {
    this.form.rfc = value.toUpperCase().replace(/\s+/g, '').slice(0, 13);
  }

  onCodigoPostalChange(value: string): void {
    this.form.codigo_postal = this.onlyDigits(value).slice(0, 5);
  }

  onRegimenFiscalChange(value: string): void {
    this.form.regimen_fiscal = this.onlyDigits(value).slice(0, 3);
  }

  onUsoCfdiChange(value: string): void {
    this.form.uso_cfdi_receptor = value.toUpperCase().replace(/\s+/g, '').slice(0, 3);
  }

  onTelefonoChange(value: string): void {
    this.form.telefono = this.onlyDigits(value).slice(0, 10);
  }

  get requiredFieldsCompleted(): number {
    const requiredValues = [
      this.form.rfc,
      this.form.razon_social,
      this.form.codigo_postal,
      this.form.regimen_fiscal,
      this.form.uso_cfdi_receptor,
      this.form.nombre_contacto,
      this.form.email,
      this.form.telefono,
    ];

    return requiredValues.filter((value) => value.trim().length > 0).length;
  }

  get completionPercent(): number {
    return Math.round((this.requiredFieldsCompleted / this.requiredFieldsTotal) * 100);
  }

  get normalizedRfcPreview(): string {
    const normalized = this.normalizeRFC(this.form.rfc);
    return normalized || 'Sin capturar';
  }

  get normalizedUsoCfdiPreview(): string {
    const value = this.form.uso_cfdi_receptor.trim().toUpperCase();
    return value || 'Sin capturar';
  }

  get formattedPhonePreview(): string {
    const digits = this.onlyDigits(this.form.telefono);

    if (!digits) {
      return 'Sin capturar';
    }

    if (digits.length < 10) {
      return digits;
    }

    return `${digits.slice(0, 3)} ${digits.slice(3, 6)} ${digits.slice(6, 10)}`;
  }

  onSubmit(formRef: NgForm): void {
    if (this.isSubmitting) return;

    if (formRef.invalid) {
      this.alert.error('Completa correctamente todos los campos requeridos antes de continuar.');
      return;
    }

    const payload = {
      ...this.form,
      rfc: this.normalizeRFC(this.form.rfc),
      razon_social: this.normalizeSpaces(this.form.razon_social),
      codigo_postal: this.onlyDigits(this.form.codigo_postal),
      regimen_fiscal: this.normalizeSpaces(this.form.regimen_fiscal),
      uso_cfdi_receptor: this.form.uso_cfdi_receptor.trim().toUpperCase(),
      nombre_contacto: this.normalizeSpaces(this.form.nombre_contacto),
      email: this.form.email.trim().toLowerCase(),
      telefono: this.onlyDigits(this.form.telefono),
    } satisfies FiscalClientCreatePayload;

    this.isSubmitting = true;

    this.facturacionService.createFiscalClient(payload).subscribe({
      next: () => {
        this.alert.success('Cliente fiscal registrado exitosamente', () => {
          void this.router.navigate(['/facturacion']);
        });
        this.isSubmitting = false;
      },
      error: (err: HttpErrorResponse) => {
        const message = this.buildApiErrorMessage(err);
        this.alert.error(message);
        this.isSubmitting = false;
      }
    });
  }

  goBack(): void {
    void this.router.navigate(['/facturacion']);
  }

  private buildApiErrorMessage(err: HttpErrorResponse): string {
    const detail = err?.error?.detail;

    if (typeof detail === 'string' && detail.trim().length > 0) {
      return detail;
    }

    if (Array.isArray(detail) && detail.length > 0) {
      const lines = detail
        .map((item: any) => {
          const field = Array.isArray(item?.loc) ? item.loc[item.loc.length - 1] : 'campo';
          const msg = typeof item?.msg === 'string' ? item.msg : 'valor invalido';
          return `${field}: ${msg}`;
        })
        .join('\n');

      return `No se pudo registrar el cliente:\n${lines}`;
    }

    const fallback = err?.error?.message;
    if (typeof fallback === 'string' && fallback.trim().length > 0) {
      return fallback;
    }

    return 'No se pudo registrar el cliente fiscal. Verifica la informacion e intenta nuevamente.';
  }

  private normalizeRFC(value: string): string {
    return value.trim().toUpperCase().replace(/\s+/g, '');
  }

  private normalizeSpaces(value: string): string {
    return value.trim().replace(/\s+/g, ' ');
  }

  private onlyDigits(value: string): string {
    return value.replace(/\D+/g, '').trim();
  }

}
