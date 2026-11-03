"""Experimento diagnóstico: garantías vulneradas se informan, no se ocultan."""
import hashlib
import json
from pathlib import Path
import sys
import uuid

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
BD = HERE.parent
sys.path.insert(0, str(BD / "laboratorio_er28"))
from run_experiment import Lab, INVENTORY, validate_inventory, literal
from schema_support import load, build, SOURCE


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    model = load()
    original_sql = BD / "laboratorio_er28/er28_experimental.sql"
    if original_sql.read_text(encoding="utf-8") != build(model):
        raise RuntimeError("SQL original no coincide con DBML")
    run_id = uuid.uuid4().hex
    # Entidades FUENTE sintéticas independientes de las PK INTEGER destino.
    source = {n: str(uuid.uuid4()) for n in ("familia", "v1", "v2", "r1", "r2", "otra_familia")}
    ev = {"run_id": run_id, "source_sha256": sha(SOURCE), "fuente_sintetica_uuid": source,
          "garantias": [], "infra_checks": []}
    paths = [HERE / n for n in ("run_u1.py", "seis_columnas.sql", "resultado_sintetico.sql")]
    paths += [original_sql, BD / "laboratorio_er28/run_experiment.py",
              BD / "laboratorio_er28/schema_support.py", BD / "laboratorio_compatibilidad_cases/datos_sinteticos.sql",
              BD / "laboratorio_compatibilidad_cases/leer_caso.sql"]
    ev["artifact_sha256"] = {p.relative_to(BD).as_posix(): sha(p) for p in paths}
    lab, failure = Lab(), None

    def infra(name, ok):
        ev["infra_checks"].append({"id": name, "passed": bool(ok)})
        if not ok:
            raise AssertionError(name)

    def guarantee(name, ok, evidence, kind="observacion"):
        ev["garantias"].append({"id": name, "satisfecha": bool(ok), "tipo": kind, "evidencia": evidence})

    def read(assignment=401):
        if type(assignment) is not int:
            raise ValueError("Solo INTEGER local")
        q = (BD / "laboratorio_compatibilidad_cases/leer_caso.sql").read_text(encoding="utf-8")
        return json.loads(lab.sql("BEGIN READ ONLY;\n" + q.replace("__ASIGNACION_ID__",str(assignment)) + "\nCOMMIT;").stdout)

    result_query = """SELECT jsonb_build_object(
      'resultado',(SELECT to_jsonb(r) FROM resultado_intento r WHERE id_resultado=901),
      'criterios',(SELECT jsonb_agg(to_jsonb(r) ORDER BY id_criterio) FROM resultado_criterio r WHERE id_resultado=901),
      'participacion',(SELECT to_jsonb(r) FROM resultado_participacion r WHERE id_resultado_participacion=921));"""

    def reference(version):
        # Consulta de laboratorio, no proveedor productivo ni autorización.
        value = str(uuid.UUID(version))
        q = """SELECT COALESCE((SELECT jsonb_build_object(
          'caso_id',c.uuid_caso,'version_id',c.uuid_version,'numero',c.numero_version,
          'rubrica_id',r.uuid_publico,'version_regla',r.version_regla)
          FROM caso c JOIN rubrica r ON r.id_caso=c.id_caso
          WHERE c.uuid_version=""" + literal(value) + """::uuid
          AND c.contenido_congelado IS TRUE AND c.estado='PUBLICADO'
          AND c.uuid_caso IS NOT NULL AND c.numero_version IS NOT NULL
          AND r.uuid_publico IS NOT NULL AND length(btrim(r.version_regla))>0),'null'::jsonb);"""
        return json.loads(lab.sql(q).stdout)

    def probe(name, statement, required, witness="SELECT to_jsonb(c) FROM caso c WHERE id_caso=10;", setup=""):
        # required es la garantía deseada, no el resultado que haga pasar el ensayo.
        batch = ("BEGIN;\n"+setup+"\n\\set ON_ERROR_STOP off\n"+statement+
                 "\n\\set observed :SQLSTATE\n\\if :ERROR\n\\else\n"+witness+
                 "\n\\endif\n\\set ON_ERROR_STOP on\nROLLBACK;\n"
                 "SELECT json_build_object('sqlstate', :'observed');")
        p = lab.sql(batch)
        rows = [json.loads(line) for line in p.stdout.splitlines() if line.strip()]
        state = rows[-1]["sqlstate"]
        ok = state != "00000" if required == "rechazar" else state == required
        guarantee(name, ok, {"sql": statement, "setup": setup, "deberia": required,
                            "sqlstate": state, "testigo": rows[:-1], "stderr": p.stderr[-1400:]}, "SQL")

    try:
        lab.start()
        infra("base_nueva_vacia", not json.loads(lab.sql(INVENTORY).stdout)["all_user_tables"])
        lab.sql(original_sql.read_text(encoding="utf-8"))
        original = json.loads(lab.sql(INVENTORY).stdout)
        infra("ER28_literal_previo", not validate_inventory(model, original))
        lab.sql((HERE / "seis_columnas.sql").read_text(encoding="utf-8"))
        inv = json.loads(lab.sql(INVENTORY).stdout)
        additions = {(c["table_name"],c["column_name"]) for c in inv["columns"]} - {
            (c["table_name"],c["column_name"]) for c in original["columns"]}
        expected = {("caso",n) for n in ("uuid_caso","uuid_version","numero_version","contenido_congelado")}
        expected |= {("rubrica",n) for n in ("uuid_publico","version_regla")}
        infra("solo_seis_columnas", additions == expected and len(inv["columns"]) == 150)
        infra("solo_28_tablas", inv["all_user_tables"] == original["all_user_tables"])
        infra("PK_FK_originales_sin_cambios", sorted((c["table"],c["name"],c["definition"]) for c in inv["constraints"] if c["type"] in ('p','f')) ==
              sorted((c["table"],c["name"],c["definition"]) for c in original["constraints"] if c["type"] in ('p','f')))
        infra("sin_triggers_agregados", inv["user_triggers"] == 0)
        ev["inventario_experimental"] = inv
        ev["columnas_agregadas"] = sorted(additions)
        lab.sql((BD / "laboratorio_compatibilidad_cases/datos_sinteticos.sql").read_text(encoding="utf-8"))
        lab.sql("BEGIN; UPDATE caso SET uuid_caso="+literal(source["familia"])+"::uuid,uuid_version="+
                literal(source["v1"])+"::uuid,numero_version=1,contenido_congelado=true,estado='PUBLICADO' WHERE id_caso=10;\n"
                "UPDATE rubrica SET uuid_publico="+literal(source["r1"])+"::uuid,version_regla='regla-lab-v1' WHERE id_rubrica=20; COMMIT;")
        lab.sql((HERE / "resultado_sintetico.sql").read_text(encoding="utf-8"))
        before, result_before = read(), json.loads(lab.sql(result_query).stdout)
        ev["asignacion_antes_v2"], ev["resultado_antes_v2"] = before, result_before
        ref1 = reference(source["v1"])
        guarantee("referencia_v1_completa", ref1 == {"caso_id":source["familia"], "version_id":source["v1"],
                  "numero":1,"rubrica_id":source["r1"],"version_regla":"regla-lab-v1"}, ref1)
        # Edición posterior independiente con sus propios padres/hijos INTEGER.
        v2 = "\n".join([
            "BEGIN;",
            "INSERT INTO caso (id_caso,id_profesor,titulo,introduccion_teorica,estado,fecha_creacion,uuid_caso,uuid_version,numero_version,contenido_congelado) VALUES (50,11,'Edición posterior','Marco posterior','PUBLICADO','2030-02-01',"+literal(source["familia"])+"::uuid,"+literal(source["v2"])+"::uuid,2,true);",
            "INSERT INTO rubrica VALUES (60,50,'Rúbrica posterior',5,"+literal(source["r2"])+"::uuid,'regla-lab-v2');",
            "INSERT INTO criterio_rubrica VALUES (61,60,'Criterio posterior',100);",
            "INSERT INTO nivel_criterio VALUES (62,61,'Nivel posterior',100);",
            "INSERT INTO escena VALUES (151,50,'Escena posterior','Contexto posterior',1,'ensayo');",
            "INSERT INTO decision VALUES (251,151,61,'Decisión posterior',1);",
            "INSERT INTO opcion_respuesta VALUES (351,251,NULL,'Opción posterior',true,'Explicación posterior',1);",
            "COMMIT;"])
        ev["insercion_v2_sql"] = v2
        lab.sql(v2)
        after, result_after = read(), json.loads(lab.sql(result_query).stdout)
        ev["asignacion_despues_v2"], ev["resultado_despues_v2"] = after, result_after
        guarantee("nueva_edicion_no_modifica_asignacion_v1", before == after, {"iguales":before == after})
        guarantee("nueva_edicion_no_modifica_resultado_guardado", result_before == result_after, result_after)
        ref2 = reference(source["v2"])
        guarantee("familia_reconocible_dos_ediciones", ref1["caso_id"] == ref2["caso_id"] == source["familia"]
                  and ref1["version_id"] != ref2["version_id"] and (ref1["numero"],ref2["numero"]) == (1,2), [ref1,ref2])
        mapping = json.loads(lab.sql("SELECT json_agg(json_build_object('integer',id_caso,'familia',uuid_caso,'version',uuid_version,'numero',numero_version) ORDER BY id_caso) FROM caso;").stdout)
        ev["correspondencia_verificada"] = mapping
        guarantee("UUID_INTEGER_correspondencia_fuente_destino", mapping == [
            {"integer":10,"familia":source["familia"],"version":source["v1"],"numero":1},
            {"integer":50,"familia":source["familia"],"version":source["v2"],"numero":2}], mapping)
        guarantee("busqueda_UUID_no_asociado_sin_fallback", reference(source["otra_familia"]) is None, None)
        # Restricciones locales e integridad referencial que sí existen.
        for name, stmt, state in (
            ("UUID_version_unico", "UPDATE caso SET uuid_version="+literal(source['v1'])+"::uuid WHERE id_caso=50;", "23505"),
            ("numero_unico_en_familia", "UPDATE caso SET numero_version=1 WHERE id_caso=50;", "23505"),
            ("numero_positivo", "UPDATE caso SET numero_version=0 WHERE id_caso=50;", "23514"),
            ("referencia_caso_completa", "UPDATE caso SET uuid_version=NULL WHERE id_caso=50;", "23514"),
            ("UUID_rubrica_unico", "UPDATE rubrica SET uuid_publico="+literal(source['r1'])+"::uuid WHERE id_rubrica=60;", "23505"),
            ("referencia_rubrica_completa", "UPDATE rubrica SET version_regla=NULL WHERE id_rubrica=60;", "23514"),
            ("regla_no_vacia", "UPDATE rubrica SET version_regla=' ' WHERE id_rubrica=60;", "23514"),
            ("FK_asignacion_sin_huerfano", "UPDATE asignacion_caso SET id_caso=99999 WHERE id_asignacion=401;", "23503"),
            ("FK_rubrica_sin_huerfano", "UPDATE rubrica SET id_caso=99999 WHERE id_rubrica=60;", "23503"),
            ("FK_par_opcion_decision", "UPDATE paso_simulacion SET id_opcion=351 WHERE id_paso=801;", "23503"),
        ):
            probe(name,stmt,state)
        # Intentos de vulnerar garantías: se espera RECHAZO, no se convierte
        # SQLSTATE 00000 en una aprobación de seguridad/inmutabilidad.
        for name, stmt, witness in (
            ("inmutabilidad_cabecera", "UPDATE caso SET titulo='Contenido alterado' WHERE id_caso=10;", "SELECT to_jsonb(c) FROM caso c WHERE id_caso=10;"),
            ("inmutabilidad_hijo", "UPDATE decision SET enunciado='Pregunta alterada' WHERE id_decision=201;", "SELECT to_jsonb(d) FROM decision d WHERE id_decision=201;"),
            ("inmutabilidad_rubrica", "UPDATE criterio_rubrica SET peso_porcentaje=1 WHERE id_criterio=21;", "SELECT to_jsonb(c) FROM criterio_rubrica c WHERE id_criterio=21;"),
            ("congelacion_irreversible", "UPDATE caso SET contenido_congelado=false WHERE id_caso=10;", "SELECT to_jsonb(c) FROM caso c WHERE id_caso=10;"),
            ("asignacion_no_reapunta_v2", "UPDATE asignacion_caso SET id_caso=50 WHERE id_asignacion=401;",
             "SELECT json_build_object('asignacion',a.id_asignacion,'version_referida',c.uuid_version,'rubrica_referida',r.uuid_publico,'nota_guardada',ri.nota_final) FROM resultado_intento ri JOIN intento i USING(id_intento) JOIN participacion p USING(id_participacion) JOIN asignacion_caso a USING(id_asignacion) JOIN caso c USING(id_caso) JOIN rubrica r USING(id_caso) WHERE ri.id_resultado=901;"),
            ("version_no_cambia_familia", "UPDATE caso SET uuid_caso="+literal(source['otra_familia'])+"::uuid WHERE id_caso=50;", "SELECT to_jsonb(c) FROM caso c WHERE id_caso=50;"),
            ("familia_no_cambia_propietario", "UPDATE caso SET id_profesor=12 WHERE id_caso=50;", "SELECT to_jsonb(c) FROM caso c WHERE id_caso=50;"),
            ("criterio_no_cruza_edicion", "UPDATE decision SET id_criterio=61 WHERE id_decision=201;", "SELECT to_jsonb(d) FROM decision d WHERE id_decision=201;"),
            ("destino_no_cruza_edicion", "UPDATE opcion_respuesta SET id_escena_destino=151 WHERE id_opcion=301;", "SELECT to_jsonb(o) FROM opcion_respuesta o WHERE id_opcion=301;"),
            ("resultado_no_alterable", "UPDATE resultado_intento SET nota_final=1 WHERE id_resultado=901;", result_query),
            ("resultado_no_usa_criterio_otra_edicion", "UPDATE resultado_criterio SET id_criterio=61,id_nivel=62 WHERE id_resultado_criterio=911;", "SELECT to_jsonb(r) FROM resultado_criterio r WHERE id_resultado_criterio=911;"),
        ):
            probe(name,stmt,"rechazar",witness)
        # Rúbrica completa no implica edición completa; el CHECK es solo local.
        probe("rubrica_no_asociada_a_edicion_sin_identidad",
              "UPDATE caso SET uuid_caso=NULL,uuid_version=NULL,numero_version=NULL,contenido_congelado=NULL WHERE id_caso=10;",
              "rechazar", "SELECT json_build_object('caso',to_jsonb(c),'rubrica',to_jsonb(r)) FROM caso c JOIN rubrica r USING(id_caso) WHERE id_caso=10;")
        infra("rollback_restaura_contenido_y_resultados", read() == before and json.loads(lab.sql(result_query).stdout) == result_before)
        infra("catalogo_final_sin_mas_modificaciones", json.loads(lab.sql(INVENTORY).stdout) == inv)
        ev["status"] = "completed_with_limitations" if any(not g["satisfecha"] for g in ev["garantias"]) else "completed"
        ev["nota_reproducibilidad"] = "Se compara nota sintética almacenada, no se recalcula ni demuestra una fórmula académica."
    except BaseException as error:
        failure = error
        ev["status"], ev["error"] = "execution_error", str(error).replace(lab.secret,"<redactado>")
    finally:
        try:
            lab.cleanup()
        except BaseException as error:
            failure = failure or error
            ev["status"],ev["cleanup_error"] = "execution_error",str(error).replace(lab.secret,"<redactado>")
        ev["laboratory"] = lab.proof
        ev["summary"] = {"satisfechas":sum(g["satisfecha"] for g in ev["garantias"]),
                         "vulneradas":sum(not g["satisfecha"] for g in ev["garantias"])}
        dest = HERE / ("evidencia_"+run_id+".json")
        dest.write_text(json.dumps(ev,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print(json.dumps({"status":ev["status"],"summary":ev["summary"],"evidence":dest.name,
                          "cleanup":lab.proof.get("cleanup")}),flush=True)
    if failure:
        raise SystemExit(ev.get("error",ev.get("cleanup_error","Fallo")))


if __name__ == "__main__":
    main()
