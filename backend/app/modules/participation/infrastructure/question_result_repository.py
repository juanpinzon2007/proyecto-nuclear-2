"""Extensión del repositorio técnico: misma cabecera, detalles sin niveles."""
from dataclasses import replace
from decimal import Decimal
from uuid import UUID
import json

from sqlalchemy import select
from app.modules.participation.application.result_provenance import huella
from app.modules.participation.application.errors import ConflictoActualizacion
from app.modules.participation.domain.evaluation import EvaluacionInconsistente
from app.modules.participation.infrastructure.result_models import ResultadoIntentoModel as R
from app.modules.participation.infrastructure.question_result_models import (
    ResultadoCalculoPreguntasModel as G, ResultadoPreguntaModel as Q, ResultadoCriterioExactoModel as C,
)


class DetallesPreguntasSQLAlchemy:
    """La autorización y el commit pertenecen a la misma UoW del consumidor."""
    def __init__(self, repositorio):
        self.base=repositorio
        self.s= repositorio.sesion

    def reproducir(self,id_intento):
        from app.modules.participation.infrastructure.repository import RepositorioParticipacionSQLAlchemy
        from app.modules.participation.infrastructure.evaluation import _evidencias
        from app.modules.participation.infrastructure.question_evaluation import preparar_calculo_historico
        from app.modules.cases.infrastructure.scoring import consultar_configuracion_preguntas
        lector=self.base.lecturas if self.base.lecturas is not None else RepositorioParticipacionSQLAlchemy(self.s,fechas=self.base.fechas)
        intento=lector.obtener_intento(id_intento)
        historico=_evidencias(self.base.alcance,intento)
        config=consultar_configuracion_preguntas(self.s,version_id=historico.rubrica.version_id)
        return preparar_calculo_historico(historico,config)

    def guardar(self,datos,fecha_calculo):
        self.base._tecnico()
        if fecha_calculo.tzinfo is None or fecha_calculo.utcoffset() is None:
            raise EvaluacionInconsistente('Reloj con zona explícita requerido.')
        if datos.id_intento!=self.base.alcance.id_intento or self.reproducir(datos.id_intento)!=datos:
            raise EvaluacionInconsistente('El cálculo no coincide con las fuentes históricas.')
        anterior=self.s.execute(select(R.__table__).where(R.id_intento==datos.id_intento)).mappings().one_or_none()
        if anterior is not None:
            if anterior['ambito']!='TECNICO' or anterior['version_regla']!='PREGUNTAS_100_V1':
                raise ConflictoActualizacion('El intento ya conserva un resultado de otro motor.')
            r=self.leer(anterior)
            if r.procedencia!=datos.procedencia:
                raise ConflictoActualizacion('No se recalifica un resultado histórico.')
            return r
        j=json.loads(datos.procedencia);f=j['rubrica'];e=j['exacto']
        rid=self.s.scalar(R.__table__.insert().values(id_intento=datos.id_intento,nota_final=datos.nota_final,
            fecha_calculo=fecha_calculo,id_caso=f['id_caso_academico'],caso_id=UUID(f['caso_id']),
            version_caso_id=UUID(f['version_id']),rubrica_id=UUID(f['rubrica_id']),version_regla=f['version_regla'],
            modalidad=datos.modalidad.value,ambito='TECNICO',politica_id='PREGUNTAS_100_V1',politica_version='1',
            politica_hash=huella(j['politica_documento']),procedencia=datos.procedencia,procedencia_sha256=datos.sha256).returning(R.id_resultado))
        self.s.execute(G.__table__.insert().values(id_resultado=rid,suma_puntajes=Decimal(e['suma_puntajes']),
            preguntas_exigidas=e['preguntas_exigidas'],preguntas_respondidas=e['preguntas_respondidas'],
            preguntas_pendientes=e['preguntas_pendientes'],configuracion_sha256=huella(j['configuracion_documento'])))
        for q in e['preguntas']:
            self.s.execute(Q.__table__.insert().values(id_resultado=rid,pregunta_id=UUID(q['pregunta_id']),
                opcion_id=UUID(q['opcion_id']),puntaje=Decimal(q['puntaje']),numero_paso=q['numero_paso']))
        for c in e['criterios']:
            self.s.execute(C.__table__.insert().values(id_resultado=rid,rubrica_id=UUID(f['rubrica_id']),
                criterio_id=UUID(c['criterio_id']),suma_puntajes=Decimal(c['suma_puntajes']),preguntas_evaluables=c['preguntas_evaluables'],
                numerador=Decimal(c['numerador']),denominador=Decimal(c['denominador'])))
        fila=self.s.execute(select(R.__table__).where(R.id_resultado==rid)).mappings().one()
        return self.leer(fila)

    def leer(self,r):
        from app.modules.participation.infrastructure.result_repository import ResultadoTecnico
        datos=self.reproducir(r['id_intento'])
        if r['procedencia']!=datos.procedencia or r['procedencia_sha256']!=datos.sha256:
            raise EvaluacionInconsistente('Procedencia histórica modificada o motor no reproducible.')
        j=json.loads(datos.procedencia);f=j['rubrica'];e=j['exacto'];rid=r['id_resultado']
        if (r['ambito'],r['nota_final'],r['modalidad'],str(r['version_caso_id']),str(r['caso_id']),r['id_caso'],str(r['rubrica_id']),r['politica_id'],r['politica_version'],r['politica_hash']) != (
            'TECNICO',datos.nota_final,datos.modalidad.value,f['version_id'],f['caso_id'],f['id_caso_academico'],f['rubrica_id'],'PREGUNTAS_100_V1','1',huella(j['politica_documento'])):
            raise EvaluacionInconsistente('Cabecera incompatible con el cálculo exacto.')
        g=self.s.execute(select(G.__table__).where(G.id_resultado==rid)).mappings().one_or_none()
        esperado=dict(id_resultado=rid,suma_puntajes=Decimal(e['suma_puntajes']),preguntas_exigidas=e['preguntas_exigidas'],
            preguntas_respondidas=e['preguntas_respondidas'],preguntas_pendientes=e['preguntas_pendientes'],configuracion_sha256=huella(j['configuracion_documento']))
        qs=self.s.execute(select(Q.__table__).where(Q.id_resultado==rid).order_by(Q.numero_paso)).mappings().all()
        cs=self.s.execute(select(C.__table__).where(C.id_resultado==rid)).mappings().all()
        if (g is None or dict(g)!=esperado or len(qs)!=len(e['preguntas']) or len(cs)!=len(e['criterios'])
            or any((str(q['pregunta_id']),str(q['opcion_id']),q['puntaje'],q['numero_paso'])!=(v['pregunta_id'],v['opcion_id'],Decimal(v['puntaje']),v['numero_paso']) for q,v in zip(qs,e['preguntas']))
            or {(str(c['criterio_id']),str(c['rubrica_id']),c['suma_puntajes'],c['preguntas_evaluables'],c['numerador'],c['denominador']) for c in cs} !=
               {(c['criterio_id'],f['rubrica_id'],Decimal(c['suma_puntajes']),c['preguntas_evaluables'],Decimal(c['numerador']),Decimal(c['denominador'])) for c in e['criterios']}):
            raise EvaluacionInconsistente('Detalle persistido no corresponde al cálculo exacto.')
        return ResultadoTecnico(rid,r['fecha_calculo'],datos.procedencia,datos.sha256,replace(datos,persistido=True),ambito='TECNICO')
