declare module 'qrcode' {
  export interface ToDataUrlOptions {
    errorCorrectionLevel?: 'L' | 'M' | 'Q' | 'H' | 'low' | 'medium' | 'quartile' | 'high';
    margin?: number;
    width?: number;
  }

  export function toDataURL(text: string, options?: ToDataUrlOptions): Promise<string>;

  const QRCode: {
    toDataURL: typeof toDataURL;
  };

  export default QRCode;
}
