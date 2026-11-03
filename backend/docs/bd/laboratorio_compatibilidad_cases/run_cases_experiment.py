"""Lectura ER28 en PostgreSQL desechable; no configura ni conecta el backend."""
import ast
import hashlib
import json
from pathlib import Path
import sys
import uuid

HERE = Path(__file__).resolve().parent
BACKEND = HERE.parents[2]
PREVIOUS = HERE.parent / "laboratorio_er28"
sys.dont_write_bytecode = True
sys.path.insert(0, str(PREVIOUS))
from run_experiment import Lab, INVENTORY, validate_inventory, literal
from schema_support import load, build, SOURCE

# Solo esquemas Pydantic/enum: no importamos app.main, ORM, DB ni dependencias HTTP.
sys.path.insert(0, str(BACKEND))
from pydantic import ValidationError
from app.modules.cases.api.schemas.caso_responses import CasoDetalleResponse


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def query(assignment_id):
    if type(assignment_id) is not int or assignment_id <= 0:
        raise ValueError("Solo un INTEGER positivo de este fixture")
    return (HERE / "leer_caso.sql").read_text(encoding="utf-8").replace(
        "__ASIGNACION_ID__", str(assignment_id))


def read(lab, assignment_id):
    return json.loads(lab.sql("BEGIN READ ONLY;\n" + query(assignment_id) + "\nCOMMIT;").stdout)


def validate_graph(graph):
    """Guardas experimentales de pertenencia, no políticas de ruta o evaluación."""
    case_id = graph["caso"]["id_caso"]
    rubric = graph["rubrica"]
    if rubric is None or rubric["id_caso"] != case_id:
        raise ValueError("Rúbrica ajena/ausente")
    criteria = {c["id_criterio"] for c in rubric["criterios"]}
    scenes = {s["id_escena"] for s in graph["escenas"]}
    characters = {p["id_personaje"] for p in graph["personajes"]}
    if graph["asignacion"]["id_caso"] != case_id:
        raise ValueError("Asignación ajena")
    for scene in graph["escenas"]:
        if scene["id_caso"] != case_id or not set(scene["personajes"]) <= characters:
            raise ValueError("Escena/personaje ajeno")
        for decision in scene["decisiones"]:
            if decision["id_escena"] != scene["id_escena"] or decision["id_criterio"] not in criteria:
                raise ValueError("Decisión/criterio ajeno")
            for option in decision["opciones"]:
                if option["id_decision"] != decision["id_decision"]:
                    raise ValueError("Opción ajena a decisión")
                target = option["id_escena_destino"]
                if target is not None and target not in scenes:
                    raise ValueError("Destino ajeno al caso")


def follow_supplied_edges(graph, start_scene, option_ids):
    """Verifica una secuencia EXPLÍCITA; no calcula progreso ni ruta académica.

    NULL significa aquí ausencia de arco, sin atribuirle finalización de intento.
    No elige primera escena ni opción y no invalida respuestas posteriores.
    """
    validate_graph(graph)
    current = start_scene
    visited = [current]
    options = {o["id_opcion"]: (s["id_escena"], o)
               for s in graph["escenas"] for d in s["decisiones"] for o in d["opciones"]}
    if current not in {s["id_escena"] for s in graph["escenas"]}:
        raise ValueError("Inicio inexistente")
    for option_id in option_ids:
        if option_id not in options or options[option_id][0] != current:
            raise ValueError("Selección fuera de la escena indicada")
        current = options[option_id][1]["id_escena_destino"]
        if current is not None:
            visited.append(current)
    return {"escenas": visited, "destino_final": current}


def known_fields_candidate(graph):
    """Renombra solo datos con correspondencia simple; deja ausencias visibles.

    NO coloca id_caso en el id de versión, ni convierte INTEGER en UUID,
    ni inventa tiempo estimado, version_regla, puntajes o descriptores.
    Este candidato está diseñado para demostrar el rechazo del contrato real.
    """
    return {
        "caso_id": graph["caso"]["id_caso"], "nombre": graph["caso"]["titulo"],
        "estado": graph["caso"]["estado"],
        "escenarios": [{"id": s["id_escena"], "orden": s["orden"],
            "contexto_situacional": s["contexto"],
            "preguntas": [{"id": d["id_decision"], "orden": d["orden"],
                "enunciado": d["enunciado"],
                "opciones": [{"id": o["id_opcion"], "orden": o["orden"],
                    "texto": o["texto"], "es_correcta": o["es_correcta"],
                    "justificacion": o["justificacion_teorica"]} for o in d["opciones"]]
            } for d in s["decisiones"]]} for s in graph["escenas"]],
        "rubrica": {"id": graph["rubrica"]["id_rubrica"],
            "nombre": graph["rubrica"]["nombre"], "criterios": [
                {"id": c["id_criterio"], "nombre": c["nombre"], "peso": c["peso_porcentaje"],
                 "niveles": [{"id": n["id_nivel"], "nombre": n["nombre"]} for n in c["niveles"]]}
                for c in graph["rubrica"]["criterios"]]},
    }


def main():
    model = load()
    sql = (PREVIOUS / "er28_experimental.sql").read_text(encoding="utf-8")
    if sql != build(model):
        raise RuntimeError("SQL BD2-02B no coincide con fuente aprobada")
    run_id = uuid.uuid4().hex  # Identificador del archivo, nunca identidad académica.
    ev = {"run_id": run_id, "tests": [], "source_sha256": digest(SOURCE)}
    files = [HERE / n for n in ("run_cases_experiment.py", "datos_sinteticos.sql", "leer_caso.sql")]
    files += [PREVIOUS / n for n in ("run_experiment.py", "schema_support.py", "er28_experimental.sql")]
    ev["artifact_sha256"] = {str(p.relative_to(BACKEND)).replace("\\", "/"): digest(p) for p in files}
    sources = [
        "cases/application/published_version.py", "cases/domain/entities/caso.py",
        "cases/api/schemas/caso_responses.py", "cases/infrastructure/models/caso.py",
        "cases/infrastructure/models/rubrica.py", "cases/domain/validators/eslabones.py",
        "scheduling/infrastructure/models.py", "scheduling/application/programar_sesion.py",
        "participation/application/integration_ports.py", "participation/application/ports.py",
    ]
    ev["production_sources_readonly"] = {n: digest(BACKEND / "app/modules" / n) for n in sources}
    # Testigos estáticos legibles; no se ejecutan Scheduling/8A contra otro esquema.
    ev["contract_fields_static"] = {}
    for name in (sources[0], sources[2], sources[8]):
        tree = ast.parse((BACKEND / "app/modules" / name).read_text(encoding="utf-8"))
        ev["contract_fields_static"][name] = {
            c.name: {a.target.id: ast.unparse(a.annotation) for a in c.body
                     if isinstance(a, ast.AnnAssign) and isinstance(a.target, ast.Name)}
            for c in tree.body if isinstance(c, ast.ClassDef)}
    lab = Lab()  # Ciclo y comprobaciones de aislamiento originales de BD2-02B.
    failure = None

    def check(name, condition, details=None):
        ev["tests"].append({"id": name, "passed": bool(condition), "details": details})
        if not condition:
            raise AssertionError(name)

    def reject(name, action):
        try:
            action()
        except ValueError as error:
            check(name, True, str(error))
        else:
            check(name, False)

    def sql_probe(name, statement, expected, setup=""):
        batch = ("BEGIN;\n" + setup + "\n\\set ON_ERROR_STOP off\n" + statement
                 + "\n\\set observed :SQLSTATE\n\\set ON_ERROR_STOP on\nROLLBACK;\n"
                 + "SELECT json_build_object('state', :'observed');")
        result = lab.sql(batch)
        state = json.loads(result.stdout)["state"]
        check(name, state == expected, {"expected": expected, "actual": state,
                                      "sql": statement, "stderr": result.stderr[-1800:]})

    try:
        lab.start()
        before = json.loads(lab.sql(INVENTORY).stdout)
        check("base_nueva_vacia", not before["all_user_tables"])
        lab.sql(sql)
        inv = json.loads(lab.sql(INVENTORY).stdout)
        errors = validate_inventory(model, inv)
        ev["inventory"] = inv
        check("ER28_exacto", not errors, errors)
        lab.sql((HERE / "datos_sinteticos.sql").read_text(encoding="utf-8"))
        graph = read(lab, 401)
        ev["lectura_interna_sintetica"] = graph
        validate_graph(graph)
        check("pertenencia_caso_rubrica_criterios_destinos", True)
        check("asignacion_caso_INTEGER", type(graph["caso"]["id_caso"]) is int
              and graph["asignacion"]["id_caso"] == 10)
        check("escenas_ordenadas", [s["id_escena"] for s in graph["escenas"]] == [101,102,103])
        check("decisiones_recuperadas", [s["decisiones"][0]["id_decision"] for s in graph["escenas"]] == [201,202,203])
        check("opciones_ordenadas", [[o["id_opcion"] for o in s["decisiones"][0]["opciones"]]
                                     for s in graph["escenas"]] == [[301,302],[303,304],[305,306]])
        check("objetivos_personajes_pistas", len(graph["objetivos"]) == 1
              and graph["escenas"][0]["personajes"] == [130]
              and graph["escenas"][0]["decisiones"][0]["pistas"][0]["id_pista"] == 140)
        check("rubrica_y_niveles", graph["rubrica"]["id_rubrica"] == 20
              and [len(c["niveles"]) for c in graph["rubrica"]["criterios"]] == [2,2])
        check("asignacion_inexistente", read(lab, 99999) is None)
        for label, choices, expected in (
            ("dialogo", [301,303,305], [101,102,103]),
            ("atajo", [302,305], [101,103]),
        ):
            route = follow_supplied_edges(graph, 101, choices)
            ev["recorrido_" + label] = route
            check("arcos_" + label, route == {"escenas": expected, "destino_final": None}, route)
        reject("seleccion_de_otra_escena", lambda: follow_supplied_edges(graph,101,[303]))
        reject("seleccion_tras_NULL", lambda: follow_supplied_edges(graph,101,[302,305,301]))
        reject("identificador_no_INTEGER", lambda: query("401"))
        # Contrato Pydantic REAL: el rechazo no se reemplaza por un DTO permisivo.
        try:
            CasoDetalleResponse.model_validate(known_fields_candidate(graph))
        except ValidationError as error:
            issues = [{"field": list(e["loc"]), "type": e["type"]}
                      for e in error.errors(include_url=False)]
            ev["rechazo_contrato_CasoDetalleResponse"] = issues
        else:
            issues = []
        check("contrato_actual_rechaza_INTEGER", any(e["field"] == ["caso_id"] and e["type"] == "uuid_type" for e in issues))
        check("contrato_no_inventa_version_tiempo", all(any(e["field"] == [n] and e["type"] == "missing" for e in issues)
              for n in ("id","numero","tiempo_estimado_min","desarrollo_situacional","contexto_historia")))
        check("contrato_no_inventa_regla_valoraciones", any(e["field"] == ["rubrica","version_regla"] for e in issues)
              and any(e["field"][-1] == "valoraciones" for e in issues))
        sql_probe("FK_opcion_decision_inexistente",
                  "INSERT INTO opcion_respuesta VALUES (999,999,NULL,'x',false,'ensayo',1);", "23503")
        sql_probe("UNIQUE_orden_decision", "INSERT INTO decision VALUES (999,101,21,'x',1);", "23505")
        sql_probe("UNIQUE_rubrica_por_caso", "INSERT INTO rubrica VALUES (999,10,'otra',5);", "23505")
        sql_probe("FK_asignacion_caso_inexistente", "UPDATE asignacion_caso SET id_caso=999 WHERE id_asignacion=401;", "23503")
        for name, statement, state in (
            ("sin_version_caso", "SELECT id FROM version_caso;", "42P01"),
            ("sin_version_en_asignacion", "SELECT version_caso_id FROM asignacion_caso;", "42703"),
            ("sin_regla_rubrica", "SELECT version_regla FROM rubrica;", "42703"),
            ("sin_valoracion_por_opcion_criterio", "SELECT puntaje FROM valoracion_opcion;", "42P01"),
            ("sin_tiempo_estimado_caso", "SELECT tiempo_estimado_min FROM caso;", "42703"),
            ("sin_descriptor_nivel", "SELECT descriptor FROM nivel_criterio;", "42703"),
        ):
            sql_probe(name, statement, state)
        # El cambio posterior deja las mismas asignaciones, pero devuelve otro contenido.
        changed = json.loads(lab.sql("BEGIN;\n"
            "UPDATE caso SET titulo='Edición posterior',introduccion_teorica='Marco cambiado' WHERE id_caso=10;\n"
            "UPDATE decision SET enunciado='Enunciado cambiado' WHERE id_decision=201;\n"
            "UPDATE rubrica SET nombre='Rúbrica modificada' WHERE id_rubrica=20;\n"
            + query(401) + "\nROLLBACK;").stdout)
        ev["lectura_tras_edicion_revertida"] = changed
        check("limite_asignacion_no_fija_version", changed["asignacion"] == graph["asignacion"]
              and changed["caso"]["titulo"] != graph["caso"]["titulo"]
              and changed["escenas"][0]["decisiones"][0]["enunciado"] != graph["escenas"][0]["decisiones"][0]["enunciado"]
              and changed["rubrica"]["nombre"] != graph["rubrica"]["nombre"])
        check("rollback_restaura_lectura_completa", read(lab,401) == graph)
        other_assignment = read(lab,402)
        check("dos_asignaciones_mismo_contenido_actual", other_assignment["caso"] == graph["caso"]
              and other_assignment["escenas"] == graph["escenas"]
              and other_assignment["rubrica"] == graph["rubrica"])
        # FKs existentes no garantizan pertenencia al mismo caso: no corregimos ER.
        setup = ("INSERT INTO caso (id_caso,id_profesor,titulo,introduccion_teorica,fecha_creacion) "
                 "VALUES (99,11,'Ajeno','ensayo','2030-01-01');\n"
                 "INSERT INTO escena VALUES (199,99,'Ajena','ensayo',1,'ensayo');\n"
                 "INSERT INTO rubrica VALUES (29,99,'Ajena',5);\n"
                 "INSERT INTO criterio_rubrica VALUES (299,29,'Ajeno',100);")
        for label, mutation in (
            ("destino_ajeno", "UPDATE opcion_respuesta SET id_escena_destino=199 WHERE id_opcion=301;"),
            ("criterio_ajeno", "UPDATE decision SET id_criterio=299 WHERE id_decision=201;"),
        ):
            sql_probe("ER_acepta_" + label, mutation, "00000", setup)
            cross = json.loads(lab.sql("BEGIN;\n" + setup + "\n" + mutation + "\n" + query(401) + "\nROLLBACK;").stdout)
            reject("lector_rechaza_" + label, lambda: validate_graph(cross))
        check("rollback_todos_ensayos", read(lab,401) == graph)
        check("catalogo_sin_cambios_ni_tablas_extra", json.loads(lab.sql(INVENTORY).stdout) == inv)
        ev["status"] = "passed"
        ev["functional_compatibility"] = "partial_read_only_ER28; current_versioned_backend_incompatible"
    except BaseException as error:
        failure = error
        ev["status"] = "failed"
        ev["error"] = str(error).replace(lab.secret, "<redactado>")
    finally:
        try:
            lab.cleanup()
        except BaseException as error:
            failure = failure or error
            ev["status"] = "failed"
            ev["cleanup_error"] = str(error).replace(lab.secret, "<redactado>")
        ev["laboratory"] = lab.proof
        dest = HERE / ("resultado_" + run_id + ".json")
        dest.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": ev["status"], "tests": len(ev["tests"]),
                          "passed": sum(t["passed"] for t in ev["tests"]),
                          "evidence": dest.name, "cleanup": lab.proof.get("cleanup")}), flush=True)
    if failure:
        raise SystemExit(ev.get("error", ev.get("cleanup_error", "Fallo experimental")))


if __name__ == "__main__":
    main()
