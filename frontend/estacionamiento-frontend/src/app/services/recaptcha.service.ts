import { Injectable, inject } from '@angular/core';
import { ConfigService } from './config.service';

@Injectable({
  providedIn: 'root'
})
export class RecaptchaService {
  private configService = inject(ConfigService);

  private scriptLoadPromise: Promise<void> | null = null;

  async execute(action: string): Promise<string> {
    const siteKey = this.configService.recaptchaSiteKey;
    if (!siteKey) {
      throw new Error('RECAPTCHA_SITE_KEY no esta configurada en config.json.');
    }

    await this.loadScript(siteKey);

    return new Promise<string>((resolve, reject) => {
      const grecaptcha = window.grecaptcha;
      if (!grecaptcha) {
        reject(new Error('No fue posible inicializar reCAPTCHA.'));
        return;
      }

      grecaptcha.ready(() => {
        grecaptcha.execute(siteKey, { action })
          .then((token) => {
            if (!token) {
              reject(new Error('No se obtuvo token de reCAPTCHA.'));
              return;
            }
            resolve(token);
          })
          .catch(() => reject(new Error('No fue posible obtener token de reCAPTCHA.')));
      });
    });
  }

  private loadScript(siteKey: string): Promise<void> {
    if (typeof window === 'undefined' || typeof document === 'undefined') {
      return Promise.reject(new Error('reCAPTCHA solo esta disponible en navegador.'));
    }

    if (window.grecaptcha) {
      return Promise.resolve();
    }

    if (this.scriptLoadPromise) {
      return this.scriptLoadPromise;
    }

    this.scriptLoadPromise = new Promise<void>((resolve, reject) => {
      const existingScript = document.querySelector('script[data-recaptcha="v3"]') as HTMLScriptElement | null;
      if (existingScript) {
        existingScript.addEventListener('load', () => resolve(), { once: true });
        existingScript.addEventListener('error', () => reject(new Error('No se pudo cargar el script de reCAPTCHA.')), { once: true });
        return;
      }

      const script = document.createElement('script');
      script.src = `https://www.google.com/recaptcha/api.js?render=${encodeURIComponent(siteKey)}`;
      script.async = true;
      script.defer = true;
      script.dataset['recaptcha'] = 'v3';
      script.addEventListener('load', () => resolve(), { once: true });
      script.addEventListener('error', () => reject(new Error('No se pudo cargar el script de reCAPTCHA.')), { once: true });

      document.head.appendChild(script);
    }).catch((error) => {
      this.scriptLoadPromise = null;
      throw error;
    });

    return this.scriptLoadPromise;
  }
}
