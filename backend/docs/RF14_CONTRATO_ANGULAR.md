# RF-14 — contrato de consulta privada para Angular

10 de noviembre de 2026. Contrato descriptivo del servidor existente; no acredita una prueba de navegador ni crea otro endpoint. Evidencia y veredicto final en RF14_CIERRE_CONTROLADO_20261110.md.

## Operación y autenticación

**GET /scheduling/convocatorias/{convocatoria_id}/resultado**, registrado en app.main por Scheduling/academic_results.py. No anteponer /api/v1. Sin body ni query; no añadir parámetros de cache-busting, versión, estudiante o nota.

Bearer JWT estudiantil real, emitido por Identity. El servidor relee cuenta activa/rol ESTUDIANTE, resuelve su UUID Scheduling y exige coincidencia tanto con el estudiante de la convocatoria como con el id_convocatoria del JWT. Un identificador enviado por el cliente no es una prueba de propiedad. El docente usa otras rutas; su JWT no permite entrar por esta operación estudiantil.

El path es UUID de convocatoria, no id_intento ni id_participacion. El backend resuelve esas relaciones. No convertir los INTEGER académicos a UUID ni elegir otro estudiante en cabeceras. No se envía un flag para solicitar correcciones o elevar visibilidad.

## Cuándo hay un 200

Se distinguen cuatro hechos: calcular no equivale a persistir; persistir no equivale a poder consultar; poder consultar provisionalmente no equivale a publicar oficialmente.

1. **Existe publicación oficial:** se verifica su snapshot y se devuelve solo la fila del titular de la última publicación vigente. Una rectificación pendiente no sustituye esa publicación sin otra autorización. El resultado puede ser COMPLETA, PARCIAL o AUSENTE.
2. **No existe publicación:** la convocatoria debe seguir ACTIVA; el docente tiene que haber habilitado expresamente mostrar_resultados_provisionales; debe existir participación, todos sus intentos deben estar cerrados y tener resultados TECNICO verificables. Se devuelve provisional, oficial=false. No se convierte LABORATORIO en nota.
3. **Explicaciones:** se llenan únicamente si la sesión está FINALIZADO, con las selecciones persistidas de la versión histórica. Durante una sesión activa se devuelve explicaciones=[], aunque la nota provisional ya esté autorizada. El reloj local del navegador no decide la visibilidad.
4. Un intento abierto no produce una nota consultable provisional. Si falta el resultado calculado, el GET no lo crea. No hay ausencia inferida, cierre, evaluación ni publicación como efecto de consultar.

El máximo entre intentos de la misma participación es el comportamiento existente del ciclo académico. Esta consulta no concede intentos adicionales ni resuelve RF25 para casos distintos. La política productora y el flujo UC05 conservan los límites RF13 documentados.

## Representación JSON real

La ruta devuelve diccionarios serializados, sin un response_model Pydantic explícito. Los tipos siguientes documentan su forma actual; no son un cliente Angular generado ni una promesa de que OpenAPI ya describa íntegramente esta unión.

```typescript
type UUID = string;
type NotaDecimal = string; // Ejemplos de formato: "0.00", "33.33", "100.00".
type Situacion = "COMPLETA" | "PARCIAL" | "AUSENTE";
interface ExplicacionSeleccion {
  pregunta_id: UUID;
  opcion_id: UUID;
  enunciado: string;
  texto_seleccionado: string;
  es_correcta: boolean;
  justificacion: string;
}
interface FeedbackIntento {
  id_intento: number; // INTEGER real
  respuestas: ExplicacionSeleccion[];
}
interface ResultadoProvisional {
  oficial: false;
  situacion: "COMPLETA" | "PARCIAL";
  nota: NotaDecimal;
  detalle: {
    id_participacion: number;
    version_caso_id: UUID;
    rubrica_id: UUID;
    intentos: {id_intento: number; id_resultado: number; nota: NotaDecimal}[];
  };
  explicaciones: FeedbackIntento[];
}
interface ResultadoOficial {
  publicacion_id: UUID;
  version_publicacion: number;
  oficial: true;
  situacion: Situacion;
  nota: NotaDecimal;
  detalle: {
    convocatoria_id: UUID;
    id_estudiante: number;
    id_asignacion: number;
    id_participacion: number | null;
    nombre_estudiante: string;
    grupo_id: number;
    grupo_nombre: string;
    caso_id: UUID;
    version_caso_id: UUID;
    rubrica_id: UUID;
    situacion: Situacion;
    nota: NotaDecimal;
    id_resultado_intento: number | null;
    id_ausencia: UUID | null;
    intentos: {
      id_intento: number; numero: number; estado: "FINALIZADO" | "VENCIDO";
      id_resultado: number; nota: NotaDecimal; sha256: string;
    }[];
  };
  explicaciones: FeedbackIntento[];
}
type ResultadoEstudiantil = ResultadoProvisional | ResultadoOficial;
```

En éxito, nota es una cadena con dos decimales, nunca null ni un float JSON. No recalcularla en JavaScript. oficial es el discriminante; un resultado provisional no se muestra como aprobado/publicado. COMPLETA/PARCIAL describen modalidad académica, no el estado del intento ni un criterio de aprobación.

Para ausencia publicada: id_participacion e id_resultado_intento son null, id_ausencia existe, intentos=[] y explicaciones=[]; no hay un intento ficticio. Una ausencia confirmada pero aún no publicada no se presenta como nota oficial.

La colección explicaciones se agrupa por intento. Una pregunta puede reaparecer en distintos intentos; no deduplicarla globalmente ni mezclar sus elecciones. Cada bloque contiene solo selecciones efectivas, en orden. En parciales se omiten explicaciones de preguntas pendientes y de ramas inaccesibles; no son preguntas con una selección inventada.

Datos excluidos: credenciales, códigos y hashes de acceso, documentos/fuentes del motor o política, resultados de otros estudiantes, padrón completo, contenido de rúbrica/ponderaciones y alternativas no seleccionadas. Los UUID de versión/rúbrica son referencias históricas, no el contenido de la rúbrica. El nombre y grupo de la fila oficial corresponden exclusivamente al titular.

No se retorna fecha de publicación en este GET; no asumirla a partir del reloj o de otro campo. Tampoco existe un campo feedback_docente en esta representación: la valoración general RF26 tiene su propia consulta autorizada; no confundirla con la justificación histórica de cada selección.

## Errores y estados de interfaz

| HTTP | Significado / tratamiento |
|---|---|
| 401 | JWT/cuenta no válidos. Solicitar autenticación, sin conservar datos de otra sesión |
| 403 | Rol/titularidad/convocatoria no autorizados. No cambiar IDs para intentar acceder a otro recurso |
| 404 | Resultado no disponible: visibilidad apagada, no existe participación/resultado o no hay fila propia publicada. No inferir una causa privada concreta ni mostrar nota cero |
| 409 | Intento propio pendiente/abierto o conflicto. No cerrarlo ni evaluarlo por una consulta |
| 422 | UUID/entrada incorrectos o query no admitida. Corregir petición; no reintentar con notas inventadas |
| 503 | Configuración, zona temporal, integridad o infraestructura no acreditadas. No confundirlo con una nota pendiente calculada ni con éxito |

Las excepciones Identity suelen usar detail={codigo,mensaje}; el rechazo de query puede usar detail de texto y la validación de FastAPI una lista. El cliente debe tolerar esas formas reales, no inventar un envelope universal. Las respuestas controladas usan Cache-Control:no-store.

Corrección Fase7: cerrado sin resultado devuelve 404, igual que el recurso técnico docente; antes una captura demasiado amplia lo convertía en 503. No se ha cambiado la política de visibilidad ni se devuelve una nota por defecto.

## Recarga, concurrencia y privacidad

GET usa una Session propia, REPEATABLE READ / READ ONLY, no_autoflush y cierre con rollback, sin commit. Puede verificar la procedencia y reproducibilidad de un resultado existente, pero no genera otro cálculo persistido, no cambia la nota ni publica. Las pruebas instrumentan DML/DDL/flush/commit y comparan la cabecera antes/después.

Repetir o recargar recupera el estado vigente autorizado. Una publicación posterior puede cambiar legítimamente de provisional a oficial o de versión oficial; no se promete que la respuesta sea eterna. No cachear entre usuarios/convocatorias; no reutilizar una autorización previamente obtenida como permiso permanente.

No almacenar tokens o respuestas académicas en capturas. Mostrar código HTTP, URL sin secretos y Test Results; ocultar Authorization, claves y códigos de login. Se verificó HTTP mediante TestClient/main y Newman/TCP con PostgreSQL17 desechable; **no se ejecutó una aplicación Angular ni un navegador**.

## MAIN y LAB

La consulta de resultado y la configuración docente de visibilidad son rutas de app.main. El docente autorizado publica mediante POST /scheduling/sesiones/{sesion_id}/evaluacion/publicaciones con revisión vigente, no mediante GET ni al finalizar un intento.

Las cuentas, grupos, matrículas, asignaciones y ciertos estados de preparación de las pruebas son datos administrativos sintéticos de LAB. Las operaciones positivas de consentimiento/inicio de otras colecciones pueden usar una aplicación LAB con puertos explícitos: no equivalen a inicio productivo ni aprobación del documento institucional. RF03/RF04/RF10/RF12/RF13/RF23/RF25 conservan sus bloqueos propios.
