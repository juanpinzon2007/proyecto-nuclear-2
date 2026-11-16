"""Motor de calificación completo (PREGUNTAS_100_V1 + RUBRICA_V1 ponderada con niveles) y construcción de resultado RF-13/RF-14."""

from datetime import UTC, datetime
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.modules.cases.infrastructure.models.caso import (
    CasoModel,
    EscenarioModel,
    OpcionRespuestaModel,
    PreguntaModel,
    VersionCasoModel,
)
from app.modules.cases.infrastructure.models.rubrica import (
    CriterioRubricaModel,
    NivelRubricaModel,
    RubricaModel,
    ValoracionOpcionModel,
)
from app.modules.identity.domain.entities import ContextoAcceso
from app.modules.identity.infrastructure.academic_models import RetroalimentacionDocenteORM
from app.modules.participation.application.result_provenance import canonico, huella
from app.modules.participation.infrastructure.codecs import FechasPersistencia
from app.modules.participation.infrastructure.models import (
    IntentoModel,
    ParticipacionModel,
    PasoSimulacionModel,
)
from app.modules.participation.infrastructure.question_evaluation import calcular_intento_por_preguntas
from app.modules.participation.infrastructure.question_result_models import ResultadoCalculoPreguntasModel
from app.modules.participation.infrastructure.result_models import ResultadoCriterioModel, ResultadoIntentoModel
from app.modules.scheduling.infrastructure.assignment_models import AsignacionCasoModel


def _q2(valor: Decimal) -> Decimal:
    return valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _seleccionar_nivel(niveles: list[NivelRubricaModel], puntaje: Decimal) -> NivelRubricaModel:
    ordenados = sorted(niveles, key=lambda n: n.puntaje)
    elegido = ordenados[0]
    for nivel in ordenados:
        if nivel.puntaje <= puntaje:
            elegido = nivel
    return elegido


def _total_preguntas_esperadas(db: Session, *, version_caso_id: UUID, pasos: list[PasoSimulacionModel]) -> int:
    escenarios = db.scalars(
        select(EscenarioModel).where(EscenarioModel.version_caso_id == version_caso_id).order_by(EscenarioModel.orden)
    ).all()
    if not escenarios:
        return max(1, len(pasos))

    preguntas_por_escena: dict[UUID, list[PreguntaModel]] = {}
    for esc in escenarios:
        qs = list(
            db.scalars(select(PreguntaModel).where(PreguntaModel.escenario_id == esc.id).order_by(PreguntaModel.orden)).all()
        )
        preguntas_por_escena[esc.id] = qs

    todas_preguntas = sum(len(qs) for qs in preguntas_por_escena.values())
    if todas_preguntas == 0:
        return max(1, len(pasos))

    # Detectar si tiene grafo configurado con 1 pregunta por escenario y transiciones
    inicial = next((e for e in escenarios if getattr(e, "es_inicial", False)), None)
    tiene_transiciones = (
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

    if inicial is not None and tiene_transiciones and all(len(qs) <= 1 for qs in preguntas_por_escena.values()):
        # Si ya llegó a FIN siguiendo el grafo, las preguntas exigidas son exactamente los pasos de esa ruta;
        # si quedó incompleto o vencido, estimar ruta máxima alcanzable para asignar 0 a pendientes.
        por_pregunta = {p.id_decision: p for p in pasos}
        actual = inicial
        visitados = set()
        recorrido = 0
        llego_fin = False
        while actual is not None and actual.id not in visitados:
            visitados.add(actual.id)
            qs = preguntas_por_escena.get(actual.id, [])
            if not qs:
                break
            q = qs[0]
            recorrido += 1
            paso = por_pregunta.get(q.id)
            if paso is None:
                break
            op = db.get(OpcionRespuestaModel, paso.id_opcion)
            if op is None:
                break
            if op.tipo_transicion == "FIN":
                llego_fin = True
                break
            if op.tipo_transicion == "ESCENA" and op.escenario_destino_id is not None:
                actual = next((e for e in escenarios if e.id == op.escenario_destino_id), None)
            else:
                actual = None
        if llego_fin and recorrido > 0:
            return recorrido
        return max(len(pasos), len([e for e in escenarios if preguntas_por_escena.get(e.id)]))

    return max(todas_preguntas, len(pasos))


def _persistir_rubrica_ponderada(
    db: Session,
    *,
    intento: IntentoModel,
    modalidad: str,
) -> ResultadoIntentoModel:
    existente = db.scalar(select(ResultadoIntentoModel).where(ResultadoIntentoModel.id_intento == intento.id_intento))
    if existente is not None:
        return existente

    participacion = db.get(ParticipacionModel, intento.id_participacion)
    asignacion = db.get(AsignacionCasoModel, participacion.id_asignacion)
    version = db.get(VersionCasoModel, asignacion.version_caso_id)
    caso_id_academico = db.scalar(select(CasoModel.id_caso).where(CasoModel.id == version.caso_id))
    rubrica = db.scalar(select(RubricaModel).where(RubricaModel.version_caso_id == version.id))
    if rubrica is None or caso_id_academico is None:
        raise RuntimeError("El caso no tiene rúbrica o identificador académico configurado.")

    criterios = list(
        db.scalars(select(CriterioRubricaModel).where(CriterioRubricaModel.rubrica_id == rubrica.id)).all()
    )
    if not criterios:
        raise RuntimeError("La rúbrica no contiene criterios configurados.")

    pasos = list(
        db.scalars(
            select(PasoSimulacionModel)
            .where(PasoSimulacionModel.id_intento == intento.id_intento)
            .order_by(PasoSimulacionModel.numero_paso)
        ).all()
    )
    total_esperadas = _total_preguntas_esperadas(db, version_caso_id=version.id, pasos=pasos)

    peso_total = sum((Decimal(c.peso) for c in criterios), Decimal("0"))
    if peso_total <= 0:
        peso_total = Decimal("100")

    nota_acumulada = Decimal("0.00")
    detalles_criterios: list[tuple[CriterioRubricaModel, NivelRubricaModel, Decimal, Decimal]] = []

    for criterio in criterios:
        niveles = list(
            db.scalars(select(NivelRubricaModel).where(NivelRubricaModel.criterio_id == criterio.id)).all()
        )
        if not niveles:
            raise RuntimeError(f"El criterio '{criterio.nombre}' no tiene niveles configurados.")

        suma_criterio = Decimal("0")
        for paso in pasos:
            val = db.get(ValoracionOpcionModel, (paso.id_opcion, criterio.id))
            if val is not None:
                puntaje_opcion = Decimal(val.puntaje)
            else:
                op = db.get(OpcionRespuestaModel, paso.id_opcion)
                puntaje_opcion = Decimal("100") if (op is not None and op.es_correcta) else Decimal("0")
            suma_criterio += max(Decimal("0"), min(Decimal("100"), puntaje_opcion))

        promedio_criterio = _q2(suma_criterio / Decimal(max(1, total_esperadas)))
        nivel_elegido = _seleccionar_nivel(niveles, promedio_criterio)
        aporte_ponderado = _q2(promedio_criterio * Decimal(criterio.peso) / peso_total)
        nota_acumulada += aporte_ponderado
        detalles_criterios.append((criterio, nivel_elegido, promedio_criterio, aporte_ponderado))

    nota_final = max(Decimal("0.00"), min(Decimal("100.00"), _q2(nota_acumulada)))
    mod_valida = "COMPLETA" if (modalidad == "COMPLETA" and intento.estado == "FINALIZADO") else "PARCIAL"

    politica_doc = canonico(
        dict(
            id="RUBRICA_PONDERADA_V1",
            version="1",
            regla=rubrica.version_regla,
            formula="sum(peso_i * (sum(valoracion_pasos)/preguntas_esperadas))",
            pendientes="CERO_SI_INCOMPLETO",
        )
    )
    procedencia_doc = canonico(
        dict(
            formato="rubrica-ponderada-v1",
            id_intento=intento.id_intento,
            id_participacion=intento.id_participacion,
            modalidad=mod_valida,
            total_esperadas=total_esperadas,
            respondidas=len(pasos),
            nota_final=str(nota_final),
            rubrica=dict(rubrica_id=str(rubrica.id)),
            criterios=[
                dict(
                    id_criterio=str(c.id),
                    nombre=c.nombre,
                    peso=str(c.peso),
                    id_nivel=str(niv.id),
                    nivel_nombre=niv.nombre,
                    puntaje_obtenido=str(prom),
                    aporte_ponderado=str(pond),
                )
                for c, niv, prom, pond in detalles_criterios
            ],
        )
    )

    resultado = ResultadoIntentoModel(
        id_intento=intento.id_intento,
        nota_final=nota_final,
        fecha_calculo=datetime.now(UTC),
        comentario_automatico=(
            f"Evaluación {mod_valida.lower()}: {len(pasos)}/{total_esperadas} decisiones registradas. Nota: {nota_final}/100."
        ),
        id_caso=caso_id_academico,
        caso_id=version.caso_id,
        version_caso_id=version.id,
        rubrica_id=rubrica.id,
        version_regla=rubrica.version_regla,
        modalidad=mod_valida,
        ambito="RUBRICA_V1",
        politica_id="RUBRICA_PONDERADA_V1",
        politica_version="1",
        politica_hash=huella(politica_doc),
        procedencia=procedencia_doc,
        procedencia_sha256=huella(procedencia_doc),
    )
    db.add(resultado)
    db.flush()

    for criterio, nivel_elegido, promedio_criterio, _ in detalles_criterios:
        db.add(
            ResultadoCriterioModel(
                id_resultado=resultado.id_resultado,
                rubrica_id=rubrica.id,
                id_criterio=criterio.id,
                id_nivel=nivel_elegido.id,
                puntaje_obtenido=promedio_criterio,
            )
        )
    db.commit()
    db.refresh(resultado)
    return resultado


def evaluar_e_persistir_intento(
    db: Session,
    *,
    usuario: ContextoAcceso,
    id_intento: int,
    fechas: FechasPersistencia,
    crear_sesion: sessionmaker[Session],
    modalidad: str = "COMPLETA",
) -> ResultadoIntentoModel:
    """Evalúa un intento cerrado usando PREGUNTAS_100_V1 cuando aplica o evaluación ponderada RUBRICA_V1."""
    existente = db.scalar(select(ResultadoIntentoModel).where(ResultadoIntentoModel.id_intento == id_intento))
    if existente is not None:
        return existente

    intento = db.get(IntentoModel, id_intento)
    if intento is None:
        raise RuntimeError("Intento no encontrado para evaluación.")

    participacion = db.get(ParticipacionModel, intento.id_participacion)
    asignacion = db.get(AsignacionCasoModel, participacion.id_asignacion)
    rubrica = db.scalar(select(RubricaModel).where(RubricaModel.version_caso_id == asignacion.version_caso_id))

    if rubrica is not None and rubrica.version_regla == "PREGUNTAS_100_V1":
        try:
            calcular_intento_por_preguntas(
                usuario=usuario,
                id_intento=id_intento,
                fechas=fechas,
                crear_sesion=crear_sesion,
            )
            db.expire_all()
            creado = db.scalar(select(ResultadoIntentoModel).where(ResultadoIntentoModel.id_intento == id_intento))
            if creado is not None:
                return creado
        except Exception:
            # Fallback limpio a evaluación ponderada multi-pregunta / criterios personalizados
            db.rollback()

    intento_recargado = db.get(IntentoModel, id_intento)
    return _persistir_rubrica_ponderada(db, intento=intento_recargado, modalidad=modalidad)


def construir_detalle_resultado_estudiante(db: Session, *, id_intento: int) -> dict:
    """Construye la vista RF-14 completa: nota final, criterios, respuestas elegidas, aciertos y justificaciones."""
    intento = db.get(IntentoModel, id_intento)
    participacion = db.get(ParticipacionModel, intento.id_participacion)
    asignacion = db.get(AsignacionCasoModel, participacion.id_asignacion)
    version = db.get(VersionCasoModel, asignacion.version_caso_id)
    resultado = db.scalar(select(ResultadoIntentoModel).where(ResultadoIntentoModel.id_intento == id_intento))
    rubrica = db.get(RubricaModel, resultado.rubrica_id) if resultado else db.scalar(
        select(RubricaModel).where(RubricaModel.version_caso_id == version.id)
    )

    pasos = list(
        db.scalars(
            select(PasoSimulacionModel)
            .where(PasoSimulacionModel.id_intento == id_intento)
            .order_by(PasoSimulacionModel.numero_paso)
        ).all()
    )
    pasos_por_pregunta = {p.id_decision: p for p in pasos}

    escenarios = list(
        db.scalars(
            select(EscenarioModel).where(EscenarioModel.version_caso_id == version.id).order_by(EscenarioModel.orden)
        ).all()
    )

    preguntas_out: list[dict] = []
    aciertos = 0
    total_respondidas = len(pasos)
    total_preguntas = 0

    for esc in escenarios:
        qs = list(
            db.scalars(select(PreguntaModel).where(PreguntaModel.escenario_id == esc.id).order_by(PreguntaModel.orden)).all()
        )
        for q in qs:
            total_preguntas += 1
            paso = pasos_por_pregunta.get(q.id)
            opciones = list(
                db.scalars(select(OpcionRespuestaModel).where(OpcionRespuestaModel.pregunta_id == q.id).order_by(OpcionRespuestaModel.orden)).all()
            )
            elegida = next((o for o in opciones if paso and o.id == paso.id_opcion), None)
            correcta = next((o for o in opciones if o.es_correcta), None)
            if elegida is not None and elegida.es_correcta:
                aciertos += 1

            # Si es grafo ramificado con preguntas inalcanzables no respondidas, solo incluir escenarios relevantes o mostrar todas
            preguntas_out.append(
                {
                    "pregunta_id": str(q.id),
                    "escenario_orden": esc.orden,
                    "escenario_contexto": esc.contexto_situacional,
                    "enunciado": q.enunciado,
                    "respondida": elegida is not None,
                    "opcion_elegida_id": str(elegida.id) if elegida else None,
                    "opcion_elegida_texto": elegida.texto if elegida else "Sin responder (0 pts)",
                    "es_correcta": bool(elegida.es_correcta) if elegida else False,
                    "justificacion_elegida": elegida.justificacion if elegida else "Pregunta sin respuesta al finalizar/vencer el tiempo.",
                    "opcion_correcta_texto": correcta.texto if correcta else None,
                    "justificacion_correcta": correcta.justificacion if correcta else None,
                    "reflexion_estudiante": paso.reflexion_estudiante if paso else None,
                }
            )

    criterios_out: list[dict] = []
    if resultado is not None and rubrica is not None:
        criterios_db = list(
            db.scalars(select(CriterioRubricaModel).where(CriterioRubricaModel.rubrica_id == rubrica.id)).all()
        )
        res_criterios = {
            rc.id_criterio: rc
            for rc in db.scalars(
                select(ResultadoCriterioModel).where(ResultadoCriterioModel.id_resultado == resultado.id_resultado)
            ).all()
        }
        for c in criterios_db:
            niveles = list(
                db.scalars(select(NivelRubricaModel).where(NivelRubricaModel.criterio_id == c.id)).all()
            )
            rc = res_criterios.get(c.id)
            if rc is not None:
                niv = db.get(NivelRubricaModel, rc.id_nivel)
                puntaje_val = float(rc.puntaje_obtenido)
            else:
                puntaje_val = float(resultado.nota_final)
                niv = _seleccionar_nivel(niveles, Decimal(str(puntaje_val))) if niveles else None

            criterios_out.append(
                {
                    "id_criterio": str(c.id),
                    "nombre": c.nombre,
                    "peso": float(c.peso),
                    "puntaje_obtenido": puntaje_val,
                    "nivel_nombre": niv.nombre if niv else "Evaluado",
                    "nivel_descriptor": niv.descriptor if niv else "",
                }
            )

    retro = db.scalar(
        select(RetroalimentacionDocenteORM).where(
            RetroalimentacionDocenteORM.id_participacion == participacion.id_participacion
        )
    )

    rcp = (
        db.get(ResultadoCalculoPreguntasModel, resultado.id_resultado)
        if resultado is not None and resultado.ambito == "TECNICO"
        else None
    )

    return {
        "id_intento": intento.id_intento,
        "id_participacion": participacion.id_participacion,
        "convocatoria_id": str(participacion.convocatoria_id),
        "estado_intento": intento.estado,
        "estado_participacion": participacion.estado,
        "caso_nombre": version.nombre,
        "rubrica_nombre": rubrica.nombre if rubrica else "Rúbrica del caso",
        "nota_final": float(resultado.nota_final) if resultado else 0.0,
        "modalidad": resultado.modalidad if resultado else "PARCIAL",
        "comentario_automatico": resultado.comentario_automatico if resultado else "",
        "fecha_calculo": resultado.fecha_calculo if resultado else intento.fin,
        "aciertos": aciertos,
        "respondidas": total_respondidas,
        "total_preguntas": rcp.preguntas_exigidas if rcp else total_preguntas,
        "criterios": criterios_out,
        "preguntas": preguntas_out,
        "retroalimentacion_docente": retro.texto if retro else None,
        "fecha_retroalimentacion": retro.fecha_registro if retro else None,
    }
