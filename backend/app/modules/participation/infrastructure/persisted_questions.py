"""Operación interna explícita sobre intento cerrado; no conecta cierre ni HTTP."""
from app.modules.participation.infrastructure.evaluation import _unidad, _evidencias_autorizadas
from app.modules.participation.infrastructure.composition import _Alcance
from app.modules.participation.infrastructure.result_repository import RepositorioResultadosTecnicosSQLAlchemy
from app.modules.participation.infrastructure.question_result_repository import DetallesPreguntasSQLAlchemy
from app.modules.participation.infrastructure.question_evaluation import preparar_calculo_historico
from app.modules.cases.infrastructure.scoring import consultar_configuracion_preguntas


def persistir_resultado_preguntas(*,usuario,id_intento,fechas,crear_sesion,reloj):
    t=_unidad(crear_sesion,fechas)
    a=_Alcance(lambda:t.sesion,usuario,id_intento,fechas)
    with t:
        repo=RepositorioResultadosTecnicosSQLAlchemy(t.sesion,alcance=a,fechas=fechas)
        repo._tecnico()
        h=_evidencias_autorizadas(t,a,usuario,id_intento)
        config=consultar_configuracion_preguntas(t.sesion,version_id=h.rubrica.version_id)
        datos=preparar_calculo_historico(h,config)
        resultado=DetallesPreguntasSQLAlchemy(repo).guardar(datos,reloj.ahora())
        t.commit()
        return resultado


def consultar_resultado_tecnico(*,usuario,id_intento,fechas,crear_sesion):
    t=_unidad(crear_sesion,fechas)
    a=_Alcance(lambda:t.sesion,usuario,id_intento,fechas)
    with t:
        _evidencias_autorizadas(t,a,usuario,id_intento)
        return RepositorioResultadosTecnicosSQLAlchemy(t.sesion,alcance=a,fechas=fechas).obtener_tecnico(id_intento=id_intento)
