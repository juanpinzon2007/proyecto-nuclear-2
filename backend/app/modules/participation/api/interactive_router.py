"""Flujo interactivo operativo del estudiante: consentimiento, ingreso tardío RF-22,
espacio de trabajo editable RF-10, temporizador RF-23, calificación con rúbrica RF-13 y resultados RF-14."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
import math
from hashlib import sha256
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.session import get_db, get_session_factory
from app.modules.cases.infrastructure.models.caso import (
    EscenarioModel,
    OpcionRespuestaModel,
    PreguntaModel,
    VersionCasoModel,
)
from app.modules.identity.api.academic_dependencies import obtener_estudiante_scheduling
from app.modules.identity.api.consent_dependencies import obtener_aprobacion_consentimiento
from app.modules.identity.api.dependencies import obtener_estudiante_actual
from app.modules.identity.domain.entities import ContextoAcceso
from app.modules.identity.domain.errors import IntegracionPendiente
from app.modules.identity.infrastructure.academic_base_models import (
    ConsentimientoORM,
    GrupoAcademicoORM,
    GrupoEstudianteORM,
)
from app.modules.identity.infrastructure.academic_identity_models import IdentidadAcademicaORM
from app.modules.identity.infrastructure.academic_models import PermisoIntentoExtraORM
from app.modules.identity.infrastructure.consent_document_models import (
    DocumentoConsentimientoVersionORM,
    SeleccionConsentimientoORM,
)
from app.modules.identity.infrastructure.consent_repository import FuenteConsentimientoSQLAlchemy
from app.modules.identity.infrastructure.repositories import id_entero
from app.modules.participation.api.dependencies import obtener_fechas_escenario
from app.modules.participation.application.interactive_evaluator import (
    construir_detalle_resultado_estudiante,
    evaluar_e_persistir_intento,
)
from app.modules.participation.infrastructure.codecs import FechasPersistencia
from app.modules.participation.infrastructure.models import (
    BorradorDecisionIntentoModel,
    HistorialCambioDecisionModel,
    IntentoModel,
    ParticipacionModel,
    PasoSimulacionModel,
)
from app.modules.participation.infrastructure.result_models import ResultadoIntentoModel
from app.modules.scheduling.domain.ingress_policy import (
    PoliticaIngresoMitadTiempo,
    PoliticaTemporalNoDisponible,
    calcular_limite_ingreso_mitad_tiempo,
)
from app.modules.scheduling.infrastructure.assignment_models import AsignacionCasoModel
from app.modules.scheduling.infrastructure.models import ConvocatoriaModel, SesionProgramadaModel


router = APIRouter(prefix="/simulacion", tags=["Simulacion Interactiva"])

BaseDatos = Annotated[Session, Depends(get_db)]
FabricaSesion = Annotated[sessionmaker, Depends(get_session_factory)]
EstudianteActual = Annotated[ContextoAcceso, Depends(obtener_estudiante_actual)]
EstudianteUUID = Annotated[UUID, Depends(obtener_estudiante_scheduling)]
Fechas = Annotated[FechasPersistencia, Depends(obtener_fechas_escenario)]

_TEXTO_CONSENTIMIENTO_INSTITUCIONAL = (
    "Consentimiento informado para simulación clínica y académica:\n\n"
    "1. Comprendo que mi participación se desarrolla en un entorno académico controlado con registro de inicio, "
    "duración y envío de respuestas.\n"
    "2. Acepto responder de forma individual, íntegra y ética dentro del tiempo máximo asignado para la sesión.\n"
    "3. Autorizo el almacenamiento institucional de mis decisiones, reflexiones y calificaciones para "
    "seguimiento académico y retroalimentación docente."
)


class GuardarBorradorRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id_opcion: UUID
    reflexion_estudiante: Annotated[str | None, Field(max_length=4000)] = None


class EnviarIntentoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    permitir_parcial: bool = False


def _asegurar_consentimiento_asignacion(
    db: Session,
    *,
    asignacion: AsignacionCasoModel,
    fallback_uid: int,
) -> DocumentoConsentimientoVersionORM:
    if get_settings().academic_runtime_scope != "LABORATORIO":
        fuente = FuenteConsentimientoSQLAlchemy(db, politica_aprobacion=obtener_aprobacion_consentimiento())
        try:
            aprobado = fuente.vigente(id_asignacion=asignacion.id_asignacion, ahora=datetime.now(UTC))
        except IntegracionPendiente:
            raise HTTPException(503, detail="La asignación aún no tiene un consentimiento institucional aprobado.") from None
        return db.get(DocumentoConsentimientoVersionORM, aprobado.id_version_documento)

    sel = db.get(SeleccionConsentimientoORM, asignacion.id_asignacion)
    if sel is not None:
        doc = db.get(DocumentoConsentimientoVersionORM, sel.id_version_documento)
        if doc is not None:
            return doc

    doc = db.scalar(
        select(DocumentoConsentimientoVersionORM).order_by(DocumentoConsentimientoVersionORM.vigente_desde.desc()).limit(1)
    )
    if doc is None:
        ahora = datetime.now(UTC)
        grupo = db.get(GrupoAcademicoORM, asignacion.id_grupo)
        publicador = grupo.id_profesor if grupo is not None else fallback_uid
        orig_bytes = _TEXTO_CONSENTIMIENTO_INSTITUCIONAL.encode("utf-8")
        evid_bytes = b"Documento sintetico de laboratorio de SPS."
        doc = DocumentoConsentimientoVersionORM(
            referencia="CONSENTIMIENTO-INST-V1",
            documento_id="sps-consentimiento-academico",
            version="1.0",
            original=orig_bytes,
            tipo_media="text/plain",
            texto=_TEXTO_CONSENTIMIENTO_INSTITUCIONAL,
            sha256_original=sha256(orig_bytes).hexdigest(),
            sha256_texto=sha256(orig_bytes).hexdigest(),
            autoridad_aprobadora="Laboratorio SPS",
            aprobado_en=ahora,
            evidencia_aprobacion=evid_bytes,
            sha256_aprobacion=sha256(evid_bytes).hexdigest(),
            publicado_por=publicador,
            publicado_en=ahora,
            vigente_desde=ahora,
        )
        db.add(doc)
        db.flush()

    sel_actual = db.get(SeleccionConsentimientoORM, asignacion.id_asignacion)
    if sel_actual is None:
        grupo = db.get(GrupoAcademicoORM, asignacion.id_grupo)
        sel_por = grupo.id_profesor if grupo is not None else fallback_uid
        db.add(
            SeleccionConsentimientoORM(
                id_asignacion=asignacion.id_asignacion,
                id_version_documento=doc.id_version_documento,
                seleccionado_por=sel_por,
                seleccionado_en=datetime.now(UTC),
            )
        )
        db.flush()
    return doc


def _resolver_contexto_convocatoria(
    db: Session,
    *,
    convocatoria_id: UUID,
    usuario: ContextoAcceso,
    estudiante_uuid: UUID,
) -> tuple[ConvocatoriaModel, SesionProgramadaModel, AsignacionCasoModel, GrupoEstudianteORM, int]:
    uid = id_entero(usuario.id_usuario)
    conv = db.get(ConvocatoriaModel, convocatoria_id)
    if conv is None or conv.estudiante_id != estudiante_uuid:
        raise HTTPException(403, detail="La convocatoria no pertenece al estudiante autenticado.")
    if conv.estado != "ACTIVA":
        raise HTTPException(403, detail="La convocatoria fue retirada o no se encuentra activa.")

    sesion = db.get(SesionProgramadaModel, conv.sesion_id)
    if sesion is None:
        raise HTTPException(404, detail="Sesión no encontrada.")

    fila = db.execute(
        select(AsignacionCasoModel, GrupoEstudianteORM)
        .join(GrupoEstudianteORM, GrupoEstudianteORM.id_grupo == AsignacionCasoModel.id_grupo)
        .where(
            AsignacionCasoModel.sesion_programada_id == sesion.id,
            GrupoEstudianteORM.id_estudiante == uid,
            GrupoEstudianteORM.activo.is_(True),
        )
        .limit(1)
    ).first()
    if fila is None:
        raise HTTPException(403, detail="El estudiante no tiene matrícula y asignación activa para esta sesión.")

    asignacion, matricula = fila
    return conv, sesion, asignacion, matricula, uid


def _limite_intento_db(intento: IntentoModel) -> datetime:
    duracion_sec = float(intento.duracion_concedida_segundos)
    return intento.inicio + timedelta(seconds=duracion_sec)


def _ordenar_preguntas_para_cierre(
    db: Session,
    *,
    version_caso_id: UUID,
    borradores: list[BorradorDecisionIntentoModel],
) -> list[BorradorDecisionIntentoModel]:
    por_pregunta = {b.id_decision: b for b in borradores}
    escenarios = list(
        db.scalars(select(EscenarioModel).where(EscenarioModel.version_caso_id == version_caso_id).order_by(EscenarioModel.orden)).all()
    )
    inicial = next((e for e in escenarios if getattr(e, "es_inicial", False)), None)
    tiene_trans = (
        db.scalar(
            select(func.count())
            .select_from(OpcionRespuestaModel)
            .join(PreguntaModel, PreguntaModel.id == OpcionRespuestaModel.pregunta_id)
            .join(EscenarioModel, EscenarioModel.id == PreguntaModel.escenario_id)
            .where(
                EscenarioModel.version_caso_id == version_caso_id,
                OpcionRespuestaModel.tipo_transicion.is_not(None),
            )
        )
        or 0
    ) > 0

    if inicial is not None and tiene_trans:
        ruta: list[BorradorDecisionIntentoModel] = []
        actual = inicial
        visitados = set()
        while actual is not None and actual.id not in visitados:
            visitados.add(actual.id)
            qs = list(
                db.scalars(select(PreguntaModel).where(PreguntaModel.escenario_id == actual.id).order_by(PreguntaModel.orden)).all()
            )
            if len(qs) != 1:
                break
            b = por_pregunta.get(qs[0].id)
            if b is None:
                break
            ruta.append(b)
            op = db.get(OpcionRespuestaModel, b.id_opcion)
            if op is None or op.tipo_transicion == "FIN":
                break
            if op.tipo_transicion == "ESCENA" and op.escenario_destino_id is not None:
                actual = next((e for e in escenarios if e.id == op.escenario_destino_id), None)
            else:
                break
        if ruta:
            return ruta

    orden_global: list[BorradorDecisionIntentoModel] = []
    for esc in escenarios:
        qs = list(
            db.scalars(select(PreguntaModel).where(PreguntaModel.escenario_id == esc.id).order_by(PreguntaModel.orden)).all()
        )
        for q in qs:
            if q.id in por_pregunta:
                orden_global.append(por_pregunta[q.id])
    return orden_global


def cerrar_intento_y_evaluar(
    db: Session,
    *,
    intento: IntentoModel,
    usuario: ContextoAcceso,
    fechas: FechasPersistencia,
    crear_sesion: sessionmaker,
    forzar_vencido: bool = False,
    permitir_parcial: bool = True,
) -> ResultadoIntentoModel | None:
    """Cierra un intento EN_CURSO (por envío o vencimiento), consolida borradores en paso_simulacion y califica."""
    if intento.estado in ("FINALIZADO", "VENCIDO"):
        return evaluar_e_persistir_intento(
            db,
            usuario=usuario,
            id_intento=intento.id_intento,
            fechas=fechas,
            crear_sesion=crear_sesion,
            modalidad="COMPLETA" if intento.estado == "FINALIZADO" else "PARCIAL",
        )

    participacion = db.get(ParticipacionModel, intento.id_participacion)
    asignacion = db.get(AsignacionCasoModel, participacion.id_asignacion)
    ahora_utc = datetime.now(UTC)
    ahora_db = fechas.hacia_db(ahora_utc, sin_offset=True)
    limite_db = _limite_intento_db(intento)

    vencido = forzar_vencido or (ahora_db >= limite_db)
    estado_cierre = "VENCIDO" if vencido else "FINALIZADO"

    borradores = list(
        db.scalars(
            select(BorradorDecisionIntentoModel).where(BorradorDecisionIntentoModel.id_intento == intento.id_intento)
        ).all()
    )
    ordenados = _ordenar_preguntas_para_cierre(
        db, version_caso_id=asignacion.version_caso_id, borradores=borradores
    )

    total_preguntas = (
        db.scalar(
            select(func.count())
            .select_from(PreguntaModel)
            .join(EscenarioModel, EscenarioModel.id == PreguntaModel.escenario_id)
            .where(EscenarioModel.version_caso_id == asignacion.version_caso_id)
        )
        or 0
    )

    # Verificar completitud cuando no es parcial ni vencido
    es_completo = False
    if ordenados:
        ultima_op = db.get(OpcionRespuestaModel, ordenados[-1].id_opcion)
        if ultima_op is not None and ultima_op.tipo_transicion == "FIN":
            es_completo = True
        elif len(ordenados) >= total_preguntas and total_preguntas > 0:
            es_completo = True

    if not vencido and not es_completo and not permitir_parcial:
        raise HTTPException(
            422,
            detail="Aún tienes preguntas pendientes por responder. Completa el recorrido o confirma entrega parcial.",
        )

    existentes = {
        p.id_decision: p
        for p in db.scalars(
            select(PasoSimulacionModel)
            .where(PasoSimulacionModel.id_intento == intento.id_intento)
            .order_by(PasoSimulacionModel.numero_paso)
        ).all()
    }
    max_num_paso = max((p.numero_paso for p in existentes.values()), default=0)
    prev_reg = max((p.registrado_en for p in existentes.values()), default=intento.inicio)

    # Limite máximo de segundos enteros estrictamente menor que duracion_concedida_segundos
    dur_total_sec = float(intento.duracion_concedida_segundos)
    max_sec_allowed = max(0, int(math.floor(dur_total_sec)) - 1)

    for b in ordenados:
        if b.id_decision in existentes:
            continue
        max_num_paso += 1
        act_db = fechas.hacia_db(
            b.actualizado_en if b.actualizado_en.utcoffset() else b.actualizado_en.replace(tzinfo=UTC),
            sin_offset=True,
        )
        raw_delta = int(math.floor((act_db - intento.inicio).total_seconds()))
        prev_delta = int(math.floor((prev_reg - intento.inicio).total_seconds()))
        delta_s = max(prev_delta, min(max_sec_allowed, max(0, raw_delta)))
        reg_db = intento.inicio + timedelta(seconds=delta_s)
        if reg_db >= limite_db:
            delta_s = max(0, int(math.floor((limite_db - intento.inicio).total_seconds())) - 1)
            reg_db = intento.inicio + timedelta(seconds=delta_s)
        prev_reg = reg_db

        db.add(
            PasoSimulacionModel(
                id_intento=intento.id_intento,
                id_decision=b.id_decision,
                id_opcion=b.id_opcion,
                numero_paso=max_num_paso,
                registrado_en=reg_db,
                tiempo_segundos=delta_s,
                reflexion_estudiante=b.reflexion_estudiante,
            )
        )

    db.flush()

    if estado_cierre == "VENCIDO":
        intento.estado = "VENCIDO"
        intento.fin = limite_db
        participacion.estado = "vencida"
    else:
        fin_candidato = max(prev_reg, min(ahora_db, limite_db - timedelta(milliseconds=10)))
        if fin_candidato < intento.inicio:
            fin_candidato = intento.inicio
        intento.estado = "FINALIZADO"
        intento.fin = fin_candidato
        participacion.estado = "finalizada" if es_completo else "parcial"

    db.commit()

    modalidad = "COMPLETA" if (estado_cierre == "FINALIZADO" and es_completo) else "PARCIAL"
    return evaluar_e_persistir_intento(
        db,
        usuario=usuario,
        id_intento=intento.id_intento,
        fechas=fechas,
        crear_sesion=crear_sesion,
        modalidad=modalidad,
    )


@router.get("/convocatorias/{convocatoria_id}/consentimiento")
def consultar_consentimiento(
    convocatoria_id: UUID,
    usuario: EstudianteActual,
    estudiante_uuid: EstudianteUUID,
    db: BaseDatos,
):
    _, _, asignacion, _, uid = _resolver_contexto_convocatoria(
        db, convocatoria_id=convocatoria_id, usuario=usuario, estudiante_uuid=estudiante_uuid
    )
    doc = _asegurar_consentimiento_asignacion(db, asignacion=asignacion, fallback_uid=uid)
    db.commit()

    consent = db.scalar(
        select(ConsentimientoORM).where(
            ConsentimientoORM.id_estudiante == uid,
            ConsentimientoORM.id_version_documento == doc.id_version_documento,
            ConsentimientoORM.fecha_revocacion.is_(None),
        )
    )
    return {
        "id_version_documento": doc.id_version_documento,
        "documento_id": doc.documento_id,
        "version": doc.version,
        "autoridad_aprobadora": doc.autoridad_aprobadora,
        "texto": doc.texto,
        "aceptado": consent is not None,
        "fecha_aceptacion": consent.fecha_aceptacion if consent else None,
    }


@router.post("/convocatorias/{convocatoria_id}/consentimiento", status_code=201)
def aceptar_consentimiento(
    convocatoria_id: UUID,
    usuario: EstudianteActual,
    estudiante_uuid: EstudianteUUID,
    db: BaseDatos,
    fechas: Fechas,
):
    _, _, asignacion, _, uid = _resolver_contexto_convocatoria(
        db, convocatoria_id=convocatoria_id, usuario=usuario, estudiante_uuid=estudiante_uuid
    )
    doc = _asegurar_consentimiento_asignacion(db, asignacion=asignacion, fallback_uid=uid)
    consent = db.scalar(
        select(ConsentimientoORM).where(
            ConsentimientoORM.id_estudiante == uid,
            ConsentimientoORM.id_version_documento == doc.id_version_documento,
            ConsentimientoORM.fecha_revocacion.is_(None),
        )
    )
    if consent is None:
        ahora_db = fechas.hacia_db(datetime.now(UTC), sin_offset=True)
        consent = ConsentimientoORM(
            id_estudiante=uid,
            version_texto=doc.referencia[:30],
            fecha_aceptacion=ahora_db,
            id_version_documento=doc.id_version_documento,
            aceptacion_explicita=True,
            huella_aceptada=doc.sha256_texto,
        )
        db.add(consent)
    db.commit()
    return {
        "aceptado": True,
        "id_consentimiento": consent.id_consentimiento,
        "fecha_aceptacion": consent.fecha_aceptacion,
    }


@router.post("/convocatorias/{convocatoria_id}/iniciar", status_code=200)
def iniciar_o_retomar_intento(
    convocatoria_id: UUID,
    usuario: EstudianteActual,
    estudiante_uuid: EstudianteUUID,
    db: BaseDatos,
    fechas: Fechas,
    crear_sesion: FabricaSesion,
):
    """Inicia un nuevo intento validando consentimiento, regla RF-22 (mitad de tiempo) y RF-25, o retoma EN_CURSO."""
    conv, sesion, asignacion, matricula, uid = _resolver_contexto_convocatoria(
        db, convocatoria_id=convocatoria_id, usuario=usuario, estudiante_uuid=estudiante_uuid
    )

    if sesion.estado != "EN_CURSO":
        raise HTTPException(
            409,
            detail=f"La sesión se encuentra en estado {sesion.estado}; debe estar EN_CURSO para participar.",
        )

    doc = _asegurar_consentimiento_asignacion(db, asignacion=asignacion, fallback_uid=uid)
    participacion = db.scalar(select(ParticipacionModel).where(ParticipacionModel.convocatoria_id == conv.id))

    if participacion is not None:
        intento_activo = db.scalar(
            select(IntentoModel).where(
                IntentoModel.id_participacion == participacion.id_participacion,
                IntentoModel.estado == "EN_CURSO",
            )
        )
        if intento_activo is not None:
            ahora_db = fechas.hacia_db(datetime.now(UTC), sin_offset=True)
            limite_db = _limite_intento_db(intento_activo)
            if ahora_db < limite_db:
                return {
                    "id_intento": intento_activo.id_intento,
                    "numero_intento": intento_activo.numero_intento,
                    "estado": intento_activo.estado,
                    "retomado": True,
                }
            # Si ya había vencido, cerrarlo automáticamente antes de evaluar reingreso
            cerrar_intento_y_evaluar(
                db,
                intento=intento_activo,
                usuario=usuario,
                fechas=fechas,
                crear_sesion=crear_sesion,
                forzar_vencido=True,
                permitir_parcial=True,
            )

    # Validar consentimiento previo
    consent = db.scalar(
        select(ConsentimientoORM).where(
            ConsentimientoORM.id_estudiante == uid,
            ConsentimientoORM.id_version_documento == doc.id_version_documento,
            ConsentimientoORM.fecha_revocacion.is_(None),
        )
    )
    if consent is None:
        raise HTTPException(409, detail="Debes leer y aceptar el consentimiento informado antes de iniciar.")

    # Validar RF-22: PoliticaIngresoMitadTiempo (máximo 50% del tiempo máximo asignado)
    ahora_utc = datetime.now(UTC)
    fecha_lim_exp = fechas.desde_db(asignacion.fecha_limite_ingreso) if asignacion.fecha_limite_ingreso else None
    try:
        ventana = PoliticaIngresoMitadTiempo(
            tiempo_maximo_minutos=sesion.tiempo_maximo_minutos,
            fecha_limite_explicita=fecha_lim_exp,
        ).obtener_ventana(id_sesion=sesion.id, inicio=sesion.fecha_inicio, fin=sesion.fecha_fin)
    except PoliticaTemporalNoDisponible:
        raise HTTPException(409, detail="La ventana temporal de la sesión no está configurada correctamente.") from None

    if ahora_utc < ventana.apertura:
        raise HTTPException(403, detail="La sesión aún no alcanza la fecha/hora de apertura programada.")
    if ahora_utc > ventana.cierre:
        raise HTTPException(
            403,
            detail=(
                "Ingreso tardío restringido: ya transcurrió más de la mitad del tiempo máximo "
                "asignado para esta sesión."
            ),
        )

    fin_sesion_utc = sesion.fecha_fin.astimezone(UTC) if sesion.fecha_fin.utcoffset() else sesion.fecha_fin.replace(tzinfo=UTC)
    segundos_restantes_sesion = int((fin_sesion_utc - ahora_utc).total_seconds())
    duracion_sec = min(sesion.tiempo_maximo_minutos * 60, segundos_restantes_sesion)
    if duracion_sec <= 5:
        raise HTTPException(403, detail="El tiempo restante de la sesión es insuficiente para iniciar.")

    ahora_db = fechas.hacia_db(ahora_utc, sin_offset=True)

    # Verificar RF-25 si ya tiene intentos previos
    permiso_extra_id: int | None = None
    next_num = 1
    if participacion is not None:
        previos = list(
            db.scalars(
                select(IntentoModel)
                .where(IntentoModel.id_participacion == participacion.id_participacion)
                .order_by(IntentoModel.numero_intento)
            ).all()
        )
        next_num = (previos[-1].numero_intento + 1) if previos else 1
        if previos:
            permisos = list(
                db.scalars(
                    select(PermisoIntentoExtraORM)
                    .where(PermisoIntentoExtraORM.id_participacion == participacion.id_participacion)
                    .order_by(PermisoIntentoExtraORM.id_permiso_extra)
                ).all()
            )
            permiso_disponible = None
            for p in permisos:
                usos = (
                    db.scalar(
                        select(func.count()).select_from(IntentoModel).where(IntentoModel.id_permiso_extra == p.id_permiso_extra)
                    )
                    or 0
                )
                if usos < p.cantidad_autorizada:
                    permiso_disponible = p
                    break
            if permiso_disponible is None:
                raise HTTPException(
                    409,
                    detail="Ya agotaste tu intento en esta sesión. Solicita a tu docente una autorización excepcional de repetición.",
                )
            permiso_extra_id = permiso_disponible.id_permiso_extra
    else:
        fecha_reg = max(ahora_db, consent.fecha_aceptacion)
        participacion = ParticipacionModel(
            id_asignacion=asignacion.id_asignacion,
            id_grupo_estudiante=matricula.id_grupo_estudiante,
            convocatoria_id=conv.id,
            estado="en_progreso",
            fecha_registro=fecha_reg,
            id_consentimiento=consent.id_consentimiento,
        )
        db.add(participacion)
        db.flush()

    consent_id = participacion.id_consentimiento or consent.id_consentimiento
    intento = IntentoModel(
        id_participacion=participacion.id_participacion,
        id_consentimiento=consent_id,
        id_permiso_extra=permiso_extra_id,
        numero_intento=next_num,
        estado="EN_CURSO",
        inicio=ahora_db,
        fin=None,
        duracion_concedida_segundos=Decimal(f"{duracion_sec:.6f}"),
    )
    db.add(intento)
    db.commit()
    db.refresh(intento)

    return {
        "id_intento": intento.id_intento,
        "numero_intento": intento.numero_intento,
        "estado": intento.estado,
        "retomado": False,
    }


def _verificar_propiedad_intento(
    db: Session,
    *,
    id_intento: int,
    usuario: ContextoAcceso,
    estudiante_uuid: UUID,
) -> tuple[IntentoModel, ParticipacionModel, AsignacionCasoModel, SesionProgramadaModel]:
    intento = db.get(IntentoModel, id_intento)
    if intento is None:
        raise HTTPException(404, detail="Intento no encontrado.")
    part = db.get(ParticipacionModel, intento.id_participacion)
    conv = db.get(ConvocatoriaModel, part.convocatoria_id)
    if conv is None or conv.estudiante_id != estudiante_uuid:
        raise HTTPException(403, detail="Este intento no pertenece al estudiante autenticado.")
    asig = db.get(AsignacionCasoModel, part.id_asignacion)
    sesion = db.get(SesionProgramadaModel, conv.sesion_id)
    return intento, part, asig, sesion


@router.get("/intentos/{id_intento}/workspace")
def obtener_workspace_intento(
    id_intento: int,
    usuario: EstudianteActual,
    estudiante_uuid: EstudianteUUID,
    db: BaseDatos,
    fechas: Fechas,
    crear_sesion: FabricaSesion,
):
    """Espacio de trabajo RF-10/RF-23: muestra escenarios, opciones sin respuestas correctas y borradores editables."""
    intento, part, asig, sesion = _verificar_propiedad_intento(
        db, id_intento=id_intento, usuario=usuario, estudiante_uuid=estudiante_uuid
    )

    ahora_utc = datetime.now(UTC)
    ahora_db = fechas.hacia_db(ahora_utc, sin_offset=True)
    limite_db = _limite_intento_db(intento)

    if intento.estado == "EN_CURSO" and ahora_db >= limite_db:
        cerrar_intento_y_evaluar(
            db,
            intento=intento,
            usuario=usuario,
            fechas=fechas,
            crear_sesion=crear_sesion,
            forzar_vencido=True,
            permitir_parcial=True,
        )
        db.refresh(intento)

    if intento.estado != "EN_CURSO":
        if db.scalar(select(ResultadoIntentoModel.id_resultado).where(ResultadoIntentoModel.id_intento == intento.id_intento)) is None:
            evaluar_e_persistir_intento(
                db,
                usuario=usuario,
                id_intento=intento.id_intento,
                fechas=fechas,
                crear_sesion=crear_sesion,
                modalidad="COMPLETA" if intento.estado == "FINALIZADO" else "PARCIAL",
            )
        return {
            "id_intento": intento.id_intento,
            "estado": intento.estado,
            "cerrado": True,
            "resultado": construir_detalle_resultado_estudiante(db, id_intento=intento.id_intento),
        }

    version = db.get(VersionCasoModel, asig.version_caso_id)
    vence_utc = fechas.desde_db(limite_db)
    segundos_restantes = max(0, int((vence_utc - ahora_utc).total_seconds()))

    escenarios = list(
        db.scalars(select(EscenarioModel).where(EscenarioModel.version_caso_id == version.id).order_by(EscenarioModel.orden)).all()
    )
    borradores = {
        b.id_decision: b
        for b in db.scalars(
            select(BorradorDecisionIntentoModel).where(BorradorDecisionIntentoModel.id_intento == intento.id_intento)
        ).all()
    }
    cambios_count = (
        db.scalar(
            select(func.count())
            .select_from(HistorialCambioDecisionModel)
            .where(HistorialCambioDecisionModel.id_intento == intento.id_intento)
        )
        or 0
    )

    inicial = next((e for e in escenarios if getattr(e, "es_inicial", False)), None)
    tiene_trans = (
        db.scalar(
            select(func.count())
            .select_from(OpcionRespuestaModel)
            .join(PreguntaModel, PreguntaModel.id == OpcionRespuestaModel.pregunta_id)
            .join(EscenarioModel, EscenarioModel.id == PreguntaModel.escenario_id)
            .where(EscenarioModel.version_caso_id == version.id, OpcionRespuestaModel.tipo_transicion.is_not(None))
        )
        or 0
    ) > 0

    escenarios_payload = []
    es_ramificado = False
    listo_para_enviar = False

    if inicial is not None and tiene_trans:
        # Verificar si es grafo de 1 pregunta por escenario para mostrar ruta alcanzada dinámica
        qs_por_esc = {
            e.id: list(
                db.scalars(select(PreguntaModel).where(PreguntaModel.escenario_id == e.id).order_by(PreguntaModel.orden)).all()
            )
            for e in escenarios
        }
        if all(len(qs) == 1 for qs in qs_por_esc.values()):
            es_ramificado = True
            actual = inicial
            visitados = set()
            while actual is not None and actual.id not in visitados:
                visitados.add(actual.id)
                q = qs_por_esc[actual.id][0]
                ops = list(
                    db.scalars(
                        select(OpcionRespuestaModel).where(OpcionRespuestaModel.pregunta_id == q.id).order_by(OpcionRespuestaModel.orden)
                    ).all()
                )
                escenarios_payload.append(
                    {
                        "id": str(actual.id),
                        "orden": actual.orden,
                        "contexto_situacional": actual.contexto_situacional,
                        "preguntas": [
                            {
                                "id": str(q.id),
                                "orden": q.orden,
                                "enunciado": q.enunciado,
                                "opciones": [{"id": str(o.id), "orden": o.orden, "texto": o.texto} for o in ops],
                            }
                        ],
                    }
                )
                b = borradores.get(q.id)
                if b is None:
                    actual = None
                    break
                op_sel = next((o for o in ops if o.id == b.id_opcion), None)
                if op_sel is None or op_sel.tipo_transicion == "FIN":
                    listo_para_enviar = True
                    actual = None
                    break
                if op_sel.tipo_transicion == "ESCENA" and op_sel.escenario_destino_id is not None:
                    actual = next((e for e in escenarios if e.id == op_sel.escenario_destino_id), None)
                else:
                    actual = None

    total_preguntas = 0
    if not es_ramificado:
        for esc in escenarios:
            qs = list(
                db.scalars(select(PreguntaModel).where(PreguntaModel.escenario_id == esc.id).order_by(PreguntaModel.orden)).all()
            )
            qs_out = []
            for q in qs:
                total_preguntas += 1
                ops = list(
                    db.scalars(
                        select(OpcionRespuestaModel).where(OpcionRespuestaModel.pregunta_id == q.id).order_by(OpcionRespuestaModel.orden)
                    ).all()
                )
                qs_out.append(
                    {
                        "id": str(q.id),
                        "orden": q.orden,
                        "enunciado": q.enunciado,
                        "opciones": [{"id": str(o.id), "orden": o.orden, "texto": o.texto} for o in ops],
                    }
                )
            escenarios_payload.append(
                {
                    "id": str(esc.id),
                    "orden": esc.orden,
                    "contexto_situacional": esc.contexto_situacional,
                    "preguntas": qs_out,
                }
            )
        listo_para_enviar = total_preguntas > 0 and len(borradores) >= total_preguntas
    else:
        total_preguntas = len(escenarios_payload)

    return {
        "id_intento": intento.id_intento,
        "numero_intento": intento.numero_intento,
        "convocatoria_id": str(part.convocatoria_id),
        "estado": intento.estado,
        "cerrado": False,
        "modo_recorrido": "RAMIFICADO" if es_ramificado else "LINEAL",
        "caso_nombre": version.nombre,
        "contexto_historia": version.contexto_historia,
        "desarrollo_situacional": version.desarrollo_situacional,
        "inicio": fechas.desde_db(intento.inicio),
        "vence_en": vence_utc,
        "segundos_restantes": segundos_restantes,
        "total_preguntas": total_preguntas,
        "respondidas": len(borradores),
        "listo_para_enviar": listo_para_enviar,
        "cambios_realizados": int(cambios_count),
        "escenarios": escenarios_payload,
        "borradores": {
            str(b.id_decision): {
                "id_opcion": str(b.id_opcion),
                "reflexion_estudiante": b.reflexion_estudiante,
                "actualizado_en": b.actualizado_en,
            }
            for b in borradores.values()
        },
    }


@router.put("/intentos/{id_intento}/borradores/{pregunta_id}")
def guardar_o_modificar_borrador(
    id_intento: int,
    pregunta_id: UUID,
    solicitud: GuardarBorradorRequest,
    usuario: EstudianteActual,
    estudiante_uuid: EstudianteUUID,
    db: BaseDatos,
    fechas: Fechas,
    crear_sesion: FabricaSesion,
):
    """Guarda o modifica libremente la respuesta de una pregunta antes de entregar definitivamente (RF-10)."""
    intento, _, asig, _ = _verificar_propiedad_intento(
        db, id_intento=id_intento, usuario=usuario, estudiante_uuid=estudiante_uuid
    )
    if intento.estado != "EN_CURSO":
        raise HTTPException(409, detail="El intento ya fue cerrado y sus respuestas son definitivas.")

    ahora_utc = datetime.now(UTC)
    ahora_db = fechas.hacia_db(ahora_utc, sin_offset=True)
    if ahora_db >= _limite_intento_db(intento):
        cerrar_intento_y_evaluar(
            db,
            intento=intento,
            usuario=usuario,
            fechas=fechas,
            crear_sesion=crear_sesion,
            forzar_vencido=True,
            permitir_parcial=True,
        )
        raise HTTPException(409, detail="Tiempo máximo agotado; el intento fue cerrado automáticamente.")

    opcion_valida = db.execute(
        select(OpcionRespuestaModel)
        .join(PreguntaModel, PreguntaModel.id == OpcionRespuestaModel.pregunta_id)
        .join(EscenarioModel, EscenarioModel.id == PreguntaModel.escenario_id)
        .where(
            EscenarioModel.version_caso_id == asig.version_caso_id,
            PreguntaModel.id == pregunta_id,
            OpcionRespuestaModel.id == solicitud.id_opcion,
        )
    ).scalar_one_or_none()
    if opcion_valida is None:
        raise HTTPException(422, detail="La opción no corresponde a la pregunta ni al caso asignado.")

    borrador = db.scalar(
        select(BorradorDecisionIntentoModel).where(
            BorradorDecisionIntentoModel.id_intento == id_intento,
            BorradorDecisionIntentoModel.id_decision == pregunta_id,
        )
    )
    cambio_opcion = False
    if borrador is None:
        borrador = BorradorDecisionIntentoModel(
            id_intento=id_intento,
            id_decision=pregunta_id,
            id_opcion=solicitud.id_opcion,
            reflexion_estudiante=solicitud.reflexion_estudiante,
            actualizado_en=ahora_utc,
        )
        db.add(borrador)
        db.add(
            HistorialCambioDecisionModel(
                id_intento=id_intento,
                id_decision=pregunta_id,
                id_opcion_anterior=None,
                id_opcion_nueva=solicitud.id_opcion,
                cambiado_en=ahora_utc,
            )
        )
    else:
        if borrador.id_opcion != solicitud.id_opcion:
            cambio_opcion = True
            db.add(
                HistorialCambioDecisionModel(
                    id_intento=id_intento,
                    id_decision=pregunta_id,
                    id_opcion_anterior=borrador.id_opcion,
                    id_opcion_nueva=solicitud.id_opcion,
                    cambiado_en=ahora_utc,
                )
            )
            borrador.id_opcion = solicitud.id_opcion
        borrador.reflexion_estudiante = solicitud.reflexion_estudiante
        borrador.actualizado_en = ahora_utc

    db.flush()

    # Si cambió de rama en un grafo ramificado, limpiar borradores huérfanos posteriores
    if cambio_opcion and opcion_valida.tipo_transicion is not None:
        todos_borradores = list(
            db.scalars(
                select(BorradorDecisionIntentoModel).where(BorradorDecisionIntentoModel.id_intento == id_intento)
            ).all()
        )
        ruta_valida_ids = {
            b.id_decision
            for b in _ordenar_preguntas_para_cierre(
                db, version_caso_id=asig.version_caso_id, borradores=todos_borradores
            )
        }
        huerfanos = [b.id_borrador for b in todos_borradores if b.id_decision not in ruta_valida_ids]
        if huerfanos:
            db.execute(
                delete(BorradorDecisionIntentoModel).where(BorradorDecisionIntentoModel.id_borrador.in_(huerfanos))
            )

    db.commit()
    return obtener_workspace_intento(id_intento, usuario, estudiante_uuid, db, fechas, crear_sesion)


@router.post("/intentos/{id_intento}/enviar")
def enviar_e_evaluar_intento(
    id_intento: int,
    usuario: EstudianteActual,
    estudiante_uuid: EstudianteUUID,
    db: BaseDatos,
    fechas: Fechas,
    crear_sesion: FabricaSesion,
    solicitud: EnviarIntentoRequest | None = None,
):
    """Confirma la entrega definitiva del intento, congela pasos en BD, calcula nota con rúbrica y devuelve resultados RF-14."""
    intento, _, _, _ = _verificar_propiedad_intento(
        db, id_intento=id_intento, usuario=usuario, estudiante_uuid=estudiante_uuid
    )
    permitir_parcial = solicitud.permitir_parcial if solicitud is not None else False
    cerrar_intento_y_evaluar(
        db,
        intento=intento,
        usuario=usuario,
        fechas=fechas,
        crear_sesion=crear_sesion,
        forzar_vencido=False,
        permitir_parcial=permitir_parcial,
    )
    return construir_detalle_resultado_estudiante(db, id_intento=intento.id_intento)


@router.get("/intentos/{id_intento}/resultado")
def consultar_resultado_intento(
    id_intento: int,
    usuario: EstudianteActual,
    estudiante_uuid: EstudianteUUID,
    db: BaseDatos,
    fechas: Fechas,
    crear_sesion: FabricaSesion,
):
    """Consulta el resultado detallado, justificaciones teóricas y feedback docente de un intento cerrado (RF-14/RF-26)."""
    intento, _, _, sesion = _verificar_propiedad_intento(
        db, id_intento=id_intento, usuario=usuario, estudiante_uuid=estudiante_uuid
    )
    if intento.estado == "EN_CURSO":
        ahora_db = fechas.hacia_db(datetime.now(UTC), sin_offset=True)
        if ahora_db >= _limite_intento_db(intento):
            cerrar_intento_y_evaluar(
                db,
                intento=intento,
                usuario=usuario,
                fechas=fechas,
                crear_sesion=crear_sesion,
                forzar_vencido=True,
                permitir_parcial=True,
            )
            db.refresh(intento)
        else:
            raise HTTPException(409, detail="El intento aún está en curso. Finalízalo primero para ver el resultado.")

    if sesion.mostrar_resultados_provisionales is False and sesion.estado != "FINALIZADO":
        raise HTTPException(
            403,
            detail="El docente restringió temporalmente la visualización provisional hasta el cierre oficial de la sesión.",
        )

    evaluar_e_persistir_intento(
        db,
        usuario=usuario,
        id_intento=intento.id_intento,
        fechas=fechas,
        crear_sesion=crear_sesion,
        modalidad="COMPLETA" if intento.estado == "FINALIZADO" else "PARCIAL",
    )
    return construir_detalle_resultado_estudiante(db, id_intento=intento.id_intento)
