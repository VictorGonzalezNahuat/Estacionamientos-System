import { ChangeDetectionStrategy, Component, inject, OnInit, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { AlertService } from '../../../core/services/alert';
import { ConfigService } from '../../../services/config.service';

type TicketType = 'entrada' | 'salida';

interface ReimpresionApiResponse<T> {
  data?: T[];
}

interface EntradaTicketRecord {
  id: number;
  encargado_id?: number;
  placa?: string;
  tarifa_id?: number;
  turno_id?: number;
  fecha_entrada?: string;
  hora_entrada?: string;
  updated_at?: string;
}

interface SalidaTicketRecord {
  id: number;
  tarifa_id?: number;
  encargado_id?: number;
  turno_id?: number;
  fecha_entrada?: string;
  hora_entrada?: string;
  fecha_salida?: string;
  hora_salida?: string;
  placa?: string;
  importe?: number;
  metodo_pago?: string;
  pagado?: boolean;
  updated_at?: string;
}

interface ReimpresionTicketRow {
  id: string;
  placa: string;
  encargadoId: string;
  tarifaId: string;
  turnoId: string;
  fechaEntrada: string;
  horaEntrada: string;
  fechaSalida: string;
  horaSalida: string;
  importe: string;
  metodoPago: string;
  pagado: string;
  actualizado: string;
}

@Component({
  selector: 'app-reimpresion-tickets',
  imports: [],
  templateUrl: './reimpresion-tickets.html',
  styleUrl: './reimpresion-tickets.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ReimpresionTickets implements OnInit {

  private readonly http = inject(HttpClient);
  private readonly config = inject(ConfigService);
  private readonly alert = inject(AlertService);

  readonly ticketType = signal<TicketType>('entrada');
  readonly reimpresionId = signal('');
  readonly records = signal<ReimpresionTicketRow[]>([]);
  readonly loading = signal(false);
  readonly lastUpdated = signal('Sin cargar');

  ngOnInit(): void {
    this.cargarRegistros();
  }

  onTicketTypeChange(value: string): void {
    const nextType: TicketType = value === 'salida' ? 'salida' : 'entrada';

    if (nextType === this.ticketType()) {
      return;
    }

    this.ticketType.set(nextType);
    this.reimpresionId.set('');
    this.cargarRegistros();
  }

  onIdInput(event: Event): void {
    const target = event.target as HTMLInputElement | null;
    this.reimpresionId.set((target?.value ?? '').trim());
  }

  reimprimirTicket(): void {
    const rawId = this.reimpresionId().trim();
    const ticketId = Number(rawId);

    if (!rawId || !Number.isFinite(ticketId) || ticketId < 0) {
      this.alert.error('Ingresa un id valido para reimprimir el ticket.');
      return;
    }

    this.http.post(`${this.config.apiUrl}${this.getReimpresionEndpoint()}/${ticketId}`, {}).subscribe({
      next: () => {
        this.alert.success('El ticket se envio a reimpresion correctamente.');
        this.cargarRegistros(false);
      },
      error: () => {
        this.alert.error('No fue posible reimprimir el ticket seleccionado.');
      }
    });
  }

  get title(): string {
    return this.ticketType() === 'entrada' ? 'Ticket de entrada' : 'Ticket de salida';
  }

  get description(): string {
    return this.ticketType() === 'entrada'
      ? 'Selecciona un ticket de entrada, revisa los ultimos 50 registros y reimprime por su id.'
      : 'Selecciona un ticket de salida, revisa el historial disponible y reimprime por su id.';
  }

  get recordCountLabel(): string {
    const total = this.records().length;
    return total === 1 ? '1 registro cargado' : `${total} registros cargados`;
  }

  private cargarRegistros(showError = true): void {
    this.loading.set(true);

    this.http.get<ReimpresionApiResponse<EntradaTicketRecord> | ReimpresionApiResponse<SalidaTicketRecord> | EntradaTicketRecord[] | SalidaTicketRecord[]>(`${this.config.apiUrl}${this.getListadoEndpoint()}`).subscribe({
      next: (response) => {
        const items = Array.isArray(response) ? response : response?.data ?? [];
        this.records.set(items.map((item) => this.mapRecord(item)));
        this.lastUpdated.set(this.formatDateTime(new Date()));
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);

        if (showError) {
          this.alert.error('No fue posible cargar los registros de reimpresion.');
        }
      }
    });
  }

  private getListadoEndpoint(): string {
    return this.ticketType() === 'entrada'
      ? '/estacionamiento/reimpresion/ultimos'
      : '/history/reimpresion/ultimos';
  }

  private getReimpresionEndpoint(): string {
    return this.ticketType() === 'entrada'
      ? '/estacionamiento/reimpresion'
      : '/history/reimpresion';
  }

  private mapRecord(item: EntradaTicketRecord | SalidaTicketRecord): ReimpresionTicketRow {
    return {
      id: this.displayValue(item?.id),
      placa: this.displayValue(item?.placa),
      encargadoId: this.displayValue(item?.encargado_id),
      tarifaId: this.displayValue(item?.tarifa_id),
      turnoId: this.displayValue(item?.turno_id),
      fechaEntrada: this.formatRawDate(item?.fecha_entrada),
      horaEntrada: this.formatRawTime(item?.hora_entrada),
      fechaSalida: this.formatRawDate((item as SalidaTicketRecord)?.fecha_salida),
      horaSalida: this.formatRawTime((item as SalidaTicketRecord)?.hora_salida),
      importe: this.formatAmount((item as SalidaTicketRecord)?.importe),
      metodoPago: this.displayValue((item as SalidaTicketRecord)?.metodo_pago),
      pagado: this.formatBoolean((item as SalidaTicketRecord)?.pagado),
      actualizado: this.formatDateTimeValue(item?.updated_at),
    };
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

  private formatBoolean(value: unknown): string {
    if (value === null || value === undefined || value === '') {
      return 'N/D';
    }

    return value === true || value === 'true' || value === 1 ? 'Si' : 'No';
  }

  private displayValue(value: unknown): string {
    if (value === null || value === undefined || value === '') {
      return 'N/D';
    }

    return String(value);
  }

}
