# Idea 001 - Onboarding inicial del sistema

Fecha: 2026-04-06
Estado: Idea
Origen: Solicitud del dueño del proyecto

## Problema
Actualmente el sistema lleva al usuario directo al flujo normal de uso. Falta una experiencia de primera configuracion guiada para que el dueno del estacionamiento:
- entienda como se esta configurando el sistema,
- confirme que los datos iniciales son correctos,
- y no omita parametros criticos.

## Propuesta
Crear un modulo de onboarding que se ejecute solo en el primer uso del sistema (controlado por una bandera de primera ejecucion).

Si la bandera indica primer uso:
- redirigir automaticamente al modulo de onboarding,
- bloquear temporalmente el acceso al resto del dashboard hasta completar configuracion minima,
- mostrar una experiencia tipo asistente por pasos (similar a configuracion inicial de Windows).

## Flujo sugerido (wizard)
1. Bienvenida
- Mensaje de introduccion al sistema.
- Explicar que se configuraran parametros base antes de operar.

2. Identidad del estacionamiento
- Nombre del estacionamiento (nuevo dato de negocio a definir en backend/config).
- Datos de contacto opcionales (si aplica en siguientes iteraciones).

3. Configuracion general del sistema
- Reusar campos existentes de configuracion general:
- SYNC_AUTO_ENABLED
- MOBILE_PRINT
- SYNC_INTERVAL_MINUTES
- ENTRY_TICKET_CODE_TYPE
- PUBLIC_STATUS_BASE_URL
- AVISO_ENTRADA
- AVISO_SALIDA

4. Configuracion de conexion a base de datos
- Reusar campos actuales:
- DATABASE_CLOUD_USER
- DATABASE_CLOUD_PASSWORD
- DATABASE_CLOUD_HOST
- DATABASE_CLOUD_PORT
- DATABASE_CLOUD_NAME

5. Configuracion de cortes y correo
- Reusar campos actuales:
- AUTOSEND_REPORT
- SMTP_HOST
- SMTP_PORT
- SMTP_USERNAME
- SMTP_PASSWORD
- SMTP_USE_TLS
- SMTP_TIMEOUT_SECONDS
- REPORT_FROM_NAME
- REPORT_SUBJECT_TEMPLATE

6. Resumen y confirmacion final
- Mostrar todos los datos capturados.
- Pedir confirmacion explicita del dueno antes de guardar.
- Guardar configuracion y marcar bandera de onboarding completado.

## Comportamiento tecnico esperado
- Nueva bandera de estado: onboardingCompleted (o firstRun = false al finalizar).
- Validar bandera al iniciar sesion/cargar dashboard.
- Si no esta completado, redirigir a onboarding.
- Al completar, permitir flujo normal y no volver a mostrar onboarding.
- Permitir reabrir onboarding desde configuracion en modo "editar" (opcional).

## Requisitos de UX
- Progreso visible por pasos (ej. Paso 2 de 6).
- Botones Anterior/Siguiente/Finalizar.
- Validaciones por paso con mensajes claros.
- Guardado con retroalimentacion visual (cargando, exito, error).

## Criterios de aceptacion iniciales
- En primer uso, el usuario siempre cae al onboarding.
- No se puede llegar al dashboard principal sin completar datos minimos.
- Se persiste la configuracion y la bandera de onboarding completado.
- En usos posteriores ya no se muestra onboarding automaticamente.

## Referencias tecnicas revisadas
- src/app/pages/dashboard/configuracion/configuracion.ts
- src/app/pages/dashboard/configuracion/configuracion.html
- src/app/pages/dashboard/configuracion-cortes/configuracion-cortes.ts
- src/app/pages/dashboard/configuracion-cortes/configuracion-cortes.html
- src/app/services/config.service.ts

## Notas
- El campo Nombre del estacionamiento no aparece en los contratos actuales de ConfigService, por lo que requeriria extension de modelo y endpoint.
- Esta idea queda en ideas hasta priorizacion y aprobacion para moverla a pending.
