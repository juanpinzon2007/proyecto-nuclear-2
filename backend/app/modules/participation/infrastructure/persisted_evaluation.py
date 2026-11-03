"""Caso de uso técnico opt-in. No instalado en Facade/API productiva."""
import inspect
import json

from app.modules.participation.application.evaluation_service import ServicioEvaluacion
from app.modules.participation.application.services import _cargar_autorizado
from app.modules.participation.application.result_provenance import canonico, huella, fuentes_motor, DefinicionPoliticaLaboratorio
from app.modules.participation.domain.evaluation import PoliticaEvaluacionPendiente
from app.modules.participation.infrastructure.composition import _Alcance, IdentityIntentoSQLAlchemy, SchedulingIntentoSQLAlchemy
from app.modules.participation.infrastructure.evaluation import CasesEvaluacionSQLAlchemy, _PoliticaBaseDocumentada, _evidencias
from app.modules.participation.infrastructure.repository import RepositorioParticipacionSQLAlchemy
from app.modules.participation.infrastructure.result_repository import RepositorioResultadosTecnicosSQLAlchemy
from app.modules.participation.infrastructure.unit_of_work import UnidadTrabajoSQLAlchemy


class _CapturaPolitica:
    def __init__(self, politica): self.politica=politica
    def clasificar(self, **kw): return self.politica.clasificar(**kw)
    def preparar_calculo(self, *, datos, rubrica):
        self.rubrica=rubrica
        self.plan=self.politica.preparar_calculo(datos=datos,rubrica=rubrica)
        return self.plan

    def preparar_calculo_para_intento(self, *, datos, rubrica, intento):
        self.rubrica=rubrica
        contextual=getattr(self.politica,"preparar_calculo_para_intento",None)
        self.plan=(contextual(datos=datos,rubrica=rubrica,intento=intento) if contextual is not None
            else self.politica.preparar_calculo(datos=datos,rubrica=rubrica))
        return self.plan


class EvaluacionPersistenteLaboratorio:
    """Una operación por instancia. Los autorizadores y repositorios comparten UoW."""
    def __init__(self, *, usuario, id_intento, fechas, crear_sesion, reloj,
                 definicion: DefinicionPoliticaLaboratorio, politica, mapeo, recorrido):
        if not isinstance(definicion,DefinicionPoliticaLaboratorio):
            raise PoliticaEvaluacionPendiente("Falta definición inmutable de laboratorio.")
        self.usuario,self.id_intento,self.reloj,self.definicion=usuario,id_intento,reloj,definicion
        self.politica,self.mapeo,self.recorrido=politica,mapeo,recorrido
        self.trabajo=UnidadTrabajoSQLAlchemy(lambda s:RepositorioParticipacionSQLAlchemy(s,fechas=fechas),
            crear_sesion=crear_sesion,crear_resultados=lambda s:RepositorioResultadosTecnicosSQLAlchemy(s,alcance=self.alcance,fechas=fechas))
        self.alcance=_Alcance(lambda:self.trabajo.sesion,usuario,id_intento,fechas)
        self.identity=IdentityIntentoSQLAlchemy(self.alcance)

    def evaluar(self, *, id_estudiante):
        with self.trabajo as t:
            t.resultados._laboratorio()  # No calcular/escribir sobre una base no identificada.
            intento,participacion=_cargar_autorizado(t.repositorio,self.identity,id_estudiante,self.id_intento)
            captura=_CapturaPolitica(self.politica)
            servicio=ServicioEvaluacion(lambda:t,self.identity,SchedulingIntentoSQLAlchemy(self.alcance,None,None),
                CasesEvaluacionSQLAlchemy(self.alcance,self.recorrido,self.mapeo),captura,_PoliticaBaseDocumentada())
            datos=servicio._preparar_intento(intento,participacion)
            if not datos.lista_para_persistir:
                raise PoliticaEvaluacionPendiente("No se persiste una evaluación pendiente.")
            fuente=_evidencias(self.alcance,intento).rubrica
            motor=fuentes_motor()
            definicion=json.loads(self.definicion.documento)
            definicion["implementaciones"]={k:inspect.getsource(type(v)) for k,v in
                (("clasificacion_calculo",self.politica),("mapeo",self.mapeo),("recorrido",self.recorrido))}
            for atributo in ("resolucion",):
                dependencia=getattr(self.politica,atributo,None)
                if dependencia is not None:
                    definicion["implementaciones"][atributo]=inspect.getsource(type(dependencia))
            base=getattr(self.mapeo,"base",None)
            if base is not None: definicion["implementaciones"]["base_mapeo"]=inspect.getsource(type(base))
            definicion["motor_sha256"]=huella(canonico(motor))
            contenido=dict(formato=1,definicion_documento=canonico(definicion),
                datos=datos,intento=intento,fuente_rubrica=fuente,rubrica=captura.rubrica,plan=captura.plan,
                motor=motor,motor_documento=canonico(motor))
            preguntas=getattr(self.politica,"preguntas_para_evaluar",None)
            if preguntas is not None:
                contenido["preguntas_aplicadas"]=preguntas(datos=datos,intento=intento)
            documento=canonico(contenido)
            resultado=t.resultados.guardar_tecnico(datos=datos,procedencia=documento,fecha_calculo=self.reloj.ahora())
            t.commit()
            return resultado

    def consultar(self, *, id_estudiante):
        with self.trabajo as t:
            _cargar_autorizado(t.repositorio,self.identity,id_estudiante,self.id_intento)
            return t.resultados.obtener_tecnico(id_intento=self.id_intento)
