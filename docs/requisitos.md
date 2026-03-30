# Requisitos del sistema

## Software base

- Sistema operativo Linux para despliegue actual de referencia.
- Git (clonado y actualizacion del repositorio).
- Python 3.11+ recomendado.
- pip (instalador de paquetes Python).
- Entorno virtual Python (`venv`).
- Node.js 20+ recomendado.
- npm 10+ (en este proyecto se usa npm 11).
- Angular CLI 21 (via `npx ng` o instalacion global opcional).
- MariaDB 10.6+ o MySQL 8+.
- Apache 2.4+ para servir frontend compilado.

## Servicios externos opcionales

- Stripe (si se habilita pago con tarjeta via Stripe).
- Mercado Pago (si se habilita ese proveedor).
- Cloudflare (si el dominio de API esta detras de WAF/proxy).

## Puertos de referencia

- Backend FastAPI: `8000`.
- Frontend en desarrollo Angular: `4200`.
- HTTP Apache: `80`.
- HTTPS Apache: `443`.
- MariaDB/MySQL: `3306` (o el definido por tu servidor).

## Recomendaciones operativas

- Separar credenciales por entorno (dev/staging/prod).
- Nunca subir `.env` con secretos al repositorio.
- Respaldar la base de datos antes de importar nuevos scripts SQL.
- Versionar la configuracion de infraestructura fuera del codigo de negocio.
