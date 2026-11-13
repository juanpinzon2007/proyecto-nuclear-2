"""Comando explícito docente; nunca se ejecuta desde finish ni desde un GET."""
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from app.modules.identity.domain.errors import AccesoDenegado, ConflictoIdentidad, IntegracionPendiente
from app.modules.participation.application.errors import AccesoDenegado as AccesoParticipacion, ConflictoActualizacion, ErrorAplicacionParticipacion
from app.modules.participation.domain.entities import EstadoIntento
from app.modules.participation.domain.evaluation import EvaluacionInconsistente, PoliticaEvaluacionPendiente
from app.modules.participation.infrastructure.evaluation import _unidad, _evidencias
from app.modules.participation.infrastructure.composition import _Alcance
from app.modules.participation.infrastructure.models import IntentoModel as I
from app.modules.participation.infrastructure.individual_feedback import AmbitoFeedbackIndividual
from app.modules.participation.infrastructure.result_models import ResultadoIntentoModel as R
from app.modules.participation.infrastructure.result_repository import RepositorioResultadosTecnicosSQLAlchemy
from app.modules.participation.infrastructure.question_result_repository import DetallesPreguntasSQLAlchemy
from app.modules.cases.infrastructure.scoring import consultar_configuracion_preguntas
from app.modules.cases.application.graph import GrafoNoDisponible
from app.modules.cases.infrastructure.models import CasoModel as C, VersionCasoModel as V
from app.modules.identity.domain.errors import ReglaIdentidadInvalida
from app.modules.participation.application.closed_attempt_recovery import IntentoRecuperado, RecuperacionCierres


class EvaluadorTecnicoDocente:
    def __init__(self, *, consulta, reloj):
        self.consulta, self.reloj = consulta, reloj

    def recuperar_cierres(self, *, id_sesion: UUID, ids_intentos: tuple[int, ...]) -> RecuperacionCierres:
        """Procesa una selección explícita sobre cierres persistidos recuperables.

        La consulta inicial verifica la cohorte completa en una instantánea de
        lectura. Cada elemento revalida su autorización en la operación existente
        y confirma su propia transacción. Un fallo conserva los cierres y los
        resultados que ya se confirmaron. Repetir la orden recupera ese historial.
        """
        if (not isinstance(id_sesion, UUID) or type(ids_intentos) is not tuple
                or not ids_intentos or any(type(i) is not int or i <= 0 for i in ids_intentos)
                or len(set(ids_intentos)) != len(ids_intentos)):
            raise ReglaIdentidadInvalida()
        revision = self.consulta.consultar(id_sesion=id_sesion)
        encontrados = {i.id_intento: (fila, i)
                       for fila in revision.convocatorias for i in fila.intentos}
        if not set(ids_intentos).issubset(encontrados):
            raise AccesoDenegado()
        resultados = []
        for identificador in ids_intentos:
            fila, intento = encontrados[identificador]
            if fila.estado != 'ACTIVA':
                resultados.append(IntentoRecuperado(identificador, 'PENDIENTE', motivo='CONVOCATORIA_RETIRADA'))
                continue
            if intento.estado not in (EstadoIntento.FINALIZADO.value, EstadoIntento.VENCIDO.value):
                resultados.append(IntentoRecuperado(identificador, 'PENDIENTE', motivo='CIERRE_NO_PERSISTIDO'))
                continue
            try:
                if intento.id_resultado_tecnico is not None:
                    lectura = self.consulta.consultar_resultado(id_sesion=id_sesion, id_intento=identificador)
                else:
                    lectura = self.evaluar(id_sesion=id_sesion, id_intento=identificador)
            except ConflictoIdentidad:
                resultados.append(IntentoRecuperado(identificador, 'PENDIENTE', motivo='CONFLICTO_RESULTADO'))
            except IntegracionPendiente:
                resultados.append(IntentoRecuperado(identificador, 'PENDIENTE', motivo='CONFIGURACION_O_PERSISTENCIA'))
            else:
                resultados.append(IntentoRecuperado(identificador, 'DISPONIBLE', lectura.resultado.id_resultado))
        return RecuperacionCierres(id_sesion, tuple(resultados))

    def evaluar(self, *, id_sesion: UUID, id_intento: int):
        if not isinstance(id_sesion,UUID) or type(id_intento) is not int or id_intento<=0:
            raise AccesoDenegado()
        try:
            self._confirmar(id_sesion,id_intento)
            # Lectura desde OTRA Session tras commit. Si esta lectura/red falla,
            # no se deshace un resultado confirmado: repetir POST/GET lo recupera.
            return self.consulta.consultar_resultado(id_sesion=id_sesion,id_intento=id_intento)
        except ConflictoActualizacion:
            raise ConflictoIdentidad() from None
        except AccesoParticipacion:
            raise AccesoDenegado() from None
        except (SQLAlchemyError,EvaluacionInconsistente,PoliticaEvaluacionPendiente,ErrorAplicacionParticipacion,GrafoNoDisponible):
            raise IntegracionPendiente() from None

    def _confirmar(self,id_sesion,id_intento):
        q=self.consulta
        t=_unidad(q.crear_sesion,q.fechas)
        with t:
            s=t.sesion
            if s.get_bind().dialect.name!='postgresql' or s.connection().get_isolation_level()!='READ COMMITTED':
                raise IntegracionPendiente()
            pk=s.scalar(select(I.id_participacion).where(I.id_intento==id_intento))
            if pk is None:raise AccesoDenegado()
            # Orden existente: participación, cuenta/rol/vínculos, ámbito académico.
            # No fabrica un ContextoAcceso estudiantil a partir del docente.
            AmbitoFeedbackIndividual(s,q.usuario).autorizar(q.usuario.id_usuario,str(pk))
            intento=t.repositorio.obtener_intento(id_intento)  # P -> I, recarga Core bajo lock
            a=_Alcance(lambda:s,q.usuario,id_intento,q.fechas)
            contexto=a.datos()
            if contexto.sesion_programada_id!=id_sesion or intento.id_participacion!=pk:
                raise AccesoDenegado()
            s.execute(select(V.id).join(C,C.id==V.caso_id).where(V.id==contexto.version_caso_id)
                .with_for_update(of=[C,V],read=True)).one()
            # Misma autorización conservadora y verificaciones históricas del GET,
            # ahora dentro de la transacción protegida de escritura.
            q._consultar(s,id_sesion)
            if intento.estado not in (EstadoIntento.FINALIZADO,EstadoIntento.VENCIDO):
                raise ConflictoIdentidad()
            repo=RepositorioResultadosTecnicosSQLAlchemy(s,alcance=a,fechas=q.fechas)
            anterior=s.execute(select(R.ambito,R.version_regla).where(R.id_intento==id_intento)).one_or_none()
            if anterior is not None:
                if anterior.ambito!='TECNICO' or anterior.version_regla!='PREGUNTAS_100_V1':
                    raise ConflictoIdentidad()
                repo.obtener_tecnico(id_intento=id_intento)  # valida; nunca sustituye ni recalifica
                return
            historico=_evidencias(a,intento)
            config=consultar_configuracion_preguntas(s,version_id=historico.rubrica.version_id)
            detalles = DetallesPreguntasSQLAlchemy(repo)
            datos=detalles.preparar(historico,config)
            detalles.guardar(datos,self.reloj.ahora())
            t.commit()
