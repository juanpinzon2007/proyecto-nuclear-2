"""Resultados técnicos inmutables, sin vía de lectura/publicación oficial."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, Context, localcontext
import json

from sqlalchemy import select, text

from app.modules.participation.application.result_provenance import (
    canonico, huella, DefinicionPoliticaLaboratorio, fuentes_motor, motor_compatible, datos_desde, rubrica_desde, plan_desde,
)
from app.modules.participation.application.evaluation_mapping import validar_mapeo_historico
from app.modules.participation.application.errors import RecursoNoDisponible
from app.modules.participation.domain.evaluation import EvaluacionInconsistente, PoliticaEvaluacionPendiente, ContextoEvaluacion, DatosEvaluacion
from app.modules.cases.application.simulation_structure import consultar_estructura_version
from app.modules.participation.domain.calculador_rubrica import CalculadorRubrica
from app.modules.participation.application.evaluation_service import seleccionar_estrategia
from app.modules.participation.infrastructure.evaluation import _evidencias
from app.modules.participation.infrastructure.repository import RepositorioParticipacionSQLAlchemy
from app.modules.participation.infrastructure.result_models import ResultadoIntentoModel as R, ResultadoCriterioModel as C


@dataclass(frozen=True)
class ResultadoTecnico:
    id_resultado: int
    fecha_calculo: datetime
    procedencia: str
    sha256: str
    datos: DatosEvaluacion

    @property
    def oficial(self) -> bool:
        return False


class RepositorioResultadosTecnicosSQLAlchemy:
    def __init__(self, sesion, *, alcance, fechas):
        self.sesion, self.alcance, self.fechas = sesion, alcance, fechas

    def _laboratorio(self):
        if not self.sesion.in_transaction() or self.sesion.get_bind().dialect.name!="postgresql":
            raise PoliticaEvaluacionPendiente("La persistencia técnica exige transacción PostgreSQL de laboratorio.")
        if self.sesion.scalar(text("SELECT current_database()"))!="sps_identity_test_resolver":
            raise PoliticaEvaluacionPendiente("La base no está identificada como laboratorio desechable.")

    def _verificar(self, documento):
        try:
            p=json.loads(documento)
            if canonico(p)!=documento or p["formato"]!=1:
                raise EvaluacionInconsistente("Procedencia no canónica.")
            definicion=DefinicionPoliticaLaboratorio(p["definicion_documento"])
            definicion_datos=json.loads(definicion.documento)
            if (not motor_compatible(p["motor"],p["plan"]["politica"]["formula"]) or p["motor_documento"]!=canonico(p["motor"])
                or definicion_datos.get("motor_sha256")!=huella(p["motor_documento"])):
                raise PoliticaEvaluacionPendiente("El motor histórico requiere su implementación versionada.")
            if not all(definicion_datos.get("implementaciones",{}).get(k) for k in ("clasificacion_calculo","mapeo","recorrido")):
                raise EvaluacionInconsistente("Falta implementación versionada de política.")
            datos=datos_desde(p["datos"]); rubrica=rubrica_desde(p["rubrica"]); plan=plan_desde(p["plan"])
            if not datos.lista_para_persistir or datos.id_intento!=self.alcance.id_intento:
                raise EvaluacionInconsistente("Resultado pendiente o de otro intento.")
            intento=RepositorioParticipacionSQLAlchemy(self.sesion,fechas=self.fechas).obtener_intento(datos.id_intento)
            evidencia=_evidencias(self.alcance,intento)
            preguntas=consultar_estructura_version(self.sesion,version_id=evidencia.rubrica.version_id).preguntas
            if any(e.id_decision not in {q.id for q in preguntas} for e in datos.evidencias):
                raise EvaluacionInconsistente("La evaluación contiene decisiones de otra versión.")
            if canonico(intento)!=canonico(p["intento"]) or canonico(evidencia.rubrica)!=canonico(p["fuente_rubrica"]):
                raise EvaluacionInconsistente("La procedencia no coincide con las fuentes históricas.")
            validar_mapeo_historico(evidencia.rubrica,rubrica)
            contexto=ContextoEvaluacion(rubrica.referencia,datos.id_participacion,datos.modalidad,
                tuple(e.id_decision for e in datos.evidencias),intento)
            preparado=seleccionar_estrategia(datos.modalidad).preparar(contexto)
            if plan.politica.formula.value=="PROMEDIO_IGUALITARIO_100":
                from app.modules.participation.application.academic_policy import PoliticaAcademicaConfirmada
                preguntas=PoliticaAcademicaConfirmada().preguntas_para_evaluar(datos=datos,intento=intento)
                if canonico(preguntas)!=canonico(p.get("preguntas_aplicadas")):
                    raise EvaluacionInconsistente("La procedencia omitió o cambió los ceros de preguntas pendientes.")
            calculo=CalculadorRubrica().calcular(rubrica,plan.niveles,plan.politica)
            if (preparado.evidencias!=datos.evidencias or calculo.criterios!=datos.criterios
                or calculo.nota_final!=datos.nota_final or calculo.politica!=datos.politica_calculo):
                raise EvaluacionInconsistente("El resultado no se reproduce con el plan efectivo.")
            for indice,(valor,maximo) in enumerate([(datos.nota_final,Decimal("1000")),*((c.puntaje_obtenido,Decimal(1000)) for c in datos.criterios)]):
                with localcontext(Context(prec=32)):
                    if valor>=maximo or (indice==0 and valor>Decimal(100)) or valor!=valor.quantize(Decimal(".01")):
                        raise EvaluacionInconsistente("La precisión del resultado no cabe exactamente en el ER; no se redondea al guardar.")
            return datos,definicion,evidencia
        except (EvaluacionInconsistente,PoliticaEvaluacionPendiente):
            raise
        except (KeyError,ValueError,TypeError,AttributeError) as error:
            raise EvaluacionInconsistente("Procedencia incompleta o corrupta.") from error

    def guardar_tecnico(self, *, datos, procedencia, fecha_calculo):
        self._laboratorio()
        verificados,definicion,evidencia=self._verificar(procedencia)
        if verificados!=datos:
            raise EvaluacionInconsistente("Datos y procedencia difieren.")
        if fecha_calculo.tzinfo is None or fecha_calculo.utcoffset() is None:
            raise EvaluacionInconsistente("La fecha de cálculo debe venir de un reloj consciente de zona.")
        d=json.loads(definicion.documento);f=evidencia.rubrica
        identificador=self.sesion.scalar(R.__table__.insert().values(id_intento=datos.id_intento,
            nota_final=datos.nota_final,fecha_calculo=fecha_calculo,id_caso=f.id_caso_academico,
            caso_id=f.caso_id,version_caso_id=f.version_id,rubrica_id=f.rubrica_id,version_regla=f.version_regla,
            modalidad=datos.modalidad.value,ambito="LABORATORIO",politica_id=d["id"],politica_version=d["version"],
            politica_hash=huella(definicion.documento),procedencia=procedencia,procedencia_sha256=huella(procedencia))
            .returning(R.id_resultado))
        for c in datos.criterios:
            self.sesion.execute(C.__table__.insert().values(id_resultado=identificador,rubrica_id=f.rubrica_id,
                id_criterio=c.id_criterio,id_nivel=c.id_nivel,puntaje_obtenido=c.puntaje_obtenido))
        return ResultadoTecnico(identificador,fecha_calculo,procedencia,huella(procedencia),datos)

    def obtener_tecnico(self, *, id_intento):
        self._laboratorio()
        r=self.sesion.execute(select(R.__table__).where(R.id_intento==id_intento)).mappings().one_or_none()
        if r is None: raise RecursoNoDisponible("Resultado técnico no disponible.")
        if r["ambito"]!="LABORATORIO" or huella(r["procedencia"])!=r["procedencia_sha256"]:
            raise EvaluacionInconsistente("Ámbito o huella del resultado incompatible.")
        datos,definicion,ev=self._verificar(r["procedencia"])
        d=json.loads(definicion.documento); f=ev.rubrica
        if (r["id_intento"],r["nota_final"],r["modalidad"],r["id_caso"],r["caso_id"],r["version_caso_id"],r["rubrica_id"],r["version_regla"],r["politica_id"],r["politica_version"],r["politica_hash"])!=(datos.id_intento,datos.nota_final,datos.modalidad.value,f.id_caso_academico,f.caso_id,f.version_id,f.rubrica_id,f.version_regla,d["id"],d["version"],huella(definicion.documento)):
            raise EvaluacionInconsistente("La cabecera almacenada difiere de la procedencia.")
        detalles=self.sesion.execute(select(C.id_criterio,C.id_nivel,C.puntaje_obtenido).where(C.id_resultado==r["id_resultado"])).all()
        if set(detalles)!={(c.id_criterio,c.id_nivel,c.puntaje_obtenido) for c in datos.criterios}:
            raise EvaluacionInconsistente("El detalle almacenado difiere de la procedencia.")
        return ResultadoTecnico(r["id_resultado"],r["fecha_calculo"],r["procedencia"],r["procedencia_sha256"],datos)

    def obtener_definitiva(self, **_):
        # Este repositorio jamás hace pasar un laboratorio por resultado oficial.
        return None

    def agregar_definitiva(self, *_):
        raise PoliticaEvaluacionPendiente("El repositorio técnico no publica ni confirma notas oficiales.")
