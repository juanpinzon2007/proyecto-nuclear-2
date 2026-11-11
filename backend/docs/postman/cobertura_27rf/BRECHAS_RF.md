# Brechas RF-01 a RF-27

Las capacidades parciales se ejecutaron, pero no se aprueba íntegramente su RF. Ningún 503 fue aceptado como cumplimiento.

- **RF-10 — Responder y modificar respuestas:** El PDF RF-10/RN-10/11 permite modificar; la profesora aclaró después respuestas inmutables. Se prueba la inmutabilidad vigente ya confirmada; faltan conciliar el documento y definir recorridos con varias preguntas/ciclos/revisitas, no reabrir PUT.
- **RF-12 — Registrar inicio y fin de participación:** Composición main condicionada presente; faltan documento institucional aprobado y políticas productivas definitivas de provisión/inicio. El recorrido positivo con puertos LAB no acredita disponibilidad productiva ni feedback por pregunta completo.
- **RF-13 — Calcular nota con rúbrica:** Motor y persistencia técnicos acreditables; no se atribuye aprobación institucional a política del equipo ni se declara cobertura de todo grafo no soportado.
- **RF-23 — Controlar tiempo máximo:** Contador y vencimiento de intentos existentes tienen pruebas; el inicio productivo que lo activa permanece cerrado. Se acredita recorrido LAB, no requisito integral productivo.
- **RF-24 — Evaluar incompletos y ausencias:** Ausencia explícita y parcial técnicos demostrables; políticas propuestas no se presentan como aprobación institucional ni ausencia inferida.
- **RF-25 — Autorizar repetición excepcional:** Permiso individual de un uso disponible; consumo por inicio productivo y vinculación de caso distinto siguen pendientes.

## Decisiones y límites que no se corrigen con pruebas verdes

- RF-10: el PDF y RN-10/11 describen modificación; la aclaración posterior de la profesora exige inmutabilidad. Se conserva el comportamiento vigente y se solicita conciliación documental, no reabrir PUT. Fuente: FASE_8B_RESPUESTAS_INMUTABLES.md.
- RF-22: se conserva sala de espera/concesión de admisión aprobada por el equipo; no se inventa un umbral tardío ni se recupera la anticipación descartada. Fuente: DECISIONES_FUNCIONALES_RF22.md y SALA_ESPERA_ADMISION_DISENO.md.
- RF-13/RF-24: fórmula técnica, ausencia y cierre parcial se prueban como reglas del equipo; no se atribuyen aprobaciones institucionales ausentes. Fuente: CONTRATO_FUNCIONAL_EVALUATION_PROPUESTO_20261107.md y matriz vigente.
- RF-20/RF-21: despacho cifrado durable y aceptación SMTP local acreditados. El proveedor externo, remitente, URL y recepción institucional requieren validación de despliegue.
- Consentimiento: se necesita la fuente institucional publicada y su composición productiva. Un documento sintético y una clase InicioLaboratorio no satisfacen esa aprobación.

## Fallos reales conservados y corrección

Los dos primeros ciclos RF-07 rechazaron correctamente una opción de orden 3 duplicada por el generador. Se corrigió la copia de la fixture; no se cambió el esperado 200 de una edición válida. El primer ciclo integral falló al convocar sobre EN_CURSO (RF-04/18/20/21) y preparar una ausencia después del cierre (RF-24). Se corrigieron exclusivamente precondiciones/orden de laboratorio. Los JSON, JUnit y logs diagnósticos se conservan. Ningún archivo productivo se modificó para evitar esos rechazos.

Las pruebas complementarias de permisos, concurrencia, rollback y guards PostgreSQL se conservan en los JUnit de pytest; no se presentan como capturas de Postman ni se suman sus conteos con pm.test.
