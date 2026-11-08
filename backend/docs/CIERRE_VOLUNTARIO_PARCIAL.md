# RF-13/RF-24: cierre voluntario incompleto — 8/11/2026

## Decisión y alcance antes de implementar

Fuente: instrucción funcional del equipo comunicada por el usuario el 8/11:
si la edición publicada acredita la misma cantidad de preguntas en todas sus rutas
completas, el intento cerrado antes de FIN puede evaluarse con ese denominador.
Es **propuesta técnica del equipo**, no aprobación institucional ni una respuesta
atribuida a la profesora. No cambia la igualdad de peso ni los puntajes docentes.

Criterios: FINALIZADO permanece cerrado, PARCIAL es la clasificación del resultado;
puntajes reales preservados, pendientes por cantidad a cero, ramas inaccesibles
excluidas, Decimal y ROUND_HALF_UP solo al final. Sin dato indispensable o con
longitudes/perfiles ambiguos, error explícito y ninguna persistencia. No crear
selecciones, preguntas o rutas futuras. Cierre, cálculo técnico y publicación son
operaciones independientes. Reproducir historia v1 sin cambiar sus huellas.

## Implementación

`preparar_calculo_historico` reutiliza ConfiguracionPreguntas.seleccionar/validar,
EvaluacionParcialStrategy, CalculadorRubrica y detalle_exacto. El perfil y la longitud
común de rutas completas ya se verificaban al publicar y al calcular. La ruta recorrida
sigue siendo únicamente el prefijo real. Cero respuestas en un intento existente y
cerrado produce PARCIAL 0.00, nunca una AUSENCIA inferida.

- FINALIZADO + FIN: COMPLETA, política 1 como antes.
- VENCIDO: PARCIAL, política 1 como antes.
- FINALIZADO sin FIN: PARCIAL, **politica_version=2**, mismo motor PREGUNTAS_100_V1.
- EN_CURSO: se rechaza; no se cierra ni evalúa implícitamente.

La versión 2 identifica CIERRE_VOLUNTARIO_PARCIAL_V1 con origen
PROPUESTA_TECNICA_EQUIPO, regla de denominador, pendientes, ramas y fuente del
clasificador. La configuración y parámetros efectivos siguen en la procedencia
inmutable; su huella se conserva con el resultado. No se altera la huella de la
política 1: calculador, Strategies, validador, contabilidad y documentos v1 no cambian.
El repositorio guarda y valida la versión real del documento, no inventa niveles.

## PostgreSQL y migración mínima

Cabeza anterior: 20261108_academic_publication.
Nueva revisión: **20261108_voluntary_partial**, dependencia de esa cabeza.
Sin tablas, columnas, PK, identificadores, ORM ni actualizaciones de datos.

Era indispensable: fp8_cabecera equiparaba FINALIZADO con COMPLETA y fijaba la
política 1. Además, la definición de una misma política/versión no admite otra huella.
La nueva revisión sustituye únicamente fp8_cabecera y fp8_completo, manteniendo
triggers, locks, search_path, SECURITY INVOKER y validaciones aritméticas/históricas.
Exige versión 2 + FINALIZADO + PARCIAL + descriptor técnico congelado; la validación
diferida exige prefijo realmente incompleto y el denominador uniforme validado en
SQL. La versión 1 no admite FINALIZADO/PARCIAL. No basta falsear la cabecera.

Instalación transaccional con ACCESS EXCLUSIVE sobre las cuatro tablas de resultados
implicadas; debe coordinarse su ejecución futura por bloqueo temporal de lectores y
escritores. No se aplicó a bases permanentes. Downgrade restaura exactamente ambas
funciones anteriores si no hay resultados v2. Si existen, se rechaza y revierte la
migración, sin borrar ni convertir resultados históricos.

El comando docente existente serializa P/I y revalida cuenta/rol/ámbito bajo locks;
resultado único e idempotente, con rollback de todas sus tablas si falla SQL.
No se modifica finish. El cierre confirmado sobrevive a cualquier fallo posterior
del cálculo. Progreso/escenario/decisiones mantienen sus protecciones.

## Contrato HTTP e integración

Mismas rutas, cuerpo y esquema: POST/GET
`/scheduling/sesiones/{sesion_id}/evaluacion/intentos/{id_intento}/resultado-tecnico`.
El caso FINALIZADO sin FIN con configuración inequívoca pasa de 503 a 200 con
modalidad=PARCIAL, oficial=false y pendientes_con_cero. Activo 409; autorización
401/403; configuración incompatible/ambigua o fallo SQL 503. El GET no calcula.

Consolidación reutiliza ese resultado; no publica ni notifica automáticamente.
La vista provisional requiere su habilitación docente explícita y sigue sin
respuestas correctas/explicaciones durante la sesión activa. Publicación oficial
sigue exigiendo cohorte resuelta y otro POST autorizado por hash. El equipo debe
validar institucionalmente la nueva propuesta antes de usarla para notas reales.
No se atribuye esa validación a un test ni al funcionamiento del endpoint.

Postman conserva requests, rutas y esquemas; se aclara en el catálogo la nueva
respuesta parcial admitida. No se añade un endpoint ni se declara Runner ejecutado.
No se altera el recorrido de entrega ni sus aserciones de 100 para rutas completas.

## Evidencias

`evidencias/cierre_voluntario_20261108/` queda local. Focalizada final inicial:
18 aprobadas, ninguna omitida/fallida, una advertencia conocida. Incluye cinco prefijos
reales (0/1/2 respuestas y dos ramas), idempotencia, SQL falseado, concurrencia,
rollback, consulta privada, autorización y ciclo de publicación explícito.
Los dos contratos negativos anteriores sustituidos se conservan como pruebas:
`test_cierre_temprano_sin_fin_evalua_parcial_sin_selecciones_ficticias` y la rama
FINALIZADO_INCOMPLETO de `test_no_inventa_cierre_ni_completitud`. EN_CURSO sigue
rechazado. Cinco aserciones de cabeza Alembic se actualizan; no se omiten pruebas.

La primera focalizada tuvo un fallo de preparación: el laboratorio independiente de
migraciones no había sembrado los roles existentes. Se corrigió la fixture, conservando
el log. No se cambió backend para ocultarlo.

Antes de modificar el motor se creó un resultado v1 y una publicación mediante el
código de c1ef7e3 en PG17 nuevo. Tras upgrade, otro proceso con el código nuevo leyó
el resultado 33.33 y la misma publicación con sus huellas idénticas. Los JSON antes/
después lo acreditan. La captura auxiliar de stdout tuvo un error de decodificación;
el hijo terminó con código 0 y guardó la evidencia verificada, sin exponer credenciales.
El contenedor propio se eliminó al cerrar. No se ejecutó código procedente de la BD.

Resultados definitivos sobre c1ef7e3 + incremento local (no atribuirlos a un commit
creado después):

| Ejecución | Aprobadas | Omitidas | Fallos / errores |
|---|---:|---:|---:|
| Focalizada final | 18 | 0 | 0 / 0 |
| Relacionada | 505 | 0 | 0 / 0 |
| General, 116 módulos y cuatro particiones disjuntas | 2472 | 38 | 0 / 0 |

No sumar las filas: se solapan. La general contiene 2510 casos nominales sin
repeticiones, 15 aceptaciones adicionales y dos contratos anteriores actualizados.
Particiones: 654/0, 567/3, 736/29 y 515/6 (aprobadas/omitidas). Las omisiones
opcionales corresponden a URLs/activación PostgreSQL externas deshabilitadas;
no son aprobaciones. Todas las nuevas pruebas obligatorias PG17 se ejecutaron.
Un tipo conocido de advertencia de Starlette/httpx se repite en cada proceso.

JUnit consolidado, omisiones, consola, SHA de fuentes antes/después y plan disjunto
quedan en la carpeta local de evidencia. Fuentes invariables durante pytest; se
conserva un JSON UUID generado por el laboratorio histórico BD2, sin versionarlo.
Node compiló 241 scripts de las colecciones afectadas, sin errores. No se ejecutó
Postman Runner ni se atribuyeron ejecuciones de pm.test a Python.

Solo los laboratorios propios se limpiaron. Se detectó un laboratorio de entrega
iniciado por otro proceso de `entrega_20261109/laboratorio.py`; se conservó intacto,
sin conectarse ni detenerlo. Tampoco se usaron bases permanentes ni se modificó .env.

## Riesgos operativos y académicos para la entrega

- Validar institucionalmente la propuesta antes de usarla como regla académica definitiva.
- La migración sigue pendiente de despliegue coordinado. Sustituye funciones y bloquea
  temporalmente las tablas de resultados; no debe aplicarse improvisadamente a datos reales.
- Si existen resultados v2, no se puede volver a la revisión anterior sin un plan que
  mantenga su lectura. El downgrade protege los datos y no los transforma silenciosamente.
- Inicio/consentimiento productivos y recorridos no soportados siguen fuera de este
  incremento. No se publican notas automáticamente por finish o por el cálculo.

## Archivos y métodos

| Archivo | Cambio |
|---|---|
| participation/infrastructure/question_evaluation.py | preparar_calculo_historico y _clasificar_cierre_preguntas: selección de modalidad, política v2 solo para el nuevo caso |
| participation/infrastructure/question_result_repository.py | guardar y leer conservan la versión efectiva de la definición |
| alembic/versions/20261108_voluntary_partial.py | upgrade/downgrade y sustitución mínima de fp8_cabecera/fp8_completo |
| tests/integration/test_voluntary_partial_http.py | 15 aceptaciones nuevas, incluyendo migración, SQL, HTTP, privacidad y publicación explícita |
| test_question_scoring.py / test_teacher_technical_evaluation.py | Dos contratos anteriores sustituidos; permanecen las negativas para intento activo |
| Cinco pruebas de cabeza Alembic | Exigen la nueva cabeza única; no se cambian los historiales que prueban revisiones concretas |
| Documentación, matriz y metadatos Postman | Procedencia de la decisión, alcance real y nuevo 200 PARCIAL, sin nuevas rutas/esquemas |

El checkpoint es local; requiere revisión antes de cualquier publicación posterior.

## Estado funcional

RF-13 y RF-24 cierran esta brecha técnica y conservan clasificación PARCIAL en la
matriz por la validación institucional pendiente de esta propuesta. RF-14 incorpora
consulta provisional/oficial de este nuevo caso conservando autorización y privacidad,
pero sigue PARCIAL por el inicio productivo pendiente y el alcance de recorridos.
Los otros 24 requisitos no se reclasifican. No se implementa otro incremento.
