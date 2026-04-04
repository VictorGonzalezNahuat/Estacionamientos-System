import { Component, inject, ChangeDetectionStrategy, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { FormBuilder, FormGroup, FormArray, Validators, ReactiveFormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { CurrencyPipe } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { ConfigService } from '../../../services/config.service';
import { AlertService } from '../../../core/services/alert';

interface HistorialResponse<T = any> {
  data: T[];
  advertencia: string | null;
}

type MetodoPagoHistorial = 'efectivo' | 'tarjeta' | string | null | undefined;

type MiTurnoEstado = 'sin-turno' | 'abierto' | 'pendiente-corte';

type MiTurnoResponse = {
  estado: MiTurnoEstado;
  turno_id?: number;
  hora_apertura?: string;
};

const MENSAJE_ADVERTENCIA_TURNO_ABIERTO =
  'Hay vehículos con turno sin cerrar. Cierra el turno para poder Exportar, Imprimir o Generar Reportes';

@Component({
  selector: 'app-corte-caja',
  standalone: true,
  imports: [ReactiveFormsModule, CurrencyPipe],
  templateUrl: './corte-caja.html',
  styleUrl: './corte-caja.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CorteCaja implements OnInit {

  private fb = inject(FormBuilder);
  private router = inject(Router);
  private http = inject(HttpClient);
  private config = inject(ConfigService);
  private alertService = inject(AlertService);
  private cdr = inject(ChangeDetectorRef);

  corteForm: FormGroup;
  advertenciaCorte: string | null = null;
  private redireccionCorteTimeout: ReturnType<typeof setTimeout> | null = null;

  constructor() {

    this.corteForm = this.fb.group({
      fecha: ['', Validators.required],
      turno: [''],
      encargado: [''],

      registros: this.fb.array([]),

      totalEfectivo: [{ value: 0, disabled: true }],
      totalTarjeta: [{ value: 0, disabled: true }],
      totalGeneral: [{ value: 0, disabled: true }]
    });

    const today = new Date();
    const hoy = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;

    this.corteForm.patchValue({
      fecha: hoy
    });
  }
  ngOnInit(): void {
    this.cargarUsuarioActual();
  }

  ngOnDestroy(): void {
    this.limpiarRedireccionPostCorte();
  }

  cargarUsuarioActual() {
    this.http.get<any>(`${this.config.apiUrl}/auth/me`)
      .subscribe({
        next: (user) => {

          let encargado = '';

          if (user?.nombre) {
            encargado = user.nombre;

            this.corteForm.patchValue({
              encargado: encargado
            });
          }

          const fecha = this.corteForm.get('fecha')?.value;

          // 👇 aquí llamamos al endpoint único
          this.cargarHistorialFiltro(fecha, undefined, encargado);
        },
        error: (err) => {
          console.error('Error obteniendo usuario actual', err);

          // Si falla usuario, igual cargamos solo por fecha
          const fecha = this.corteForm.get('fecha')?.value;
          this.cargarHistorialFiltro(fecha);
        }
      });
  }



  cargarHistorialFiltro(fecha: string, turno?: string, encargado?: string) {

    let params: any = { fecha };

    if (turno && turno.trim() !== '') {
      params.turno = turno;
    }

    if (encargado && encargado.trim() !== '') {
      params.encargado = encargado;
    }

    this.http.get<HistorialResponse>(
      `${this.config.apiUrl}/history/dia/filtrar`,
      { params }
    ).subscribe({
      next: (response) => {
        const data = this.procesarRespuestaHistorial(response);
        this.cargarTabla(data);
        this.cdr.markForCheck();

        if (!data || data.length === 0) {
          this.alertService.error('No se encontraron registros con ese filtro');
        }
      },
      error: (err) => {
        this.advertenciaCorte = null;
        this.cdr.markForCheck();

        const statusCode = err.status;

        if (statusCode === 404) {
          this.alertService.error(err.error?.detail || 'Recurso no encontrado');
        }
        else if (statusCode === 401) {
          this.alertService.error('Sesión expirada. Inicia sesión nuevamente');
        }
        else if (statusCode === 422) {
          this.alertService.error('Datos inválidos en el filtro');
        }
        else {
          this.alertService.error(`Error inesperado (${statusCode})`);
        }

        console.error(err);
      }
    });
  }

  cargarHistorialRango(desde: string, hasta: string) {

    this.http.get<HistorialResponse>(
      `${this.config.apiUrl}/history/rango`,
      {
        params: { desde, hasta }
      }
    ).subscribe({
      next: (response) => {
        const data = this.procesarRespuestaHistorial(response);
        this.cargarTabla(data);
        this.cdr.markForCheck();
      },
      error: () => {
        this.advertenciaCorte = null;
        this.cdr.markForCheck();
        console.error('Error cargando historial por rango');
      }
    });
  }

  private procesarRespuestaHistorial(response: HistorialResponse | any[]): any[] {
    // Compatibilidad temporal: si el backend aún responde un arreglo directo, se usa tal cual.
    if (Array.isArray(response)) {
      this.advertenciaCorte = null;
      return response;
    }

    this.advertenciaCorte = response?.advertencia ? MENSAJE_ADVERTENCIA_TURNO_ABIERTO : null;

    return Array.isArray(response?.data) ? response.data : [];
  }

  get registros(): FormArray {
    return this.corteForm.get('registros') as FormArray;
  }

  cargarTabla(data: any[]) {
    this.registros.clear();

    data.forEach(item => {
      this.agregarRegistro({
        id: item.id,
        placa: item.placa,
        turnoId: item.turno_id,
        fechaEntrada: this.formatearFecha(item.fecha_entrada),
        fechaSalida: this.formatearFecha(item.fecha_salida),
        horaEntrada: this.formatearHora(item.hora_entrada),
        horaSalida: this.formatearHora(item.hora_salida),
        tiempo: this.calcularTiempo(
          item.fecha_entrada,
          item.hora_entrada,
          item.fecha_salida,
          item.hora_salida
        ),
        importe: item.importe,
        metodoPago: this.obtenerMetodoPago(item)
      });
    });

    this.calcularTotales();
  }

  private formatearFecha(fecha: string): string {
    if (!fecha) {
      return '';
    }

    const partes = fecha.split('-');

    if (partes.length === 3) {
      const [anio, mes, dia] = partes;
      return `${dia}/${mes}/${anio}`;
    }

    return fecha;
  }

  private formatearHora(hora: string): string {
    if (!hora) {
      return '';
    }

    const partes = hora.split(':');

    if (partes.length < 2) {
      return hora;
    }

    const horas24 = Number(partes[0]);
    const minutos = partes[1];

    if (Number.isNaN(horas24)) {
      return hora;
    }

    const periodo = horas24 >= 12 ? 'pm' : 'am';
    const horas12 = horas24 % 12 || 12;

    return `${String(horas12).padStart(2, '0')}:${minutos} ${periodo}`;
  }

  calcularTiempo(
    fechaEntrada: string,
    horaEntrada: string,
    fechaSalida: string,
    horaSalida: string
  ): string {

    if (!fechaEntrada || !horaEntrada || !fechaSalida || !horaSalida) {
      return '0h 0m';
    }

    const entrada = new Date(`${fechaEntrada}T${horaEntrada}`);
    const salida = new Date(`${fechaSalida}T${horaSalida}`);

    const diffMs = salida.getTime() - entrada.getTime();

    if (diffMs <= 0) {
      return '0h 0m';
    }

    const diffSeg = diffMs / 1000;

    const horas = Math.floor(diffSeg / 3600);
    const minutos = Math.floor((diffSeg % 3600) / 60);

    return `${horas}h ${minutos}m`;
  }


  agregarRegistro(data: any) {
    const registro = this.fb.group({
      id: [data.id],
      placa: [data.placa],
      turnoId: [data.turnoId],
      fechaEntrada: [data.fechaEntrada],
      fechaSalida: [data.fechaSalida],
      horaEntrada: [data.horaEntrada],
      horaSalida: [data.horaSalida],
      tiempo: [data.tiempo],
      importe: [data.importe],
      metodoPago: [data.metodoPago ?? 'efectivo']
    });

    this.registros.push(registro);
    this.calcularTotales();
  }

  eliminarRegistro(index: number) {
    this.registros.removeAt(index);
    this.calcularTotales();
  }

  ordenarAZ() {
    const sorted = [...this.registros.value].sort((a, b) =>
      a.placa.localeCompare(b.placa)
    );

    this.registros.clear();
    sorted.forEach(r => this.agregarRegistro(r));
  }

  /* ===============================
     CÁLCULOS
  =============================== */

  calcularTotales() {

    const registros = this.registros.getRawValue();

    const totals = registros.reduce(
      (acc: { general: number; efectivo: number; tarjeta: number }, item: any) => {
        const importe = Number(item.importe ?? 0);
        const metodoPago = this.normalizarMetodoPago(item.metodoPago);

        acc.general += importe;

        if (metodoPago === 'tarjeta') {
          acc.tarjeta += importe;
        } else {
          acc.efectivo += importe;
        }

        return acc;
      },
      { general: 0, efectivo: 0, tarjeta: 0 }
    );

    this.corteForm.patchValue({
      totalGeneral: totals.general,
      totalEfectivo: totals.efectivo,
      totalTarjeta: totals.tarjeta
    });
  }



  aceptar() {
    if (this.corteForm.invalid) {
      this.corteForm.markAllAsTouched();
      return;
    }

    const { fecha, turno, encargado } = this.corteForm.getRawValue();

    this.cargarHistorialFiltro(fecha, turno, encargado);
  }

  regresar() {
    this.router.navigate(['/dashboard']);
  }

  exportarExcel() {
    console.log('Exportando...');
  }

  async cortarCaja() {
    if (this.advertenciaCorte) {
      this.alertService.error(this.advertenciaCorte);
      return;
    }

    try {
      const turno = await firstValueFrom(
        this.http.get<MiTurnoResponse>(`${this.config.apiUrl}/turnos/mi-turno`)
      );

      if (turno?.estado === 'abierto') {
        this.alertService.error('El turno debe cerrarse para realizar el corte de caja.');
        return;
      }

      const turnoId = Number(turno?.turno_id);
      if (!Number.isFinite(turnoId)) {
        this.alertService.error('No se pudo obtener el turno actual para realizar el corte');
        return;
      }

      const formValues = this.corteForm.getRawValue();
      const totalGeneral = Number(formValues.totalGeneral ?? 0);
      const totalEfectivo = Number(formValues.totalEfectivo ?? 0);
      const totalTarjeta = Number(formValues.totalTarjeta ?? 0);
      const registros = this.registros.length;

      const totalDeclarado = await this.alertService.requestCorteCajaPreview({
        turnoId,
        totalGeneral,
        totalEfectivo,
        totalTarjeta,
        registros,
        fecha: formValues.fecha,
        encargado: formValues.encargado,
      });

      if (totalDeclarado === null) {
        return;
      }

      const corteResponse = await firstValueFrom(
        this.http.post(`${this.config.apiUrl}/corte-caja/`, {
          turno_id: turnoId,
          total_declarado: totalDeclarado,
        })
      );

      const corteId = Number((corteResponse as any)?.id);
      if (!Number.isFinite(corteId)) {
        this.alertService.showCorteCajaError('El corte se proceso, pero no se recibio un id valido para descargar el PDF.');
        return;
      }

      this.alertService.showCorteCajaSuccess(
        corteId,
        () => this.descargarPdfCorte(corteId),
        () => this.redirigirDashboardMain()
      );
      this.programarRedireccionPostCorte();
    } catch (err: any) {
      console.error('Error realizando corte de caja', err);

      const statusCode = err?.status;
      if (statusCode === 400) {
        this.alertService.showCorteCajaError(err?.error?.detail || 'No fue posible realizar el corte de caja');
      } else if (statusCode === 401) {
        this.alertService.showCorteCajaError('Sesión expirada. Inicia sesión nuevamente');
      } else if (statusCode === 404) {
        this.alertService.showCorteCajaError('No se encontró un turno abierto para cortar caja');
      } else if (statusCode === 422) {
        this.alertService.showCorteCajaError('El total declarado no es válido');
      } else {
        this.alertService.showCorteCajaError('Error inesperado al realizar el corte de caja');
      }
    }
  }

  duplicarCorte() {
    console.log('Duplicando corte...');
  }

  guardarEnSistema() {
    console.log('Guardando...');
  }

  private obtenerMetodoPago(item: any): MetodoPagoHistorial {
    return item?.metodo_pago ?? item?.metodoPago ?? item?.tipo_pago ?? item?.payment_method ?? null;
  }

  private normalizarMetodoPago(value: MetodoPagoHistorial): 'efectivo' | 'tarjeta' {
    const normalized = String(value ?? '')
      .trim()
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '');

    // Soporta variantes devueltas por backend: "TARJETA", "pago con tarjeta", "stripe", etc.
    if (
      normalized === '2'
      || normalized.includes('tarjeta')
      || normalized.includes('card')
      || normalized.includes('credito')
      || normalized.includes('debito')
      || normalized.includes('stripe')
      || normalized.includes('mercadopago')
      || normalized.includes('mercado pago')
      || normalized === 'mp'
    ) {
      return 'tarjeta';
    }

    return 'efectivo';
  }

  private async descargarPdfCorte(corteId: number): Promise<void> {
    const response = await firstValueFrom(
      this.http.get(`${this.config.apiUrl}/corte-caja/${corteId}/pdf`, {
        observe: 'response',
        responseType: 'blob',
      })
    );

    const blob = response.body;
    if (!blob) {
      throw new Error('No se recibio el archivo PDF');
    }

    const contentDisposition = response.headers.get('content-disposition') || '';
    const fileName = this.extraerNombreArchivo(contentDisposition) || `corte-${corteId}.pdf`;

    const url = window.URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = fileName;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.URL.revokeObjectURL(url);
  }

  private programarRedireccionPostCorte(): void {
    this.limpiarRedireccionPostCorte();
    this.redireccionCorteTimeout = setTimeout(() => {
      this.alertService.handleCorteCajaStatusClose();
    }, 8000);
  }

  private limpiarRedireccionPostCorte(): void {
    if (this.redireccionCorteTimeout) {
      clearTimeout(this.redireccionCorteTimeout);
      this.redireccionCorteTimeout = null;
    }
  }

  private redirigirDashboardMain(): void {
    this.limpiarRedireccionPostCorte();
    this.router.navigate(['/dashboard']);
  }

  private extraerNombreArchivo(contentDisposition: string): string | null {
    const utfMatch = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i);
    if (utfMatch?.[1]) {
      return decodeURIComponent(utfMatch[1]);
    }

    const asciiMatch = contentDisposition.match(/filename="?([^";]+)"?/i);
    if (asciiMatch?.[1]) {
      return asciiMatch[1];
    }

    return null;
  }
}