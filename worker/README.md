# Worker SPS

Aquí se ubicará el proceso independiente de tareas programadas.
Todavía no hay tareas periódicas, cierre automático de sesiones ni servicios de correo.

Scheduling coordinará los futuros contratos con este proceso. El equipo debe acordar
su mecanismo de ejecución, dependencias y comunicación antes de implementarlo.
Entonces se añadirá un Dockerfile y el servicio worker a Docker Compose.
Si requiere acceso a datos, deberá reutilizar el paquete backend y su configuración,
sin duplicar reglas del dominio ni la configuración de persistencia.
