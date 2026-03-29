import { ChangeDetectionStrategy, Component, inject, OnDestroy, OnInit, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { ConfigService } from '../../../services/config.service';
import { AlertService } from '../../../core/services/alert';

interface EstacionadoRow {
  id: string;
  placa: string;
  turnoId: string;
  fechaEntrada: string;
  horaEntrada: string;
  montoEstimado: string;
  ingresoCompleto: string;
  tiempoTranscurrido: string;
}

@Component({
  selector: 'app-estacionados',
  imports: [],
  templateUrl: './estacionados.html',
  styleUrl: './estacionados.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Estacionados implements OnInit, OnDestroy {

  private http = inject(HttpClient);
  private config = inject(ConfigService);
  private alert = inject(AlertService);
  private router = inject(Router);
  private refreshInterval: ReturnType<typeof setInterval> | null = null;

  loading = signal(true);
  estacionados = signal<EstacionadoRow[]>([]);
  ultimaActualizacion = signal(this.formatDateTime(new Date()));

  ngOnInit(): void {
    this.cargarEstacionados();
    this.refreshInterval = setInterval(() => {
      this.cargarEstacionados(false);
    }, 15000);
  }

  ngOnDestroy(): void {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval);
    }
  }

  goBack(): void {
    this.router.navigate(['/dashboard/entradas_salidas']);
  }

  refrescar(): void {
    this.cargarEstacionados();
  }

  private cargarEstacionados(showError = true): void {
    this.loading.set(true);

    this.http.get<any[]>(`${this.config.apiUrl}/estacionamiento/estacionados`).subscribe({
      next: (response) => {
        this.estacionados.set((response ?? []).map((item) => this.mapEstacionado(item)));
        this.ultimaActualizacion.set(this.formatDateTime(new Date()));
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        if (showError) {
          this.alert.error('Error cargando autos estacionados');
        }
      }
    });
  }

  private mapEstacionado(item: any): EstacionadoRow {
    const entryDate = this.parseEntryDate(item?.fecha_entrada, item?.hora_entrada);

    return {
      id: this.displayValue(item?.id),
      placa: this.displayValue(item?.placa),
      turnoId: this.displayValue(item?.turno_id),
      fechaEntrada: entryDate ? this.formatDate(entryDate) : this.formatRawDate(item?.fecha_entrada),
      horaEntrada: entryDate ? this.formatTime(entryDate) : this.formatRawTime(item?.hora_entrada),
      montoEstimado: this.formatAmount(item?.monto_estimado),
      ingresoCompleto: entryDate
        ? this.formatDateTime(entryDate)
        : this.combineDateTime(item?.fecha_entrada, item?.hora_entrada),
      tiempoTranscurrido: this.formatElapsed(entryDate),
    };
  }

  private parseEntryDate(fecha?: string, hora?: string): Date | null {
    if (fecha && hora) {
      const fullDate = new Date(`${fecha}T${hora}`);
      if (!Number.isNaN(fullDate.getTime())) {
        return fullDate;
      }
    }

    if (fecha) {
      const dateOnly = new Date(fecha);
      if (!Number.isNaN(dateOnly.getTime())) {
        return dateOnly;
      }
    }

    return null;
  }

  private formatElapsed(date: Date | null): string {
    if (!date) {
      return 'N/D';
    }

    const diffMs = Date.now() - date.getTime();
    if (diffMs <= 0) {
      return '0m';
    }

    const totalMinutes = Math.floor(diffMs / 60000);
    const days = Math.floor(totalMinutes / 1440);
    const hours = Math.floor((totalMinutes % 1440) / 60);
    const minutes = totalMinutes % 60;

    if (days > 0) {
      return `${days}d ${hours}h ${minutes}m`;
    }

    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    }

    return `${minutes}m`;
  }

  private formatDate(date: Date): string {
    return new Intl.DateTimeFormat('es-MX', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric'
    }).format(date);
  }

  private formatTime(date: Date): string {
    const hours24 = date.getHours();
    const minutes = String(date.getMinutes()).padStart(2, '0');
    const seconds = String(date.getSeconds()).padStart(2, '0');
    const period = hours24 >= 12 ? 'pm' : 'am';
    const hours12 = hours24 % 12 === 0 ? 12 : hours24 % 12;

    return `${String(hours12).padStart(2, '0')}:${minutes}:${seconds} ${period}`;
  }

  private formatRawDate(value: unknown): string {
    const raw = this.displayValue(value);
    if (raw === 'N/D') return raw;

    const datePart = raw.includes('T') ? raw.split('T')[0] : raw;
    const match = datePart.match(/^(\d{4})-(\d{2})-(\d{2})$/);

    if (!match) return raw;

    const [, year, month, day] = match;
    return `${day}/${month}/${year}`;
  }

  private formatRawTime(value: unknown): string {
    const raw = this.displayValue(value);
    if (raw === 'N/D') return raw;

    const match = raw.match(/^(\d{1,2}):(\d{2})(?::(\d{2}))?$/);
    if (!match) return raw;

    const hours24 = Number(match[1]);
    if (Number.isNaN(hours24) || hours24 < 0 || hours24 > 23) return raw;

    const minutes = match[2];
    const seconds = match[3] ?? '00';
    const period = hours24 >= 12 ? 'pm' : 'am';
    const hours12 = hours24 % 12 === 0 ? 12 : hours24 % 12;

    return `${String(hours12).padStart(2, '0')}:${minutes}:${seconds} ${period}`;
  }

  private formatDateTime(date: Date): string {
    return new Intl.DateTimeFormat('es-MX', {
      dateStyle: 'medium',
      timeStyle: 'short'
    }).format(date);
  }

  private formatAmount(value: unknown): string {
    if (value === null || value === undefined || value === '') {
      return 'N/D';
    }

    const amount = Number(value);
    if (Number.isNaN(amount)) {
      return this.displayValue(value);
    }

    return new Intl.NumberFormat('es-MX', {
      style: 'currency',
      currency: 'MXN',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount);
  }

  private combineDateTime(fecha?: string, hora?: string): string {
    const dateValue = this.displayValue(fecha);
    const timeValue = this.displayValue(hora);

    if (dateValue === 'N/D' && timeValue === 'N/D') {
      return 'N/D';
    }

    if (dateValue === 'N/D') {
      return timeValue;
    }

    if (timeValue === 'N/D') {
      return dateValue;
    }

    return `${dateValue} ${timeValue}`;
  }

  private displayValue(value: unknown): string {
    if (value === null || value === undefined || value === '') {
      return 'N/D';
    }

    return String(value);
  }

}
