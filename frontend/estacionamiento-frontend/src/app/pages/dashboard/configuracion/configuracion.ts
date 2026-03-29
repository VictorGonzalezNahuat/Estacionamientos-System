import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { firstValueFrom } from 'rxjs';
import { ConfigService, SystemConfigResponse, SystemConfigUpdate } from '../../../services/config.service';
import { AlertService } from '../../../core/services/alert';
import { AuthService } from '../../../services/auth.service';

@Component({
  selector: 'app-configuracion',
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './configuracion.html',
  styleUrl: './configuracion.css',
})
export class Configuracion implements OnInit {
  private fb = inject(FormBuilder);
  private configService = inject(ConfigService);
  private alertService = inject(AlertService);
  private authService = inject(AuthService);
  private cdr = inject(ChangeDetectorRef);

  configForm!: FormGroup;
  isLoading = true;
  isSaving = false;

  ngOnInit() {
    this.initializeForm();
    this.loadConfig();
  }

  private initializeForm() {
    this.configForm = this.fb.group({
      DATABASE_CLOUD_USER: ['', Validators.required],
      DATABASE_CLOUD_PASSWORD: ['', Validators.required],
      DATABASE_CLOUD_HOST: ['', Validators.required],
      DATABASE_CLOUD_PORT: [1, [Validators.required, Validators.min(1)]],
      DATABASE_CLOUD_NAME: ['', Validators.required],
      SYNC_AUTO_ENABLED: [false, Validators.required],
      MOBILE_PRINT: [false, Validators.required],
      SYNC_INTERVAL_MINUTES: [1, [Validators.required, Validators.min(1)]],
      ENTRY_TICKET_CODE_TYPE: ['', Validators.required],
      PUBLIC_STATUS_BASE_URL: ['', Validators.required],
    });
  }

  private loadConfig() {
    this.isLoading = true;
    this.configService.getSystemConfig().subscribe({
      next: (config: SystemConfigResponse) => {
        this.configForm.patchValue({
          ...config,
          DATABASE_CLOUD_PASSWORD: ''
        });
        this.isLoading = false;
        this.cdr.detectChanges();
      },
      error: (error) => {
        console.error('Error cargando configuración:', error);
        this.alertService.error('Error al cargar la configuración del sistema');
        this.isLoading = false;
        this.cdr.detectChanges();
      }
    });
  }

  async onSubmit() {
    if (this.configForm.invalid) {
      this.configForm.markAllAsTouched();
      this.alertService.error('Por favor completa todos los campos requeridos');
      return;
    }

    const adminPassword = await this.alertService.requestPassword(
      'Confirmar cambios de configuración',
      'Ingresa la contraseña del administrador en sesión para autorizar la actualización'
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
      this.alertService.error('La contraseña del administrador es incorrecta');
      return;
    }

    this.isSaving = true;
    const configData: SystemConfigUpdate = this.configForm.value;

    this.configService.updateSystemConfig(configData).subscribe({
      next: (response) => {
        this.alertService.success('Configuración actualizada exitosamente');
        this.configForm.patchValue({
          ...response,
          DATABASE_CLOUD_PASSWORD: ''
        });
        this.isSaving = false;
      },
      error: (error) => {
        console.error('Error actualizando configuración:', error);
        this.alertService.error('Error al actualizar la configuración del sistema');
        this.isSaving = false;
      }
    });
  }

  onReset() {
    this.loadConfig();
  }
}
