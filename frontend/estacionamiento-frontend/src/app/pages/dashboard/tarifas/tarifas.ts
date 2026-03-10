import { Component, inject, signal, ChangeDetectionStrategy } from '@angular/core';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { CurrencyPipe } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { ConfigService } from '../../../services/config.service';
import { AlertService } from '../../../core/services/alert';

interface Tarifa {
  id?: string;
  numero: number;
  tipo_vehiculo: string;
  hora: number;
  fraccion: number;
  diario: number;
  medio_dia: number;
  observaciones: string;
  default?: number;
  eliminado?: number;
}

interface NextNumeroResponse {
  siguiente_numero: number;
}

@Component({
  selector: 'app-tarifas',
  standalone: true,
  imports: [ReactiveFormsModule, CurrencyPipe],
  templateUrl: './tarifas.html',
  styleUrls: ['./tarifas.css'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Tarifas {
  private fb = inject(FormBuilder);
  private http = inject(HttpClient);
  private configService = inject(ConfigService);
  private alertService = inject(AlertService);

  tarifaForm!: FormGroup;
  tarifas = signal<Tarifa[]>([]);
  tarifaDefault = signal<Tarifa | null>(null);
  editandoId = signal<string | null>(null);
  cargandoNumero = signal(false);
  cargandoDefault = signal<number | null>(null);

  constructor() {
    this.initializeForm();
    this.cargarTarifas();
    this.cargarTarifaDefault();
  }

  /**
   * Inicializa el formulario reactivo
   */
  private initializeForm(): void {
    this.tarifaForm = this.fb.group({
      numero: ['', [Validators.required, Validators.min(1)]],
      tipoVehiculo: ['', Validators.required],
      hora: ['', [Validators.required, Validators.min(0)]],
      fraccion: ['', [Validators.required, Validators.min(0)]],
      diario: ['', [Validators.required, Validators.min(0)]],
      medioDia: ['', [Validators.required, Validators.min(0)]],
      observaciones: [''],
    });
  }

  /**
   * Carga las tarifas desde el servidor
   */
  private cargarTarifas(): void {
    const apiUrl = `${this.configService.apiUrl}/tarifas`;
    this.http.get<Tarifa[]>(apiUrl).subscribe({
      next: (data) => {
        this.tarifas.set(data);
        this.cargarTarifaDefault();
      },
      error: (err) => {
        console.error('Error al cargar tarifas:', err);
        this.alertService.error('No se pudieron cargar las tarifas');
        // Simulamos datos locales para demostración
        this.tarifas.set([]);
      },
    });
  }

  /**
   * Carga la tarifa default desde el servidor
   */
  private cargarTarifaDefault(): void {
    const apiUrl = `${this.configService.apiUrl}/tarifas/default`;
    this.http.get<Tarifa>(apiUrl).subscribe({
      next: (data) => {
        this.tarifaDefault.set(data);
      },
      error: (err) => {
        console.error('Error al cargar tarifa default:', err);
        this.tarifaDefault.set(null);
      },
    });
  }

  /**
   * Guarda o actualiza una tarifa
   */
  guardarTarifa(): void {
    if (this.tarifaForm.invalid) {
      this.alertService.error('Por favor completa todos los campos requeridos');
      return;
    }

    // Pedir contraseña
    this.requestPasswordAndSave();
  }

  /**
   * Pide la contraseña y luego guarda la tarifa
   */
  private async requestPasswordAndSave(): Promise<void> {
    const password = await this.alertService.requestPassword(
      'Confirmar contraseña',
      'Por favor ingresa tu contraseña para guardar la tarifa'
    );

    if (!password) {
      return; // Usuario canceló
    }

    const formData = this.tarifaForm.value;
    
    // Transformar de camelCase a snake_case para el backend
    const datos = {
      numero: formData.numero,
      tipo_vehiculo: formData.tipoVehiculo,
      hora: formData.hora,
      fraccion: formData.fraccion,
      diario: formData.diario,
      medio_dia: formData.medioDia,
      observaciones: formData.observaciones,
      password: password,
    };

    const apiUrl = `${this.configService.apiUrl}/tarifas`;

    if (this.editandoId()) {
      // Actualizar tarifa existente
      const id = this.editandoId();
      this.http.put(`${apiUrl}/${id}`, datos).subscribe({
        next: () => {
          this.alertService.success('Tarifa actualizada correctamente');
          this.cargarTarifas();
          this.limpiarFormulario();
        },
        error: (err) => {
          console.error('Error al actualizar:', err);
          let mensajeError = 'No se pudo actualizar la tarifa';
          
          // Manejar errores específicos del backend
          if (err.status === 400 && err.error?.message) {
            mensajeError = err.error.message;
          }
          
          this.alertService.error(mensajeError);
        },
      });
    } else {
      // Crear nueva tarifa
      this.http.post(apiUrl, datos).subscribe({
        next: () => {
          this.alertService.success('Tarifa creada correctamente');
          this.cargarTarifas();
          this.limpiarFormulario();
        },
        error: (err) => {
          console.error('Error al crear:', err);
          let mensajeError = 'No se pudo crear la tarifa';
          
          // Manejar errores específicos del backend
          if (err.status === 400 && err.error?.message) {
            mensajeError = err.error.message;
          }
          
          this.alertService.error(mensajeError);
        },
      });
    }
  }

  /**
   * Carga una tarifa en el formulario para editar
   */
  editarTarifa(tarifa: Tarifa): void {
    this.tarifaForm.patchValue({
      numero: tarifa.numero,
      tipoVehiculo: tarifa.tipo_vehiculo,
      hora: tarifa.hora,
      fraccion: tarifa.fraccion,
      diario: tarifa.diario,
      medioDia: tarifa.medio_dia,
      observaciones: tarifa.observaciones,
    });
    this.editandoId.set(tarifa.id || null);
    // Scroll al formulario
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  /**
   * Elimina una tarifa
   */
  async eliminarTarifa(id: string | undefined): Promise<void> {
    if (!id) {
      this.alertService.error('ID de tarifa no válido');
      return;
    }

    const confirmed = await this.alertService.confirm(
      '¿Estás seguro de que deseas eliminar esta tarifa?',
      'Eliminar tarifa'
    );

    if (!confirmed) {
      return;
    }

    const apiUrl = `${this.configService.apiUrl}/tarifas/${id}`;
    this.http.delete(apiUrl).subscribe({
      next: () => {
        this.alertService.success('Tarifa eliminada correctamente');
        this.cargarTarifas();
      },
      error: (err) => {
        console.error('Error al eliminar:', err);
        let mensajeError = 'Hay vehiculos asociados a esta tarifa, crea una nueva y marcala por defecto';
        
        // Manejar errores específicos del backend
        if (err.status === 400 && err.error?.message) {
          mensajeError = err.error.message;
        }
        
        this.alertService.error(mensajeError);
      },
    });
  }

  /**
   * Limpia el formulario
   */
  limpiarFormulario(): void {
    this.tarifaForm.reset();
    this.editandoId.set(null);
  }

  /**
   * Cancela la edición
   */
  cancelarEdicion(): void {
    this.limpiarFormulario();
  }

  /**
   * Obtiene el próximo número de tarifa desde el backend
   */
  obtenerProximoNumero(): void {
    this.cargandoNumero.set(true);
    const apiUrl = `${this.configService.apiUrl}/tarifas/next-numero`;

    this.http.get<NextNumeroResponse>(apiUrl).subscribe({
      next: (response) => {
        console.log('Respuesta del backend:', response);
        const numeroControl = this.tarifaForm.get('numero');
        if (numeroControl) {
          numeroControl.setValue(Number(response.siguiente_numero));
          console.log('Valor asignado:', numeroControl.value);
        }
        this.cargandoNumero.set(false);
      },
      error: (err) => {
        console.error('Error al obtener siguiente número:', err);
        this.alertService.error('No se pudo obtener el siguiente número');
        this.cargandoNumero.set(false);
      },
    });
  }

  /**
   * Establece una tarifa como default
   */
  async establecerDefaultTarifa(numero: number): Promise<void> {
    const confirmed = await this.alertService.confirm(
      `¿Estás seguro de que deseas establecer esta tarifa como predeterminada?`,
      'Establecer como default'
    );

    if (!confirmed) {
      return;
    }

    this.cargandoDefault.set(numero);
    const apiUrl = `${this.configService.apiUrl}/tarifas/${numero}/set-default`;

    this.http.patch(apiUrl, {}).subscribe({
      next: () => {
        this.cargandoDefault.set(null);
        this.alertService.sessionRestartRequired(
          'Tu sesión se reiniciara para aplicar cambios, vuelve a iniciar sesión por favor'
        );
      },
      error: (err) => {
        console.error('Error al establecer tarifa como default:', err);
        let mensajeError = 'No se pudo establecer como default';
        
        // Manejar errores específicos del backend
        if (err.status === 400 && err.error?.message) {
          mensajeError = err.error.message;
        }
        
        this.alertService.error(mensajeError);
        this.cargandoDefault.set(null);
      },
    });
  }
}
