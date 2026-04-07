import { Component, inject, signal, OnInit, ElementRef, ViewChild, OnDestroy, ChangeDetectionStrategy, AfterViewInit } from '@angular/core';
import { CurrencyPipe, DatePipe } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { ConfigService } from '../../../services/config.service';
import { AlertService } from '../../../core/services/alert';
import { ActivatedRoute, Router } from '@angular/router';
import QRCode from 'qrcode';

type MetodoPago = 'efectivo' | 'tarjeta';

interface SalidaTarjetaResponse {
  checkout_url?: string;
  preferencia_id?: string;
}

interface EstadoPagoResponse {
  estado_transaccion?: string;
  transaccion_exitosa?: boolean;
  mensaje_estado?: string;
  pagado?: boolean;
  metodo_pago?: string;
  importe?: number;
  webhook_timestamp?: string;
}

interface CancelarPagoRequest {
  provider: string;
  motivo: string;
}

interface CancelarPagoResponse {
  preferencia_id?: string;
  estado_transaccion?: string;
  cancelado_local?: boolean;
  cancelado_remoto?: boolean;
  provider?: string;
  motivo?: string;
  detalle?: string;
}

interface PagoPendienteStorage {
  preferenciaId: string;
  placa: string;
  createdAt: number;
  checkoutUrl?: string;
}

@Component({
  selector: 'app-entradas-salidas',
  standalone: true,
  imports: [ReactiveFormsModule, DatePipe, CurrencyPipe],
  templateUrl: './entradas-salidas.html',
  styleUrl: './entradas-salidas.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class EntradasSalidas implements OnInit, OnDestroy, AfterViewInit {

  private static readonly PAGO_PENDIENTE_KEY = 'pago_tarjeta_pendiente';
  private static readonly POLLING_INTERVAL_MS = 4000;
  private static readonly POLLING_TIMEOUT_MS = 120000;
  private static readonly PAGO_PENDIENTE_TTL_MS = 15 * 60 * 1000;

  private http = inject(HttpClient);
  private fb = inject(FormBuilder);
  private config = inject(ConfigService);
  private alert = inject(AlertService);
  private router = inject(Router);
  private route = inject(ActivatedRoute);
  private relojInterval: any;
  private refreshInterval: any;
  private pagoPollingInterval: any;
  private pagoPollingTimeout: any;


  @ViewChild('placaInput') placaInput!: ElementRef<HTMLInputElement>;

  user = signal<any>(null);
  turno = signal<any>(null);
  tarifa = signal<any>(null);
  loading = signal(false);
  now = signal(new Date());
  estacionados = signal<any[]>([]);
  estado = signal<any>(null);
  preferenciaIdPendiente = signal<string | null>(null);
  placaPendientePago = signal<string | null>(null);
  pollingEnCurso = signal(false);
  checkoutUrlPendiente = signal<string | null>(null);
  checkoutQrDataUrl = signal<string | null>(null);
  qrGenerando = signal(false);
  qrVisible = signal(false);
  cancelandoPago = signal(false);



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
    this.restaurarPagoPendiente();
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


  async ingresarVehiculo() {
    if (this.form.invalid) return;
    if (this.pollingEnCurso()) {
      this.alert.error('Ya hay un pago con tarjeta en proceso de confirmacion');
      return;
    }

    const placa = this.form.value.placa?.toUpperCase().trim();

    if (!placa) return;

    this.loading.set(true);
    const yaDentro = this.estacionados().some(auto => (auto?.placa ?? '').toUpperCase() === placa);

    if (yaDentro) {
      await this.solicitarSalidaSegunMetodo(placa, true);
      return;
    }

    this.solicitarIngreso(placa, true);
  }

  getSubmitLabel(): string {
    if (this.pollingEnCurso()) {
      return 'Consultando pago...';
    }
    return this.loading() ? 'Procesando...' : 'Ingresar / Salir';
  }

  private reintentarConsultaPago() {
    const preferenciaId = this.preferenciaIdPendiente();
    if (preferenciaId) {
      this.iniciarPollingPago(preferenciaId);
      return;
    }

    const placaFormulario = this.form.value.placa?.toUpperCase().trim();
    const placa = placaFormulario || this.placaPendientePago();

    if (!placa) {
      this.alert.error('No hay referencia de pago. Ingresa la placa para buscar un pendiente.');
      return;
    }

    this.buscarPagoPendientePorPlaca(placa);
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
          void this.solicitarSalidaSegunMetodo(placa, false);
          return;
        }
        this.alert.error('La placa no pudo ingresar ni salir', () => this.focusAndSelectPlaca());
        this.loading.set(false);
      }
    });
  }

  private async solicitarSalidaSegunMetodo(placa: string, allowFallback: boolean) {
    const metodo = await this.seleccionarMetodoPagoSalida();
    if (!metodo) {
      this.loading.set(false);
      this.focusAndSelectPlaca();
      return;
    }

    if (metodo === 'tarjeta') {
      this.solicitarSalidaTarjeta(placa, allowFallback);
      return;
    }

    this.solicitarSalida(placa, allowFallback);
  }

  private seleccionarMetodoPagoSalida(): Promise<MetodoPago | null> {
    return this.alert.selectPaymentMethod(
      'Selecciona como deseas cobrar la salida del vehiculo.',
      'Metodo de pago',
      'Efectivo',
      'Pagar en linea',
      'Cancelar'
    );
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

  private solicitarSalidaTarjeta(placa: string, allowFallback: boolean) {
    this.http.post<SalidaTarjetaResponse>(
      `${this.config.apiUrl}/pagos/salir_tarjeta`,
      { placa }
    ).subscribe({
      next: (res) => {
        const checkoutUrl = res?.checkout_url;
        const preferenciaId = res?.preferencia_id;

        if (!checkoutUrl || !preferenciaId) {
          this.alert.error('No fue posible iniciar el pago con tarjeta.');
          this.loading.set(false);
          return;
        }

        this.guardarPagoPendiente(preferenciaId, placa, checkoutUrl);
        this.mostrarQrPago(checkoutUrl);
        this.iniciarPollingPago(preferenciaId);
        this.loading.set(false);
      },
      error: () => {
        if (allowFallback) {
          this.solicitarIngreso(placa, false);
          return;
        }

        this.alert.error('No se pudo iniciar el pago con tarjeta', () => this.focusAndSelectPlaca());
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
    this.detenerPollingPago();
  }

  private restaurarPagoPendiente() {
    const preferenciaEnQuery = this.route.snapshot.queryParamMap.get('preferencia_id');
    const placaEnQuery = this.route.snapshot.queryParamMap.get('placa');
    const checkoutUrlEnQuery = this.route.snapshot.queryParamMap.get('checkout_url');

    if (preferenciaEnQuery) {
      const placa = placaEnQuery?.toUpperCase().trim() || this.placaPendientePago() || '';
      this.guardarPagoPendiente(preferenciaEnQuery, placa, checkoutUrlEnQuery ?? undefined);
      if (checkoutUrlEnQuery) {
        this.mostrarQrPago(checkoutUrlEnQuery);
      }
      this.iniciarPollingPago(preferenciaEnQuery);
      return;
    }

    const pendiente = this.leerPagoPendiente();
    if (!pendiente) return;

    this.preferenciaIdPendiente.set(pendiente.preferenciaId);
    this.placaPendientePago.set(pendiente.placa);
    if (pendiente.checkoutUrl) {
      this.mostrarQrPago(pendiente.checkoutUrl);
    }
    this.iniciarPollingPago(pendiente.preferenciaId);
  }

  private iniciarPollingPago(preferenciaId: string) {
    this.detenerPollingPago();

    this.preferenciaIdPendiente.set(preferenciaId);
    this.pollingEnCurso.set(true);
    this.cancelandoPago.set(false);

    this.consultarEstadoPago(preferenciaId);

    this.pagoPollingInterval = setInterval(() => {
      this.consultarEstadoPago(preferenciaId);
    }, EntradasSalidas.POLLING_INTERVAL_MS);

    this.pagoPollingTimeout = setTimeout(() => {
      this.detenerPollingPago();
      this.loading.set(false);
      void this.ofrecerReintentoConsulta(
        'No se pudo confirmar el pago en el tiempo esperado. ¿Deseas reintentar la consulta?'
      );
    }, EntradasSalidas.POLLING_TIMEOUT_MS);
  }

  private consultarEstadoPago(preferenciaId: string) {
    this.http.get<EstadoPagoResponse>(
      `${this.config.apiUrl}/pagos/estado/${encodeURIComponent(preferenciaId)}`
    ).subscribe({
      next: (estado) => this.procesarEstadoPago(estado),
      error: () => {
        this.detenerPollingPago();
        this.loading.set(false);
        void this.ofrecerReintentoConsulta(
          'No se pudo consultar el estado del pago por un problema de red. ¿Deseas reintentar?'
        );
      }
    });
  }

  private procesarEstadoPago(estado: EstadoPagoResponse) {
    const estadoTransaccion = (estado?.estado_transaccion ?? '').toLowerCase();
    const transaccionExitosa = estado?.transaccion_exitosa === true;
    const pagado = estado?.pagado === true;
    const mensajeEstado = estado?.mensaje_estado?.trim();

    if ((estadoTransaccion === 'completado' || transaccionExitosa) && pagado) {
      this.detenerPollingPago();
      this.limpiarPagoPendiente();
      this.alert.success(
        mensajeEstado || 'Pago con tarjeta confirmado. Vehiculo retirado correctamente.',
        () => this.focusAndSelectPlaca()
      );
      this.speak('Pago con tarjeta confirmado. Vehiculo retirado correctamente');
      this.postOperacionExitosa();
      return;
    }

    if (estadoTransaccion === 'rechazado' || estadoTransaccion === 'cancelado') {
      this.detenerPollingPago();
      this.limpiarPagoPendiente();
      this.loading.set(false);
      this.alert.error(mensajeEstado || `El pago fue ${estadoTransaccion}.`);
      return;
    }
  }

  private buscarPagoPendientePorPlaca(placa: string) {
    this.loading.set(true);
    this.http.get<any>(
      `${this.config.apiUrl}/pagos/placa/${encodeURIComponent(placa)}/pendiente`
    ).subscribe({
      next: (res) => {
        const preferenciaId = this.extraerPreferenciaId(res);
        this.loading.set(false);

        if (!preferenciaId) {
          this.alert.error(`No existe pago pendiente para la placa ${placa}.`);
          return;
        }

        this.guardarPagoPendiente(preferenciaId, placa);
        this.iniciarPollingPago(preferenciaId);
      },
      error: () => {
        this.loading.set(false);
        this.alert.error('No fue posible buscar pagos pendientes por placa.');
      }
    });
  }

  private async ofrecerReintentoConsulta(mensaje: string) {
    const reintentar = await this.alert.confirm(
      mensaje,
      'Pago con tarjeta',
      'Reintentar',
      'Cerrar'
    );

    if (reintentar) {
      this.reintentarConsultaPago();
    }
  }

  private extraerPreferenciaId(payload: any): string | null {
    if (!payload || typeof payload !== 'object') return null;

    if (typeof payload.preferencia_id === 'string' && payload.preferencia_id.trim()) {
      return payload.preferencia_id;
    }

    if (payload.data && typeof payload.data.preferencia_id === 'string' && payload.data.preferencia_id.trim()) {
      return payload.data.preferencia_id;
    }

    return null;
  }

  private guardarPagoPendiente(preferenciaId: string, placa: string, checkoutUrl?: string) {
    this.preferenciaIdPendiente.set(preferenciaId);
    this.placaPendientePago.set(placa);
    this.checkoutUrlPendiente.set(checkoutUrl ?? null);

    const data: PagoPendienteStorage = {
      preferenciaId,
      placa,
      createdAt: Date.now(),
      checkoutUrl,
    };

    localStorage.setItem(EntradasSalidas.PAGO_PENDIENTE_KEY, JSON.stringify(data));
  }

  private leerPagoPendiente(): PagoPendienteStorage | null {
    const raw = localStorage.getItem(EntradasSalidas.PAGO_PENDIENTE_KEY);
    if (!raw) return null;

    try {
      const parsed = JSON.parse(raw) as Partial<PagoPendienteStorage>;
      if (!parsed.preferenciaId || !parsed.createdAt || !parsed.placa) {
        this.limpiarPagoPendiente();
        return null;
      }

      const vencido = Date.now() - parsed.createdAt > EntradasSalidas.PAGO_PENDIENTE_TTL_MS;
      if (vencido) {
        this.limpiarPagoPendiente();
        return null;
      }

      return {
        preferenciaId: parsed.preferenciaId,
        placa: parsed.placa,
        createdAt: parsed.createdAt,
        checkoutUrl: parsed.checkoutUrl,
      };
    } catch {
      this.limpiarPagoPendiente();
      return null;
    }
  }

  private limpiarPagoPendiente() {
    localStorage.removeItem(EntradasSalidas.PAGO_PENDIENTE_KEY);
    this.preferenciaIdPendiente.set(null);
    this.placaPendientePago.set(null);
    this.checkoutUrlPendiente.set(null);
    this.checkoutQrDataUrl.set(null);
    this.qrVisible.set(false);
    this.cancelandoPago.set(false);
  }

  ocultarQrPago() {
    this.qrVisible.set(false);
  }

  async copiarCheckoutUrl() {
    const url = this.checkoutUrlPendiente();
    if (!url) {
      this.alert.error('No hay link de pago disponible para copiar.');
      return;
    }

    try {
      await navigator.clipboard.writeText(url);
      this.alert.success('Link de pago copiado al portapapeles.');
    } catch {
      this.alert.error('No se pudo copiar el link de pago.');
    }
  }

  async cancelarPagoEnLinea() {
    const preferenciaId = this.preferenciaIdPendiente();
    if (!preferenciaId || this.cancelandoPago()) {
      return;
    }

    const confirmar = await this.alert.confirm(
      'Esto cancelara la transaccion en linea y detendra la consulta del estado. ¿Deseas continuar?',
      'Cancelar pago en linea',
      'Si, cancelar pago',
      'Seguir esperando'
    );

    if (!confirmar) {
      return;
    }

    this.cancelandoPago.set(true);
    this.detenerPollingPago();

    const placa = this.placaPendientePago() || 'N/D';
    const payload: CancelarPagoRequest = {
      provider: 'stripe',
      motivo: `Cancelado por operador en Entradas/Salidas. Placa: ${placa}`,
    };

    this.http.post<CancelarPagoResponse>(
      `${this.config.apiUrl}/pagos/cancelar/${encodeURIComponent(preferenciaId)}`,
      payload
    ).subscribe({
      next: (res) => {
        const canceladoLocal = res?.cancelado_local === true;
        const canceladoRemoto = res?.cancelado_remoto === true;
        const detalle = res?.detalle?.trim();

        if (canceladoLocal && canceladoRemoto) {
          this.alert.success(detalle || 'Pago en linea cancelado correctamente.', () => this.focusAndSelectPlaca());
        } else if (canceladoLocal || canceladoRemoto) {
          this.alert.info(
            detalle || 'La cancelacion fue parcial. Verifica el estado final de la transaccion.',
            res
          );
        } else {
          this.alert.error(detalle || 'No fue posible cancelar la transaccion en linea.');
        }

        this.limpiarPagoPendiente();
        this.loading.set(false);
        this.cancelandoPago.set(false);
      },
      error: () => {
        this.cancelandoPago.set(false);
        this.loading.set(false);
        this.alert.error('No se pudo cancelar el pago en linea.');
      }
    });
  }

  private mostrarQrPago(checkoutUrl: string) {
    this.checkoutUrlPendiente.set(checkoutUrl);
    this.qrVisible.set(true);
    void this.generarQrDesdeCheckoutUrl(checkoutUrl);
  }

  private async generarQrDesdeCheckoutUrl(checkoutUrl: string) {
    this.qrGenerando.set(true);
    this.checkoutQrDataUrl.set(null);

    try {
      const dataUrl = await QRCode.toDataURL(checkoutUrl, {
        errorCorrectionLevel: 'M',
        margin: 2,
        width: 320,
      });
      this.checkoutQrDataUrl.set(dataUrl);
    } catch {
      this.alert.error('No se pudo generar el codigo QR para el pago.');
    } finally {
      this.qrGenerando.set(false);
    }
  }

  private detenerPollingPago() {
    if (this.pagoPollingInterval) {
      clearInterval(this.pagoPollingInterval);
      this.pagoPollingInterval = null;
    }

    if (this.pagoPollingTimeout) {
      clearTimeout(this.pagoPollingTimeout);
      this.pagoPollingTimeout = null;
    }

    this.pollingEnCurso.set(false);
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
