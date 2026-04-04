# Configuracion local del backend

Para que el backend funcione, debes crear una carpeta local llamada `config` en la raiz del proyecto con estos archivos:

- `config/config.json`
- `config/config_cortes.json`

Esta carpeta esta excluida en Git (`.gitignore`) para evitar subir configuraciones sensibles al repositorio.

## Estructura esperada

```text
Estacionamientos-backend/
  config/
    config.json
    config_cortes.json
```

## Notas

- Si no existe `config/config.json`, se tomaran valores por defecto donde aplique, pero varias rutas del backend dependen de ese archivo.
- Si no existe `config/config_cortes.json`, se usara la configuracion por defecto definida en codigo para el modulo de cortes.
- No subas credenciales reales al repositorio.
