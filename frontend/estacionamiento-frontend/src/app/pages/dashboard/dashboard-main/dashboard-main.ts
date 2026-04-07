import { ChangeDetectionStrategy, Component, inject, OnInit, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { RouterLink } from '@angular/router';
import { ConfigService } from '../../../services/config.service';

type MiTurnoEstado = 'sin-turno' | 'abierto' | 'pendiente-corte';

type MiTurnoResponse = {
  estado: MiTurnoEstado;
  turno_id?: number;
  hora_apertura?: string;
};

@Component({
  selector: 'app-dashboard-main',
  imports: [RouterLink],
  templateUrl: './dashboard-main.html',
  styleUrl: './dashboard-main.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DashboardMain implements OnInit {

  private readonly http = inject(HttpClient);
  private readonly configService = inject(ConfigService);

  readonly loadingEstadoTurno = signal(true);
  readonly estadoTurno = signal<MiTurnoEstado | null>(null);

  ngOnInit(): void {
    this.obtenerEstadoTurno();
  }

  private obtenerEstadoTurno(): void {
    this.loadingEstadoTurno.set(true);

    this.http.get<MiTurnoResponse>(`${this.configService.apiUrl}/turnos/mi-turno`).subscribe({
      next: (response) => {
        this.estadoTurno.set(response?.estado ?? 'sin-turno');
        this.loadingEstadoTurno.set(false);
      },
      error: () => {
        this.estadoTurno.set(null);
        this.loadingEstadoTurno.set(false);
      },
    });
  }

  get turnoStatusText(): string {
    const estado = this.estadoTurno();

    if (estado === 'abierto') {
      return 'Tu turno actual está abierto.';
    }

    if (estado === 'pendiente-corte') {
      return 'Tu turno está pendiente de corte.';
    }

    if (estado === 'sin-turno') {
      return 'No tienes turno abierto actualmente.';
    }

    return 'No se pudo obtener el estado del turno.';
  }

  get turnoStatusClass(): string {
    const estado = this.estadoTurno();

    if (estado === 'abierto') {
      return 'status-open';
    }

    if (estado === 'pendiente-corte') {
      return 'status-warning';
    }

    if (estado === 'sin-turno') {
      return 'status-closed';
    }

    return 'status-error';
  }
}
