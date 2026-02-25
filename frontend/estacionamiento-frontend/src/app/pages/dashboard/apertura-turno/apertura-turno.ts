import { Component, signal, inject } from '@angular/core';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { DatePipe, CommonModule } from '@angular/common';
import { ConfigService } from '../../../services/config.service';
import { Router } from '@angular/router';
import { AlertService } from '../../../core/services/alert';

@Component({
  selector: 'app-apertura-turno',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, DatePipe],
  templateUrl: './apertura-turno.html',
  styleUrls: ['./apertura-turno.css'],
})
export class AperturaTurno {
  

  private http = inject(HttpClient);
  private fb = inject(FormBuilder);
  private configService = inject(ConfigService);
  private router = inject(Router);
  private alertService = inject(AlertService);

  user = signal<any>(null);
  loading = signal(false);

  aperturaForm: FormGroup = this.fb.group({
    password: ['', Validators.required]
  });

  today = new Date();
  now = new Date();

  constructor() {
    this.cargarUsuario();
  }

  goDashboard() {
    this.router.navigate(['/dashboard']);
  }

  cargarUsuario() {
    this.http.get(
      `${this.configService.apiUrl}/auth/me`
    ).subscribe({
      next: data => this.user.set(data),
      error: err => {
        console.error(err);
        this.alertService.error('Error obteniendo datos del usuario');


      }
    });
  }

  abrirTurno() {
    if (this.aperturaForm.invalid) return;

    this.loading.set(true);
    

    this.http.post(
      `${this.configService.apiUrl}/turnos/`,
      this.aperturaForm.value
    ).subscribe({
      next: (res: any) => {
        this.loading.set(false);
        this.alertService.success(`Turno creado correctamente (ID: ${res.id})`);

        this.aperturaForm.reset();
        this.router.navigate(['/dashboard']);
      },
      error: (err) => {
        this.loading.set(false);
        const statusCode = err.status;
        if (statusCode === 401) {
          this.alertService.error('Contraseña incorrecta, intentelo de nuevo');
        } else if (statusCode === 403) {
          this.alertService.error('No tienes permisos para abrir este turno');
        } else if (statusCode === 404) {
          this.alertService.error('Ya existe turno abierto para este encargado');
        }
        else {
          this.alertService.error('Error inesperado en el servidor (' + statusCode + ')');
        }
        console.error(err);
      }
    });
  }


}
