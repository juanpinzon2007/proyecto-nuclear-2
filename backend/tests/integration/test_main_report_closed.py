"""RF-16: main/PG17 reales; ninguna nota o ausencia se fabrica para exportar."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import select,func,inspect

from app.modules.identity.api.dependencies import construir_tokens
from app.modules.identity.domain.errors import IntegracionPendiente
from app.modules.identity.infrastructure.models import UsuarioORM
from app.modules.identity.infrastructure.academic_identity_models import IdentidadAcademicaORM
from app.modules.identity.infrastructure.academic_base_models import GrupoEstudianteORM as M
from app.modules.identity.infrastructure.reporting_queries import TablasLecturaReporte
from app.modules.participation.infrastructure.models import ParticipacionModel as P
from app.modules.participation.infrastructure.result_models import ResultadoIntentoModel as R
from app.modules.scheduling.infrastructure.models import ConvocatoriaModel as C
from tests.integration.test_main_current_scenario import principal, integracion, autor, pg_autoria, payload_valido  # noqa: F401
from tests.integration.test_main_teacher_followup import observar_lectura


@pytest.fixture
def reporte(principal):
    h = principal
    tokens = construir_tokens()  # Emisión docente SOLO de laboratorio.
    h.propietario = {'Authorization':'Bearer '+tokens.emitir(str(h.a.propio))}
    h.ajeno = {'Authorization':'Bearer '+tokens.emitir(str(h.a.propio+1))}
    h.reporte = f'/api/v1/identity/seguimiento/sesiones/{h.sesion}/reporte'
    return h


@pytest.mark.parametrize('actor,estado',[
    ('propietario',503),('ajeno',503),('estudiante',403),('anonimo',401),('invalido',401),
])
def test_reporte_principal_cerrado_no_exporta_ni_escribe(reporte,actor,estado):
    h = reporte
    headers={'propietario':h.propietario,'ajeno':h.ajeno,'estudiante':h.main_headers,
             'anonimo':{},'invalido':{'Authorization':'Bearer invalido'}}[actor]
    with observar_lectura() as operaciones:
        r = h.principal.get(h.reporte,headers=headers)
    assert r.status_code == estado, r.text
    assert operaciones == [] and r.headers['cache-control'] == 'no-store'
    assert 'content-disposition' not in r.headers and 'text/csv' not in r.headers['content-type']
    for prohibido in ('id_estudiante','nota_definitiva','nota_final','clave_hash',h.codigo):
        assert prohibido not in r.text


def test_convocado_sin_participacion_no_se_convierte_en_ausencia_o_nota(reporte,record_property):
    h = reporte
    # Preparación administrativa de padrón histórico sintético, no alta pública
    # durante EN_CURSO. Las relaciones se persisten; no se sustituye SQL por mocks.
    with h.sesiones.begin() as s:
        grupo = s.get(M,h.matricula).id_grupo
        nuevo = UsuarioORM(id_rol=2,nombre='Convocado LAB',correo=f'padron-{uuid4().hex}@universidad.test',
                           clave_hash='sin-login-de-personal-en-fixture')
        s.add(nuevo)
        s.flush()
        uuid_estudiante = uuid4()
        s.add(IdentidadAcademicaORM(id_usuario=nuevo.id_usuario,sistema='SCHEDULING',id_academico=uuid_estudiante))
        s.add(M(id_grupo=grupo,id_estudiante=nuevo.id_usuario,fecha_ingreso=h.reloj.ahora().replace(tzinfo=None)))
        s.add(C(sesion_id=h.sesion,estudiante_id=uuid_estudiante,codigo_hash='codigo-no-utilizable-LAB',estado='ACTIVA'))
    with h.sesiones() as s:
        convocados = s.scalar(select(func.count()).select_from(C).where(C.sesion_id==h.sesion))
        participaciones = s.scalar(select(func.count()).select_from(P).join(C,C.id==P.convocatoria_id).where(C.sesion_id==h.sesion))
        assert (convocados,participaciones) == (2,1)
        assert 'resultado_participacion' not in inspect(s.get_bind()).get_table_names()
        assert s.scalar(select(func.count()).select_from(R)) == 0
    with observar_lectura() as operaciones:
        r = h.principal.get(h.reporte,headers=h.propietario)
    assert r.status_code == 503 and operaciones == []
    record_property('padron_observado','2 convocatorias; 1 participación; 0 resultados de intento; sin consolidado')
    record_property('respuesta_sin_reporte',r.text)
    # No hay un fallback que trate resultado_intento LAB como consolidación.
    with pytest.raises(IntegracionPendiente):
        TablasLecturaReporte(P.__table__,M.__table__,R.__table__)


def test_reintentos_concurrentes_no_producen_csv_parcial(reporte):
    h = reporte
    barrera = Barrier(2,timeout=15)

    def consultar(_):
        barrera.wait()
        return h.principal.get(h.reporte,headers=h.propietario)

    with observar_lectura() as operaciones:
        with ThreadPoolExecutor(max_workers=2) as pool:
            respuestas = list(pool.map(consultar,range(2)))
    assert all(r.status_code==503 for r in respuestas)
    assert respuestas[0].json() == respuestas[1].json() and operaciones == []
