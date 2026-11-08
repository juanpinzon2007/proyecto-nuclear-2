"""Ciclo académico explícito: ausencias, revisión, publicación y consulta privada."""
from datetime import timezone
from uuid import UUID,uuid4
import json
from sqlalchemy import select,func,text
from sqlalchemy.exc import SQLAlchemyError
from app.modules.identity.domain.entities import Rol
from app.modules.identity.domain.errors import AccesoDenegado,ConflictoIdentidad,IntegracionPendiente,RecursoNoDisponible
from app.modules.identity.infrastructure.repositories import RepositorioUsuariosSQLAlchemy,id_entero
from app.modules.identity.infrastructure.models import UsuarioORM as U,RolORM
from app.modules.identity.infrastructure.academic_identity_models import IdentidadAcademicaORM as IA
from app.modules.identity.infrastructure.academic_base_models import GrupoEstudianteORM as M,GrupoAcademicoORM as G
from app.modules.identity.application.academic_identity import SistemaAcademico,ResolverIdentidadAcademica
from app.modules.identity.infrastructure.academic_identity_repository import RepositorioIdentidadAcademicaSQLAlchemy
from app.modules.participation.application.result_provenance import canonico,huella
from app.modules.participation.application.errors import ConflictoActualizacion,ErrorAplicacionParticipacion
from app.modules.participation.domain.evaluation import EvaluacionInconsistente,PoliticaEvaluacionPendiente
from app.modules.participation.infrastructure.evaluation import _unidad
from app.modules.participation.infrastructure.teacher_result import ConsultaResultadoDocenteSQLAlchemy
from app.modules.participation.infrastructure.models import ParticipacionModel as P,IntentoModel as I,PasoSimulacionModel as Paso
from app.modules.participation.infrastructure.result_models import ResultadoIntentoModel as R
from app.modules.participation.infrastructure.academic_results_models import AusenciaAcademicaModel as Aus,PublicacionEvaluacionModel as Pub,ResultadoParticipacionModel as RP
from app.modules.scheduling.infrastructure.models import SesionProgramadaModel as S,ConvocatoriaModel as C,EventoAuditoriaModel as E
from app.modules.scheduling.application.crear_notificacion import crear_notificacion


class CicloAcademicoSQL(ConsultaResultadoDocenteSQLAlchemy):
    def __init__(self,*,reloj,**kw):super().__init__(**kw);self.reloj=reloj

    def _escribir(self,fn):
        try:
            with _unidad(self.crear_sesion,self.fechas) as t:
                if t.sesion.get_bind().dialect.name!='postgresql':raise IntegracionPendiente()
                respuesta=fn(t.sesion)
                t.commit()
                return respuesta
        except ConflictoActualizacion:raise ConflictoIdentidad() from None
        except SQLAlchemyError as e:
            if getattr(e.orig,'sqlstate',None) in {'23505','40P01','40001'}:raise ConflictoIdentidad() from None
            raise IntegracionPendiente() from None
        except (EvaluacionInconsistente,PoliticaEvaluacionPendiente,ErrorAplicacionParticipacion):raise IntegracionPendiente() from None

    def _base(self,s,sid,bloquear=False):
        if not isinstance(sid,UUID):raise AccesoDenegado()
        if bloquear:
            # P -> I primero, como escritores/cálculo existentes. Fuente se relee tras S.
            ps=s.scalars(select(P.id_participacion).join(C,C.id==P.convocatoria_id).where(C.sesion_id==sid).order_by(P.id_participacion).with_for_update(of=P)).all()
            if ps:s.execute(select(I.id_intento).where(I.id_participacion.in_(ps)).order_by(I.id_intento).with_for_update()).all()
            uid=id_entero(self.usuario.id_usuario)
            rol=s.scalar(select(U.id_rol).where(U.id_usuario==uid).with_for_update())
            if rol is None:raise AccesoDenegado()
            s.execute(select(RolORM.id_rol).where(RolORM.id_rol==rol).with_for_update(read=True)).all()
            s.execute(select(IA.id_academico).where(IA.id_usuario==uid).with_for_update(read=True)).all()
            s.get(S,sid,with_for_update=True,populate_existing=True)
            s.execute(select(C.id).where(C.sesion_id==sid).order_by(C.id).with_for_update()).all()
            # Congelar asociaciones que autorizan la revisión en esta UoW.
            from app.modules.scheduling.infrastructure.assignment_models import AsignacionCasoModel as A
            asigs=s.scalars(select(A).where(A.sesion_programada_id==sid).order_by(A.id_asignacion).with_for_update(read=True)).all()
            gids=[a.id_grupo for a in asigs]
            if gids:
                s.execute(select(G.id_grupo).where(G.id_grupo.in_(gids)).order_by(G.id_grupo).with_for_update(read=True)).all()
                s.execute(select(M.id_grupo_estudiante).where(M.id_grupo.in_(gids)).order_by(M.id_grupo_estudiante).with_for_update(read=True)).all()
        return self._autorizar_contexto(s,sid)

    def _audit(self,s,sid,tipo,datos):
        s.add(E(id=uuid4(),sesion_id=sid,tipo=tipo,origen='DOCENTE',descripcion=canonico(dict(id_docente=id_entero(self.usuario.id_usuario),**datos)),creado_en=self.reloj.ahora()))

    def _ultima_ausencia(self,s,cid):
        return s.scalar(select(Aus).where(Aus.convocatoria_id==cid).order_by(Aus.revision.desc()).limit(1))

    def ausencia(self,*,id_sesion,convocatoria_id,motivo,rectificar_id=None):
        def ejecutar(s):
            actual,resolver,sesion,v,caso,r,asigs=self._base(s,id_sesion,True)
            c=s.get(C,convocatoria_id)
            if c is None or c.sesion_id!=id_sesion or c.estado!='ACTIVA':raise AccesoDenegado()
            if sesion.estado!='FINALIZADO':raise ConflictoIdentidad()
            uid=s.scalar(select(IA.id_usuario).where(IA.sistema=='SCHEDULING',IA.id_academico==c.estudiante_id))
            if uid is None or resolver.resolver(id_usuario=str(uid),sistema=SistemaAcademico.SCHEDULING)!=c.estudiante_id:raise AccesoDenegado()
            ms=s.scalars(select(M).where(M.id_estudiante==uid,M.id_grupo.in_([a.id_grupo for a in asigs]))).all()
            if len(ms)!=1:raise IntegracionPendiente()
            if s.scalar(select(func.count()).select_from(I).join(P,P.id_participacion==I.id_participacion).where(P.convocatoria_id==c.id)):
                raise ConflictoIdentidad()
            anterior=self._ultima_ausencia(s,c.id);confirmar=rectificar_id is None
            if anterior and anterior.confirmada==confirmar:
                if confirmar or anterior.anterior_id==rectificar_id:return self._ausencia_dto(anterior)
                raise ConflictoIdentidad()
            if not confirmar and (anterior is None or anterior.id!=rectificar_id):raise ConflictoIdentidad()
            a=Aus(id=uuid4(),convocatoria_id=c.id,sesion_id=id_sesion,id_estudiante=uid,id_profesor=id_entero(actual.id_usuario),
                version_caso_id=v.id,revision=1 if anterior is None else anterior.revision+1,confirmada=confirmar,
                anterior_id=anterior.id if anterior else None,motivo=motivo,fecha=self.reloj.ahora())
            s.add(a);self._audit(s,id_sesion,'AUSENCIA_CONFIRMADA' if confirmar else 'AUSENCIA_RECTIFICADA',dict(convocatoria_id=c.id,id_ausencia=a.id,motivo=motivo))
            return self._ausencia_dto(a)
        return self._escribir(ejecutar)

    def _ausencia_dto(self,a):
        return dict(id=a.id,convocatoria_id=a.convocatoria_id,revision=a.revision,confirmada=a.confirmada,motivo=a.motivo,fecha=a.fecha,
            nota='0.00' if a.confirmada else None,oficial=False)

    def visibilidad(self,*,id_sesion,mostrar_provisional):
        def ejecutar(s):
            _,_,sesion,*_=self._base(s,id_sesion,True)
            if sesion.mostrar_resultados_provisionales is not mostrar_provisional:
                sesion.mostrar_resultados_provisionales=mostrar_provisional
                sesion.visibilidad_docente_id=id_entero(self.usuario.id_usuario);sesion.visibilidad_actualizada_en=self.reloj.ahora()
                self._audit(s,id_sesion,'EVALUACION_VISIBILIDAD',dict(mostrar_provisional=mostrar_provisional))
            return dict(id_sesion=id_sesion,mostrar_provisional=sesion.mostrar_resultados_provisionales,
                actualizada_en=sesion.visibilidad_actualizada_en,correctas_durante_sesion_activa=False)
        return self._escribir(ejecutar)

    def _cohorte(self,s,sid,bloquear=False):
        actual,resolver,sesion,version,caso,rubrica,asigs=self._base(s,sid,bloquear)
        filas=[];retiradas=[];pendientes=[]
        cs=s.scalars(select(C).where(C.sesion_id==sid).order_by(C.id)).all()
        for c in cs:
            if c.estado=='RETIRADA':retiradas.append(str(c.id));continue
            if c.estado!='ACTIVA':raise IntegracionPendiente()
            uid=s.scalar(select(IA.id_usuario).where(IA.sistema=='SCHEDULING',IA.id_academico==c.estudiante_id))
            if uid is None or resolver.resolver(id_usuario=str(uid),sistema=SistemaAcademico.SCHEDULING)!=c.estudiante_id:raise IntegracionPendiente()
            p=s.scalar(select(P).where(P.convocatoria_id==c.id))
            ms=s.scalars(select(M).where(M.id_estudiante==uid,M.id_grupo.in_([a.id_grupo for a in asigs]))).all()
            if p:
                m=next((x for x in ms if x.id_grupo_estudiante==p.id_grupo_estudiante),None)
                a=next((x for x in asigs if x.id_asignacion==p.id_asignacion),None)
                if m is None or a is None or a.id_grupo!=m.id_grupo:raise IntegracionPendiente()
            else:
                if len(ms)!=1:raise IntegracionPendiente()
                m=ms[0];a=next((x for x in asigs if x.id_grupo==m.id_grupo),None)
                if a is None:raise IntegracionPendiente()
            intentos=s.scalars(select(I).where(I.id_participacion==p.id_participacion).order_by(I.id_intento)).all() if p else []
            persona=s.get(U,uid);grupo=s.get(G,m.id_grupo)
            f=dict(convocatoria_id=str(c.id),id_estudiante=uid,id_asignacion=a.id_asignacion,id_participacion=p.id_participacion if p else None,
                nombre_estudiante=persona.nombre,grupo_id=grupo.id_grupo,grupo_nombre=grupo.nombre,caso_id=str(caso.id),version_caso_id=str(version.id),rubrica_id=str(rubrica.id),
                situacion=None,nota=None,id_resultado_intento=None,id_ausencia=None,intentos=[])
            if not intentos:
                ausencia=self._ultima_ausencia(s,c.id)
                if ausencia and ausencia.confirmada:
                    f.update(situacion='AUSENTE',nota='0.00',id_ausencia=str(ausencia.id))
                else:pendientes.append(dict(convocatoria_id=str(c.id),codigo='AUSENCIA_NO_CONFIRMADA'))
            else:
                resultados=[]
                for i in intentos:
                    if i.numero_intento>1:
                        from app.modules.identity.infrastructure.academic_models import PermisoIntentoExtraORM as Extra
                        permiso=s.get(Extra,i.id_permiso_extra) if i.id_permiso_extra is not None else None
                        usos=s.scalar(select(func.count()).select_from(I).where(I.id_permiso_extra==i.id_permiso_extra)) if permiso else 0
                        if permiso is None or permiso.id_participacion!=p.id_participacion or permiso.id_profesor!=id_entero(actual.id_usuario) or permiso.cantidad_autorizada!=1 or usos!=1:
                            pendientes.append(dict(convocatoria_id=str(c.id),id_intento=i.id_intento,codigo='REPETICION_SIN_AUTORIZACION_VERIFICABLE'));continue
                    cab=s.execute(select(R.id_resultado,R.ambito).where(R.id_intento==i.id_intento)).one_or_none()
                    if i.estado not in {'FINALIZADO','VENCIDO'} or cab is None or cab.ambito!='TECNICO':
                        pendientes.append(dict(convocatoria_id=str(c.id),id_intento=i.id_intento,codigo='INTENTO_O_RESULTADO_PENDIENTE'));continue
                    tecnico=self._resultado_tecnico(s,i.id_intento)
                    if tecnico.datos.id_participacion!=p.id_participacion:raise IntegracionPendiente()
                    resultados.append(tecnico)
                    f['intentos'].append(dict(id_intento=i.id_intento,numero=i.numero_intento,estado=i.estado,id_resultado=tecnico.id_resultado,nota=format(tecnico.datos.nota_final,'.2f'),sha256=tecnico.sha256))
                if len(resultados)==len(intentos):
                    mejor=sorted(resultados,key=lambda t:(-t.datos.nota_final,t.datos.id_intento))[0]
                    f.update(situacion=mejor.datos.modalidad.value,nota=format(mejor.datos.nota_final,'.2f'),id_resultado_intento=mejor.id_resultado)
            filas.append(f)
        if sesion.estado!='FINALIZADO':pendientes.append(dict(codigo='SESION_NO_FINALIZADA'))
        if not filas:pendientes.append(dict(codigo='SIN_CONVOCATORIAS_ACTIVAS'))
        doc=canonico(dict(regla='MAXIMO_MISMA_PARTICIPACION_V1',sesion_id=str(sid),version_caso_id=str(version.id),filas=filas,retiradas=retiradas))
        return dict(id_sesion=sid,publicable=not pendientes,pendientes=pendientes,revision_sha256=huella(doc),filas=filas,retiradas=retiradas),doc

    def revisar(self,*,id_sesion):
        try:return self._lectura(lambda s:self._cohorte(s,id_sesion)[0])
        except (ErrorAplicacionParticipacion,EvaluacionInconsistente,PoliticaEvaluacionPendiente):raise IntegracionPendiente() from None

    def _publicada(self,s,pub):
        if huella(pub.fuente_documento)!=pub.fuente_sha256:raise IntegracionPendiente()
        documento=json.loads(pub.fuente_documento)
        filas=s.scalars(select(RP).where(RP.publicacion_id==pub.id).order_by(RP.convocatoria_id)).all()
        esperadas={f['convocatoria_id']:f for f in documento['filas']}
        if len(filas)!=len(esperadas) or any(str(f.convocatoria_id) not in esperadas or canonico(esperadas[str(f.convocatoria_id)])!=f.detalle or esperadas[str(f.convocatoria_id)]['nota']!=format(f.nota_definitiva,'.2f') for f in filas):raise IntegracionPendiente()
        return dict(id=pub.id,id_sesion=pub.sesion_id,version=pub.version,fecha=pub.fecha,revision_sha256=pub.fuente_sha256,oficial=True,
            resultados=[dict(convocatoria_id=x.convocatoria_id,id_participacion=x.id_participacion,id_estudiante=x.id_estudiante,situacion=x.situacion,
                nota=format(x.nota_definitiva,'.2f'),detalle=json.loads(x.detalle)) for x in filas],retiradas=json.loads(pub.fuente_documento)['retiradas'])

    def publicar(self,*,id_sesion,revision_sha256):
        def ejecutar(s):
            revision,doc=self._cohorte(s,id_sesion,True)
            if not revision['publicable'] or revision['revision_sha256']!=revision_sha256:raise ConflictoIdentidad()
            anterior=s.scalar(select(Pub).where(Pub.sesion_id==id_sesion).order_by(Pub.version.desc()).limit(1))
            if anterior and anterior.fuente_sha256==revision_sha256:return self._publicada(s,anterior)
            pub=Pub(id=uuid4(),sesion_id=id_sesion,id_profesor=id_entero(self.usuario.id_usuario),version=anterior.version+1 if anterior else 1,
                fecha=self.reloj.ahora(),fuente_documento=doc,fuente_sha256=revision_sha256)
            s.add(pub);s.flush()
            from decimal import Decimal
            for f in revision['filas']:
                cid=UUID(f['convocatoria_id'])
                s.add(RP(publicacion_id=pub.id,convocatoria_id=cid,id_participacion=f['id_participacion'],id_estudiante=f['id_estudiante'],
                    id_asignacion=f['id_asignacion'],id_resultado_intento=f['id_resultado_intento'],id_ausencia=UUID(f['id_ausencia']) if f['id_ausencia'] else None,
                    situacion=f['situacion'],nota_definitiva=Decimal(f['nota']),detalle=canonico(f)))
                n=crear_notificacion(s,destinatario_id=s.get(C,cid).estudiante_id,tipo='CALIFICACION',canal='INTERNA',convocatoria_id=cid,
                    mensaje=f'El docente publicó resultados oficiales de tu convocatoria {cid}. Consulta tu resultado privado en la plataforma.')
                n.publicacion_evaluacion_id=pub.id
            self._audit(s,id_sesion,'RESULTADOS_PUBLICADOS',dict(publicacion_id=pub.id,version=pub.version,revision_sha256=revision_sha256))
            s.flush();return self._publicada(s,pub)
        return self._escribir(ejecutar)

    def consultar_publicacion(self,*,id_sesion):
        def leer(s):
            self._base(s,id_sesion)
            pub=s.scalar(select(Pub).where(Pub.sesion_id==id_sesion).order_by(Pub.version.desc()).limit(1))
            if pub is None:raise RecursoNoDisponible()
            return self._publicada(s,pub)
        return self._lectura(leer)

    def estudiante(self,*,convocatoria_id):
        def leer(s):
            cuenta=RepositorioUsuariosSQLAlchemy(s).obtener(self.usuario.id_usuario)
            if cuenta is None or not cuenta.activo or Rol.ESTUDIANTE not in cuenta.roles:raise AccesoDenegado()
            c=s.get(C,convocatoria_id)
            resolver=ResolverIdentidadAcademica(RepositorioIdentidadAcademicaSQLAlchemy(s))
            uuid_est=resolver.resolver(id_usuario=cuenta.id_usuario,sistema=SistemaAcademico.SCHEDULING)
            if c is None or c.estudiante_id!=uuid_est or str(self.usuario.id_convocatoria)!=str(c.id):raise AccesoDenegado()
            sesion=s.get(S,c.sesion_id)
            pub=s.scalar(select(Pub).where(Pub.sesion_id==c.sesion_id).order_by(Pub.version.desc()).limit(1))
            if pub:
                self._publicada(s,pub)  # Verificar snapshot inmutable antes de exponer la fila propia.
                fila=s.scalar(select(RP).where(RP.publicacion_id==pub.id,RP.convocatoria_id==c.id,RP.id_estudiante==id_entero(cuenta.id_usuario)))
                if fila is None:raise RecursoNoDisponible()
                resultado=dict(publicacion_id=pub.id,version_publicacion=pub.version,oficial=True,situacion=fila.situacion,nota=format(fila.nota_definitiva,'.2f'),detalle=json.loads(fila.detalle))
            else:
                if c.estado!='ACTIVA':raise AccesoDenegado()
                if sesion.mostrar_resultados_provisionales is not True:raise RecursoNoDisponible()
                p=s.scalar(select(P).where(P.convocatoria_id==c.id))
                if p is None:raise RecursoNoDisponible()
                intentos=s.scalars(select(I).where(I.id_participacion==p.id_participacion).order_by(I.id_intento)).all()
                if not intentos or any(i.estado not in {'FINALIZADO','VENCIDO'} for i in intentos):raise ConflictoIdentidad()
                tecnicos=[self._resultado_tecnico(s,i.id_intento) for i in intentos]
                if any(t.ambito!='TECNICO' for t in tecnicos):raise IntegracionPendiente()
                mejor=sorted(tecnicos,key=lambda t:(-t.datos.nota_final,t.datos.id_intento))[0]
                resultado=dict(oficial=False,situacion=mejor.datos.modalidad.value,nota=format(mejor.datos.nota_final,'.2f'),
                    detalle=dict(id_participacion=p.id_participacion,version_caso_id=str(sesion.version_caso_id),rubrica_id=json.loads(mejor.procedencia)['rubrica']['rubrica_id'],intentos=[dict(id_intento=t.datos.id_intento,id_resultado=t.id_resultado,nota=format(t.datos.nota_final,'.2f')) for t in tecnicos]))
            resultado['explicaciones']=[]
            if sesion.estado=='FINALIZADO':
                from dataclasses import asdict
                from app.modules.cases.application.answer_feedback import consultar_explicaciones_seleccionadas
                for i in resultado['detalle'].get('intentos',[]):
                    pasos=s.execute(select(Paso.id_decision,Paso.id_opcion).where(Paso.id_intento==i['id_intento']).order_by(Paso.numero_paso)).all()
                    resultado['explicaciones'].append(dict(id_intento=i['id_intento'],respuestas=[asdict(x) for x in consultar_explicaciones_seleccionadas(s,version_id=UUID(resultado['detalle']['version_caso_id']),selecciones=tuple(pasos))]))
            return resultado
        try:return self._lectura(leer)
        except (ErrorAplicacionParticipacion,EvaluacionInconsistente,PoliticaEvaluacionPendiente):raise IntegracionPendiente() from None
