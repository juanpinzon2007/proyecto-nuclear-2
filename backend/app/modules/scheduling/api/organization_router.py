"""Rutas operativas de organización académica (espacios, grupos, matrículas RF-04) y portal estudiantil."""

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.cases.infrastructure.models.caso import EscenarioModel, VersionCasoModel
from app.modules.identity.api.academic_dependencies import obtener_estudiante_scheduling
from app.modules.identity.api.dependencies import obtener_estudiante_actual, obtener_usuario_actual
from app.modules.identity.application.authorization import ServicioAutorizacion
from app.modules.identity.domain.entities import ContextoAcceso, Rol
from app.modules.identity.domain.errors import AccesoDenegado
from app.modules.identity.infrastructure.academic_base_models import (
    ConsentimientoORM,
    GrupoAcademicoORM,
    GrupoEstudianteORM,
)
from app.modules.identity.infrastructure.academic_identity_models import IdentidadAcademicaORM
from app.modules.identity.infrastructure.academic_models import PermisoIntentoExtraORM, RetroalimentacionDocenteORM
from app.modules.identity.infrastructure.models import RolORM, UsuarioORM
from app.modules.identity.infrastructure.repositories import id_entero
from app.modules.participation.api.dependencies import obtener_fechas_escenario
from app.modules.participation.infrastructure.academic_results_models import (
    AusenciaAcademicaModel,
    PublicacionEvaluacionModel,
    ResultadoParticipacionModel,
)
from app.modules.participation.infrastructure.models import IntentoModel, ParticipacionModel
from app.modules.participation.infrastructure.result_models import ResultadoIntentoModel
from app.modules.scheduling.domain.ingress_policy import calcular_limite_ingreso_mitad_tiempo
from app.modules.scheduling.infrastructure.assignment_models import AsignacionCasoModel
from app.modules.scheduling.infrastructure.models import (
    ConvocatoriaModel,
    DocenteEspacioAcademicoModel,
    EspacioAcademicoModel,
    NotificacionModel,
    SesionProgramadaModel,
)


router = APIRouter(tags=["Organization"])

BaseDatos = Annotated[Session, Depends(get_db)]
UsuarioActual = Annotated[ContextoAcceso, Depends(obtener_usuario_actual)]


def _exigir_docente_o_admin(usuario: ContextoAcceso) -> None:
    if not usuario.roles.intersection({Rol.DOCENTE, Rol.ADMINISTRADOR}):
        raise HTTPException(403, detail="Operación reservada para docentes o administradores.")


class DocenteBreve(BaseModel):
    id_usuario: int
    nombre: str
    correo: str
    uuid_scheduling: UUID | None = None


class EspacioConAutorizaciones(BaseModel):
    id: UUID
    nombre: str
    autorizado_para_mi: bool
    docentes_autorizados: list[DocenteBreve]


class AutorizarEspacioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id_docente: int | None = None


class CrearGrupoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    nombre: Annotated[str, Field(min_length=2, max_length=120)]
    periodo: Annotated[str, Field(min_length=2, max_length=30)]
    id_profesor: int | None = None


class MatricularEstudianteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id_usuario: int = Field(gt=0)


class EstudianteMatriculadoItem(BaseModel):
    id_usuario: int
    nombre: str
    correo: str
    uuid_scheduling: UUID | None = None
    fecha_ingreso: datetime
    activo: bool


class GrupoResponse(BaseModel):
    id_grupo: int
    nombre: str
    periodo: str
    id_profesor: int
    estudiantes: list[EstudianteMatriculadoItem]


class EstudianteDisponibleItem(BaseModel):
    id_usuario: int
    nombre: str
    correo: str
    uuid_scheduling: UUID | None = None


class MiConvocatoriaItem(BaseModel):
    convocatoria_id: UUID
    sesion_id: UUID
    espacio_nombre: str
    caso_nombre: str
    contexto_historia: str
    desarrollo_situacional: str
    escenarios_count: int
    docente_nombre: str
    fecha_inicio: datetime
    fecha_fin: datetime
    fecha_limite_mitad_tiempo: datetime
    tiempo_maximo_minutos: int
    lugar: str | None
    mensaje_personalizado: str | None
    estado_sesion: str
    estado_convocatoria: str
    consentimiento_aceptado: bool
    id_participacion: int | None = None
    estado_participacion: str | None = None
    intento_id: int | None = None
    intento_estado: str | None = None
    intento_inicio: datetime | None = None
    intento_vence_en: datetime | None = None
    intentos_realizados: int = 0
    permisos_extra_disponibles: int = 0
    nota_visible: float | None = None
    tiene_retroalimentacion: bool = False
    es_ausente: bool = False
    notificaciones_recientes: list[str] = Field(default_factory=list)


def _serializar_grupo(db: Session, grupo: GrupoAcademicoORM) -> GrupoResponse:
    filas = db.execute(
        select(
            UsuarioORM.id_usuario,
            UsuarioORM.nombre,
            UsuarioORM.correo,
            GrupoEstudianteORM.fecha_ingreso,
            GrupoEstudianteORM.activo,
        )
        .join(GrupoEstudianteORM, GrupoEstudianteORM.id_estudiante == UsuarioORM.id_usuario)
        .where(GrupoEstudianteORM.id_grupo == grupo.id_grupo)
        .order_by(UsuarioORM.nombre, UsuarioORM.id_usuario)
    ).all()

    uids = [f.id_usuario for f in filas]
    uuids = {}
    if uids:
        vinculos = db.scalars(
            select(IdentidadAcademicaORM).where(
                IdentidadAcademicaORM.id_usuario.in_(uids),
                IdentidadAcademicaORM.sistema == "SCHEDULING",
            )
        ).all()
        uuids = {v.id_usuario: v.id_academico for v in vinculos}

    estudiantes = [
        EstudianteMatriculadoItem(
            id_usuario=f.id_usuario,
            nombre=f.nombre,
            correo=f.correo,
            uuid_scheduling=uuids.get(f.id_usuario),
            fecha_ingreso=f.fecha_ingreso,
            activo=bool(f.activo),
        )
        for f in filas
        if f.activo
    ]
    return GrupoResponse(
        id_grupo=grupo.id_grupo,
        nombre=grupo.nombre,
        periodo=grupo.periodo,
        id_profesor=grupo.id_profesor,
        estudiantes=estudiantes,
    )


@router.get("/espacios/todos", response_model=list[EspacioConAutorizaciones])
def listar_todos_espacios(usuario: UsuarioActual, db: BaseDatos) -> list[EspacioConAutorizaciones]:
    _exigir_docente_o_admin(usuario)
    uid = id_entero(usuario.id_usuario)
    espacios = db.scalars(select(EspacioAcademicoModel).order_by(EspacioAcademicoModel.nombre)).all()
    if not espacios:
        return []
    auths = db.execute(
        select(
            DocenteEspacioAcademicoModel.espacio_academico_id,
            UsuarioORM.id_usuario,
            UsuarioORM.nombre,
            UsuarioORM.correo,
        )
        .join(UsuarioORM, UsuarioORM.id_usuario == DocenteEspacioAcademicoModel.id_docente)
    ).all()
    por_espacio: dict[UUID, list[DocenteBreve]] = {}
    for eid, u_id, nombre, correo in auths:
        por_espacio.setdefault(eid, []).append(DocenteBreve(id_usuario=u_id, nombre=nombre, correo=correo))
    return [
        EspacioConAutorizaciones(
            id=e.id,
            nombre=e.nombre,
            autorizado_para_mi=any(d.id_usuario == uid for d in por_espacio.get(e.id, [])),
            docentes_autorizados=por_espacio.get(e.id, []),
        )
        for e in espacios
    ]


@router.post("/espacios/{espacio_id}/autorizar", status_code=200)
def autorizar_espacio_docente(
    espacio_id: UUID,
    usuario: UsuarioActual,
    db: BaseDatos,
    datos: AutorizarEspacioRequest | None = None,
):
    _exigir_docente_o_admin(usuario)
    espacio = db.get(EspacioAcademicoModel, espacio_id)
    if espacio is None:
        raise HTTPException(404, detail="Espacio académico no encontrado.")

    caller_uid = id_entero(usuario.id_usuario)
    es_admin = Rol.ADMINISTRADOR in usuario.roles
    target_uid = datos.id_docente if (datos and datos.id_docente is not None) else caller_uid

    if not es_admin and target_uid != caller_uid:
        raise HTTPException(403, detail="Solo un administrador puede autorizar espacios a otros docentes.")

    docente = db.get(UsuarioORM, target_uid)
    if docente is None or not docente.activo:
        raise HTTPException(404, detail="Docente no encontrado o inactivo.")
    rol = db.get(RolORM, docente.id_rol)
    if rol is None or rol.nombre.strip().upper() != "DOCENTE":
        raise HTTPException(422, detail="El usuario seleccionado no tiene rol DOCENTE.")

    existente = db.get(DocenteEspacioAcademicoModel, (target_uid, espacio_id))
    if existente is None:
        db.add(DocenteEspacioAcademicoModel(id_docente=target_uid, espacio_academico_id=espacio_id))
        db.commit()

    return {"ok": True, "espacio_id": str(espacio_id), "id_docente": target_uid}


@router.get("/docentes", response_model=list[DocenteBreve])
def listar_docentes_disponibles(usuario: UsuarioActual, db: BaseDatos) -> list[DocenteBreve]:
    _exigir_docente_o_admin(usuario)
    filas = db.execute(
        select(UsuarioORM.id_usuario, UsuarioORM.nombre, UsuarioORM.correo)
        .join(RolORM, RolORM.id_rol == UsuarioORM.id_rol)
        .where(func.upper(func.trim(RolORM.nombre)) == "DOCENTE", UsuarioORM.activo.is_(True))
        .order_by(UsuarioORM.nombre)
    ).all()
    uids = [f.id_usuario for f in filas]
    uuids = {}
    if uids:
        vinculos = db.scalars(
            select(IdentidadAcademicaORM).where(
                IdentidadAcademicaORM.id_usuario.in_(uids),
                IdentidadAcademicaORM.sistema == "SCHEDULING",
            )
        ).all()
        uuids = {v.id_usuario: v.id_academico for v in vinculos}
    return [
        DocenteBreve(
            id_usuario=f.id_usuario,
            nombre=f.nombre,
            correo=f.correo,
            uuid_scheduling=uuids.get(f.id_usuario),
        )
        for f in filas
    ]


@router.get("/estudiantes", response_model=list[EstudianteDisponibleItem])
def listar_estudiantes_activos(usuario: UsuarioActual, db: BaseDatos) -> list[EstudianteDisponibleItem]:
    _exigir_docente_o_admin(usuario)
    filas = db.execute(
        select(UsuarioORM.id_usuario, UsuarioORM.nombre, UsuarioORM.correo)
        .join(RolORM, RolORM.id_rol == UsuarioORM.id_rol)
        .where(func.upper(func.trim(RolORM.nombre)) == "ESTUDIANTE", UsuarioORM.activo.is_(True))
        .order_by(UsuarioORM.nombre, UsuarioORM.id_usuario)
    ).all()
    uids = [f.id_usuario for f in filas]
    uuids = {}
    if uids:
        vinculos = db.scalars(
            select(IdentidadAcademicaORM).where(
                IdentidadAcademicaORM.id_usuario.in_(uids),
                IdentidadAcademicaORM.sistema == "SCHEDULING",
            )
        ).all()
        uuids = {v.id_usuario: v.id_academico for v in vinculos}
    return [
        EstudianteDisponibleItem(
            id_usuario=f.id_usuario,
            nombre=f.nombre,
            correo=f.correo,
            uuid_scheduling=uuids.get(f.id_usuario),
        )
        for f in filas
    ]


@router.get("/grupos", response_model=list[GrupoResponse])
def listar_grupos(usuario: UsuarioActual, db: BaseDatos) -> list[GrupoResponse]:
    _exigir_docente_o_admin(usuario)
    consulta = select(GrupoAcademicoORM).order_by(GrupoAcademicoORM.id_grupo.desc())
    if Rol.ADMINISTRADOR not in usuario.roles:
        consulta = consulta.where(GrupoAcademicoORM.id_profesor == id_entero(usuario.id_usuario))
    grupos = db.scalars(consulta).all()
    return [_serializar_grupo(db, g) for g in grupos]


@router.post("/grupos", response_model=GrupoResponse, status_code=201)
def crear_grupo(datos: CrearGrupoRequest, usuario: UsuarioActual, db: BaseDatos) -> GrupoResponse:
    _exigir_docente_o_admin(usuario)
    caller_uid = id_entero(usuario.id_usuario)
    prof_uid = datos.id_profesor if (Rol.ADMINISTRADOR in usuario.roles and datos.id_profesor is not None) else caller_uid
    prof = db.get(UsuarioORM, prof_uid)
    if prof is None:
        raise HTTPException(404, detail="Profesor no encontrado.")

    grupo = GrupoAcademicoORM(id_profesor=prof_uid, nombre=datos.nombre, periodo=datos.periodo)
    db.add(grupo)
    db.commit()
    db.refresh(grupo)
    return _serializar_grupo(db, grupo)


@router.post("/grupos/{grupo_id}/estudiantes", response_model=GrupoResponse)
def matricular_estudiante(
    grupo_id: int,
    datos: MatricularEstudianteRequest,
    usuario: UsuarioActual,
    db: BaseDatos,
) -> GrupoResponse:
    _exigir_docente_o_admin(usuario)
    grupo = db.get(GrupoAcademicoORM, grupo_id)
    if grupo is None:
        raise HTTPException(404, detail="Grupo no encontrado.")
    if Rol.ADMINISTRADOR not in usuario.roles and grupo.id_profesor != id_entero(usuario.id_usuario):
        raise HTTPException(403, detail="No puedes modificar matrículas de otro docente.")

    est = db.get(UsuarioORM, datos.id_usuario)
    if est is None or not est.activo:
        raise HTTPException(404, detail="Estudiante no encontrado o inactivo.")
    rol = db.get(RolORM, est.id_rol)
    if rol is None or rol.nombre.strip().upper() != "ESTUDIANTE":
        raise HTTPException(422, detail="El usuario debe tener rol ESTUDIANTE.")

    # Garantizar vínculo SCHEDULING si aún no lo tiene, para programar sesiones sin fricciones.
    vinculo = db.scalar(
        select(IdentidadAcademicaORM).where(
            IdentidadAcademicaORM.id_usuario == est.id_usuario,
            IdentidadAcademicaORM.sistema == "SCHEDULING",
        )
    )
    if vinculo is None:
        db.add(IdentidadAcademicaORM(sistema="SCHEDULING", id_academico=uuid4(), id_usuario=est.id_usuario))

    matricula = db.scalar(
        select(GrupoEstudianteORM).where(
            GrupoEstudianteORM.id_grupo == grupo_id,
            GrupoEstudianteORM.id_estudiante == est.id_usuario,
        )
    )
    ahora_naive = datetime.now(UTC).replace(tzinfo=None)
    if matricula is None:
        db.add(
            GrupoEstudianteORM(
                id_grupo=grupo_id,
                id_estudiante=est.id_usuario,
                fecha_ingreso=ahora_naive,
                activo=True,
            )
        )
    else:
        matricula.activo = True
        matricula.fecha_ingreso = ahora_naive

    db.commit()
    return _serializar_grupo(db, grupo)


@router.delete("/grupos/{grupo_id}/estudiantes/{id_usuario}", response_model=GrupoResponse)
def retirar_estudiante(
    grupo_id: int,
    id_usuario: int,
    usuario: UsuarioActual,
    db: BaseDatos,
) -> GrupoResponse:
    _exigir_docente_o_admin(usuario)
    grupo = db.get(GrupoAcademicoORM, grupo_id)
    if grupo is None:
        raise HTTPException(404, detail="Grupo no encontrado.")
    if Rol.ADMINISTRADOR not in usuario.roles and grupo.id_profesor != id_entero(usuario.id_usuario):
        raise HTTPException(403, detail="No puedes modificar matrículas de otro docente.")

    matricula = db.scalar(
        select(GrupoEstudianteORM).where(
            GrupoEstudianteORM.id_grupo == grupo_id,
            GrupoEstudianteORM.id_estudiante == id_usuario,
        )
    )
    if matricula is None:
        raise HTTPException(404, detail="Matrícula no encontrada.")
    matricula.activo = False
    db.commit()
    return _serializar_grupo(db, grupo)


@router.get("/mis-convocatorias", response_model=list[MiConvocatoriaItem])
def listar_mis_convocatorias(
    usuario: Annotated[ContextoAcceso, Depends(obtener_estudiante_actual)],
    estudiante_uuid: Annotated[UUID, Depends(obtener_estudiante_scheduling)],
    db: BaseDatos,
) -> list[MiConvocatoriaItem]:
    """Portal estudiantil RF-01/RF-22/RF-25/RF-27: convocatorias asignadas sin exponer respuestas ni rúbricas."""
    uid = id_entero(usuario.id_usuario)
    fechas = obtener_fechas_escenario()

    convocatorias = db.scalars(
        select(ConvocatoriaModel)
        .where(ConvocatoriaModel.estudiante_id == estudiante_uuid)
        .order_by(ConvocatoriaModel.id)
    ).all()

    tiene_consentimiento = (
        db.scalar(
            select(ConsentimientoORM.id_consentimiento).where(
                ConsentimientoORM.id_estudiante == uid,
                ConsentimientoORM.fecha_revocacion.is_(None),
            ).limit(1)
        )
        is not None
    )

    items: list[MiConvocatoriaItem] = []
    for conv in convocatorias:
        sesion = db.get(SesionProgramadaModel, conv.sesion_id)
        if sesion is None:
            continue
        espacio = db.get(EspacioAcademicoModel, sesion.espacio_academico_id)
        version = db.get(VersionCasoModel, sesion.version_caso_id)
        escenarios_count = db.scalar(
            select(func.count()).select_from(EscenarioModel).where(EscenarioModel.version_caso_id == sesion.version_caso_id)
        ) or 0

        doc_uid = db.scalar(
            select(IdentidadAcademicaORM.id_usuario).where(
                IdentidadAcademicaORM.sistema == "SCHEDULING",
                IdentidadAcademicaORM.id_academico == sesion.docente_id,
            )
        )
        docente_nombre = "Docente asignado"
        if doc_uid is not None:
            doc_u = db.get(UsuarioORM, doc_uid)
            if doc_u is not None:
                docente_nombre = doc_u.nombre

        asig = db.scalar(
            select(AsignacionCasoModel).where(
                AsignacionCasoModel.sesion_programada_id == sesion.id,
            ).limit(1)
        )
        fecha_lim_exp = None
        if asig is not None and asig.fecha_limite_ingreso is not None:
            fecha_lim_exp = fechas.desde_db(asig.fecha_limite_ingreso)

        mitad = calcular_limite_ingreso_mitad_tiempo(
            inicio=sesion.fecha_inicio,
            fin=sesion.fecha_fin,
            tiempo_maximo_minutos=sesion.tiempo_maximo_minutos,
            fecha_limite_explicita=fecha_lim_exp,
        )

        part = db.scalar(select(ParticipacionModel).where(ParticipacionModel.convocatoria_id == conv.id))
        intentos = []
        permisos_extra = 0
        tiene_feedback = False
        nota_visible: float | None = None

        if part is not None:
            intentos = list(
                db.scalars(
                    select(IntentoModel)
                    .where(IntentoModel.id_participacion == part.id_participacion)
                    .order_by(IntentoModel.numero_intento.desc())
                ).all()
            )
            total_permisos_extra = int(
                db.scalar(
                    select(func.coalesce(func.sum(PermisoIntentoExtraORM.cantidad_autorizada), 0)).where(
                        PermisoIntentoExtraORM.id_participacion == part.id_participacion
                    )
                )
                or 0
            )
            usados_extra = sum(1 for i in intentos if i.id_permiso_extra is not None)
            permisos_extra = max(0, total_permisos_extra - usados_extra)
            tiene_feedback = (
                db.scalar(
                    select(RetroalimentacionDocenteORM.id_retroalimentacion).where(
                        RetroalimentacionDocenteORM.id_participacion == part.id_participacion
                    )
                )
                is not None
            )

        ultimo_intento = intentos[0] if intentos else None
        intento_vence_en: datetime | None = None
        if ultimo_intento is not None:
            inicio_utc = fechas.desde_db(ultimo_intento.inicio)
            duracion = float(ultimo_intento.duracion_concedida_segundos)
            from datetime import timedelta

            vence_por_tiempo = inicio_utc + timedelta(seconds=duracion)
            fin_sesion_utc = sesion.fecha_fin.astimezone(UTC) if sesion.fecha_fin.utcoffset() else sesion.fecha_fin.replace(tzinfo=UTC)
            intento_vence_en = min(vence_por_tiempo, fin_sesion_utc)

            res = db.scalar(
                select(ResultadoIntentoModel).where(ResultadoIntentoModel.id_intento == ultimo_intento.id_intento)
            )
            pub_actual = db.scalar(
                select(PublicacionEvaluacionModel)
                .where(PublicacionEvaluacionModel.sesion_id == sesion.id)
                .order_by(PublicacionEvaluacionModel.version.desc())
                .limit(1)
            )
            if pub_actual is not None:
                rp = db.scalar(
                    select(ResultadoParticipacionModel).where(
                        ResultadoParticipacionModel.publicacion_id == pub_actual.id,
                        ResultadoParticipacionModel.convocatoria_id == conv.id,
                    )
                )
                if rp is not None:
                    nota_visible = float(rp.nota_definitiva)
            elif res is not None and (
                sesion.mostrar_resultados_provisionales is True or ultimo_intento.estado != "EN_CURSO"
            ):
                nota_visible = float(res.nota_final)

        aus = db.scalar(
            select(AusenciaAcademicaModel)
            .where(AusenciaAcademicaModel.convocatoria_id == conv.id)
            .order_by(AusenciaAcademicaModel.revision.desc())
            .limit(1)
        )
        es_ausente = bool(aus and aus.confirmada)
        if es_ausente:
            nota_visible = 0.0

        notifs = list(
            db.scalars(
                select(NotificacionModel.mensaje)
                .where(NotificacionModel.convocatoria_id == conv.id)
                .order_by(NotificacionModel.creada_en.desc())
                .limit(5)
            ).all()
        )

        items.append(
            MiConvocatoriaItem(
                convocatoria_id=conv.id,
                sesion_id=sesion.id,
                espacio_nombre=espacio.nombre if espacio else "Espacio académico",
                caso_nombre=version.nombre if version else "Caso clínico",
                contexto_historia=version.contexto_historia if version else "",
                desarrollo_situacional=version.desarrollo_situacional if version else "",
                escenarios_count=int(escenarios_count),
                docente_nombre=docente_nombre,
                fecha_inicio=sesion.fecha_inicio,
                fecha_fin=sesion.fecha_fin,
                fecha_limite_mitad_tiempo=mitad,
                tiempo_maximo_minutos=sesion.tiempo_maximo_minutos,
                lugar=sesion.lugar,
                mensaje_personalizado=sesion.mensaje_personalizado,
                estado_sesion=sesion.estado,
                estado_convocatoria=conv.estado,
                consentimiento_aceptado=tiene_consentimiento or (part is not None and part.id_consentimiento is not None),
                id_participacion=part.id_participacion if part else None,
                estado_participacion=part.estado if part else None,
                intento_id=ultimo_intento.id_intento if ultimo_intento else None,
                intento_estado=ultimo_intento.estado if ultimo_intento else None,
                intento_inicio=fechas.desde_db(ultimo_intento.inicio) if ultimo_intento else None,
                intento_vence_en=intento_vence_en,
                intentos_realizados=len(intentos),
                permisos_extra_disponibles=permisos_extra,
                nota_visible=nota_visible,
                tiene_retroalimentacion=tiene_feedback,
                es_ausente=es_ausente,
                notificaciones_recientes=notifs,
            )
        )

    items.sort(key=lambda x: x.fecha_inicio, reverse=True)
    return items
