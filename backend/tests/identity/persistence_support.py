"""Laboratorio aislado; los esquemas externos se leen del DBML, solo para tests."""

from pathlib import Path
import re

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, MetaData, Numeric, String, Table, Text, UniqueConstraint, text

from app.modules.identity.infrastructure.models import PermisoORM, RolORM, RolPermisoORM, UsuarioORM


BACKEND = Path(__file__).resolve().parents[2]
DBML = BACKEND / "app/modules/identity/reference/sps.dbml"
ACCESS_TABLES = (RolORM.__table__, PermisoORM.__table__, RolPermisoORM.__table__, UsuarioORM.__table__)


def bloque_dbml(nombre):
    return re.search(r"Table " + re.escape(nombre) + r" \{(.*?)\n\}", DBML.read_text(encoding="utf-8"), re.S).group(1)


def columnas_dbml(nombre):
    return re.findall(r"^  (\w+) (int|varchar|text|boolean|timestamp|decimal)(?:\(([^)]+)\))?(?: \[([^\]]+)\])?\s*$",
                      bloque_dbml(nombre), re.M)


def tablas_academicas_prueba(engine):
    """Solo el subconjunto literal de DBML necesario; nunca en Base.metadata."""
    metadata = MetaData()
    for tabla in ACCESS_TABLES:
        tabla.to_metadata(metadata)
    nombres = ("grupo_academico", "grupo_estudiante", "caso", "asignacion_caso", "participacion",
               "resultado_participacion", "permiso_intento_extra", "retroalimentacion_docente")
    for nombre in nombres:
        columnas = []
        for campo, tipo, tamanio, flags in columnas_dbml(nombre):
            tipos = {"int": Integer, "text": Text, "boolean": Boolean, "timestamp": DateTime}
            if tipo == "varchar":
                tipo_sql = String(int(tamanio))
            elif tipo == "decimal":
                tipo_sql = Numeric(*map(int, tamanio.split(",")))
            else:
                tipo_sql = tipos[tipo]()
            parametros = {"primary_key": "pk" in flags, "nullable": "not null" not in flags and "pk" not in flags}
            if "increment" in flags:
                parametros["autoincrement"] = True
            if "unique" in flags:
                parametros["unique"] = True
            default = re.search(r"default: ([^,\]]+)", flags)
            if default:
                parametros["server_default"] = text(default.group(1))
            fk = re.search(r"ref: > ([\w.]+)", flags)
            argumentos = [ForeignKey(fk.group(1))] if fk else []
            columnas.append(Column(campo, tipo_sql, *argumentos, **parametros))
        unicas = [UniqueConstraint(*(c.strip() for c in lista.split(",")))
                  for lista in re.findall(r"\(([^)]+)\) \[unique\]", bloque_dbml(nombre))]
        Table(nombre, metadata, *columnas, *unicas)
    metadata.create_all(engine)
    return metadata.tables
