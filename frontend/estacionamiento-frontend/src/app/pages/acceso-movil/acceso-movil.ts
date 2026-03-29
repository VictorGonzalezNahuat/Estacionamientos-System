import { Component, ChangeDetectionStrategy, ElementRef, OnDestroy, OnInit, ViewChild, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { ActivatedRoute, Router } from '@angular/router';
import { ConfigService } from '../../services/config.service';
import { AlertService } from '../../core/services/alert';
import { AuthService } from '../../services/auth.service';
import type { BrowserMultiFormatReader, IScannerControls } from '@zxing/browser';
import QRCode from 'qrcode';

type BarcodeLike = { rawValue?: string };

type BarcodeDetectorLike = {
  detect(source: ImageBitmapSource): Promise<BarcodeLike[]>;
};

type BarcodeDetectorCtorLike = {
  new(options?: { formats?: string[] }): BarcodeDetectorLike;
};

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
}

interface PagoPendienteStorage {
  preferenciaId: string;
  placa: string;
  createdAt: number;
  checkoutUrl?: string;
}

@Component({
  selector: 'app-acceso-movil',
  imports: [],
  templateUrl: './acceso-movil.html',
  styleUrl: './acceso-movil.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AccesoMovil implements OnDestroy {

  @ViewChild('videoPreview') private videoPreview?: ElementRef<HTMLVideoElement>;

  private http = inject(HttpClient);
  private config = inject(ConfigService);
  private alert = inject(AlertService);
  private authService = inject(AuthService);
  private router = inject(Router);
  private route = inject(ActivatedRoute);

  private static readonly PAGO_PENDIENTE_KEY = 'pago_tarjeta_pendiente_movil';
  private static readonly POLLING_INTERVAL_MS = 4000;
  private static readonly POLLING_TIMEOUT_MS = 120000;
  private static readonly PAGO_PENDIENTE_TTL_MS = 15 * 60 * 1000;

  scanning = signal(false);
  loading = signal(false);
  scannerError = signal('');
  pollingEnCurso = signal(false);
  preferenciaIdPendiente = signal<string | null>(null);
  placaPendientePago = signal<string | null>(null);
  checkoutUrlPendiente = signal<string | null>(null);
  checkoutQrDataUrl = signal<string | null>(null);
  qrGenerando = signal(false);
  qrVisible = signal(false);

  private scanInterval: ReturnType<typeof setInterval> | null = null;
  private videoStream: MediaStream | null = null;
  private detector: BarcodeDetectorLike | null = null;
  private zxingReader: BrowserMultiFormatReader | null = null;
  private zxingControls: IScannerControls | null = null;
  private scanningFrame = false;
  private pagoPollingInterval: ReturnType<typeof setInterval> | null = null;
  private pagoPollingTimeout: ReturnType<typeof setTimeout> | null = null;

  ngOnInit(): void {
    this.restaurarPagoPendiente();
  }

  ngOnDestroy(): void {
    this.stopScanner();
    this.detenerPollingPago();
  }

  logout(): void {
    const message = '¿Deseas cerrar tu sesión?';
    this.alert.confirm(
      message,
      'Cerrar Sesión',
      'Cerrar Sesión',
      'Cancelar'
    ).then((confirmed) => {
      if (confirmed) {
        localStorage.removeItem('token');
        this.router.navigate(['/login']);
      }
    });
  }

  async startScanner(): Promise<void> {
    this.scannerError.set('');
    if (this.scanning()) return;

    const BarcodeDetectorCtor = (window as Window & { BarcodeDetector?: BarcodeDetectorCtorLike }).BarcodeDetector;
    if (!navigator.mediaDevices?.getUserMedia) {
      this.fallbackManualEntry();
      return;
    }

    this.scanning.set(true);

    const video = await this.waitForVideoElement();
    if (!video) {
      this.stopScanner();
      return;
    }

    if (!BarcodeDetectorCtor) {
      await this.startZxingScanner(video);
      return;
    }

    try {
      this.detector = new BarcodeDetectorCtor({
        formats: ['qr_code', 'code_128', 'code_39', 'ean_13', 'ean_8', 'upc_a', 'upc_e']
      });

      this.videoStream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: { ideal: 'environment' }
        },
        audio: false,
      });

      video.srcObject = this.videoStream;
      await video.play();
      this.startDetectLoop();
    } catch {
      this.stopScanner();
      this.scannerError.set('No se pudo acceder a la cámara. Puedes capturar el código manualmente.');
      this.fallbackManualEntry();
    }
  }

  closeScanner(): void {
    this.stopScanner();
  }

  private startDetectLoop(): void {
    if (this.scanInterval) {
      clearInterval(this.scanInterval);
    }

    this.scanInterval = setInterval(async () => {
      if (this.scanningFrame || !this.detector) return;

      const video = this.videoPreview?.nativeElement;
      if (!video || video.readyState < HTMLMediaElement.HAVE_ENOUGH_DATA) return;

      this.scanningFrame = true;

      try {
        const barcodes = await this.detector.detect(video);
        const value = barcodes.find(code => !!code.rawValue)?.rawValue?.trim();

        if (value) {
          this.stopScanner();
          this.retirarVehiculo(value);
        }
      } catch {
        this.scannerError.set('No fue posible leer el código. Intenta nuevamente.');
      } finally {
        this.scanningFrame = false;
      }
    }, 250);
  }

  private stopScanner(): void {
    if (this.scanInterval) {
      clearInterval(this.scanInterval);
      this.scanInterval = null;
    }

    if (this.videoStream) {
      this.videoStream.getTracks().forEach(track => track.stop());
      this.videoStream = null;
    }

    if (this.zxingControls) {
      this.zxingControls.stop();
      this.zxingControls = null;
    }

    this.zxingReader = null;

    const video = this.videoPreview?.nativeElement;
    if (video) {
      video.pause();
      video.srcObject = null;
    }

    this.detector = null;
    this.scanning.set(false);
  }

  private async waitForVideoElement(): Promise<HTMLVideoElement | null> {
    for (let i = 0; i < 6; i++) {
      const video = this.videoPreview?.nativeElement;
      if (video) return video;
      await new Promise(resolve => setTimeout(resolve, 40));
    }
    this.scannerError.set('No se pudo iniciar el visor de camara.');
    return null;
  }

  private async startZxingScanner(video: HTMLVideoElement): Promise<void> {
    try {
      const zxing = await import('@zxing/browser');
      this.zxingReader = new zxing.BrowserMultiFormatReader();
      this.zxingControls = await this.zxingReader.decodeFromVideoDevice(undefined, video, (result) => {
        const code = result?.getText?.()?.trim();
        if (!code) return;
        this.stopScanner();
        this.retirarVehiculo(code);
      });
    } catch {
      this.stopScanner();
      this.scannerError.set('No se pudo iniciar el escáner en este dispositivo.');
      this.fallbackManualEntry();
    }
  }

  private fallbackManualEntry(): void {
    const code = window.prompt('Escáner no disponible. Ingresa la placa/código para salida:');
    if (!code) return;

    this.retirarVehiculo(code);
  }

  private async retirarVehiculo(code: string): Promise<void> {
    const placa = code.trim().toUpperCase();
    if (!placa) return;

    if (this.pollingEnCurso()) {
      this.alert.error('Ya hay un pago con tarjeta en proceso de confirmacion');
      return;
    }

    const metodo = await this.seleccionarMetodoPagoSalida();
    if (!metodo) return;

    this.loading.set(true);

    if (metodo === 'tarjeta') {
      this.solicitarSalidaTarjeta(placa);
      return;
    }

    this.http.post(`${this.config.apiUrl}/estacionamiento/salir`, { placa }).subscribe({
      next: (res: any) => {
        this.alert.info('Vehículo retirado correctamente', res);
        const importe = res?.importe != null ? `El importe a cobrar es ${res.importe} pesos` : '';
        this.speak(`Vehículo retirado. ${importe}`);
        this.loading.set(false);
      },
      error: () => {
        this.alert.error('No se pudo retirar el vehículo con el código leído');
        this.loading.set(false);
      }
    });
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

  private solicitarSalidaTarjeta(placa: string): void {
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
        this.alert.error('No se pudo iniciar el pago con tarjeta');
        this.loading.set(false);
      }
    });
  }

  private restaurarPagoPendiente(): void {
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

  private iniciarPollingPago(preferenciaId: string): void {
    this.detenerPollingPago();

    this.preferenciaIdPendiente.set(preferenciaId);
    this.pollingEnCurso.set(true);

    this.consultarEstadoPago(preferenciaId);

    this.pagoPollingInterval = setInterval(() => {
      this.consultarEstadoPago(preferenciaId);
    }, AccesoMovil.POLLING_INTERVAL_MS);

    this.pagoPollingTimeout = setTimeout(() => {
      this.detenerPollingPago();
      this.loading.set(false);
      void this.ofrecerReintentoConsulta(
        'No se pudo confirmar el pago en el tiempo esperado. ¿Deseas reintentar la consulta?'
      );
    }, AccesoMovil.POLLING_TIMEOUT_MS);
  }

  private consultarEstadoPago(preferenciaId: string): void {
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

  private procesarEstadoPago(estado: EstadoPagoResponse): void {
    const estadoTransaccion = (estado?.estado_transaccion ?? '').toLowerCase();
    const transaccionExitosa = estado?.transaccion_exitosa === true;
    const pagado = estado?.pagado === true;
    const mensajeEstado = estado?.mensaje_estado?.trim();

    if ((estadoTransaccion === 'completado' || transaccionExitosa) && pagado) {
      this.detenerPollingPago();
      this.limpiarPagoPendiente();
      this.alert.success(
        mensajeEstado || 'Pago con tarjeta confirmado. Vehiculo retirado correctamente.'
      );
      this.speak('Pago con tarjeta confirmado. Vehiculo retirado correctamente');
      this.loading.set(false);
      return;
    }

    if (estadoTransaccion === 'rechazado' || estadoTransaccion === 'cancelado') {
      this.detenerPollingPago();
      this.limpiarPagoPendiente();
      this.loading.set(false);
      this.alert.error(mensajeEstado || `El pago fue ${estadoTransaccion}.`);
    }
  }

  private async ofrecerReintentoConsulta(mensaje: string): Promise<void> {
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

  private reintentarConsultaPago(): void {
    const preferenciaId = this.preferenciaIdPendiente();
    if (preferenciaId) {
      this.iniciarPollingPago(preferenciaId);
      return;
    }

    const placa = this.placaPendientePago();
    if (!placa) {
      this.alert.error('No hay referencia de pago pendiente para reintentar.');
      return;
    }

    this.buscarPagoPendientePorPlaca(placa);
  }

  private buscarPagoPendientePorPlaca(placa: string): void {
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

  private guardarPagoPendiente(preferenciaId: string, placa: string, checkoutUrl?: string): void {
    this.preferenciaIdPendiente.set(preferenciaId);
    this.placaPendientePago.set(placa);
    this.checkoutUrlPendiente.set(checkoutUrl ?? null);

    const data: PagoPendienteStorage = {
      preferenciaId,
      placa,
      createdAt: Date.now(),
      checkoutUrl,
    };

    localStorage.setItem(AccesoMovil.PAGO_PENDIENTE_KEY, JSON.stringify(data));
  }

  private leerPagoPendiente(): PagoPendienteStorage | null {
    const raw = localStorage.getItem(AccesoMovil.PAGO_PENDIENTE_KEY);
    if (!raw) return null;

    try {
      const parsed = JSON.parse(raw) as Partial<PagoPendienteStorage>;
      if (!parsed.preferenciaId || !parsed.createdAt || !parsed.placa) {
        this.limpiarPagoPendiente();
        return null;
      }

      const vencido = Date.now() - parsed.createdAt > AccesoMovil.PAGO_PENDIENTE_TTL_MS;
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

  private limpiarPagoPendiente(): void {
    localStorage.removeItem(AccesoMovil.PAGO_PENDIENTE_KEY);
    this.preferenciaIdPendiente.set(null);
    this.placaPendientePago.set(null);
    this.checkoutUrlPendiente.set(null);
    this.checkoutQrDataUrl.set(null);
    this.qrVisible.set(false);
  }

  private detenerPollingPago(): void {
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

  private mostrarQrPago(checkoutUrl: string): void {
    this.checkoutUrlPendiente.set(checkoutUrl);
    this.qrVisible.set(true);
    void this.generarQrDesdeCheckoutUrl(checkoutUrl);
  }

  ocultarQrPago(): void {
    this.qrVisible.set(false);
  }

  async copiarCheckoutUrl(): Promise<void> {
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

  private async generarQrDesdeCheckoutUrl(checkoutUrl: string): Promise<void> {
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

  private speak(text: string): void {
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

}
