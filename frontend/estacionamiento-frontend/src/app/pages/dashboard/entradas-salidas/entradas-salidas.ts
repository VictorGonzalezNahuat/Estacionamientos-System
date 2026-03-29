import { Component, inject, signal, OnInit, ElementRef, ViewChild, OnDestroy, ChangeDetectionStrategy, AfterViewInit } from '@angular/core';
import { CurrencyPipe, DatePipe } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { ConfigService } from '../../../services/config.service';
import { AlertService } from '../../../core/services/alert';
import { Router } from '@angular/router';

@Component({
  selector: 'app-entradas-salidas',
  standalone: true,
  imports: [ReactiveFormsModule, DatePipe, CurrencyPipe],
  templateUrl: './entradas-salidas.html',
  styleUrl: './entradas-salidas.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class EntradasSalidas implements OnInit, OnDestroy, AfterViewInit {

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

  goEstacionados() {
    this.router.navigate(['/dashboard/estacionados']);
  }

  ngOnInit() {
    this.cargarDatos();
    this.cargarEstacionados();
    this.cargarEstado();
    this.iniciarReloj();
    this.iniciarAutoRefresh();
  }

  ngAfterViewInit() {
    this.focusAndSelectPlaca();
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
    const yaDentro = this.estacionados().some(auto => (auto?.placa ?? '').toUpperCase() === placa);

    if (yaDentro) {
      this.solicitarSalida(placa, true);
      return;
    }

    this.solicitarIngreso(placa, true);
  }

  private solicitarIngreso(placa: string, allowFallback: boolean) {
    this.http.post(
      `${this.config.apiUrl}/estacionamiento/ingresar`,
      { placa }
    ).subscribe({
      next: () => {
        this.alert.success('Vehículo ingresado correctamente', () => this.focusAndSelectPlaca());
        this.speak('Ha ingresado un nuevo vehiculo');
        this.postOperacionExitosa();
      },
      error: () => {
        if (allowFallback) {
          this.solicitarSalida(placa, false);
          return;
        }
        this.alert.error('La placa no pudo ingresar ni salir', () => this.focusAndSelectPlaca());
        this.loading.set(false);
      }
    });
  }

  private solicitarSalida(placa: string, allowFallback: boolean) {
    this.http.post(
      `${this.config.apiUrl}/estacionamiento/salir`,
      { placa }
    ).subscribe({
      next: (res: any) => {
        this.alert.info('Vehículo retirado correctamente', res);
        const importe = res?.importe != null ? `El importe a cobrar es ${res.importe} pesos` : '';
        this.speak(`Vehículo retirado. ${importe}`);
        this.postOperacionExitosa();
      },

      error: () => {
        if (allowFallback) {
          this.solicitarIngreso(placa, false);
          return;
        }
        this.alert.error('La placa no pudo ingresar ni salir', () => this.focusAndSelectPlaca());
        this.loading.set(false);
      }
    });
  }

  postOperacionExitosa() {
    this.form.reset();
    this.loading.set(false);
    this.cargarEstacionados();
    this.cargarEstado();

    setTimeout(() => this.focusAndSelectPlaca(), 100);
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
      if (this.loading()) return;
      this.cargarEstacionados();
      this.cargarEstado();
    }, 10000);
  }
  ngOnDestroy() {
    clearInterval(this.relojInterval);
    clearInterval(this.refreshInterval);
  }

  private focusAndSelectPlaca() {
    const input = this.placaInput?.nativeElement;
    if (!input) return;
    input.focus();
    input.select();
  }

  private speak(text: string) {
    if (!('speechSynthesis' in window)) return;

    const synth = window.speechSynthesis;
    const utterance = new SpeechSynthesisUtterance(text);
    const preferredName = this.config.speechVoiceName;
    const preferredLang = this.config.speechLang;

    utterance.lang = preferredLang;
    utterance.rate = this.config.speechRate;
    utterance.pitch = this.config.speechPitch;
    utterance.volume = this.config.speechVolume;

    const voices = synth.getVoices();
    const selectedVoice =
      (preferredName ? voices.find(v => v.name === preferredName) : undefined) ??
      voices.find(v => v.lang === preferredLang) ??
      voices.find(v => v.lang.startsWith('es'));

    if (selectedVoice) {
      utterance.voice = selectedVoice;
      utterance.lang = selectedVoice.lang;
    }

    synth.cancel();
    synth.speak(utterance);
  }

  formatFecha(fecha: string | null | undefined): string {
    if (!fecha) return '';

    const fechaBase = fecha.includes('T') ? fecha.split('T')[0] : fecha;
    const match = fechaBase.match(/^(\d{4})-(\d{2})-(\d{2})$/);

    if (match) {
      const [, anio, mes, dia] = match;
      return `${dia}/${mes}/${anio}`;
    }

    return fecha;
  }

  formatHora(hora: string | null | undefined): string {
    if (!hora) return '';

    const match = hora.match(/^(\d{1,2}):(\d{2})(?::(\d{2}))?$/);
    if (!match) return hora;

    const horas24 = Number(match[1]);
    const minutos = match[2];
    const segundos = match[3] ?? '00';

    if (Number.isNaN(horas24) || horas24 < 0 || horas24 > 23) return hora;

    const periodo = horas24 >= 12 ? 'pm' : 'am';
    const horas12 = horas24 % 12 === 0 ? 12 : horas24 % 12;
    const horas12Str = String(horas12).padStart(2, '0');

    return `${horas12Str}:${minutos}:${segundos} ${periodo}`;
  }

  formatImporteAprox(value: unknown): string {
    if (value === null || value === undefined || value === '') {
      return 'N/D';
    }

    const amount = Number(value);
    if (Number.isNaN(amount)) {
      return String(value);
    }

    return new Intl.NumberFormat('es-MX', {
      style: 'currency',
      currency: 'MXN',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount);
  }

}
