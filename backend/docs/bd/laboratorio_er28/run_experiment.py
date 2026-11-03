"""Ensayo ER28. Solo Docker nuevo sin red/puertos; nunca importa app o Alembic."""
import json
import hashlib
import os
from pathlib import Path
import secrets
import subprocess
import time
import uuid
from schema_support import HERE, SOURCE, EXPECTED_SHA, load, counts, order, build, quoted, fields

DB, USER = "er28_experiment", "er28_lab"


def literal(value):
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def row_for(t):
    row = {}
    for c in t["columns"]:
        if c["nullable"]:
            value = None
        elif c["default"] is not None:
            d = c["default"]
            value = (d == "true") if d in ("true", "false") else (d[1:-1] if d.startswith("'") else int(d))
        elif c["type"] == "int" or c["type"].startswith("decimal"):
            value = 1
        elif c["type"] == "timestamp":
            value = "2026-11-01 12:00:00"
        elif c["type"] == "boolean":
            value = True
        else:
            value = "fixture_" + t["name"] + "_" + c["name"]
            if c["type"].startswith("varchar"):
                value = value[:int(c["type"][8:-1])]
        row[c["name"]] = value
    return row


def insert(name, row):
    return "INSERT INTO " + quoted(name) + " (" + fields(row) + ") VALUES (" + ", ".join(literal(v) for v in row.values()) + ");"


def fresh(t, seed, number=900001):
    row = dict(seed)
    fk_cols = {c for f in t["fk"] for c in f["columns"]}
    for name in t["pk"]:
        if name not in fk_cols:
            row[name] = number
    for c in t["columns"]:
        n = c["name"]
        if n in ("orden", "numero_intento", "numero_paso"):
            row[n] = number
        if c["type"].startswith("varchar") and any(n in u for u in t["unique"]) and n not in fk_cols:
            row[n] = ("nuevo_" + n)[:int(c["type"][8:-1])]
    return row


def probes(tables, seeds):
    tests = []
    def add(name, sql, state, **meta):
        tests.append(dict(id=name, sql=sql, expected=state, **meta))
    for name, t in tables.items():
        for i, f in enumerate(t["fk"], 1):
            row = fresh(t, seeds[name])
            setup = ""
            if name == "retroalimentacion_docente" and f["columns"] == ["id_profesor"]:
                # Aislar la FK del profesor: la asignación 1 ya tiene comentario
                # UNIQUE. Una segunda asignación válida evita probar esa UQ.
                setup = insert("asignacion_caso", fresh(tables["asignacion_caso"], seeds["asignacion_caso"], 2)) + "\n"
                row["id_asignacion"] = 2
            for col in f["columns"]:
                row[col] = 900001
            add(f"FK:{name}:{i}", setup + insert(name, row), "23503", target=f["target"])
        for i, u in enumerate(t["unique"], 1):
            row = fresh(t, seeds[name])
            row.update({col: seeds[name][col] for col in u})
            add(f"UNIQUE:{name}:{i}", insert(name, row), "23505",
                columns=u, redundant_with_pk=set(t["pk"]) <= set(u))
        for c in t["columns"]:
            if not c["nullable"]:
                row = fresh(t, seeds[name])
                row[c["name"]] = None
                add(f"NOT_NULL:{name}:{c['name']}", insert(name, row), "23502")
    add("ROLLBACK:insert_caso", insert("caso", fresh(tables["caso"], seeds["caso"])), "00000")

    # Los dos IDs existen por separado, pero no forman el par referenciado.
    decision2 = fresh(tables["decision"], seeds["decision"], 2)
    step2 = fresh(tables["paso_simulacion"], seeds["paso_simulacion"], 2) | {"id_decision": 2}
    add("FK_PAIR:opcion_no_pertenece_decision", insert("decision", decision2)+"\n"+insert("paso_simulacion", step2), "23503")
    criterion2 = fresh(tables["criterio_rubrica"], seeds["criterio_rubrica"], 2)
    detail2 = fresh(tables["resultado_criterio"], seeds["resultado_criterio"], 2) | {"id_criterio": 2}
    add("FK_PAIR:nivel_no_pertenece_criterio", insert("criterio_rubrica", criterion2)+"\n"+insert("resultado_criterio", detail2), "23503")

    # Ambigüedades verificadas sin imponer políticas nuevas; todo se revierte.
    case2 = fresh(tables["caso"], seeds["caso"], 2)
    scene2 = fresh(tables["escena"], seeds["escena"], 2) | {"id_caso": 2}
    option2 = fresh(tables["opcion_respuesta"], seeds["opcion_respuesta"], 2) | {"id_escena_destino": 2}
    add("AMBIGUITY:destino_otro_caso", "\n".join([insert("caso", case2), insert("escena", scene2), insert("opcion_respuesta", option2)]), "00000")
    rub2 = fresh(tables["rubrica"], seeds["rubrica"], 2) | {"id_caso": 2}
    crit2 = fresh(tables["criterio_rubrica"], seeds["criterio_rubrica"], 2) | {"id_rubrica": 2}
    decision2 = fresh(tables["decision"], seeds["decision"], 2) | {"id_criterio": 2}
    add("AMBIGUITY:criterio_otro_caso", "\n".join([insert("caso", case2), insert("rubrica", rub2), insert("criterio_rubrica", crit2), insert("decision", decision2)]), "00000")
    person2 = fresh(tables["personaje"], seeds["personaje"], 2) | {"id_caso": 2}
    add("AMBIGUITY:personaje_otra_escena", "\n".join([insert("caso", case2), insert("personaje", person2),
        insert("personaje_escena", {"id_personaje": 2, "id_escena": 1})]), "00000")
    user2 = fresh(tables["usuario"], seeds["usuario"], 2)
    consent2 = fresh(tables["consentimiento"], seeds["consentimiento"], 2) | {"id_estudiante": 2}
    attempt2 = fresh(tables["intento"], seeds["intento"], 2) | {"id_consentimiento": 2, "numero_intento": 2}
    add("AMBIGUITY:consentimiento_ajeno_y_repeticion", "\n".join([insert("usuario", user2), insert("consentimiento", consent2), insert("intento", attempt2)]), "00000")
    step2 = fresh(tables["paso_simulacion"], seeds["paso_simulacion"], 2)
    add("AMBIGUITY:decision_repetida_en_intento", insert("paso_simulacion", step2), "00000")
    return tests


INVENTORY = r"""
SELECT json_build_object(
 'all_user_tables',(SELECT json_agg(json_build_object('schema',n.nspname,'table',r.relname) ORDER BY n.nspname,r.relname)
 FROM pg_class r JOIN pg_namespace n ON n.oid=r.relnamespace
 WHERE r.relkind IN ('r','p','f') AND n.nspname <> 'information_schema' AND n.nspname !~ '^pg_'),
 'tables', (SELECT json_agg(table_name ORDER BY table_name) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE'),
 'columns', (SELECT json_agg(row_to_json(x)) FROM (
 SELECT table_name,column_name,ordinal_position,is_nullable,data_type,udt_name,
 character_maximum_length,numeric_precision,numeric_scale,column_default,is_identity,identity_generation
 FROM information_schema.columns WHERE table_schema='public' ORDER BY table_name,ordinal_position) x),
 'constraints', (SELECT json_agg(json_build_object(
 'table',r.relname,'name',c.conname,'type',c.contype,'definition',pg_get_constraintdef(c.oid),
 'columns',(SELECT json_agg(a.attname ORDER BY k.n) FROM unnest(c.conkey) WITH ORDINALITY k(attnum,n) JOIN pg_attribute a ON a.attrelid=c.conrelid AND a.attnum=k.attnum),
 'target',p.relname,'target_columns',(SELECT json_agg(a.attname ORDER BY k.n) FROM unnest(c.confkey) WITH ORDINALITY k(attnum,n) JOIN pg_attribute a ON a.attrelid=c.confrelid AND a.attnum=k.attnum),
 'match',c.confmatchtype,'update',c.confupdtype,'delete',c.confdeltype,'validated',c.convalidated,'deferrable',c.condeferrable))
 FROM pg_constraint c JOIN pg_class r ON r.oid=c.conrelid JOIN pg_namespace n ON n.oid=r.relnamespace
 LEFT JOIN pg_class p ON p.oid=c.confrelid WHERE n.nspname='public'),
 'indexes',(SELECT json_agg(row_to_json(x)) FROM (SELECT tablename,indexname,indexdef FROM pg_indexes WHERE schemaname='public' ORDER BY tablename,indexname) x),
 'user_triggers',(SELECT count(*) FROM pg_trigger g JOIN pg_class r ON r.oid=g.tgrelid JOIN pg_namespace n ON n.oid=r.relnamespace WHERE n.nspname='public' AND NOT g.tgisinternal)
);
"""


def validate_inventory(model, inv):
    errors = []
    all_tables = inv["all_user_tables"] or []
    if len(all_tables) != 28 or {(t["schema"],t["table"]) for t in all_tables} != {("public",n) for n in model}:
        errors.append("Tablas de usuario adicionales/faltantes en cualquier schema")
    if set(inv["tables"]) != set(model) or len(inv["tables"]) != 28:
        errors.append("Inventario de tablas")
    if len(inv["columns"]) != 144:
        errors.append("Inventario de columnas")
    for name, t in model.items():
        actual = [c for c in inv["columns"] if c["table_name"] == name]
        if [c["column_name"] for c in actual] != [c["name"] for c in t["columns"]]:
            errors.append("Columnas/orden: " + name)
            continue
        for c, a in zip(t["columns"], actual):
            label = name + "." + c["name"]
            if (a["is_nullable"] == "YES") != c["nullable"]:
                errors.append("NULL: " + label)
            typ = c["type"]
            expected = "int4" if typ == "int" else ("varchar" if typ.startswith("varchar") else ("numeric" if typ.startswith("decimal") else ("bool" if typ == "boolean" else typ)))
            if a["udt_name"] != expected:
                errors.append("Tipo: " + label)
            if typ.startswith("varchar") and a["character_maximum_length"] != int(typ[8:-1]):
                errors.append("Longitud: " + label)
            if typ.startswith("decimal"):
                precision, scale = map(int, typ[8:-1].split(","))
                if (a["numeric_precision"], a["numeric_scale"]) != (precision, scale):
                    errors.append("Precision: " + label)
            if (a["is_identity"] == "YES") != c["increment"]:
                errors.append("Identity: " + label)
            if c["increment"] and a["identity_generation"] != "BY DEFAULT":
                errors.append("Generacion: " + label)
            d = a["column_default"]
            if c["default"] is None and d is not None:
                errors.append("Default inesperado: " + label)
            if c["default"] is not None:
                normalized = d.split("::", 1)[0].strip("()") if d else d
                if normalized != c["default"]:
                    errors.append("Default distinto: " + label)
        cs = [c for c in inv["constraints"] if c["table"] == name]
        if [c["columns"] for c in cs if c["type"] == "p"] != [t["pk"]]:
            errors.append("PK: " + name)
        if sorted(c["columns"] for c in cs if c["type"] == "u") != sorted(t["unique"]):
            errors.append("UNIQUE: " + name)
        fs = [c for c in cs if c["type"] == "f"]
        signature = lambda f: (tuple(f["columns"]), f["target"], tuple(f["target_columns"]))
        if sorted(map(signature, fs)) != sorted(map(signature, t["fk"])):
            errors.append("FK: " + name)
        if any(c["type"] not in ("p", "u", "f") or not c["validated"] or c["deferrable"] for c in cs):
            errors.append("Restriccion adicional/diferente: " + name)
        if any(f["match"] != "s" or f["update"] != "a" or f["delete"] != "a" for f in fs):
            errors.append("Acciones FK distintas: " + name)
    expected_indexes = {"pk_" + n for n in model}
    expected_indexes.update(f"uq_{n}_{i}" for n, t in model.items() for i in range(1, len(t["unique"])+1))
    if {i["indexname"] for i in inv["indexes"]} != expected_indexes or len(inv["indexes"]) != 47:
        errors.append("Indices")
    if inv["user_triggers"] != 0:
        errors.append("Triggers adicionales")
    return errors


class Lab:
    def __init__(self):
        self.cid = None
        self.secret = secrets.token_urlsafe(32)
        self.name = "sps-er28-lab-" + uuid.uuid4().hex
        self.proof = {}
    def docker(self, *args, input=None, timeout=30):
        env = os.environ.copy()
        env["POSTGRES_PASSWORD"] = self.secret
        env["PGPASSWORD"] = self.secret
        return subprocess.run(["docker", *args], input=input, text=True, encoding="utf-8",
                              errors="replace", capture_output=True, timeout=timeout, env=env)
    def sql(self, text, check=True):
        if not self.proof.get("isolated"):
            raise RuntimeError("No ejecutar SQL sin demostrar aislamiento")
        p = self.docker("exec", "--env", "PGPASSWORD", "-i", self.cid,
                        "psql", "-X", "-q", "-A", "-t", "-v", "ON_ERROR_STOP=1",
                        "-v", "VERBOSITY=verbose", "-h", "127.0.0.1", "-U", USER, "-d", DB,
                        input=text, timeout=60)
        if check and p.returncode:
            raise RuntimeError(p.stderr.replace(self.secret, "<redactado>"))
        return p
    def start(self):
        p = self.docker("image", "inspect", "postgres:17")
        if p.returncode:
            raise RuntimeError("Imagen postgres:17 no disponible; no hacer pull automatico")
        self.proof["image_id"] = json.loads(p.stdout)[0]["Id"]
        p = self.docker("create", "--name", self.name, "--label", "sps.er28.experiment=true",
                        "--network", "none", "--tmpfs", "/var/lib/postgresql/data",
                        "--env", "POSTGRES_DB="+DB, "--env", "POSTGRES_USER="+USER,
                        "--env", "POSTGRES_PASSWORD", "postgres:17")
        if p.returncode:
            raise RuntimeError(p.stderr.replace(self.secret, "<redactado>"))
        self.cid = p.stdout.strip()
        if not __import__("re").fullmatch("[0-9a-f]{64}", self.cid):
            self.cid = None
            raise RuntimeError("ID invalido: no se opera un identificador ambiguo")
        self.proof["container_id"] = self.cid
        self.proof["name"] = self.name
        if self.docker("start", self.cid).returncode:
            raise RuntimeError("Fallo al iniciar contenedor propio")
        data = json.loads(self.docker("inspect", self.cid).stdout)[0]
        isolated = (data["Id"] == self.cid and data["Name"] == "/" + self.name
                    and data["Config"]["Labels"].get("sps.er28.experiment") == "true"
                    and data["HostConfig"]["NetworkMode"] == "none"
                    and not data["HostConfig"].get("PortBindings")
                    and not data["HostConfig"].get("Binds")
                    and set((data["HostConfig"].get("Tmpfs") or {}).keys()) == {"/var/lib/postgresql/data"}
                    and all(m["Type"] == "tmpfs" for m in data["Mounts"])
                    and data["Config"]["Image"] == "postgres:17")
        self.proof.update(isolated=bool(isolated), network="none", published_ports=[],
                          tmpfs_configuration=data["HostConfig"].get("Tmpfs"),
                          mounts=[{"type": m["Type"], "destination": m["Destination"]} for m in data["Mounts"]])
        if not isolated:
            raise RuntimeError("Aislamiento no demostrado")
        mount = self.docker("exec", self.cid, "cat", "/proc/self/mountinfo")
        data_mounts = [line for line in mount.stdout.splitlines() if len(line.split()) > 4
                       and line.split()[4] == "/var/lib/postgresql/data"]
        verified_mount = mount.returncode == 0 and len(data_mounts) == 1 and data_mounts[0].split(" - ")[1].split()[0] == "tmpfs"
        self.proof["data_mount_tmpfs_verified"] = verified_mount
        if not verified_mount:
            self.proof["isolated"] = False
            raise RuntimeError("Montaje real de datos no demostrado como tmpfs")
        until = time.monotonic() + 60
        while time.monotonic() < until:
            p = self.sql("SELECT json_build_object('database',current_database(),'user',current_user,'version',current_setting('server_version_num'));", check=False)
            if p.returncode == 0:
                identity = json.loads(p.stdout)
                if identity["database"] != DB or identity["user"] != USER or not 170000 <= int(identity["version"]) < 180000:
                    raise RuntimeError("Identidad PostgreSQL inesperada")
                self.proof["postgresql"] = identity
                return
            time.sleep(.2)
        raise RuntimeError("PostgreSQL TCP no disponible dentro del contenedor propio")
    def cleanup(self):
        if self.cid is None:
            self.proof["cleanup"] = "not_created"
            return
        before = self.docker("inspect", self.cid)
        if before.returncode:
            self.proof["cleanup"] = "unverified"
            raise RuntimeError("No se puede verificar contenedor antes de limpiar")
        data = json.loads(before.stdout)[0]
        if data["Id"] != self.cid or data["Name"] != "/"+self.name or data["Config"]["Labels"].get("sps.er28.experiment") != "true":
            raise RuntimeError("No se elimina un contenedor sin propiedad demostrada")
        result = self.docker("rm", "--force", self.cid)
        after = self.docker("inspect", self.cid)
        self.proof["remove_exit_code"] = result.returncode
        self.proof["inspect_after_exit_code"] = after.returncode
        self.proof["cleanup"] = "removed_verified" if result.returncode == 0 and after.returncode != 0 and "No such" in after.stderr else "unverified"
        if self.proof["cleanup"] != "removed_verified":
            raise RuntimeError("Eliminacion no demostrada")


def main():
    model = load()  # Preflight antes de cualquier Docker/SQL.
    generated = build(model)
    sqlpath = HERE / "er28_experimental.sql"
    if not sqlpath.exists() or sqlpath.read_text(encoding="utf-8") != generated:
        raise RuntimeError("Preparar y revisar SQL con schema_support.py antes del experimento")
    runid = uuid.uuid4().hex
    evidence = {"source_sha256": EXPECTED_SHA, "counts_source": counts(model), "run_id": runid}
    evidence["artifact_sha256"] = {n: hashlib.sha256((HERE/n).read_bytes()).hexdigest()
                                   for n in ("schema_support.py", "run_experiment.py", "er28_experimental.sql")}
    lab = Lab()
    failure = None
    try:
        lab.start()
        initial = json.loads(lab.sql(INVENTORY).stdout)
        if initial["tables"] or initial["all_user_tables"]:
            raise RuntimeError("Base del laboratorio no vacia")
        lab.sql(generated)
        inv = json.loads(lab.sql(INVENTORY).stdout)
        errors = validate_inventory(model, inv)
        evidence["inventory"] = inv
        evidence["inventory_errors"] = errors
        if errors:
            raise RuntimeError("Diferencias estructurales: " + repr(errors))
        seeds = {n: row_for(t) for n, t in model.items()}
        lab.sql("BEGIN;\n" + "\n".join(insert(n, seeds[n]) for n in order(model)) + "\nCOMMIT;")
        tests = probes(model, seeds)
        batch = ["\\set ON_ERROR_STOP off", "BEGIN;"]
        for t in tests:
            batch += ["SAVEPOINT probe;", t["sql"], "\\set observed :SQLSTATE",
                      "ROLLBACK TO SAVEPOINT probe;", "RELEASE SAVEPOINT probe;",
                      "SELECT json_build_object('id', "+literal(t["id"])+", 'state', :'observed');"]
        batch.append("ROLLBACK;")
        result = lab.sql("\n".join(batch))
        actual = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
        if len(actual) != len(tests) or [r["id"] for r in actual] != [t["id"] for t in tests]:
            raise RuntimeError("Resultados de pruebas incompletos")
        evidence["tests"] = [{k: v for k, v in t.items() if k != "sql"} | {"actual": r["state"], "passed": r["state"] == t["expected"]}
                             for t, r in zip(tests, actual)]
        evidence["expected_error_log_tail"] = result.stderr.replace(lab.secret, "<redactado>")[-6000:]
        final_counts = json.loads(lab.sql("SELECT json_build_object(" + ", ".join(literal(n)+", (SELECT count(*) FROM "+quoted(n)+")" for n in model) + ");").stdout)
        evidence["rows_after_rollback"] = final_counts
        evidence["rollback_preserved_all_seed_rows"] = all(n == 1 for n in final_counts.values())
        evidence["inventory_after_tests_unchanged"] = json.loads(lab.sql(INVENTORY).stdout) == inv
        if not all(t["passed"] for t in evidence["tests"]) or not evidence["rollback_preserved_all_seed_rows"] or not evidence["inventory_after_tests_unchanged"]:
            raise RuntimeError("Prueba fallida: revisar evidencia sin alterar ER")
        evidence["status"] = "passed"
    except BaseException as error:
        failure = error
        evidence["status"] = "failed"
        evidence["error"] = str(error).replace(lab.secret, "<redactado>")
    finally:
        try:
            lab.cleanup()
        except BaseException as error:
            evidence["cleanup_error"] = str(error).replace(lab.secret, "<redactado>")
            evidence["status"] = "failed"
            failure = failure or error
        evidence["laboratory"] = lab.proof
        dest = HERE / ("evidencia_" + runid + ".json")
        dest.write_text(json.dumps(evidence, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        print(json.dumps({"status": evidence["status"], "evidence": dest.name,
                          "container": lab.cid, "cleanup": lab.proof.get("cleanup"),
                          "tests": len(evidence.get("tests", []))}, ensure_ascii=False), flush=True)
    if failure:
        raise SystemExit(evidence.get("error", evidence.get("cleanup_error", "Experimento fallido")))


if __name__ == "__main__":
    main()
