import { Component, inject, signal, OnInit, ElementRef, ViewChild, OnDestroy } from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { ConfigService } from '../../../services/config.service';
import { AlertService } from '../../../core/services/alert';
import { Router } from '@angular/router';


@Component({
  selector: 'app-entradas-salidas',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, DatePipe],
  templateUrl: './entradas-salidas.html',
  styleUrl: './entradas-salidas.css'
})
export class EntradasSalidas implements OnInit, OnDestroy{

  private http = inject(HttpClient);
  private fb = inject(FormBuilder);
  private config = inject(ConfigService);
  private alert = inject(AlertService);
  private router = inject(Router);
  private relojInterval: any;
  private refreshInterval: any;


  @ViewChild('placaInput') placaInput!: ElementRef<HTMLInputElement>;

  user = signal<any>(null);
  turno = signal<any>(null);
  tarifa = signal<any>(null);
  loading = signal(false);
  now = signal(new Date());
  estacionados = signal<any[]>([]);
  estado = signal<any>(null);



  form = this.fb.group({
    placa: ['', [Validators.required]]
  });

  goDashboard() {
    this.router.navigate(['/dashboard']);
  }

  ngOnInit() {
    this.cargarDatos();
    this.cargarEstacionados();
    this.cargarEstado();
    this.iniciarReloj();
    this.iniciarAutoRefresh();
  }

  cargarEstado() {
    this.http.get(
      `${this.config.apiUrl}/estacion/estado`
    ).subscribe({
      next: (res) => this.estado.set(res),
      error: () => this.alert.error('Error cargando estado del estacionamiento')
    });
  }
  cargarDatos() {
    this.http.get(`${this.config.apiUrl}/auth/me`)
      .subscribe(res => this.user.set(res));

    this.http.get(`${this.config.apiUrl}/turnos/mi-turno`)
      .subscribe(res => this.turno.set(res));

    this.http.get(`${this.config.apiUrl}/tarifas/default`)
      .subscribe(res => this.tarifa.set(res));
  }

  iniciarReloj() {
    this.relojInterval = setInterval(() => {
      this.now.set(new Date());
    }, 1000);
  }


  ingresarVehiculo() {
    if (this.form.invalid) return;

    const placa = this.form.value.placa?.toUpperCase().trim();

    if (!placa) return;

    this.loading.set(true);

    this.http.post(
      `${this.config.apiUrl}/estacionamiento/ingresar`,
      { placa }
    ).subscribe({
      next: () => {
        this.alert.success('Vehículo ingresado correctamente');
        this.postOperacionExitosa();
      },
      error: () => {
        this.intentarSalida(placa);
      }
    });
  }

  intentarSalida(placa: string) {
    this.http.post(
      `${this.config.apiUrl}/estacionamiento/salir`,
      { placa }
    ).subscribe({
      next: (res: any) => {
        this.alert.info('Vehículo retirado correctamente', res);
        this.postOperacionExitosa();
      },

      error: () => {
        this.alert.error('La placa no pudo ingresar ni salir');
        this.loading.set(false);
      }
    });
  }

  postOperacionExitosa() {
    this.form.reset();
    this.loading.set(false);
    this.cargarEstacionados();
    this.cargarEstado();

    setTimeout(() => {
      this.placaInput?.nativeElement.focus();
    }, 100);
  }




  cargarEstacionados() {
    this.http.get<any[]>(
      `${this.config.apiUrl}/estacionamiento/estacionados`
    ).subscribe({
      next: (res) => this.estacionados.set(res),
      error: () => this.alert.error('Error cargando autos estacionados')
    });
  }
  iniciarAutoRefresh() {
    this.refreshInterval = setInterval(() => {
      this.cargarEstacionados();
      this.cargarEstado();
    }, 10000);
  }
  ngOnDestroy() {
    clearInterval(this.relojInterval);
    clearInterval(this.refreshInterval);
  }

}
