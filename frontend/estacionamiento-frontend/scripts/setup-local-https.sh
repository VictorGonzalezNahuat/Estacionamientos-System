#!/usr/bin/env bash
set -euo pipefail

LOCAL_IP="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || true)"

mkdir -p certs

mkcert -install

if [[ -n "$LOCAL_IP" ]]; then
  mkcert -key-file certs/local-dev-key.pem -cert-file certs/local-dev-cert.pem localhost 127.0.0.1 ::1 "$LOCAL_IP"
  echo "HTTPS local configurado para localhost y IP LAN: $LOCAL_IP"
else
  mkcert -key-file certs/local-dev-key.pem -cert-file certs/local-dev-cert.pem localhost 127.0.0.1 ::1
  echo "HTTPS local configurado para localhost. No se detecto IP LAN automaticamente."
fi
