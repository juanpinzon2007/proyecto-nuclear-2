"""Regresión real de leases HTTP, PG17 propio y una conexión disponible."""
from pathlib import Path
import json

import sqlalchemy as sa
import pytest

from app.db.session import get_session_factory
from tests.integration.test_main_configured_student_flow import (
    configurado, asignable, personal, lab, inicializar, payload_valido,
    aceptar, admitir, iniciar,
)  # noqa: F401 - fixtures reales, sin overrides de autenticación


@pytest.mark.parametrize('operacion', ['progreso', 'escenario', 'ingreso'])
def test_progreso_autenticado_libera_conexion_de_identidad_antes_del_caso_de_uso(configurado, operacion):
    h=configurado
    consentimiento=aceptar(h)
    admitir(h)
    resultado=iniciar(h,consentimiento)
    assert resultado.status_code==201
    fabrica=get_session_factory()
    anterior=fabrica.kw['bind']
    limitado=sa.create_engine(anterior.url,pool_size=1,max_overflow=0,pool_timeout=.3,pool_pre_ping=True)
    eventos=[]
    sa.event.listen(limitado,'checkout',lambda *args:eventos.append('checkout'))
    sa.event.listen(limitado,'checkin',lambda *args:eventos.append('checkin'))
    try:
        fabrica.configure(bind=limitado)
        if operacion=='ingreso':
            respuesta=h.cliente.post('/scheduling/validar-ingreso',headers=h.estudiante,
                json=dict(convocatoria_id=h.cid,estudiante_id=str(h.a.estudiante),codigo_acceso=h.codigo))
        else:
            sufijo='progress' if operacion=='progreso' else 'current-scenario'
            respuesta=h.cliente.get(f'/api/v1/attempts/{resultado.json()["id_intento"]}/{sufijo}',headers=h.estudiante)
        evidencia=dict(pool_size=1,max_overflow=0,pool_timeout=.3,http=respuesta.status_code,
            respuesta=respuesta.json(),eventos=eventos,conexiones_finales=limitado.pool.checkedout())
        # Nombre distinto por ejecución mediante variable exclusivamente de evidencia.
        import os
        destino=os.environ.get('AUDIT_POOL_OUTPUT')
        if destino:
            Path(destino).with_stem(Path(destino).stem+'_'+operacion).write_text(json.dumps(evidencia,ensure_ascii=False,indent=2),encoding='utf-8')
        assert respuesta.status_code==200, f'Una consulta privada legítima produjo HTTP {respuesta.status_code} al retener la conexión de autenticación.'
        assert limitado.pool.checkedout()==0
    finally:
        fabrica.configure(bind=anterior)
        limitado.dispose()


@pytest.mark.parametrize("lector", ["cuenta", "vinculos", "convocatoria"])
def test_lector_breve_devuelve_conexion_y_revierte_error_sql_real(configurado, lector):
    from sqlalchemy.orm import sessionmaker
    from uuid import UUID
    from app.modules.identity.application.academic_identity import SistemaAcademico
    from app.modules.identity.domain.errors import IntegracionPendiente
    from app.modules.identity.infrastructure.account_reader import (
        ConsultaCuentaPorIdSQLAlchemy,
        ConsultaVinculosSesionBreveSQLAlchemy,
        ValidadorContextoSesionBreveSQLAlchemy,
    )
    from app.modules.identity.infrastructure.academic_identity_models import IdentidadAcademicaORM

    h = configurado
    with h.a.h.sesiones() as sesion:
        usuario_id = str(sesion.scalar(sa.select(IdentidadAcademicaORM.id_usuario).where(
            IdentidadAcademicaORM.id_academico == h.a.estudiante)))
    engine = sa.create_engine(get_session_factory().kw["bind"].url, pool_size=1, max_overflow=0, pool_timeout=.3)
    sesiones = sessionmaker(engine)
    inyectar = True

    def fallar_sql(conexion, cursor, sentencia, parametros, contexto, varios):
        nonlocal inyectar
        if inyectar:
            inyectar = False
            conexion.exec_driver_sql("SELECT 1 / 0")

    sa.event.listen(engine, "before_cursor_execute", fallar_sql)
    try:
        with pytest.raises(IntegracionPendiente):
            if lector == "cuenta":
                ConsultaCuentaPorIdSQLAlchemy(sesiones).obtener(usuario_id)
            elif lector == "vinculos":
                ConsultaVinculosSesionBreveSQLAlchemy(sesiones).obtener(
                    id_usuario=usuario_id, sistema=SistemaAcademico.SCHEDULING)
            else:
                ValidadorContextoSesionBreveSQLAlchemy(sesiones).validar_contexto(
                    id_usuario=usuario_id, contexto=h.cid, solicitada=UUID(h.cid))
        assert not inyectar, "El error debe ocurrir sobre una conexión PostgreSQL real."
        assert engine.pool.checkedout() == 0
        with sesiones() as sesion:
            assert sesion.scalar(sa.text("SELECT 1")) == 1
        assert engine.pool.checkedout() == 0
    finally:
        engine.dispose()


@pytest.mark.parametrize("rechazo", ["sin_jwt", "jwt_invalido", "cuenta_inactiva", "convocatoria_retirada"])
def test_rechazo_http_no_retiene_conexion_ni_escribe(configurado, rechazo):
    from uuid import UUID
    from app.modules.identity.infrastructure.academic_identity_models import IdentidadAcademicaORM
    from app.modules.identity.infrastructure.models import UsuarioORM
    from app.modules.scheduling.infrastructure.models import ConvocatoriaModel

    h = configurado
    consentimiento = aceptar(h)
    admitir(h)
    inicio = iniciar(h, consentimiento)
    assert inicio.status_code == 201
    headers = h.estudiante
    esperado = 403
    if rechazo == "sin_jwt":
        headers = {}
        esperado = 401
    elif rechazo == "jwt_invalido":
        headers = {"Authorization": "Bearer invalido"}
        esperado = 401
    elif rechazo == "cuenta_inactiva":
        with h.a.h.sesiones.begin() as sesion:
            usuario_id = sesion.scalar(sa.select(IdentidadAcademicaORM.id_usuario).where(
                IdentidadAcademicaORM.id_academico == h.a.estudiante))
            sesion.get(UsuarioORM, usuario_id).activo = False
        esperado = 401
    else:
        with h.a.h.sesiones.begin() as sesion:
            sesion.get(ConvocatoriaModel, UUID(h.cid)).estado = "RETIRADA"
    fabrica = get_session_factory()
    original = fabrica.kw["bind"]
    engine = sa.create_engine(original.url, pool_size=1, max_overflow=0, pool_timeout=.3)
    escrituras = []

    def registrar(conexion, cursor, sentencia, parametros, contexto, varios):
        if sentencia.lstrip().split()[0].upper() in {"INSERT", "UPDATE", "DELETE"}:
            escrituras.append(sentencia)

    sa.event.listen(engine, "before_cursor_execute", registrar)
    sa.event.listen(engine, "commit", lambda conexion: escrituras.append("COMMIT"))
    try:
        fabrica.configure(bind=engine)
        respuesta = h.cliente.get(
            f'/api/v1/attempts/{inicio.json()["id_intento"]}/progress', headers=headers)
        assert respuesta.status_code == esperado
        assert engine.pool.checkedout() == 0
        assert escrituras == []
    finally:
        fabrica.configure(bind=original)
        engine.dispose()
