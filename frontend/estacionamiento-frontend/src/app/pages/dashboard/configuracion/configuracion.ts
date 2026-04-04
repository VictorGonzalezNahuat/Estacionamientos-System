import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { firstValueFrom } from 'rxjs';
import { ConfigService, SystemConfigResponse, GeneralConfigUpdate, DatabaseConfigUpdate } from '../../../services/config.service';
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
  isSavingDatabase = false;
  isSavingGeneral = false;
  isPublicStatusUrlVisible = false;
  dbFieldVisibility: Record<string, boolean> = {
    DATABASE_CLOUD_USER: false,
    DATABASE_CLOUD_PASSWORD: false,
    DATABASE_CLOUD_HOST: false,
    DATABASE_CLOUD_PORT: false,
    DATABASE_CLOUD_NAME: false,
  };

  ngOnInit() {
    this.initializeForm();
    this.loadConfig();
  }

  private initializeForm() {
    this.configForm = this.fb.group({
      // Configuración General (PATCH /)
      SYNC_AUTO_ENABLED: [false],
      MOBILE_PRINT: [false],
      SYNC_INTERVAL_MINUTES: [1, [Validators.min(1)]],
      ENTRY_TICKET_CODE_TYPE: [''],
      PUBLIC_STATUS_BASE_URL: [''],
      AVISO_ENTRADA: [''],
      AVISO_SALIDA: [''],
      // Configuración de Base de Datos (PATCH /base-datos) - todos opcionales
      DATABASE_CLOUD_USER: [''],
      DATABASE_CLOUD_PASSWORD: [''],
      DATABASE_CLOUD_HOST: [''],
      DATABASE_CLOUD_PORT: [1, [Validators.min(1)]],
      DATABASE_CLOUD_NAME: [''],
    });
  }

  private loadConfig() {
    this.isLoading = true;
    this.configService.getSystemConfig().subscribe({
      next: (config: SystemConfigResponse) => {
        const avisoEntrada = this.fromApiNewlines(config.AVISO_ENTRADA);
        const avisoSalida = this.fromApiNewlines(config.AVISO_SALIDA);

        this.configForm.patchValue({
          ...config,
          AVISO_ENTRADA: avisoEntrada,
          AVISO_SALIDA: avisoSalida,
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

  async onSubmitDatabase() {
    if (!this.isDatabaseFormValid()) {
      this.alertService.error('Por favor completa todos los campos de Base de Datos');
      return;
    }

    const adminPassword = await this.alertService.requestPassword(
      'Confirmar cambios de configuración de Base de Datos',
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

    this.isSavingDatabase = true;
    
    try {
      const databasePort = Number(this.configForm.get('DATABASE_CLOUD_PORT')?.value);
      if (!Number.isFinite(databasePort) || databasePort < 1) {
        this.alertService.error('El puerto de Base de Datos debe ser un número mayor a 0');
        this.isSavingDatabase = false;
        return;
      }

      const databaseChanges: DatabaseConfigUpdate = {
        DATABASE_CLOUD_USER: this.configForm.get('DATABASE_CLOUD_USER')?.value,
        DATABASE_CLOUD_PASSWORD: this.configForm.get('DATABASE_CLOUD_PASSWORD')?.value,
        DATABASE_CLOUD_HOST: this.configForm.get('DATABASE_CLOUD_HOST')?.value,
        DATABASE_CLOUD_PORT: databasePort,
        DATABASE_CLOUD_NAME: this.configForm.get('DATABASE_CLOUD_NAME')?.value,
      };

      const response = await firstValueFrom(this.configService.updateDatabaseConfig(databaseChanges));
      const avisoEntrada = this.fromApiNewlines(response.AVISO_ENTRADA);
      const avisoSalida = this.fromApiNewlines(response.AVISO_SALIDA);
      
      this.configForm.patchValue({
        ...response,
        AVISO_ENTRADA: avisoEntrada,
        AVISO_SALIDA: avisoSalida,
        DATABASE_CLOUD_PASSWORD: ''
      });

      this.alertService.success('Configuración de Base de Datos actualizada exitosamente');
      this.isSavingDatabase = false;
    } catch (error) {
      console.error('Error actualizando configuración de BD:', error);
      this.alertService.error('Error al actualizar la configuración de Base de Datos');
      this.isSavingDatabase = false;
    }
  }

  async onSubmitGeneral() {
    if (!this.isGeneralFormValid()) {
      this.alertService.error('Por favor completa todos los campos obligatorios');
      return;
    }

    const adminPassword = await this.alertService.requestPassword(
      'Confirmar cambios de configuración',
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

    this.isSavingGeneral = true;
    
    try {
      const generalChanges: GeneralConfigUpdate = {
        SYNC_AUTO_ENABLED: this.configForm.get('SYNC_AUTO_ENABLED')?.value,
        MOBILE_PRINT: this.configForm.get('MOBILE_PRINT')?.value,
        SYNC_INTERVAL_MINUTES: this.configForm.get('SYNC_INTERVAL_MINUTES')?.value,
        ENTRY_TICKET_CODE_TYPE: this.configForm.get('ENTRY_TICKET_CODE_TYPE')?.value,
        PUBLIC_STATUS_BASE_URL: this.configForm.get('PUBLIC_STATUS_BASE_URL')?.value,
        AVISO_ENTRADA: this.toApiNewlines(this.configForm.get('AVISO_ENTRADA')?.value),
        AVISO_SALIDA: this.toApiNewlines(this.configForm.get('AVISO_SALIDA')?.value),
      };

      const response = await firstValueFrom(this.configService.updateGeneralConfig(generalChanges));

      this.configForm.patchValue({
        ...response,
        AVISO_ENTRADA: this.fromApiNewlines(response.AVISO_ENTRADA),
        AVISO_SALIDA: this.fromApiNewlines(response.AVISO_SALIDA),
      });

      this.alertService.success('Configuración General actualizada exitosamente');
      this.isSavingGeneral = false;
    } catch (error) {
      console.error('Error actualizando configuración general:', error);
      this.alertService.error('Error al actualizar la configuración general');
      this.isSavingGeneral = false;
    }
  }

  isDatabaseFormValid(): boolean {
    const dbFields = ['DATABASE_CLOUD_USER', 'DATABASE_CLOUD_PASSWORD', 'DATABASE_CLOUD_HOST', 'DATABASE_CLOUD_NAME'];
    const allFieldsWithValue = dbFields.every(field => {
      const value = this.configForm.get(field)?.value;
      return value !== null && value !== undefined && String(value).trim() !== '';
    });

    const databasePort = Number(this.configForm.get('DATABASE_CLOUD_PORT')?.value);
    return allFieldsWithValue && Number.isFinite(databasePort) && databasePort > 0;
  }

  isGeneralFormValid(): boolean {
    const generalFields = ['SYNC_INTERVAL_MINUTES', 'ENTRY_TICKET_CODE_TYPE', 'PUBLIC_STATUS_BASE_URL'];
    return generalFields.every(field => {
      const value = this.configForm.get(field)?.value;
      return value !== null && value !== undefined && String(value).trim() !== '';
    });
  }

  onReset() {
    this.loadConfig();
  }

  toggleDbFieldVisibility(fieldName: string) {
    this.dbFieldVisibility[fieldName] = !this.dbFieldVisibility[fieldName];
  }

  isDbFieldVisible(fieldName: string): boolean {
    return Boolean(this.dbFieldVisibility[fieldName]);
  }

  togglePublicStatusUrlVisibility() {
    this.isPublicStatusUrlVisible = !this.isPublicStatusUrlVisible;
  }

  private toApiNewlines(value: unknown): string {
    if (value === null || value === undefined) {
      return '';
    }

    return String(value).replace(/\r?\n/g, '\\n');
  }

  private fromApiNewlines(value: unknown): string {
    if (value === null || value === undefined) {
      return '';
    }

    return String(value).replace(/\\n/g, '\n');
  }
}
