"""Grafo REAL persistido: SQLite aislado y PostgreSQL desechable.

No hay proveedor simulado de recorrido. La autorización temporal positiva sigue
siendo exclusivamente una fixture: no sustituye la política Scheduling pendiente.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import timezone
from threading import Barrier
from types import SimpleNamespace
from uuid import uuid4

from alembic import command
import pytest
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError, DBAPIError
from sqlalchemy.orm import sessionmaker

from app.modules.cases.application.graph import GrafoNoDisponible, ReglaRecorridoPendiente, SeleccionFueraDeRecorrido
from app.modules.cases.domain.entities.caso import Escenario, Pregunta, OpcionRespuesta
from app.modules.cases.domain.enums import EstadoCaso
from app.modules.cases.domain.exceptions import ErrorPersistenciaCaso
from app.modules.cases.infrastructure.models import EscenarioModel as E, PreguntaModel as Q, OpcionRespuestaModel as O
from app.modules.cases.infrastructure.repositories.caso_repository import CasoRepository
from app.modules.cases.infrastructure.repositories.graph_repository import RepositorioGrafoSQLAlchemy as Graph
from app.modules.participation.application.dto import SeleccionDecision
from app.modules.participation.application.errors import ReglaPendiente, AccesoDenegado
from app.modules.participation.domain.errors import RespuestaInmutable
from app.modules.participation.infrastructure.cases_route import RecorridoCasesSQLAlchemy
from tests.identity.academic_identity_support import motor_identidades, motor_postgresql_desechable, config_alembic  # noqa: F401
from tests.integration.test_cases_history import nuevo, publicar

HEAD = "20261102_cases_graph"
PARENT = "20261102_academic_policy"


def version_grafo():
    v = nuevo()
    for i in (2, 3):
        v.escenarios.append(Escenario(i, f"Rama {i}", preguntas=[Pregunta(1, "Decisión", opciones=[
            OpcionRespuesta(o.orden, o.texto, o.es_correcta, o.justificacion, valoraciones=dict(o.valoraciones))
            for o in v.escenarios[0].preguntas[0].opciones])]))
    return v


def configurar(sesiones, v):
    ids = [e.id for e in v.escenarios]
    opciones = [e.preguntas[0].opciones for e in v.escenarios]
    transiciones = tuple((o.id, "ESCENA", ids[i+1]) for i, o in enumerate(opciones[0])) + \
        tuple((o.id, "FIN", None) for os in opciones[1:] for o in os)
    with sesiones.begin() as s:
        Graph(s).configurar(version_id=v.id, docente_id=v.docente_creador_id, inicial_id=ids[0], transiciones=transiciones)
    return ids, opciones


@pytest.fixture
def g(motor_identidades):
    v = version_grafo()
    sesiones = sessionmaker(motor_identidades, expire_on_commit=False)
    with sesiones() as s:
        CasoRepository(s).guardar(v)
    ids, opciones = configurar(sesiones, v)
    return SimpleNamespace(v=v, sesiones=sesiones, engine=motor_identidades, ids=ids, opciones=opciones)


def leer(g, publicada=False):
    with g.sesiones() as s:
        return Graph(s).leer(g.v.id, solo_publicada=publicada)


def publicar_g(g):
    g.v = publicar(g.sesiones, g.v)
    return g


def test_grafo_persistido_recuperacion_y_entrada(g):
    grafo = leer(publicar_g(g), True)
    ruta = grafo.recorrer(())
    assert ruta.escenas == (g.ids[0],) and ruta.escena_actual == g.ids[0] and not ruta.finalizado
    assert grafo == leer(g, True)
    assert "es_correcta" not in repr(grafo) and "valoraciones" not in repr(grafo)


@pytest.mark.parametrize("rama", [0, 1])
def test_transicion_ramificada_y_fin_real(g, rama):
    grafo = leer(publicar_g(g), True)
    inicio = g.v.escenarios[0].preguntas[0].id
    destino = g.v.escenarios[rama+1].preguntas[0].id
    seleccion = ((inicio, g.opciones[0][rama].id),)
    ruta = grafo.recorrer(seleccion)
    assert ruta.escenas == (g.ids[0], g.ids[rama+1]) and ruta.escena_actual == g.ids[rama+1]
    final = grafo.recorrer((*seleccion, (destino, g.opciones[rama+1][0].id)))
    assert final.finalizado and final.escena_actual is None
    assert final.decisiones == (inicio, destino)


def test_opcion_ajena_y_respuesta_de_rama_no_elegida(g):
    grafo = leer(g)
    preguntas = [e.preguntas[0].id for e in g.v.escenarios]
    with pytest.raises(SeleccionFueraDeRecorrido):
        grafo.recorrer(((preguntas[0], g.opciones[1][0].id),))
    with pytest.raises(SeleccionFueraDeRecorrido):
        grafo.recorrer(((preguntas[0], g.opciones[0][0].id), (preguntas[2], g.opciones[2][0].id)))


def test_multiples_iniciales_rechazadas(g):
    with pytest.raises(IntegrityError), g.sesiones.begin() as s:
        s.execute(sa.update(E).where(E.id == g.ids[1]).values(es_inicial=True))
    assert leer(g).validar_ejecutable() == g.ids[0]


@pytest.mark.parametrize("tipo,destino", [("OTRO", None), ("ESCENA", None), ("FIN", "propio"), (None, "propio")])
def test_check_directo_coherencia(g, tipo, destino):
    with pytest.raises(IntegrityError), g.sesiones.begin() as s:
        s.execute(sa.update(O).where(O.id == g.opciones[0][0].id)
            .values(tipo_transicion=tipo, escenario_destino_id=g.ids[1] if destino else None))


def test_fk_destino_inexistente(g):
    with pytest.raises(IntegrityError), g.sesiones.begin() as s:
        s.execute(sa.update(O).where(O.id == g.opciones[0][0].id).values(escenario_destino_id=uuid4()))


@pytest.mark.parametrize("faltante", ["entrada", "arista"])
def test_configuracion_incompleta_no_ejecutable(g, faltante):
    with g.sesiones.begin() as s:
        if faltante == "entrada":
            s.execute(sa.update(E).where(E.id == g.ids[0]).values(es_inicial=False))
        else:
            s.execute(sa.update(O).where(O.id == g.opciones[1][0].id)
                .values(tipo_transicion=None, escenario_destino_id=None))
    with pytest.raises(GrafoNoDisponible):
        leer(g).validar_ejecutable()


def test_ciclo_persistible_pero_ejecucion_pendiente(g):
    with g.sesiones.begin() as s:
        Graph(s).configurar(version_id=g.v.id, docente_id=g.v.docente_creador_id, inicial_id=g.ids[0],
            transiciones=((g.opciones[1][0].id, "ESCENA", g.ids[0]),))
    with pytest.raises(ReglaRecorridoPendiente, match="Ciclos"):
        leer(g).recorrer(())


def test_varias_preguntas_se_conservan_pero_no_se_eligen_por_orden(g):
    with g.sesiones.begin() as s:
        s.add(Q(escenario_id=g.ids[0], orden=2, enunciado="Pregunta adicional"))
    with pytest.raises(ReglaRecorridoPendiente, match="varias"):
        leer(g).recorrer(())


def test_escritura_ajena_y_rollback(g):
    antes = leer(g)
    with pytest.raises(GrafoNoDisponible), g.sesiones.begin() as s:
        Graph(s).configurar(version_id=g.v.id, docente_id=uuid4(), inicial_id=g.ids[0], transiciones=())
    with pytest.raises(RuntimeError), g.sesiones.begin() as s:
        Graph(s).configurar(version_id=g.v.id, docente_id=g.v.docente_creador_id, inicial_id=g.ids[1], transiciones=())
        raise RuntimeError("Rollback deliberado")
    assert leer(g) == antes


def test_edicion_legacy_no_puede_borrar_grafo_configurado(g):
    with g.sesiones() as s:
        v = CasoRepository(s).obtener_version(g.v.id, g.v.docente_creador_id)
        with pytest.raises(ErrorPersistenciaCaso, match="descartaría"):
            CasoRepository(s).reemplazar(v)
    assert leer(g).validar_ejecutable() == g.ids[0]


def test_adaptador_proporciona_ruta_real_y_bloquea_modificacion(g):
    publicar_g(g)
    with g.sesiones.begin() as s:
        adaptador = RecorridoCasesSQLAlchemy(lambda: s)
        q0, q1 = (g.v.escenarios[i].preguntas[0].id for i in (0, 1))
        a = SeleccionDecision(q0, g.opciones[0][0].id)
        b = SeleccionDecision(q1, g.opciones[1][0].id)
        adaptador.validar_cambio(version_id=g.v.id, selecciones=(), propuesta=a)
        parcial = adaptador.obtener(version_id=g.v.id, selecciones=(a,))
        assert parcial.disponible and not parcial.total_conocido and parcial.decisiones == (q0, q1)
        final = adaptador.obtener(version_id=g.v.id, selecciones=(a, b))
        assert final.total_conocido and final.decisiones == (q0, q1)
        with pytest.raises(RespuestaInmutable):
            adaptador.validar_cambio(version_id=g.v.id, selecciones=(a, b), propuesta=a)


def test_borrador_no_es_recorrido_publicado(g):
    with g.sesiones() as s, pytest.raises(GrafoNoDisponible):
        Graph(s).leer(g.v.id)


@pytest.fixture(scope="module")
def pg_grafo():
    with motor_postgresql_desechable() as e:
        with e.begin() as s:
            command.upgrade(config_alembic(s), "head")
            from app.modules.identity.infrastructure.models import RolORM
            s.execute(sa.insert(RolORM), [dict(id_rol=1, nombre="DOCENTE"), dict(id_rol=2, nombre="ESTUDIANTE")])
        yield e


def test_upgrade_downgrade_y_legacy_sin_configuracion():
    with motor_postgresql_desechable() as e:
        with e.begin() as s:
            command.upgrade(config_alembic(s), PARENT)
        sesiones = sessionmaker(e)
        v = nuevo()
        with sesiones() as s:
            CasoRepository(s).guardar(v)
        publicar(sesiones, v)
        with e.begin() as s:
            tablas = set(sa.inspect(s).get_table_names())
            command.upgrade(config_alembic(s), HEAD)
            assert set(sa.inspect(s).get_table_names()) == tablas
            assert not s.scalar(sa.text("SELECT bool_or(es_inicial) FROM escenario"))
            assert s.scalar(sa.text("SELECT count(*) FROM opcion_respuesta WHERE tipo_transicion IS NOT NULL")) == 0
            assert s.scalar(sa.text("SELECT count(*) FROM pg_trigger WHERE NOT tgisinternal")) == 43
            command.downgrade(config_alembic(s), PARENT)
            assert s.scalar(sa.text("SELECT count(*) FROM pg_trigger WHERE NOT tgisinternal")) == 40
            assert set(sa.inspect(s).get_table_names()) == tablas
            assert "es_inicial" not in {c["name"] for c in sa.inspect(s).get_columns("escenario")}
            command.upgrade(config_alembic(s), HEAD)
            assert s.scalar(sa.text("SELECT count(*) FROM caso")) == 1


@pytest.fixture
def gpg(pg_grafo):
    # Reutilizar la preparación real, sin ejecutar SQLite para garantías SQL PG.
    return g.__wrapped__(pg_grafo)


@pytest.mark.parametrize("estado", [EstadoCaso.PUBLICADO, EstadoCaso.ARCHIVADO])
def test_sql_no_modifica_grafo_historico(gpg, estado):
    g = publicar_g(gpg)
    if estado == EstadoCaso.ARCHIVADO:
        g.v.archivar()
        with g.sesiones() as s:
            CasoRepository(s).actualizar_estado(g.v)
    antes = leer(g, True)
    for sentencia in (sa.update(E).where(E.id == g.ids[0]).values(es_inicial=False),
                      sa.update(O).where(O.id == g.opciones[0][0].id).values(tipo_transicion="FIN", escenario_destino_id=None)):
        with pytest.raises(IntegrityError), g.sesiones.begin() as s:
            s.execute(sentencia)
    assert leer(g, True) == antes


@pytest.mark.parametrize("cambio", ["destino", "origen", "padre_destino", "borrar_destino"])
def test_integridad_sql_entre_versiones_y_referencias(gpg, cambio):
    g = gpg
    ajeno = nuevo()
    with g.sesiones() as s:
        CasoRepository(s).guardar(ajeno)
    otro = ajeno.escenarios[0].id
    sentencias = {
        "destino": sa.update(O).where(O.id == g.opciones[0][0].id).values(escenario_destino_id=otro),
        "origen": sa.update(Q).where(Q.id == g.v.escenarios[0].preguntas[0].id).values(escenario_id=otro),
        "padre_destino": sa.update(E).where(E.id == g.ids[1]).values(version_caso_id=ajeno.id),
        "borrar_destino": sa.delete(E).where(E.id == g.ids[1]),
    }
    with pytest.raises(IntegrityError), g.sesiones.begin() as s:
        s.execute(sentencias[cambio])
    assert leer(g).validar_ejecutable() == g.ids[0]


def test_downgrade_no_pierde_grafo(gpg):
    with pytest.raises(RuntimeError, match="No eliminar"), gpg.engine.begin() as s:
        command.downgrade(config_alembic(s), PARENT)
    assert leer(gpg).validar_ejecutable() == gpg.ids[0]


def test_escritura_concurrente_de_entrada_no_deja_dos(gpg):
    g = gpg
    barrera = Barrier(2)
    def cambiar(indice):
        barrera.wait(timeout=5)
        with g.sesiones.begin() as s:
            Graph(s).configurar(version_id=g.v.id, docente_id=g.v.docente_creador_id,
                inicial_id=g.ids[indice], transiciones=())
    with ThreadPoolExecutor(max_workers=2) as pool:
        a, b = pool.submit(cambiar, 1), pool.submit(cambiar, 2)
        a.result(timeout=10)
        b.result(timeout=10)
    assert sum(e.inicial for e in leer(g).escenas) == 1


@pytest.fixture
def simulacion(pg_grafo):
    from app.modules.cases.infrastructure.models import CasoModel
    from app.modules.scheduling.infrastructure.models import SesionProgramadaModel
    from app.modules.scheduling.infrastructure.assignment_models import AsignacionCasoModel
    from app.modules.scheduling.application.crear_convocatoria import crear_convocatoria
    from tests.integration.test_participation_persistence import contexto, participacion, intento, FECHA
    from tests.integration.test_attempt_state import principal
    c = contexto(pg_grafo)
    v = version_grafo()
    v.caso_id, v.docente_creador_id, v.numero = c.version.caso_id, c.version.docente_creador_id, 2
    with c.sesiones.begin() as s:
        mapeado = CasoRepository(s)._mapear(v)
        edicion = mapeado.versiones.pop()
        familia = s.get(CasoModel, v.caso_id)
        familia.versiones.append(edicion)
    configurar(c.sesiones, v)
    c.version = publicar(c.sesiones, v)
    with c.sesiones.begin() as s:
        vieja = s.get(SesionProgramadaModel, c.sesion)
        nueva = SesionProgramadaModel(espacio_academico_id=vieja.espacio_academico_id, version_caso_id=v.id,
            docente_id=vieja.docente_id, fecha_inicio=vieja.fecha_inicio, fecha_fin=vieja.fecha_fin,
            tiempo_maximo_minutos=vieja.tiempo_maximo_minutos, estado="SIN_INICIAR")
        s.add(nueva); s.flush()
        a = s.get(AsignacionCasoModel, c.datos["id_asignacion"])
        asignacion = AsignacionCasoModel(id_grupo=a.id_grupo, id_caso=a.id_caso, sesion_programada_id=nueva.id,
            version_caso_id=v.id, apertura=a.apertura, cierre=a.cierre, fecha_limite_ingreso=a.fecha_limite_ingreso,
            tiempo_maximo_min=a.tiempo_maximo_min)
        s.add(asignacion); s.flush()
        conv = crear_convocatoria(s, sesion_id=nueva.id, estudiante_id=c.uuid)
        nueva.estado = "EN_CURSO"
        c.datos = c.datos | dict(id_asignacion=asignacion.id_asignacion, convocatoria_id=conv.convocatoria_id)
        c.sesion = nueva.id
    c.pk = participacion(c); c.ik = intento(c, c.pk)
    c.usuario = principal(c)
    from datetime import timedelta
    c.ahora = FECHA.replace(tzinfo=timezone.utc) + timedelta(minutes=1)
    return c


def facade(c):
    from tests.integration.test_steps_uuid import fachada
    # Default recorrido=None ahora compone el adaptador SQL REAL. Solo el permiso
    # de Scheduling procede de EdicionFixture, sin habilitar autorización real.
    return fachada(c)


def responder(c, escena):
    q = c.version.escenarios[escena].preguntas[0]
    return facade(c).registrar_decision(id_estudiante=c.alumno, id_intento=c.ik,
        id_decision=q.id, id_opcion=q.opciones[0].id)


def test_facade_con_recorrido_sql_real_y_evaluation(simulacion):
    from app.modules.participation.infrastructure.evaluation import crear_evaluacion_8c
    from app.modules.participation.infrastructure.codecs import FechasPersistencia
    from tests.integration.test_evaluation_persisted import MapeoFixture, PoliticaFixture
    from tests.integration.test_steps_uuid import filas
    c = simulacion
    responder(c, 0)
    antes = filas(c)
    with pytest.raises(AccesoDenegado):
        responder(c, 2)
    assert filas(c) == antes
    p = facade(c).consultar_progreso(id_estudiante=c.alumno, id_intento=c.ik)
    assert p.total_aplicable is None and len(p.pendientes) == 1
    responder(c, 1)
    p = facade(c).consultar_progreso(id_estudiante=c.alumno, id_intento=c.ik)
    assert p.total_aplicable == 2 and p.pendientes == ()
    facade(c).finalizar(id_estudiante=c.alumno, id_intento=c.ik)
    servicio = crear_evaluacion_8c(usuario=c.usuario, id_intento=c.ik,
        fechas=FechasPersistencia(timezone.utc), crear_sesion=c.sesiones,
        mapeo=MapeoFixture(), politica=PoliticaFixture(c, calculo=False))
    candidato = servicio.previsualizar_intento(id_estudiante=c.alumno, id_intento=c.ik)
    assert tuple(e.id_decision for e in candidato.evidencias) == tuple(s.id_decision for s in p.selecciones)
    assert candidato.nota_final is None and candidato.pendientes
    # No evaluación oficial: solo la ruta procede ahora de Cases persistido.


def test_facade_modificacion_pendiente_no_pierde_historia(simulacion):
    from tests.integration.test_steps_uuid import filas
    c = simulacion
    responder(c, 0)
    antes = filas(c)
    q = c.version.escenarios[0].preguntas[0]
    with pytest.raises(RespuestaInmutable):
        facade(c).modificar_decision(id_estudiante=c.alumno, id_intento=c.ik,
            id_decision=q.id, id_opcion=q.opciones[1].id)
    assert filas(c) == antes


def test_configuracion_y_publicacion_concurrentes(gpg):
    g, barrera = gpg, Barrier(2)
    def configurar_entrada():
        barrera.wait(timeout=5)
        try:
            with g.sesiones.begin() as s:
                Graph(s).configurar(version_id=g.v.id, docente_id=g.v.docente_creador_id,
                    inicial_id=g.ids[1], transiciones=())
            return "configurada"
        except GrafoNoDisponible:
            return "publicada"
    def publicar_version():
        barrera.wait(timeout=5)
        publicar_g(g)
    with ThreadPoolExecutor(max_workers=2) as pool:
        a, b = pool.submit(configurar_entrada), pool.submit(publicar_version)
        resultado = a.result(timeout=10); b.result(timeout=10)
    assert [e.id for e in leer(g, True).escenas if e.inicial] == [g.ids[1] if resultado == "configurada" else g.ids[0]]


def test_snapshot_antiguo_rechazado_solo_para_version_configurada(gpg):
    g = gpg
    with pytest.raises(DBAPIError) as error:
        with g.engine.connect().execution_options(isolation_level="REPEATABLE READ") as s, s.begin():
            s.execute(sa.update(O).where(O.id == g.opciones[1][0].id).values(tipo_transicion="FIN"))
    assert error.value.orig.sqlstate == "40001"


def test_otro_caso_sin_grafo_conserva_aislamiento_previo(gpg):
    v = nuevo()
    with gpg.sesiones() as s:
        CasoRepository(s).guardar(v)
    with gpg.engine.connect().execution_options(isolation_level="REPEATABLE READ") as s, s.begin():
        s.execute(sa.update(Q).where(Q.id == v.escenarios[0].preguntas[0].id).values(enunciado="Edición válida"))
    with gpg.sesiones() as s:
        assert s.get(Q, v.escenarios[0].preguntas[0].id).enunciado == "Edición válida"


def test_no_reutilizar_destino_borrado_en_otra_version(gpg):
    g, v = gpg, nuevo()
    with g.sesiones() as s:
        CasoRepository(s).guardar(v)
    with pytest.raises(IntegrityError), g.sesiones.begin() as s:
        s.execute(sa.delete(E).where(E.id == g.ids[1]))
        # La FK diferible no basta: el mismo UUID existe al confirmar, pero ahora
        # pertenece a otra edición. El trigger debe rechazar esta sustitución.
        s.execute(sa.insert(E).values(id=g.ids[1], version_caso_id=v.id, orden=2, contexto_situacional="Ajeno"))
    assert leer(g).validar_ejecutable() == g.ids[0]
