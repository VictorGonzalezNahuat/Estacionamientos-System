import { Component } from '@angular/core';
import { FormBuilder, FormGroup, FormArray, Validators, ReactiveFormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { OnInit } from '@angular/core';
import { ConfigService } from '../../../services/config.service';
import { AlertService } from '../../../core/services/alert';
import { ChangeDetectorRef } from '@angular/core';

@Component({
  selector: 'app-corte-caja',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './corte-caja.html',
  styleUrl: './corte-caja.css',
})
export class CorteCaja implements OnInit {

  corteForm: FormGroup;

  constructor(
    private fb: FormBuilder,
    private router: Router,
    private http: HttpClient,
    private config: ConfigService,
    private alertService: AlertService,
    private cdr: ChangeDetectorRef
  ){

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

    this.http.get<any[]>(
      `${this.config.apiUrl}/history/dia/filtrar`,
      { params }
    ).subscribe({
      next: (data) => {
        this.cargarTabla(data);

        if (!data || data.length === 0) {
          this.alertService.error('No se encontraron registros con ese filtro');
        }
      },
      error: (err) => {

        const statusCode = err.status;

        if (statusCode === 404) {
          this.alertService.error(err.error?.detail || 'Recurso no encontrado');
        }
        else if (statusCode === 409) {
          this.alertService.error('Hay turnos sin cerrar en el historial de busqueda');
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

    this.http.get<any[]>(
      `${this.config.apiUrl}/history/rango`,
      {
        params: { desde, hasta }
      }
    ).subscribe({
      next: (data) => {
        this.cargarTabla(data);
      },
      error: () => {
        console.error('Error cargando historial por rango');
      }
    });
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
        fechaEntrada: item.fecha_entrada,
        fechaSalida: item.fecha_salida,
        horaEntrada: item.hora_entrada,
        horaSalida: item.hora_salida,
        tiempo: this.calcularTiempo(
          item.fecha_entrada,
          item.hora_entrada,
          item.fecha_salida,
          item.hora_salida
        ),
        importe: item.importe
      });
    });

    this.calcularTotales();

    // 👇 ESTA ES LA CLAVE
    this.cdr.detectChanges();
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
      importe: [data.importe]
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

    const total = registros.reduce(
      (acc: number, item: any) => acc + Number(item.importe),
      0
    );

    this.corteForm.patchValue({
      totalGeneral: total,
      totalEfectivo: total,
      totalTarjeta: 0
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

  imprimir() {
    window.print();
  }

  duplicarCorte() {
    console.log('Duplicando corte...');
  }

  guardarEnSistema() {
    console.log('Guardando...');
  }
}