"""Rutas administrativas para gestión integral de usuarios, roles, permisos e identidades (RF-03)."""

from collections.abc import Callable, Sequence
from typing import Annotated, Literal
from uuid import UUID, uuid4
import secrets

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session, load_only

from app.db.session import get_db
from app.modules.identity.api.dependencies import obtener_notificador_negocio, obtener_usuario_actual
from app.modules.identity.application.authorization import ServicioAutorizacion
from app.modules.identity.domain.entities import ContextoAcceso, Rol, normalizar_correo
from app.modules.identity.domain.errors import AccesoDenegado, ReglaIdentidadInvalida
from app.modules.identity.infrastructure.academic_identity_models import IdentidadAcademicaORM
from app.modules.identity.infrastructure.business_notifications import notificar_registro_usuario
from app.modules.identity.infrastructure.credentials import obtener_hasheador
from app.modules.identity.infrastructure.models import PermisoORM, RolORM, RolPermisoORM, UsuarioORM, UsuarioPermisoORM
from app.modules.identity.infrastructure.onboarding import registrar_estado_primer_ingreso
from app.modules.identity.infrastructure.repositories import RepositorioUsuariosSQLAlchemy, id_entero
from app.modules.identity.infrastructure.user_catalog import DetallesUsuario, cargar_detalles_usuarios


router = APIRouter(tags=["identity-admin"])

UsuarioActual = Annotated[ContextoAcceso, Depends(obtener_usuario_actual)]
BaseDatos = Annotated[Session, Depends(get_db)]
NotificadorNegocio = Annotated[Callable[..., None] | None, Depends(obtener_notificador_negocio)]


def _exigir_admin(usuario: ContextoAcceso) -> None:
    try:
        ServicioAutorizacion.exigir_rol(usuario, Rol.ADMINISTRADOR)
    except AccesoDenegado:
        raise HTTPException(403, detail="Operación reservada para administradores.") from None


class UsuarioGestionItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id_usuario: str
    nombre: str
    correo: str
    rol: str
    activo: bool
    permisos_rol: list[str]
    permisos_individuales: dict[str, bool]
    permisos_efectivos: list[str]
    identidad_cases: UUID | None = None
    identidad_scheduling: UUID | None = None
    primer_ingreso_verificado: bool = True


class CatalogoUsuariosRespuesta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    usuarios: list[UsuarioGestionItem]
    permisos_disponibles: list[str]
    roles_disponibles: list[str]


class PaginaUsuariosRespuesta(CatalogoUsuariosRespuesta):
    total: int
    activos: int
    filtrados: int
    pagina: int


class CrearUsuarioAdminSolicitud(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: Annotated[str, Field(min_length=2, max_length=120)]
    correo: Annotated[str, Field(min_length=3, max_length=254)]
    rol: Literal["ADMINISTRADOR", "DOCENTE", "ESTUDIANTE"]
    clave: Annotated[SecretStr | None, Field(min_length=6, max_length=1024)] = None
    activo: bool = True
    permisos_individuales: dict[str, bool] = Field(default_factory=dict)
    crear_identidades_academicas: bool = True


class ActualizarUsuarioAdminSolicitud(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: Annotated[str | None, Field(min_length=2, max_length=120)] = None
    correo: Annotated[str | None, Field(min_length=3, max_length=254)] = None
    rol: Literal["ADMINISTRADOR", "DOCENTE", "ESTUDIANTE"] | None = None
    activo: bool | None = None
    clave: Annotated[SecretStr | None, Field(min_length=6, max_length=1024)] = None
    permisos_individuales: dict[str, bool] | None = None
    primer_ingreso_verificado: bool | None = None


def _representar_usuario(usuario: UsuarioORM, rol: str, detalles: DetallesUsuario) -> UsuarioGestionItem:
    return UsuarioGestionItem(
        id_usuario=str(usuario.id_usuario),
        nombre=usuario.nombre,
        correo=usuario.correo,
        rol=rol,
        activo=bool(usuario.activo),
        permisos_rol=detalles.permisos_rol,
        permisos_individuales=detalles.permisos_individuales,
        permisos_efectivos=detalles.permisos_efectivos,
        identidad_cases=detalles.identidad_cases,
        identidad_scheduling=detalles.identidad_scheduling,
        primer_ingreso_verificado=detalles.primer_ingreso_verificado,
    )


def _serializar_usuario(db: Session, usuario: UsuarioORM) -> UsuarioGestionItem:
    rol = db.get(RolORM, usuario.id_rol)
    detalles = cargar_detalles_usuarios(db, [usuario])
    return _representar_usuario(usuario, rol.nombre.strip().upper() if rol else "DESCONOCIDO",
                               detalles[usuario.id_usuario])


def _asegurar_identidades(db: Session, id_usuario: int) -> tuple[UUID, UUID]:
    existentes = db.scalars(
        select(IdentidadAcademicaORM).where(IdentidadAcademicaORM.id_usuario == id_usuario)
    ).all()
    mapa = {v.sistema: v.id_academico for v in existentes}
    for sistema in ("CASES", "SCHEDULING"):
        if sistema not in mapa:
            nuevo_uuid = uuid4()
            db.add(IdentidadAcademicaORM(sistema=sistema, id_academico=nuevo_uuid, id_usuario=id_usuario))
            mapa[sistema] = nuevo_uuid
    db.flush()
    return mapa["CASES"], mapa["SCHEDULING"]


def _aplicar_permisos_individuales(db: Session, id_usuario: int, mapa_permisos: dict[str, bool]) -> None:
    db.execute(delete(UsuarioPermisoORM).where(UsuarioPermisoORM.id_usuario == id_usuario))
    if not mapa_permisos:
        return
    codigos = set(mapa_permisos.keys())
    filas = db.execute(
        select(PermisoORM.id_permiso, PermisoORM.codigo).where(PermisoORM.codigo.in_(codigos))
    ).all()
    por_codigo = {codigo: id_permiso for id_permiso, codigo in filas}
    if len(por_codigo) != len(codigos):
        faltantes = sorted(codigos - set(por_codigo.keys()))
        raise HTTPException(422, detail=f"Permisos desconocidos: {', '.join(faltantes)}")
    for codigo, concedido in mapa_permisos.items():
        db.add(UsuarioPermisoORM(id_usuario=id_usuario, id_permiso=por_codigo[codigo], concedido=concedido))


def _catalogo_usuarios(db: Session, usuarios_orm: Sequence[UsuarioORM]) -> CatalogoUsuariosRespuesta:
    permisos_disp = list(db.scalars(select(PermisoORM.codigo).order_by(PermisoORM.codigo)).all())
    roles = {r.id_rol: r.nombre.strip().upper() for r in db.scalars(select(RolORM)) if r.nombre and r.nombre.strip()}
    detalles = cargar_detalles_usuarios(db, usuarios_orm)
    return CatalogoUsuariosRespuesta(
        usuarios=[_representar_usuario(u, roles.get(u.id_rol, "DESCONOCIDO"), detalles[u.id_usuario])
                  for u in usuarios_orm],
        permisos_disponibles=permisos_disp,
        roles_disponibles=sorted(set(roles.values())) or ["ADMINISTRADOR", "DOCENTE", "ESTUDIANTE"],
    )


def _consulta_directorio():
    return select(UsuarioORM).options(load_only(
        UsuarioORM.id_usuario, UsuarioORM.id_rol, UsuarioORM.nombre, UsuarioORM.correo, UsuarioORM.activo,
    ))


@router.get("/usuarios", response_model=CatalogoUsuariosRespuesta)
def listar_usuarios_admin(usuario: UsuarioActual, db: BaseDatos) -> CatalogoUsuariosRespuesta:
    _exigir_admin(usuario)
    return _catalogo_usuarios(db, db.scalars(_consulta_directorio().order_by(UsuarioORM.id_usuario)).all())


@router.get("/usuarios/pagina", response_model=PaginaUsuariosRespuesta)
def paginar_usuarios_admin(
    usuario: UsuarioActual,
    db: BaseDatos,
    pagina: Annotated[int, Query(ge=0)] = 0,
    tamano: Annotated[int, Query(ge=1, le=50)] = 12,
    buscar: Annotated[str, Query(max_length=254)] = "",
) -> PaginaUsuariosRespuesta:
    _exigir_admin(usuario)
    total, activos = db.execute(select(
        func.count(UsuarioORM.id_usuario),
        func.count(UsuarioORM.id_usuario).filter(UsuarioORM.activo.is_(True)),
    )).one()
    termino = buscar.strip()
    consulta = _consulta_directorio()
    filtrados = total
    if termino:
        filtro = or_(
            UsuarioORM.nombre.icontains(termino, autoescape=True),
            UsuarioORM.correo.icontains(termino, autoescape=True),
        )
        consulta = consulta.where(filtro)
        filtrados = db.scalar(select(func.count(UsuarioORM.id_usuario)).where(filtro)) or 0
    pagina = min(pagina, max(0, (filtrados - 1) // tamano))
    filas = db.scalars(consulta.order_by(
        func.lower(UsuarioORM.nombre), UsuarioORM.id_usuario,
    ).offset(pagina * tamano).limit(tamano)).all()
    return PaginaUsuariosRespuesta(
        **_catalogo_usuarios(db, filas).model_dump(),
        total=total, activos=activos, filtrados=filtrados, pagina=pagina,
    )


@router.post("/usuarios", response_model=UsuarioGestionItem, status_code=201)
def crear_usuario_admin(
    solicitud: CrearUsuarioAdminSolicitud,
    usuario_actual: UsuarioActual,
    db: BaseDatos,
    background_tasks: BackgroundTasks,
    notificador: NotificadorNegocio,
) -> UsuarioGestionItem:
    _exigir_admin(usuario_actual)
    try:
        correo = normalizar_correo(solicitud.correo)
    except ReglaIdentidadInvalida:
        raise HTTPException(422, detail="Correo institucional inválido.") from None

    if len(correo) > 200:
        raise HTTPException(422, detail="Correo demasiado largo.")

    repo = RepositorioUsuariosSQLAlchemy(db)
    if repo.obtener_por_correo(correo) is not None:
        raise HTTPException(409, detail="Ya existe una cuenta registrada con ese correo.")

    rol_orm = db.scalars(
        select(RolORM).where(func.upper(func.trim(RolORM.nombre)) == solicitud.rol)
    ).one_or_none()
    if rol_orm is None:
        raise HTTPException(422, detail=f"Rol no configurado en catálogo: {solicitud.rol}")

    if solicitud.rol in ("ADMINISTRADOR", "DOCENTE") and solicitud.clave is None:
        raise HTTPException(422, detail="Se requiere contraseña para cuentas de personal.")

    clave_plana = (
        solicitud.clave.get_secret_value()
        if solicitud.clave is not None
        else secrets.token_urlsafe(24)
    )
    clave_hash = obtener_hasheador().hash(clave_plana)

    nuevo = UsuarioORM(
        id_rol=rol_orm.id_rol,
        nombre=solicitud.nombre.strip(),
        correo=correo,
        clave_hash=clave_hash,
        activo=solicitud.activo,
    )
    db.add(nuevo)
    db.flush()

    if solicitud.permisos_individuales:
        _aplicar_permisos_individuales(db, nuevo.id_usuario, solicitud.permisos_individuales)

    if solicitud.crear_identidades_academicas and solicitud.rol in ("DOCENTE", "ESTUDIANTE"):
        _asegurar_identidades(db, nuevo.id_usuario)

    if solicitud.rol == "ESTUDIANTE":
        registrar_estado_primer_ingreso(db, id_usuario=nuevo.id_usuario, verificado=False)

    db.commit()
    db.refresh(nuevo)
    notificar_registro_usuario(
        correo=nuevo.correo,
        nombre=nuevo.nombre,
        rol=solicitud.rol,
        background_tasks=background_tasks,
        notificador=notificador,
    )
    return _serializar_usuario(db, nuevo)


@router.patch("/usuarios/{id_usuario}", response_model=UsuarioGestionItem)
def actualizar_usuario_admin(
    id_usuario: str,
    solicitud: ActualizarUsuarioAdminSolicitud,
    usuario_actual: UsuarioActual,
    db: BaseDatos,
) -> UsuarioGestionItem:
    _exigir_admin(usuario_actual)
    try:
        uid = id_entero(id_usuario)
    except ReglaIdentidadInvalida:
        raise HTTPException(422, detail="Identificador de usuario inválido.") from None

    objetivo = db.get(UsuarioORM, uid)
    if objetivo is None:
        raise HTTPException(404, detail="Usuario no encontrado.")

    es_mismo_admin = str(uid) == usuario_actual.id_usuario
    if es_mismo_admin:
        if solicitud.activo is False:
            raise HTTPException(409, detail="No puedes desactivar tu propia cuenta de administrador.")
        if solicitud.rol is not None and solicitud.rol != "ADMINISTRADOR":
            raise HTTPException(409, detail="No puedes revocar tu propio rol de administrador.")

    if solicitud.nombre is not None:
        objetivo.nombre = solicitud.nombre.strip()

    if solicitud.correo is not None:
        try:
            nuevo_correo = normalizar_correo(solicitud.correo)
        except ReglaIdentidadInvalida:
            raise HTTPException(422, detail="Correo inválido.") from None
        existente = RepositorioUsuariosSQLAlchemy(db).obtener_por_correo(nuevo_correo)
        if existente is not None and existente.id_usuario != str(uid):
            raise HTTPException(409, detail="El correo ya pertenece a otro usuario.")
        objetivo.correo = nuevo_correo

    if solicitud.rol is not None:
        rol_orm = db.scalars(
            select(RolORM).where(func.upper(func.trim(RolORM.nombre)) == solicitud.rol)
        ).one_or_none()
        if rol_orm is None:
            raise HTTPException(422, detail=f"Rol no configurado: {solicitud.rol}")
        objetivo.id_rol = rol_orm.id_rol
        if solicitud.rol in ("DOCENTE", "ESTUDIANTE"):
            _asegurar_identidades(db, uid)

    if solicitud.activo is not None:
        objetivo.activo = solicitud.activo

    if solicitud.clave is not None:
        objetivo.clave_hash = obtener_hasheador().hash(solicitud.clave.get_secret_value())

    if solicitud.permisos_individuales is not None:
        _aplicar_permisos_individuales(db, uid, solicitud.permisos_individuales)

    if solicitud.primer_ingreso_verificado is not None:
        registrar_estado_primer_ingreso(db, id_usuario=uid, verificado=solicitud.primer_ingreso_verificado)

    db.commit()
    db.refresh(objetivo)
    return _serializar_usuario(db, objetivo)


@router.post("/usuarios/{id_usuario}/identidades-academicas", response_model=UsuarioGestionItem)
def asegurar_identidades_usuario(
    id_usuario: str,
    usuario_actual: UsuarioActual,
    db: BaseDatos,
) -> UsuarioGestionItem:
    _exigir_admin(usuario_actual)
    try:
        uid = id_entero(id_usuario)
    except ReglaIdentidadInvalida:
        raise HTTPException(422, detail="Identificador inválido.") from None

    objetivo = db.get(UsuarioORM, uid)
    if objetivo is None:
        raise HTTPException(404, detail="Usuario no encontrado.")

    _asegurar_identidades(db, uid)
    db.commit()
    db.refresh(objetivo)
    return _serializar_usuario(db, objetivo)

