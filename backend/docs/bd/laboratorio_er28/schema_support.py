"""Conversión estricta del subconjunto DBML oficial; sin importar el backend."""
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SOURCE = ROOT / "app/modules/identity/reference/sps.dbml"
EXPECTED_SHA = "fb6ab07cfdfee38ba59e1acc879335ec0b377150acc3474b4a817a9eece229d7"


def endpoint(text):
    table, fields = text.strip().split(".", 1)
    return table, [c.strip() for c in fields.strip("()").split(",")]


def load():
    raw = SOURCE.read_bytes()
    if hashlib.sha256(raw).hexdigest() != EXPECTED_SHA:
        raise ValueError("La fuente no coincide con el ER verificado; detener y revisar.")
    source = raw.decode("utf-8").replace("\r\n", "\n")
    tables = {}
    for name, body in re.findall(r"^Table (\w+) \{\n(.*?)^\}", source, re.M | re.S):
        if name in tables:
            raise ValueError("Tabla duplicada")
        t = {"name": name, "columns": [], "pk": [], "unique": [], "fk": []}
        in_indexes = False
        for line in body.splitlines():
            line = line.strip()
            if not line or line.startswith("//"):
                continue
            if line == "indexes {":
                in_indexes = True
                continue
            if in_indexes:
                if line == "}":
                    in_indexes = False
                    continue
                match = re.fullmatch(r"\(([^)]+)\) \[(pk|unique)\]", line)
                if not match:
                    raise ValueError("Indice no soportado: " + line)
                cols = [c.strip() for c in match[1].split(",")]
                if match[2] == "pk":
                    if t["pk"]:
                        raise ValueError("PK duplicada")
                    t["pk"] = cols
                else:
                    t["unique"].append(cols)
                continue
            m = re.fullmatch(r"(\w+) (int|varchar\(\d+\)|decimal\(\d+,\d+\)|text|boolean|timestamp)(?: \[(.*)\])?", line)
            if not m:
                raise ValueError("Declaracion no soportada: " + line)
            field, typ, opts = m.groups()
            opts = opts or ""
            # Comas dentro de la FK no existen en flags de esta fuente.
            flags = [f.strip() for f in opts.split(",")] if opts else []
            valid = {"pk", "increment", "not null", "unique"}
            for flag in flags:
                if flag not in valid and not re.fullmatch(r"default: (true|false|\d+|'[^']*')|ref: > \w+\.\w+", flag):
                    raise ValueError("Flag no soportado: " + flag)
            default = next((f[9:] for f in flags if f.startswith("default: ")), None)
            c = {"name": field, "type": typ, "nullable": "not null" not in flags and "pk" not in flags,
                 "increment": "increment" in flags, "default": default}
            t["columns"].append(c)
            if "pk" in flags:
                if t["pk"]:
                    raise ValueError("PK duplicada")
                t["pk"] = [field]
            if "unique" in flags:
                t["unique"].append([field])
            for f in flags:
                if f.startswith("ref: > "):
                    parent, fields = endpoint(f[7:])
                    t["fk"].append({"columns": [field], "target": parent, "target_columns": fields})
        tables[name] = t
    for child, parent in re.findall(r"^Ref:\s*(.*?)\s*>\s*(.*?)\s*$", source, re.M):
        table, cols = endpoint(child)
        target, target_cols = endpoint(parent)
        tables[table]["fk"].append({"columns": cols, "target": target, "target_columns": target_cols})
    for t in tables.values():
        if not t["pk"]:
            raise ValueError("Tabla sin PK")
        fields = [c["name"] for c in t["columns"]]
        if len(fields) != len(set(fields)):
            raise ValueError("Columna duplicada")
        for c in t["columns"]:
            if c["name"] in t["pk"]:
                c["nullable"] = False
        for k in [t["pk"], *t["unique"]]:
            if not set(k) <= set(fields):
                raise ValueError("Clave inexistente")
        for f in t["fk"]:
            p = tables[f["target"]]
            if f["target_columns"] not in [p["pk"], *p["unique"]]:
                raise ValueError("FK sin clave candidata")
            if len(f["columns"]) != len(f["target_columns"]):
                raise ValueError("Aridad FK")
            for a, b in zip(f["columns"], f["target_columns"]):
                if next(c["type"] for c in t["columns"] if c["name"] == a) != next(c["type"] for c in p["columns"] if c["name"] == b):
                    raise ValueError("Tipo FK incompatible")
    totals = counts(tables)
    if totals != {"tables": 28, "columns": 144, "pk": 28, "fk": 40, "unique": 19}:
        raise ValueError("Conteo diferente: " + repr(totals))
    return tables


def counts(tables):
    return {"tables": len(tables), "columns": sum(len(t["columns"]) for t in tables.values()),
            "pk": sum(bool(t["pk"]) for t in tables.values()),
            "fk": sum(len(t["fk"]) for t in tables.values()),
            "unique": sum(len(t["unique"]) for t in tables.values())}


def order(tables):
    result = []
    while len(result) < len(tables):
        ready = [n for n, t in tables.items() if n not in result and {f["target"] for f in t["fk"]} <= set(result)]
        if not ready:
            raise ValueError("Dependencias ciclicas/no resueltas; detener.")
        result.extend(ready)
    return result


def quoted(name):
    if not re.fullmatch(r"[a-z_][a-z_0-9]*", name):
        raise ValueError("Identificador no soportado")
    return '"' + name + '"'


def fields(names):
    return ", ".join(quoted(n) for n in names)


def sql_type(typ):
    if typ == "int":
        return "INTEGER"
    if typ == "timestamp":
        return "TIMESTAMP WITHOUT TIME ZONE"
    return typ.upper().replace("DECIMAL", "NUMERIC")


def build(tables):
    lines = ["-- EXPERIMENTAL BD2-02B. NO MIGRACION DEL BACKEND.",
             "-- Fuente SHA256: " + EXPECTED_SHA,
             "-- 28 tablas, 144 columnas, 28 PK, 40 FK, 19 UNIQUE.",
             "BEGIN;"]
    for name in order(tables):
        t = tables[name]
        declarations = []
        for c in t["columns"]:
            d = quoted(c["name"]) + " " + sql_type(c["type"])
            if c["increment"]:
                d += " GENERATED BY DEFAULT AS IDENTITY"
            if not c["nullable"]:
                d += " NOT NULL"
            if c["default"] is not None:
                d += " DEFAULT " + c["default"]
            declarations.append(d)
        declarations.append("CONSTRAINT " + quoted("pk_" + name) + " PRIMARY KEY (" + fields(t["pk"]) + ")")
        for i, cols in enumerate(t["unique"], 1):
            declarations.append("CONSTRAINT " + quoted(f"uq_{name}_{i}") + " UNIQUE (" + fields(cols) + ")")
        for i, f in enumerate(t["fk"], 1):
            declarations.append("CONSTRAINT " + quoted(f"fk_{name}_{i}") + " FOREIGN KEY (" + fields(f["columns"]) +
                                ") REFERENCES " + quoted(f["target"]) + " (" + fields(f["target_columns"]) + ")")
        lines.append("CREATE TABLE " + quoted(name) + " (\n  " + ",\n  ".join(declarations) + "\n);")
    lines.append("COMMIT;")
    return "\n\n".join(lines) + "\n"


if __name__ == "__main__":
    tables = load()
    sql = build(tables)
    dest = HERE / "er28_experimental.sql"
    if dest.exists() and dest.read_text(encoding="utf-8") != sql:
        raise SystemExit("SQL existente difiere; revisar, no sobrescribir.")
    dest.write_text(sql, encoding="utf-8")
    print(json.dumps(counts(tables)))
