import { ChangeDetectionStrategy, Component, inject, OnInit, signal } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { AlertService } from '../../../core/services/alert';
import { ConfigService } from '../../../services/config.service';

interface CancelacionResponse {
  detail?: string;
}

interface CanceladoRecord {
  id?: number;
  historial_id?: number;
  history_id?: number;
  history_estacionamiento_id?: number;
  placa?: string;
  motivo?: string;
  cancelado_por?: number;
  fecha_cancelacion?: string;
  hora_cancelacion?: string;
  updated_at?: string;
  fecha_salida?: string;
  hora_salida?: string;
  importe?: number;
}

interface CanceladosApiResponse<T> {
  data?: T[];
}

interface CanceladoTicketRow {
  historialId: string;
  placa: string;
  motivo: string;
  canceladoPor: string;
  fechaSalida: string;
  horaSalida: string;
  importe: string;
  canceladoEn: string;
}

@Component({
  selector: 'app-cancelacion-tickets',
  imports: [],
  templateUrl: './cancelacion-tickets.html',
  styleUrl: './cancelacion-tickets.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CancelacionTickets implements OnInit {

  private readonly http = inject(HttpClient);
  private readonly config = inject(ConfigService);
  private readonly alert = inject(AlertService);

  readonly ticketId = signal('');
  readonly motivo = signal('');

  readonly desde = signal('');
  readonly hasta = signal('');
  readonly placa = signal('');
  readonly canceladoPor = signal('');

  readonly cancelando = signal(false);
  readonly cargando = signal(false);
  readonly rows = signal<CanceladoTicketRow[]>([]);
  readonly lastUpdated = signal('Sin cargar');

  ngOnInit(): void {
    this.cargarCancelados();
  }

  onTicketIdInput(event: Event): void {
    const target = event.target as HTMLInputElement | null;
    this.ticketId.set((target?.value ?? '').trim());
  }

  onMotivoInput(event: Event): void {
    const target = event.target as HTMLTextAreaElement | null;
    this.motivo.set(target?.value ?? '');
  }

  onDesdeInput(event: Event): void {
    const target = event.target as HTMLInputElement | null;
    this.desde.set((target?.value ?? '').trim());
  }

  onHastaInput(event: Event): void {
    const target = event.target as HTMLInputElement | null;
    this.hasta.set((target?.value ?? '').trim());
  }

  onPlacaInput(event: Event): void {
    const target = event.target as HTMLInputElement | null;
    this.placa.set((target?.value ?? '').trim().toUpperCase());
  }

  onCanceladoPorInput(event: Event): void {
    const target = event.target as HTMLInputElement | null;
    this.canceladoPor.set((target?.value ?? '').trim());
  }

  async cancelarTicket(): Promise<void> {
    const rawId = this.ticketId().trim();
    const historialId = Number(rawId);

    if (!rawId || !Number.isInteger(historialId) || historialId <= 0) {
      this.alert.error('Ingresa un id de ticket valido para cancelar.');
      return;
    }

    const motivo = this.motivo().trim();
    if (!motivo) {
      this.alert.error('El motivo de cancelacion es obligatorio.');
      return;
    }

    const password = await this.alert.requestPassword(
      'Confirmar contraseña',
      'Ingresa tu contraseña para autorizar la cancelacion del ticket'
    );

    if (!password) {
      return;
    }

    this.cancelando.set(true);

    this.http.post<CancelacionResponse>(
      `${this.config.apiUrl}/history/cancelar/${historialId}`,
      {
        motivo,
        password,
      }
    ).subscribe({
      next: (res) => {
        this.cancelando.set(false);
        this.alert.success(res?.detail || `Ticket ${historialId} cancelado correctamente.`);
        this.cargarCancelados(false);
      },
      error: (err) => {
        this.cancelando.set(false);
        const statusCode = Number(err?.status ?? 0);

        if (statusCode === 401) {
          this.alert.error('Contraseña incorrecta. Intenta nuevamente.');
          return;
        }

        if (statusCode === 403) {
          this.alert.error('No tienes permisos para cancelar tickets.');
          return;
        }

        if (statusCode === 404) {
          this.alert.error(err?.error?.detail || 'No se encontro el ticket indicado.');
          return;
        }

        if (statusCode === 400) {
          this.alert.error(err?.error?.detail || 'Los datos enviados no son validos.');
          return;
        }

        this.alert.error(err?.error?.detail || `Error inesperado del servidor (${statusCode}).`);
      }
    });
  }

  buscarCancelados(): void {
    this.cargarCancelados();
  }

  limpiarFiltros(): void {
    this.desde.set('');
    this.hasta.set('');
    this.placa.set('');
    this.canceladoPor.set('');
    this.cargarCancelados();
  }

  get countLabel(): string {
    const total = this.rows().length;
    return total === 1 ? '1 ticket cancelado' : `${total} tickets cancelados`;
  }

  private cargarCancelados(showError = true): void {
    this.cargando.set(true);

    let params = new HttpParams();

    if (this.desde().trim()) {
      params = params.set('desde', this.desde().trim());
    }

    if (this.hasta().trim()) {
      params = params.set('hasta', this.hasta().trim());
    }

    if (this.placa().trim()) {
      params = params.set('placa', this.placa().trim());
    }

    const canceladoPor = Number(this.canceladoPor().trim());
    if (!Number.isNaN(canceladoPor) && canceladoPor >= 0 && this.canceladoPor().trim()) {
      params = params.set('cancelado_por', String(canceladoPor));
    }

    this.http.get<CanceladoRecord[] | CanceladosApiResponse<CanceladoRecord>>(
      `${this.config.apiUrl}/history/cancelados`,
      { params }
    ).subscribe({
      next: (response) => {
        this.cargando.set(false);
        const records = Array.isArray(response) ? response : response?.data ?? [];
        this.rows.set(records.map((record) => this.toRow(record)));
        this.lastUpdated.set(this.formatDateTime(new Date()));
      },
      error: () => {
        this.cargando.set(false);

        if (showError) {
          this.alert.error('No fue posible cargar los tickets cancelados.');
        }
      }
    });
  }

  private toRow(record: CanceladoRecord): CanceladoTicketRow {
    const historialId =
      record.id
      ?? record.historial_id
      ?? record.history_id
      ?? record.history_estacionamiento_id;

    const canceladoEn = this.formatDateTimeValue(
      record.updated_at || this.combineDateAndTime(record.fecha_cancelacion, record.hora_cancelacion)
    );

    return {
      historialId: this.displayValue(historialId),
      placa: this.displayValue(record.placa),
      motivo: this.displayValue(record.motivo),
      canceladoPor: this.displayValue(record.cancelado_por),
      fechaSalida: this.formatRawDate(record.fecha_salida),
      horaSalida: this.formatRawTime(record.hora_salida),
      importe: this.formatAmount(record.importe),
      canceladoEn,
    };
  }

  private combineDateAndTime(dateValue?: string, timeValue?: string): string {
    const date = (dateValue ?? '').trim();
    const time = (timeValue ?? '').trim();

    if (!date && !time) {
      return '';
    }

    if (!date) {
      return time;
    }

    if (!time) {
      return date;
    }

    return `${date}T${time}`;
  }

  private formatRawDate(value: unknown): string {
    const raw = this.displayValue(value);

    if (raw === 'N/D') {
      return raw;
    }

    const datePart = raw.includes('T') ? raw.split('T')[0] : raw;
    const match = datePart.match(/^(\d{4})-(\d{2})-(\d{2})$/);

    if (!match) {
      return raw;
    }

    const [, year, month, day] = match;
    return `${day}/${month}/${year}`;
  }

  private formatRawTime(value: unknown): string {
    const raw = this.displayValue(value);

    if (raw === 'N/D') {
      return raw;
    }

    const match = raw.match(/^(\d{1,2}):(\d{2})(?::(\d{2}))?$/);
    if (!match) {
      return raw;
    }

    const hours24 = Number(match[1]);
    if (Number.isNaN(hours24) || hours24 < 0 || hours24 > 23) {
      return raw;
    }

    const minutes = match[2];
    const seconds = match[3] ?? '00';
    const period = hours24 >= 12 ? 'pm' : 'am';
    const hours12 = hours24 % 12 === 0 ? 12 : hours24 % 12;

    return `${String(hours12).padStart(2, '0')}:${minutes}:${seconds} ${period}`;
  }

  private formatDateTimeValue(value: unknown): string {
    const raw = this.displayValue(value);

    if (raw === 'N/D') {
      return raw;
    }

    const normalized = raw.includes('T') ? raw : raw.replace(' ', 'T');
    const date = new Date(normalized);

    if (Number.isNaN(date.getTime())) {
      return raw;
    }

    return this.formatDateTime(date);
  }

  private formatDateTime(date: Date): string {
    return new Intl.DateTimeFormat('es-MX', {
      dateStyle: 'medium',
      timeStyle: 'short',
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

  private displayValue(value: unknown): string {
    if (value === null || value === undefined) {
      return 'N/D';
    }

    const text = String(value).trim();
    return text ? text : 'N/D';
  }

}
