> Actualización vigente: sala de espera y admisión aprobadas por el equipo.
> Se registran solicitudes propias antes de habilitar y se congela el conjunto
> elegible en la transacción docente SIN_INICIAR → EN_CURSO. EN_CURSO sin concesión
> individual rechaza con 403. No hay tolerancia anticipada ni tardía ni presencia
> online inferida. Las afirmaciones anteriores sobre falta de señal de admisión
> quedan como historia; se conserva el cierre del inicio por consentimiento oficial.
> Contrato, migración y evidencia: `SALA_ESPERA_ADMISION_DISENO.md` (backend/docs).

---

# Registro de decisiones funcionales RF-22

5 de noviembre de 2026, America/Bogota. Fuentes: instrucciones explícitas del
usuario como comunicación del responsable funcional del equipo; no se atribuye
aprobación institucional de políticas adicionales.

| Decisión | Estado | Consecuencia |
|---|---|---|
| Validación desde diez minutos antes de inicio | DESCARTADA por corrección posterior | Retirar fuente/constante/rama anticipada. Conservar evidencias anteriores como antecedentes, no contratos vigentes |
| Solo puede ingresar cuando la sesión haya sido habilitada | VIGENTE | EN_CURSO persistido es condición indispensable. SIN_INICIAR rechaza sin importar fecha programada |
| Habilitación docente | MECANISMO EXISTENTE COMPROBADO | POST `/scheduling/sesiones/{sesion_id}/estado`, acción iniciar; State, commit y auditoría reales. No equivale a alcanzar fecha_inicio |
| Ventana de ingreso completa después de habilitar | PENDIENTE | PoliticaIngresoNoConfigurada mantiene 503. No introducir minutos, usar retraso del worker ni asumir ventana completa desde la habilitación |
| Consentimiento previo a P y no revocable durante ejecución | CONSERVADA, fuera del cambio | No modificar código ni abrir provisión/inicio. Fuente/version del documento y controles siguen según informe de consentimiento |

La corrección de anticipación es un cambio de requisito, no un fallo de
programación respecto a la instrucción anterior. No se habilita RF-22 completo,
inicio productivo, notas ni otro módulo.

Se mantienen sin cambios los 34 archivos del manifiesto como respaldo histórico
verificado antes de corregir; las modificaciones RF-22 autorizadas se distinguen
por SHA-256 en `evidencias/rf22_habilitacion_20261106T002442Z/delta_autorizado.json`.
El manifiesto y la conciliación de consentimiento permanecen intactos. Antes de
un futuro commit autorizado hay que revisar las huellas actuales; no usar las
antiguas como si todavía describieran el árbol corregido.

Validación actual: 30 aceptaciones HTTP, 558 relacionadas y general 2102 aprobadas,
38 omitidas, 0 fallos/errores, una advertencia conocida. Son ejecuciones solapadas.
Los 200 adicionales usan política explícita LAB; la composición productiva se
acredita cerrada ante política faltante. Informe y comandos en
[RF22_INGRESO_ANTICIPADO.md](RF22_INGRESO_ANTICIPADO.md), nombre conservado por trazabilidad.

## Precisión definitiva posterior: oportunidad del ingreso

El responsable funcional confirmó que no hay tolerancia anticipada NI tardía.
La habilitación es transición docente persistida EN_CURSO; no se deduce del horario.
Pero ese estado no demuestra cuándo una solicitud fue recibida oportunamente.
Sin una señal objetiva adicional el proveedor sigue cerrado (503). Se descartan
como sustitutos una igualdad exacta entre timestamps, minutos implícitos o permitir
todo EN_CURSO. Se propone definir una etapa de admisión con apertura/cierre
explícitos del servidor, sin duración por defecto; todavía NO se implementa.

Se confirman además: aceptación previa a P, reutilizable mientras su versión siga
vigente; nueva aceptación para P nueva tras cambio de versión; no revocación durante
ejecución; aún no existe documento oficial. Los componentes internos y sus límites,
borrador no aprobado y evidencia actual 2126/38 están en
`CONSENTIMIENTO_E_INICIO_INTERNO.md`. No son autorización de inicio productivo.
