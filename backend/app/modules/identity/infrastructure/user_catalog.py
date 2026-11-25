"""Lectura agrupada de los detalles del directorio administrativo."""

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import batched
from uuid import UUID

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.modules.identity.infrastructure.academic_identity_models import IdentidadAcademicaORM
from app.modules.identity.infrastructure.models import PermisoORM, RolPermisoORM, UsuarioORM, UsuarioPermisoORM
from app.modules.identity.infrastructure.onboarding_models import VerificacionPrimerIngresoORM


@dataclass(frozen=True)
class DetallesUsuario:
    permisos_rol: list[str]
    permisos_individuales: dict[str, bool]
    permisos_efectivos: list[str]
    identidad_cases: UUID | None
    identidad_scheduling: UUID | None
    primer_ingreso_verificado: bool


def cargar_detalles_usuarios(db: Session, usuarios: Sequence[UsuarioORM]) -> dict[int, DetallesUsuario]:
    if not usuarios:
        return {}

    roles = {usuario.id_rol for usuario in usuarios}
    permisos_por_rol: dict[int, set[str]] = defaultdict(set)
    for id_rol, codigo in db.execute(
        select(RolPermisoORM.id_rol, PermisoORM.codigo)
        .join(PermisoORM, PermisoORM.id_permiso == RolPermisoORM.id_permiso)
        .where(RolPermisoORM.id_rol.in_(roles))
    ):
        permisos_por_rol[id_rol].add(codigo)

    verificacion_disponible = db.get_bind().dialect.name != "sqlite" or inspect(db.connection()).has_table(
        VerificacionPrimerIngresoORM.__tablename__
    )
    detalles = {}
    # Acotar los parámetros incluso en la ruta histórica sin paginar.
    for lote in batched(usuarios, 500):
        ids = [usuario.id_usuario for usuario in lote]
        permisos_por_usuario: dict[int, dict[str, bool]] = defaultdict(dict)
        for id_usuario, codigo, concedido in db.execute(
            select(UsuarioPermisoORM.id_usuario, PermisoORM.codigo, UsuarioPermisoORM.concedido)
            .join(PermisoORM, PermisoORM.id_permiso == UsuarioPermisoORM.id_permiso)
            .where(UsuarioPermisoORM.id_usuario.in_(ids))
        ):
            permisos_por_usuario[id_usuario][codigo] = concedido

        identidades: dict[int, dict[str, UUID]] = defaultdict(dict)
        for id_usuario, sistema, id_academico in db.execute(
            select(IdentidadAcademicaORM.id_usuario, IdentidadAcademicaORM.sistema, IdentidadAcademicaORM.id_academico)
            .where(IdentidadAcademicaORM.id_usuario.in_(ids))
            .order_by(IdentidadAcademicaORM.id_usuario, IdentidadAcademicaORM.sistema, IdentidadAcademicaORM.id_academico)
        ):
            identidades[id_usuario].setdefault(sistema, id_academico)

        verificacion = {}
        if verificacion_disponible:
            verificacion = dict(db.execute(
                select(VerificacionPrimerIngresoORM.id_usuario, VerificacionPrimerIngresoORM.verificado)
                .where(VerificacionPrimerIngresoORM.id_usuario.in_(ids))
            ).tuples().all())

        for usuario in lote:
            id_usuario = usuario.id_usuario
            permisos_rol = permisos_por_rol[usuario.id_rol]
            individuales = permisos_por_usuario.get(id_usuario, {})
            efectivos = (permisos_rol - individuales.keys()) | {
                codigo for codigo, concedido in individuales.items() if concedido
            }
            detalles[id_usuario] = DetallesUsuario(
                permisos_rol=sorted(permisos_rol),
                permisos_individuales=individuales,
                permisos_efectivos=sorted(efectivos),
                identidad_cases=identidades[id_usuario].get("CASES"),
                identidad_scheduling=identidades[id_usuario].get("SCHEDULING"),
                primer_ingreso_verificado=verificacion.get(id_usuario, True),
            )
    return detalles
