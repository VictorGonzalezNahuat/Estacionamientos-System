import { ChangeDetectorRef, Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { firstValueFrom } from 'rxjs';
import { AlertService } from '../../../core/services/alert';
import { AuthService } from '../../../services/auth.service';
import { ConfigService, CortesConfigResponse, CortesConfigUpdate } from '../../../services/config.service';

@Component({
  selector: 'app-configuracion-cortes',
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './configuracion-cortes.html',
  styleUrl: './configuracion-cortes.css',
})
export class ConfiguracionCortes implements OnInit {
  private fb = inject(FormBuilder);
  private configService = inject(ConfigService);
  private alertService = inject(AlertService);
  private authService = inject(AuthService);
  private cdr = inject(ChangeDetectorRef);

  configForm!: FormGroup;
  isLoading = true;
  isSaving = false;
  isSmtpPasswordVisible = false;

  ngOnInit(): void {
    this.initializeForm();
    this.loadConfig();
  }

  private initializeForm(): void {
    this.configForm = this.fb.group({
      AUTOSEND_REPORT: [false],
      SMTP_HOST: ['', [Validators.required]],
      SMTP_PORT: [1, [Validators.required, Validators.min(1)]],
      SMTP_USERNAME: ['', [Validators.required]],
      SMTP_PASSWORD: ['', [Validators.required]],
      SMTP_USE_TLS: [true],
      SMTP_TIMEOUT_SECONDS: [1, [Validators.required, Validators.min(1)]],
      REPORT_FROM_NAME: ['', [Validators.required]],
      REPORT_SUBJECT_TEMPLATE: ['', [Validators.required]],
    });
  }

  private loadConfig(): void {
    this.isLoading = true;
    this.configService.getCortesConfig().subscribe({
      next: (config: CortesConfigResponse) => {
        this.configForm.patchValue({
          ...config,
          SMTP_PORT: this.normalizePositiveInt(config.SMTP_PORT),
          SMTP_TIMEOUT_SECONDS: this.normalizePositiveInt(config.SMTP_TIMEOUT_SECONDS),
          SMTP_PASSWORD: '',
        });
        this.isLoading = false;
        this.cdr.detectChanges();
      },
      error: (error) => {
        console.error('Error cargando configuración de cortes:', error);
        this.alertService.error('Error al cargar la configuración de cortes de caja');
        this.isLoading = false;
        this.cdr.detectChanges();
      }
    });
  }

  async onSubmit(): Promise<void> {
    if (!this.isFormValid()) {
      this.alertService.error('Completa todos los campos obligatorios con valores válidos');
      return;
    }

    const adminPassword = await this.alertService.requestPassword(
      'Confirmar cambios de configuración de cortes',
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
      const smtpPort = Number(this.configForm.get('SMTP_PORT')?.value);
      const smtpTimeoutSeconds = Number(this.configForm.get('SMTP_TIMEOUT_SECONDS')?.value);

      if (!Number.isFinite(smtpPort) || smtpPort < 1 || !Number.isFinite(smtpTimeoutSeconds) || smtpTimeoutSeconds < 1) {
        this.alertService.error('SMTP_PORT y SMTP_TIMEOUT_SECONDS deben ser números mayores a 0');
        this.isSaving = false;
        return;
      }

      const payload: CortesConfigUpdate = {
        AUTOSEND_REPORT: Boolean(this.configForm.get('AUTOSEND_REPORT')?.value),
        SMTP_HOST: String(this.configForm.get('SMTP_HOST')?.value ?? '').trim(),
        SMTP_PORT: smtpPort,
        SMTP_USERNAME: String(this.configForm.get('SMTP_USERNAME')?.value ?? '').trim(),
        SMTP_PASSWORD: String(this.configForm.get('SMTP_PASSWORD')?.value ?? ''),
        SMTP_USE_TLS: Boolean(this.configForm.get('SMTP_USE_TLS')?.value),
        SMTP_TIMEOUT_SECONDS: smtpTimeoutSeconds,
        REPORT_FROM_NAME: String(this.configForm.get('REPORT_FROM_NAME')?.value ?? '').trim(),
        REPORT_SUBJECT_TEMPLATE: String(this.configForm.get('REPORT_SUBJECT_TEMPLATE')?.value ?? '').trim(),
      };

      const response = await firstValueFrom(this.configService.updateCortesConfig(payload));

      this.configForm.patchValue({
        ...response,
        SMTP_PORT: this.normalizePositiveInt(response.SMTP_PORT),
        SMTP_TIMEOUT_SECONDS: this.normalizePositiveInt(response.SMTP_TIMEOUT_SECONDS),
        SMTP_PASSWORD: '',
      });

      this.alertService.success('Configuración de cortes actualizada exitosamente');
      this.isSaving = false;
    } catch (error) {
      console.error('Error actualizando configuración de cortes:', error);
      this.alertService.error('Error al actualizar la configuración de cortes de caja');
      this.isSaving = false;
    }
  }

  isFormValid(): boolean {
    const requiredFields = ['SMTP_HOST', 'SMTP_USERNAME', 'SMTP_PASSWORD', 'REPORT_FROM_NAME', 'REPORT_SUBJECT_TEMPLATE'];
    const requiredOk = requiredFields.every((field) => {
      const value = this.configForm.get(field)?.value;
      return value !== null && value !== undefined && String(value).trim() !== '';
    });

    const smtpPort = Number(this.configForm.get('SMTP_PORT')?.value);
    const smtpTimeoutSeconds = Number(this.configForm.get('SMTP_TIMEOUT_SECONDS')?.value);

    return requiredOk && Number.isFinite(smtpPort) && smtpPort > 0 && Number.isFinite(smtpTimeoutSeconds) && smtpTimeoutSeconds > 0;
  }

  onReset(): void {
    this.loadConfig();
  }

  toggleSmtpPasswordVisibility(): void {
    this.isSmtpPasswordVisible = !this.isSmtpPasswordVisible;
  }

  private normalizePositiveInt(value: unknown): number {
    const numericValue = Number(value);
    if (!Number.isFinite(numericValue) || numericValue < 1) {
      return 1;
    }

    return Math.floor(numericValue);
  }

}
