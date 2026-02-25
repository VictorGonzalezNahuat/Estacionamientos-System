import { Component, inject, signal } from '@angular/core';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { CommonModule, DatePipe } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { ConfigService } from '../../../services/config.service';
import { AlertService } from '../../../core/services/alert';
@Component({
  selector: 'app-cierre-turno',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, DatePipe],
  templateUrl: './cierre-turno.html',
  styleUrls: ['./cierre-turno.css'],
})
export class CierreTurno {

  private fb = inject(FormBuilder);
  private http = inject(HttpClient);
  private router = inject(Router);
  private configService = inject(ConfigService);
  private alertService = inject(AlertService);

  loading = signal(false);

  cierreForm: FormGroup = this.fb.group({
    password: ['', Validators.required]
  });

  today = new Date();
  turno = signal<any>(null);
  duracion = signal<string>('Calculando...');
  now = new Date();

  constructor() {
    this.obtenerTurno();
  }


  goDashboard() {
    this.router.navigate(['/dashboard']);
  }


  cerrarTurno() {
    if (this.cierreForm.invalid) return;

    this.loading.set(true);

    const body = {
      password: this.cierreForm.value.password
    };

    this.http.request(
      'delete',
      `${this.configService.apiUrl}/turnos/`,
      { body }
    ).subscribe({
      next: () => {
        this.loading.set(false);
        this.alertService.success('Turno cerrado correctamente');
        this.router.navigate(['/dashboard']);
      },
      
      error: (err) => {
        this.loading.set(false);
        const statusCode = err.status;
        if (statusCode === 401) {
          this.alertService.error('Contraseña incorrecta, intentelo de nuevo');
        } else if (statusCode === 403) {
          this.alertService.error('No tienes permisos para cerrar este turno');
        } else if (statusCode === 404) {
          this.alertService.error('No existe turno abierto para este encargado');
        } else if (statusCode === 400) {
          this.alertService.error('Aun existen vehiculos dentro del estacionamiento');
        }
        else {
          this.alertService.error('Error inesperado en el servidor (' + statusCode + ')');
        }
        console.error(err);
      }
    });
  }


  obtenerTurno() {
    this.http.get(
      `${this.configService.apiUrl}/turnos/mi-turno`
    ).subscribe({
      next: (data: any) => {
        this.turno.set(data);
        this.calcularDuracion(data.hora_apertura);
      },
      error: (err) => {
        console.error(err);
        this.alertService.error('Error obteniendo turno actual');
      }
    });
  }

  calcularDuracion(horaApertura: string) {

    const hoy = new Date();

    const [h, m, s] = horaApertura.split(':').map(Number);

    const inicio = new Date(
      hoy.getFullYear(),
      hoy.getMonth(),
      hoy.getDate(),
      h,
      m,
      s
    );

    const ahora = new Date();

    const diffMs = ahora.getTime() - inicio.getTime();

    const horas = Math.floor(diffMs / (1000 * 60 * 60));
    const minutos = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));

    this.duracion.set(`${horas}h ${minutos}m`);
  }

}
