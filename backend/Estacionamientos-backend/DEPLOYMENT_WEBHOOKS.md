# Despliegue: Webhooks de Pago (Stripe y Cloudflare)

> Nota: Esta guia tambien fue integrada en `docs/deployment-webhooks.md` para centralizar la documentacion del proyecto.

Este documento evita un problema comun en produccion: Stripe envia eventos, pero Cloudflare bloquea la peticion antes de llegar al backend.

## Contexto

Si Stripe muestra error de entrega con HTTP 403 y la respuesta contiene HTML de Cloudflare ("Sorry, you have been blocked"), el bloqueo no es de llaves ni firma: la peticion no llega al backend.

## Endpoint recomendado

Para Stripe usar endpoint especifico:

- `POST /pagos/webhook/stripe`

URL de ejemplo en produccion:

- `https://api-estacionamiento.server-ofic.online/pagos/webhook/stripe`

Tambien existe endpoint generico:

- `POST /pagos/webhook`

## Configuracion en Stripe

1. Ir a **Developers > Webhooks > Add endpoint**.
2. Registrar URL exacta del webhook.
3. Seleccionar eventos:
   - `checkout.session.completed`
   - `checkout.session.expired`
   - `checkout.session.async_payment_failed`
4. Copiar el **Signing secret** (`whsec_...`) de ese endpoint exacto.
5. Guardarlo en `.env` como `STRIPE_WEBHOOK_SECRET`.
6. Reiniciar backend despues de actualizar variables.

## Configuracion obligatoria en Cloudflare

Crear una regla WAF con accion **Skip** para el endpoint webhook.

### Regla sugerida (estricta)

- Condicion:
  - `http.request.method eq "POST" and http.request.uri.path eq "/pagos/webhook/stripe"`
- Accion:
  - `Skip`
- Componentes a omitir:
  - All managed rules
  - All Super Bot Fight Mode Rules
  - All rate limiting rules
  - All remaining custom rules (si hay bloqueos de otras reglas)

### Prioridad de regla

- Colocar esta regla al inicio (First / Top / prioridad mas alta).

## Variables de entorno minimas

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

## Checklist post-deploy

1. Reenviar evento desde Stripe Dashboard (Resend).
2. Confirmar HTTP 200 en delivery de Stripe.
3. Verificar BD:
   - `payment_transactions.estado` cambia a `completado` cuando corresponda.
   - `payment_transactions.webhook_timestamp` deja de ser `NULL`.
   - `history_estacionamiento.pagado` se actualiza.
4. Confirmar que el vehiculo sale de `current_estacionamiento` tras pago aprobado.

## Diagnostico rapido

### Caso A: 403 con HTML de Cloudflare

- Causa: Cloudflare bloquea antes de backend.
- Solucion: ajustar regla WAF Skip para la ruta webhook.

### Caso B: 403 JSON {"detail":"Firma de webhook invalida"}

- Causa: el request llego al backend pero el secret no coincide.
- Revisar:
  - secret del endpoint exacto en Stripe
  - modo test/live correcto
  - backend reiniciado

## Notas operativas

- No probar webhook abriendo la URL en navegador: sin `Stripe-Signature` siempre fallara.
- Usar siempre Stripe Dashboard (Send test event / Resend) o Stripe CLI.
- Si hay mas de un endpoint en Stripe, evitar duplicados para no confundir signing secrets.
