import { Component, ChangeDetectionStrategy, ElementRef, OnDestroy, ViewChild, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { ConfigService } from '../../services/config.service';
import { AlertService } from '../../core/services/alert';
import { AuthService } from '../../services/auth.service';
import type { BrowserMultiFormatReader, IScannerControls } from '@zxing/browser';

type BarcodeLike = { rawValue?: string };

type BarcodeDetectorLike = {
  detect(source: ImageBitmapSource): Promise<BarcodeLike[]>;
};

type BarcodeDetectorCtorLike = {
  new(options?: { formats?: string[] }): BarcodeDetectorLike;
};

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

  scanning = signal(false);
  loading = signal(false);
  scannerError = signal('');

  private scanInterval: ReturnType<typeof setInterval> | null = null;
  private videoStream: MediaStream | null = null;
  private detector: BarcodeDetectorLike | null = null;
  private zxingReader: BrowserMultiFormatReader | null = null;
  private zxingControls: IScannerControls | null = null;
  private scanningFrame = false;

  ngOnDestroy(): void {
    this.stopScanner();
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

  private retirarVehiculo(code: string): void {
    const placa = code.trim().toUpperCase();
    if (!placa) return;

    this.loading.set(true);
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
