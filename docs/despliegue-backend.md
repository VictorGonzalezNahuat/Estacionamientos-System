# Despliegue backend (FastAPI)

Ruta del backend:
- `backend/Estacionamientos-backend`

## 1) Clonar repositorio

```bash
git clone <URL_DEL_REPO>
cd Estacionamientos
```

## 2) Crear entorno virtual e instalar dependencias

```bash
cd backend/Estacionamientos-backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 3) Configurar variables de entorno (`.env`)

Crear archivo `.env` en `backend/Estacionamientos-backend/.env`.

Ejemplo minimo (ajusta valores reales):

```dotenv
DATABASE_URL=mysql+pymysql://usuario:password@host:3306/estacionamiento
APP_TIMEZONE=America/Mexico_City
PAYMENT_PROVIDER=stripe

# Stripe (si aplica)
STRIPE_SECRET_KEY=sk_test_xxx
STRIPE_PUBLISHABLE_KEY=pk_test_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
WEBHOOK_URL=https://api.tudominio.com
STRIPE_SUCCESS_URL=https://app.tudominio.com/pago-exitoso?session_id={CHECKOUT_SESSION_ID}
STRIPE_CANCEL_URL=https://app.tudominio.com/pago-cancelado
STRIPE_CURRENCY=mxn

# Mercado Pago (si aplica)
MERCADO_PAGO_ACCESS_TOKEN=APP_USR_xxx
MERCADO_PAGO_PUBLIC_KEY=APP_USR_xxx
MERCADO_PAGO_WEBHOOK_SECRET=xxx
MERCADO_PAGO_CURRENCY=MXN

# Impresora de red (opcional)
PRINTER_HOST=192.168.1.130
PRINTER_PORT=9100
PRINTER_TIMEOUT=10
```

Notas:
- `DATABASE_URL` es obligatoria.
- Algunas opciones de sincronizacion se guardan en `config.json` (no en `.env`).

## 4) Configurar `config.json`

Archivo: `backend/Estacionamientos-backend/config.json`

Campos relevantes:
- `DATABASE_CLOUD_URL` (obligatoria para sync).
- `SYNC_AUTO_ENABLED`.
- `SYNC_INTERVAL_MINUTES`.
- `MOBILE_PRINT`.
- `ENTRY_TICKET_CODE_TYPE` (`BARCODE` o `QR`).
- `PUBLIC_STATUS_BASE_URL`.

## 5) Ejecutar en modo prueba

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Validar:
- `GET /` responde estado OK.
- `GET /db-test` confirma conexion a base de datos.

## 6) Ejecutar como servicio (base inicial)

Ejemplo de unidad systemd (referencia inicial):

```ini
[Unit]
Description=API Estacionamientos FastAPI
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/estacionamientos/backend/Estacionamientos-backend
Environment="PATH=/opt/estacionamientos/backend/Estacionamientos-backend/.venv/bin"
ExecStart=/opt/estacionamientos/backend/Estacionamientos-backend/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Comandos utiles:

```bash
sudo systemctl daemon-reload
sudo systemctl enable estacionamientos-backend
sudo systemctl start estacionamientos-backend
sudo systemctl status estacionamientos-backend
```

## 7) Siguientes mejoras recomendadas

- Limitar CORS en produccion (actualmente `allow_origins=["*"]`).
- Ejecutar detras de Nginx/Apache reverse proxy con HTTPS.
- Implementar rotacion de logs y monitoreo de procesos.
