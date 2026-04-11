import { ChangeDetectorRef, Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { firstValueFrom } from 'rxjs';
import { AlertService } from '../../../core/services/alert';
import { AuthService } from '../../../services/auth.service';
import { ConfigService, PrinterConfigResponse, PrinterConfigUpdate } from '../../../services/config.service';

@Component({
  selector: 'app-configuracion-impresora',
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './configuracion-impresora.html',
  styleUrl: './configuracion-impresora.css',
})
export class ConfiguracionImpresora implements OnInit {
  private fb = inject(FormBuilder);
  private configService = inject(ConfigService);
  private alertService = inject(AlertService);
  private authService = inject(AuthService);
  private cdr = inject(ChangeDetectorRef);

  configForm!: FormGroup;
  isLoading = true;
  isSaving = false;

  ngOnInit(): void {
    this.initializeForm();
    this.loadConfig();
  }

  private initializeForm(): void {
    this.configForm = this.fb.group({
      method: ['NETWORK', [Validators.required]],
      network_host: ['', [Validators.required]],
      network_port: [9100, [Validators.required, Validators.min(1)]],
      network_timeout: [10, [Validators.required, Validators.min(1)]],
      usb_mode: ['WINDOWS_DEFAULT', [Validators.required]],
      usb_printer_name: [''],
    });
  }

  private loadConfig(): void {
    this.isLoading = true;
    this.configService.getPrinterConfig().subscribe({
      next: (config: PrinterConfigResponse) => {
        this.configForm.patchValue({
          method: this.normalizeMethod(config.method),
          network_host: String(config.network?.host ?? ''),
          network_port: this.normalizePositiveInt(config.network?.port, 9100),
          network_timeout: this.normalizePositiveInt(config.network?.timeout, 10),
          usb_mode: String(config.usb?.mode ?? 'WINDOWS_DEFAULT').trim() || 'WINDOWS_DEFAULT',
          usb_printer_name: String(config.usb?.printer_name ?? ''),
        });
        this.isLoading = false;
        this.cdr.detectChanges();
      },
      error: (error) => {
        console.error('Error cargando configuración de impresora:', error);
        this.alertService.error('Error al cargar la configuración de impresora');
        this.isLoading = false;
        this.cdr.detectChanges();
      },
    });
  }

  async onSubmit(): Promise<void> {
    if (!this.isFormValid()) {
      this.alertService.error('Completa los campos requeridos con valores válidos');
      return;
    }

    const adminPassword = await this.alertService.requestPassword(
      'Confirmar cambios de configuración de impresora',
      'Ingresa la contraseña del usuario para autorizar la actualización'
    );

    if (!adminPassword) {
      return;
    }

    let currentUserCode: string;
    try {
      const currentUser = await firstValueFrom(this.authService.getCurrentUser());
      currentUserCode = String(currentUser?.codigo ?? '');
      await firstValueFrom(
        this.authService.login({
          username: currentUserCode,
          password: adminPassword,
        })
      );
    } catch {
      this.alertService.error('La contraseña es incorrecta');
      return;
    }

    this.isSaving = true;

    try {
      const networkPort = Number(this.configForm.get('network_port')?.value);
      const networkTimeout = Number(this.configForm.get('network_timeout')?.value);

      if (!Number.isFinite(networkPort) || networkPort < 1 || !Number.isFinite(networkTimeout) || networkTimeout < 1) {
        this.alertService.error('Puerto y timeout de red deben ser números mayores a 0');
        this.isSaving = false;
        return;
      }

      const payload: PrinterConfigUpdate = {
        method: this.normalizeMethod(this.configForm.get('method')?.value),
        network: {
          host: String(this.configForm.get('network_host')?.value ?? '').trim(),
          port: networkPort,
          timeout: networkTimeout,
        },
        usb: {
          mode: String(this.configForm.get('usb_mode')?.value ?? 'WINDOWS_DEFAULT').trim() || 'WINDOWS_DEFAULT',
          printer_name: String(this.configForm.get('usb_printer_name')?.value ?? '').trim(),
        },
      };

      if (payload.method === 'NETWORK' && payload.network.host === '') {
        this.alertService.error('El host de red es obligatorio cuando el método es NETWORK');
        this.isSaving = false;
        return;
      }

      if (payload.method === 'USB' && payload.usb.mode !== 'WINDOWS_DEFAULT' && payload.usb.printer_name === '') {
        this.alertService.error('El nombre de impresora USB es obligatorio para el modo seleccionado');
        this.isSaving = false;
        return;
      }

      const response = await firstValueFrom(this.configService.updatePrinterConfig(payload));

      this.configForm.patchValue({
        method: this.normalizeMethod(response.method),
        network_host: String(response.network?.host ?? ''),
        network_port: this.normalizePositiveInt(response.network?.port, 9100),
        network_timeout: this.normalizePositiveInt(response.network?.timeout, 10),
        usb_mode: String(response.usb?.mode ?? 'WINDOWS_DEFAULT').trim() || 'WINDOWS_DEFAULT',
        usb_printer_name: String(response.usb?.printer_name ?? ''),
      });

      this.alertService.success('Configuración de impresora actualizada exitosamente');
      this.isSaving = false;
    } catch (error) {
      console.error('Error actualizando configuración de impresora:', error);
      this.alertService.error('Error al actualizar la configuración de impresora');
      this.isSaving = false;
    }
  }

  isFormValid(): boolean {
    const method = this.normalizeMethod(this.configForm.get('method')?.value);
    const networkPort = Number(this.configForm.get('network_port')?.value);
    const networkTimeout = Number(this.configForm.get('network_timeout')?.value);
    const usbMode = String(this.configForm.get('usb_mode')?.value ?? 'WINDOWS_DEFAULT').trim() || 'WINDOWS_DEFAULT';
    const usbPrinterName = String(this.configForm.get('usb_printer_name')?.value ?? '').trim();

    const validNetworkNumbers = Number.isFinite(networkPort) && networkPort > 0 && Number.isFinite(networkTimeout) && networkTimeout > 0;

    if (!validNetworkNumbers || !usbMode) {
      return false;
    }

    if (method === 'NETWORK') {
      const host = String(this.configForm.get('network_host')?.value ?? '').trim();
      return host !== '';
    }

    if (method === 'USB' && usbMode !== 'WINDOWS_DEFAULT') {
      return usbPrinterName !== '';
    }

    return true;
  }

  onReset(): void {
    this.loadConfig();
  }

  isNetworkMethod(): boolean {
    return this.normalizeMethod(this.configForm.get('method')?.value) === 'NETWORK';
  }

  isUsbMethod(): boolean {
    return this.normalizeMethod(this.configForm.get('method')?.value) === 'USB';
  }

  private normalizeMethod(value: unknown): string {
    const method = String(value ?? '').trim().toUpperCase();
    return method === 'USB' ? 'USB' : 'NETWORK';
  }

  private normalizePositiveInt(value: unknown, fallback: number): number {
    const numericValue = Number(value);
    if (!Number.isFinite(numericValue) || numericValue < 1) {
      return fallback;
    }

    return Math.floor(numericValue);
  }

}
