import { Injectable } from '@angular/core';
import { Capacitor } from '@capacitor/core';
import { NativeBiometric } from 'capacitor-native-biometric';

type BiometricPlatform = 'mobile' | 'web';

@Injectable({
  providedIn: 'root'
})
export class BiometricService {
  private readonly mobileCredentialKey = 'quick-access-token';
  private readonly webCredentialIdKey = 'quick-access-webauthn-credential-id';
  private readonly webTokenKey = 'quick-access-token-web';
  private readonly rpName = 'Estacionamiento';
  private readonly rpId = window.location.hostname;

  async registerBiometrics(token: string = this.getCurrentToken()): Promise<boolean> {
    if (!token) {
      throw new Error('No hay token para registrar acceso biometrico.');
    }

    if (this.getPlatform() === 'mobile') {
      await this.registerOnMobile(token);
      return true;
    }

    await this.registerOnWeb(token);
    return true;
  }

  async loginWithBiometrics(): Promise<string | null> {
    if (this.getPlatform() === 'mobile') {
      return this.loginOnMobile();
    }

    return this.loginOnWeb();
  }

  private getPlatform(): BiometricPlatform {
    return Capacitor.isNativePlatform() ? 'mobile' : 'web';
  }

  private async registerOnMobile(token: string): Promise<void> {
    const availability = await NativeBiometric.isAvailable();
    if (!availability.isAvailable) {
      throw new Error('Biometria no disponible en este dispositivo.');
    }

    await NativeBiometric.setCredentials({
      username: this.mobileCredentialKey,
      password: token,
      server: this.rpName
    });
  }

  private async loginOnMobile(): Promise<string | null> {
    const availability = await NativeBiometric.isAvailable();
    if (!availability.isAvailable) {
      return null;
    }

    await NativeBiometric.verifyIdentity({
      title: 'Acceso rapido',
      subtitle: 'Autenticacion biometrica',
      description: 'Confirma tu identidad para iniciar sesion',
      maxAttempts: 3
    });

    const credentials = await NativeBiometric.getCredentials({
      server: this.rpName
    });

    if (credentials.username !== this.mobileCredentialKey) {
      return null;
    }

    return credentials.password;
  }

  private async registerOnWeb(token: string): Promise<void> {
    this.ensureWebAuthnSupport();

    const challenge = this.randomBuffer(32);
    const userId = this.getOrCreateWebUserId();

    const credential = await navigator.credentials.create({
      publicKey: {
        challenge,
        rp: {
          name: this.rpName,
          id: this.rpId
        },
        user: {
          id: userId,
          name: 'quick-access',
          displayName: 'Acceso rapido'
        },
        pubKeyCredParams: [
          { type: 'public-key', alg: -7 },
          { type: 'public-key', alg: -257 }
        ],
        timeout: 60_000,
        authenticatorSelection: {
          residentKey: 'preferred',
          userVerification: 'preferred'
        },
        attestation: 'none'
      }
    });

    if (!(credential instanceof PublicKeyCredential)) {
      throw new Error('No fue posible registrar passkey en el navegador.');
    }

    const rawId = new Uint8Array(credential.rawId);
    localStorage.setItem(this.webCredentialIdKey, this.bytesToBase64Url(rawId));
    localStorage.setItem(this.webTokenKey, token);
  }

  private async loginOnWeb(): Promise<string | null> {
    this.ensureWebAuthnSupport();

    const storedCredentialId = localStorage.getItem(this.webCredentialIdKey);
    const storedToken = localStorage.getItem(this.webTokenKey);

    if (!storedCredentialId || !storedToken) {
      return null;
    }

    const assertion = await navigator.credentials.get({
      publicKey: {
        challenge: this.randomBuffer(32),
        allowCredentials: [
          {
            type: 'public-key',
            id: this.base64UrlToBuffer(storedCredentialId)
          }
        ],
        userVerification: 'preferred',
        timeout: 60_000
      }
    });

    if (!(assertion instanceof PublicKeyCredential)) {
      return null;
    }

    return storedToken;
  }

  private ensureWebAuthnSupport(): void {
    const hasSupport =
      typeof window !== 'undefined' &&
      window.isSecureContext &&
      typeof PublicKeyCredential !== 'undefined' &&
      typeof navigator.credentials !== 'undefined';

    if (!hasSupport) {
      throw new Error('WebAuthn no esta disponible. Usa HTTPS y un navegador compatible.');
    }
  }

  private getCurrentToken(): string {
    return localStorage.getItem('token') ?? '';
  }

  private getOrCreateWebUserId(): ArrayBuffer {
    const key = 'quick-access-webauthn-user-id';
    const existing = localStorage.getItem(key);
    if (existing) {
      return this.base64UrlToBuffer(existing);
    }

    const newUserId = this.randomBuffer(32);
    localStorage.setItem(key, this.bufferToBase64Url(newUserId));
    return newUserId;
  }

  private randomBuffer(length: number): ArrayBuffer {
    const buffer = new ArrayBuffer(length);
    crypto.getRandomValues(new Uint8Array(buffer));
    return buffer;
  }

  private bytesToBase64Url(bytes: Uint8Array): string {
    const binary = Array.from(bytes, byte => String.fromCharCode(byte)).join('');
    return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
  }

  private bufferToBase64Url(buffer: ArrayBuffer): string {
    return this.bytesToBase64Url(new Uint8Array(buffer));
  }

  private base64UrlToBuffer(value: string): ArrayBuffer {
    const base64 = value.replace(/-/g, '+').replace(/_/g, '/');
    const padded = base64.padEnd(Math.ceil(base64.length / 4) * 4, '=');
    const binary = atob(padded);
    return Uint8Array.from(binary, char => char.charCodeAt(0)).buffer.slice(0);
  }
}