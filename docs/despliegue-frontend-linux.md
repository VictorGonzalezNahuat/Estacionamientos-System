# Despliegue frontend en Linux (Angular + Apache)

Ruta del frontend:
- `frontend/estacionamiento-frontend`

## 1) Instalar dependencias

```bash
cd frontend/estacionamiento-frontend
npm install
npm audit fix
```

`npm audit fix` es opcional, segun resultados y politica de versiones del proyecto.

## 2) Compilar proyecto

```bash
npm run build
```

Salida esperada en:
- `dist/estacionamiento-frontend/browser/`

## 3) Configurar URL de API

Ajustar `public/config.json` y/o `src/assets/config.json` segun el flujo de build usado.

Clave principal:
- `apiUrl`: URL base del backend, ejemplo `http://IP_SERVIDOR:8000` o dominio HTTPS.

## 4) Publicar en Apache

Ejemplo de despliegue del build a Apache:

```bash
sudo mkdir -p /var/www/angular
sudo cp -r dist/estacionamiento-frontend/browser/* /var/www/angular/
```

## 5) Configuracion minima de VirtualHost

Ejemplo basico:

```apache
<VirtualHost *:80>
    ServerName estacionamiento.local
    DocumentRoot /var/www/angular

    <Directory /var/www/angular>
        Options Indexes FollowSymLinks
        AllowOverride All
        Require all granted
    </Directory>

    ErrorLog ${APACHE_LOG_DIR}/estacionamiento-error.log
    CustomLog ${APACHE_LOG_DIR}/estacionamiento-access.log combined
</VirtualHost>
```

Si usas rutas Angular, agrega fallback a `index.html` via `mod_rewrite` o configuracion equivalente.

## 6) Reiniciar Apache

```bash
sudo systemctl restart apache2
sudo systemctl status apache2
```

## 7) Nota de alcance

Este documento cubre Linux como base actual.

Pendiente por documentar en otra iteracion:
- flujo completo de despliegue en Windows.
