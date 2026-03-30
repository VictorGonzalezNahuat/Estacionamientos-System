# Base de datos (MariaDB / MySQL)

## 1) Crear base de datos

Conectate al servidor MariaDB/MySQL y ejecuta:

```sql
CREATE DATABASE estacionamiento;
```

## 2) Seleccionar script SQL inicial

En la carpeta `bd/` existen varios dumps/scripts.

Criterio actual de despliegue:
- usar el archivo mas reciente con formato `ddmmaa.sql`.
- validar que corresponda al ultimo corte liberado por el equipo.

Ejemplos de nombres observados:
- `14MBD.sql`
- `170326.sql`
- `280326.sql`
- `290326.sql`

## 3) Importar script

Ejemplo con usuario root:

```bash
mysql -u root -p estacionamiento < bd/290326.sql
```

Ajusta el nombre del archivo segun la version actual.

## 4) Validacion minima

Despues de importar:
- verificar que existan tablas clave (`usuarios`, `tarifa`, `current_estacionamiento`, `history_estacionamiento`).
- validar acceso desde backend con endpoint de prueba `/db-test`.

## 5) Buenas practicas

- Respaldar antes de aplicar cambios:

```bash
mysqldump -u root -p estacionamiento > backup_pre_update.sql
```

- Aplicar scripts primero en ambiente de pruebas.
- Registrar fecha, autor y archivo SQL aplicado en bitacora interna.
