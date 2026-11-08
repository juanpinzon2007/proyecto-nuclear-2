# RF-13 / RF-24 — cálculo técnico por preguntas

7 de noviembre de 2026. Rama feature/backend-continuidad, base
9a1d1333e74289661aba4e911f3edb3e0fabcc9c más cambios locales sin commit.
Fuente funcional: instrucciones expresas del usuario de este incremento.
No se presenta como un acta institucional ni se modifica el contrato propuesto
anterior, que permanece como antecedente.

## Resultado y límites

Implementados: validación de nuevas versiones evaluables, cálculo técnico interno
de un intento histórico completo o vencido y trazabilidad reproducible de su
configuración. No hay persistencia del NUEVO resultado, nota oficial, endpoint de
calificación, consolidación, ausencia automática ni publicación. RF-13 y RF-24
avanzan a PARCIAL, no a IMPLEMENTADO. Sus tramos oficiales siguen cerrados.

El motor anterior exigía niveles discretos y una fórmula por criterio. La política
igualitaria anterior rechazaba aportes como 100/3 por falta de redondeo aprobado.
Esos contratos históricos no se sustituyen. La operación nueva se añade al mismo
CalculadorRubrica, reutiliza las estrategias COMPLETA/PARCIAL y lee las mismas
respuestas inmutables; no hay otro repositorio de grafo ni de resultados.

## Configuración docente y validación de publicación

Opt-in técnico en el atributo existente rubric.versionRegla: PREGUNTAS_100_V1.
No se crea columna ni se infiere esta regla por fecha, puntaje o última edición.
El docente configura valoraciones de alternativas mediante el DSL existente.
Cada valoración es un puntaje explícito Decimal 0–100. No se multiplican los
valores históricos 0–5 por 20 ni se interpreta un nivel como porcentaje.

Si una alternativa tiene varias valoraciones por criterio, deben representar el
mismo puntaje explícito; si difieren, falta un puntaje único y la versión se
rechaza como evaluable. No se suman/promedian criterios para inventarlo. Todas
las opciones de una pregunta deben tener las mismas correspondencias de criterio.
La cadena existente sigue exigiendo valoraciones para todos los criterios.

La columna actual valoracion_opcion.puntaje es NUMERIC(5,2). La autoría de la
nueva regla rechaza valores fuera de 0–100 o que no quepan exactamente a dos
decimales ANTES del INSERT/reemplazo. La comprobación no modifica el valor.
No se permite que la coerción SQL redondee 1.005 a 1.01 silenciosamente.
Para puntajes docentes con más precisión hará falta adaptar esa columna primero;
no se inventa una restricción académica de precisión.

Antes de publicar se comprueba, bajo el mismo lock de version_caso:

- Grafo real, una inicial, una pregunta por escena y sin ciclos alcanzables,
  conforme al recorrido actualmente soportado. No se definen ciclos/revisitas.
- Identificadores únicos; ninguna opción/pregunta ajena ni doble conteo.
- Puntajes completos y correspondencia inequívoca con la rúbrica.
- Igual número de preguntas en TODAS las rutas completas alcanzables.
- Igual cantidad de preguntas por criterio en cada ruta; igualdad de los perfiles
  entre ramas. Los pesos históricos de criterios no multiplican la nota nueva.

Se usan perfiles y longitudes memoizados, no enumeración exponencial de rutas.
Los guards PostgreSQL existentes congelan grafo, rúbrica y valoraciones al
publicar/archivar. No se rellenan ni alteran versiones históricas. Las reglas
anteriores conservan sus requisitos de publicación y cálculo.

## Intentos completos y vencidos

Entrada interna: calcular_intento_por_preguntas(usuario, id_intento, fechas,
crear_sesion). Reutiliza la UoW, autorización Identity persistente, convocatoria,
matrícula y asignación/UUID histórico exacto. No recibe puntajes del cliente.

El prefijo de respuestas debe pertenecer al grafo y respetar el orden real.
FINALIZADO exige llegar a FIN; un cierre voluntario incompleto se rechaza.
VENCIDO conserva PARCIAL y las selecciones reales. EN_CURSO se rechaza; esta
operación no vence ni cierra intentos.

Nota = suma de puntajes seleccionados / preguntas exigidas por ruta completa.
Cada pregunta tiene exactamente un voto. No hay multiplicadores por escena,
criterio o dificultad. Una pregunta omitida aporta cero al numerador.
Las preguntas de una rama inaccesible no se añaden al denominador.

Al vencer antes de elegir una rama, no se inventa una continuación. Todas las
continuaciones ya han probado longitud y perfil iguales, por lo que el denominador
es único aunque las identidades de las preguntas futuras no lo sean. Si no se
puede probar, el cálculo se rechaza. Los pendientes se representan por cantidad,
no por selecciones o IDs ficticios.

Se suman Decimal exactos con contexto local suficiente. Se decide el redondeo
final mediante cociente/resto en centavos, ROUND_HALF_UP a dos decimales. No se
redondea un tercio ni un aporte intermedio. La salida contiene nota_final,
modalidad, cantidades, procedencia canónica con configuración histórica, fuentes
del motor/validador y SHA-256; oficial=false y persistido=false.

La lectura revierte/cierra su UoW sin commit ni DML. Repeticiones y concurrencia
devuelven el mismo documento; no hay resultados persistidos que duplicar.
Esto NO acredita idempotencia de una futura escritura ni entrega exactamente una vez.

## Incompatibilidad concreta de persistencia

No se crea una segunda fuente de resultados. Se conserva resultado_intento /
resultado_criterio y su repositorio técnico existente. Hay tres incompatibilidades:

1. DatosEvaluacion exige resultados de criterio con un id_nivel real. Un promedio
   de preguntas puede no coincidir con ningún nivel. Ejemplo: 100 y 0 dan 50,
   pero el criterio histórico puede tener solo nivel 5. No se crea un nivel 50.
2. resultado_criterio.id_nivel es NOT NULL y su FK compuesta acredita el criterio.
   No puede insertarse un nivel vacío, ajeno o elegido por proximidad.
3. puntaje_obtenido es NUMERIC(5,2), y el verificador exige representación exacta.
   Un aporte 100/3 no cabe sin el redondeo intermedio expresamente prohibido.

Además, el repositorio actual guarda solo ámbito LABORATORIO y conserva sus
restricciones de procedencia. Esta tarea no convierte registros LAB en notas.

Primer cambio de persistencia a revisar: conservar la cabecera única por intento,
discriminar esta fórmula en su procedencia y representar el detalle sin asignar
niveles ficticios, con aportes exactos (numerador/denominador) si se conservan
contribuciones por criterio. Requiere acordar la semántica de ese detalle y revisar
NOT NULL, FK, precisión, triggers y verificador de procedencia conjuntamente.
No basta permitir NULL en id_nivel ni redondear NUMERIC para que el INSERT pase.
No se preparó/aplicó migración ni se alteró el ER aprobado.

## Evidencia actual y conservación histórica

Aceptación y regresión relacionada: 212 aprobadas, 0 omitidas/fallidas/errores,
1 advertencia Starlette conocida, 118.08 s. Incluye 39 casos nuevos (24 sin BD y
15 PostgreSQL, cuatro de ellos HTTP con JWT real en aplicación aislada de Cases).
Se reutilizan fixtures administrativas de laboratorio; no se acreditan nuevas
rutas de notas en app.main. Regresión general nueva: 2323 aprobadas, 38 omitidas, 0 fallidas/errores,
1 advertencia Starlette, 1290.02 s (21 min 30 s), 2361 casos JUnit. Las 38
omisiones son externas/configurables históricas; ninguna de las 39 nuevas se omitió.
Fuentes estables durante cada ejecución. La general solo generó una evidencia
BD2-04 nueva, conservada, sin tocar archivos preexistentes.

Evidencia: evidencias/motor_preguntas_20261107/. Cada ejecución conserva comando,
HEAD, huellas de fuentes, consola y JUnit. No sumar suites solapadas.
Se conservan las primeras ejecuciones fallidas: preparación de tiempos del
fixture, referencia ORM de la nueva edición, expectativas HTTP y clasificación
de error de precisión. Se corrigieron sin desactivar controles ni omitir pruebas.

El fixture evaluation_motor_v2.json conserva el motor de 9a1d133. Su SHA exacto
se admite solo para las dos fórmulas históricas que siguen idénticas. No se ejecuta
código recibido de la base. Una prueba PostgreSQL guarda procedencia del motor
anterior y recupera el resultado desde otra sesión con el código actual.

## HTTP / Postman y continuidad

No hay ruta nueva. La autoría existente /api/v1/cases permite rubric.versionRegla
y valoraciones; publicar una nueva versión evaluable desigual responde 422 con
error preciso. Puntaje fuera de escala o precisión no representable: 400 al guardar.
No se modifican colecciones, entorno, recorrido integral ni rutas estudiantiles.

Capturas futuras: POST de borrador con regla explícita y puntajes sintéticos;
PUT de grafo; POST publish válido; publicación de otra versión desigual con 422;
rechazo 400 de puntaje 1.005. Usar el laboratorio Postman existente. No se afirma
haber ejecutado pm.test ni se ofrece una URL de calificaciones inexistente.

RF-14 sigue bloqueado por persistencia/visibilidad/autorización; RF-16 por padrón,
ausencias/consolidación y publicación; RF-25 por identidad de evaluación,
comparabilidad y autorización de repeticiones. No se implementan ausencias,
rectificaciones, reportes, avisos ni selección de mejor intento.

## Trazabilidad de los criterios de aceptación

Todos los métodos están en tests/integration/test_question_scoring.py. Las
aserciones numéricas se ejecutaron sobre el motor real, no se inferieron del log.

| Criterio | Evidencia específica | Límite |
|---|---|---|
| 100 y cero | test_postgresql_recorrido_historico_sin_ramas_inaccesibles (ambas rutas); test_postgresql_todas_cero | Puntajes explícitos sintéticos; no notas oficiales |
| Peso uniforme y tercios | test_decimal_peso_unico_sin_redondeo_intermedio; test_correspondencia_multicriterio_no_multiplica_preguntas | Pruebas puras Decimal, no consultas SQL |
| Ramas inaccesibles | test_ramas_excluidas_no_penalizan_y_no_se_eligen_al_vencer; prueba PostgreSQL de ambas rutas | Solo grafo soportado |
| Pendientes y VENCIDO | test_postgresql_vencido_denominador_completo_sin_respuestas_ficticias | Conserva PARCIAL; no confirma ausencia |
| Edición histórica | test_postgresql_puntajes_publicados_inmutables_y_otro_caso_no_recalifica | El método ahora añade una edición número 2 de la MISMA familia |
| Doble conteo/configuración incompleta | test_configuraciones_ambiguas_o_incompletas_se_rechazan | Duplicados se rechazan, no se eliminan silenciosamente |
| Nuevas publicaciones desiguales | test_http_publicar_solo_nuevas_versiones_evaluables_validas; test_postgresql_publicacion_desigual_revierte_y_legado_no_se_reinterpreta | HTTP aislado con JWT real y repositorios SQL |
| Fuente histórica del motor | test_motor_previo_sigue_verificable_sin_ejecutar_fuentes_recibidas; test_resultado_motor_anterior_recuperable_desde_postgresql | Recupera formato anterior, no inventa persistencia del nuevo |
| Concurrencia/autorización/rollback | test_postgresql_concurrencia_no_escribe_y_rollback_error | Rechazo de actor ajeno y lecturas concurrentes; sin escrituras nuevas |
| Sin cierres inventados | test_no_inventa_cierre_ni_completitud | EN_CURSO y cierre voluntario incompleto rechazados |
| Sin publicación ni resultados duplicados | La prueba PostgreSQL de recorridos verifica cero filas de resultado para el intento nuevo | Unicidad de una futura escritura nueva todavía NO acreditada |

Los perfiles de rutas y la precisión se validan en aplicación. No se presentan
como nuevas restricciones SQL: no hay migración. El cálculo revalida la fuente
incluso si alguien hubiera publicado un borrador mediante SQL directo. Los guards
históricos PostgreSQL existentes sí impiden alterar el contenido ya publicado.

Para reproducir de forma aislada desde esta carpeta original:

```powershell
.\.venv\Scripts\python.exe -B evidencias\motor_preguntas_20261107\ejecutar_validacion.py casos
.\.venv\Scripts\python.exe -B evidencias\motor_preguntas_20261107\ejecutar_validacion.py focal
.\.venv\Scripts\python.exe -B evidencias\motor_preguntas_20261107\ejecutar_validacion.py total
```

El ejecutor es evidencia local sin seguimiento: desactiva lectura de .env solo
en el proceso hijo, elimina conexiones heredadas y usa el fixture Docker dueño
de su PostgreSQL 17 nuevo. No usar una URL de una base permanente para repetirlo.
No se suman ejecuciones solapadas. No se ejecutaron pm.test.
