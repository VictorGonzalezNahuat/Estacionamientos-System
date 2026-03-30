# Despliegue de webhooks de pago (Stripe y Cloudflare)

Esta guia integra y extiende el documento operativo `backend/Estacionamientos-backend/DEPLOYMENT_WEBHOOKS.md`.

Objetivo:
- asegurar que los eventos webhook lleguen al backend sin bloqueo WAF.
- validar firma correctamente y reflejar pagos en base de datos.

## 1) Endpoint recomendado

Usar endpoint especifico de Stripe:
- `POST /pagos/webhook/stripe`

Ejemplo URL produccion:
- `https://api-estacionamiento.server-ofic.online/pagos/webhook/stripe`

Tambien existe endpoint generico:
- `POST /pagos/webhook`

## 2) Configurar webhook en Stripe

1. Ir a Developers > Webhooks > Add endpoint.
2. Registrar URL exacta del endpoint.
3. Suscribir eventos:
   - `checkout.session.completed`
   - `checkout.session.expired`
   - `checkout.session.async_payment_failed`
4. Copiar Signing Secret (`whsec_...`).
5. Guardar en `.env` como `STRIPE_WEBHOOK_SECRET`.
6. Reiniciar backend.

## 3) Configurar Cloudflare (obligatorio si hay WAF)

Si Stripe reporta HTTP 403 con HTML de Cloudflare, la peticion no llega al backend.

Crear regla WAF tipo Skip para el endpoint:

Condicion sugerida:
- `http.request.method eq "POST" and http.request.uri.path eq "/pagos/webhook/stripe"`

Accion:
- `Skip`

Componentes a omitir:
- Managed Rules
- Super Bot Fight Mode Rules
- Rate limiting rules
- Custom rules restantes que bloqueen esta ruta

Prioridad:
- colocar la regla al inicio (prioridad mas alta).

## 4) Variables de entorno minimas (Stripe)

```dotenv
PAYMENT_PROVIDER=stripe
STRIPE_SECRET_KEY=sk_test_xxx
STRIPE_PUBLISHABLE_KEY=pk_test_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
WEBHOOK_URL=https://api-estacionamiento.server-ofic.online
STRIPE_SUCCESS_URL=https://api-estacionamiento.server-ofic.online/pago-exitoso?session_id={CHECKOUT_SESSION_ID}
STRIPE_CANCEL_URL=https://api-estacionamiento.server-ofic.online/pago-cancelado
STRIPE_CURRENCY=mxn
APP_TIMEZONE=America/Mexico_City
```

## 5) Checklist post deploy

1. Reenviar evento desde Stripe Dashboard (Resend).
2. Confirmar HTTP 200 en delivery.
3. Verificar en BD:
   - `payment_transactions.estado` cambia a `completado`.
   - `payment_transactions.webhook_timestamp` deja de ser `NULL`.
   - `history_estacionamiento.pagado` se actualiza.
4. Confirmar salida de vehiculo de `current_estacionamiento`.

## 6) Diagnostico rapido

Caso A: 403 con HTML de Cloudflare.
- Causa: bloqueo WAF antes del backend.
- Accion: corregir regla Skip.

Caso B: 403 JSON {"detail":"Firma de webhook invalida"}.
- Causa: el request llega al backend, pero firma no coincide.
- Accion:
  - verificar secret del endpoint exacto;
  - validar modo test/live correcto;
  - reiniciar backend tras cambios en `.env`.

## 7) Notas operativas

- No probar webhook abriendo URL en navegador.
- Probar desde Stripe Dashboard o Stripe CLI.
- Evitar endpoints duplicados en Stripe para no mezclar secrets.
