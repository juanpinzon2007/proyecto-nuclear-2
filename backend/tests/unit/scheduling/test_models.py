
from app.modules.scheduling.infrastructure.models import (
    EspacioAcademicoModel,
    SesionProgramadaModel,
    ConvocatoriaModel,
    NotificacionModel,
    EventoAuditoriaModel,
)


def test_tabla_espacio_academico():
    assert EspacioAcademicoModel.__tablename__ == (
        "espacio_academico"
    )


def test_tabla_sesion_programada():
    assert SesionProgramadaModel.__tablename__ == (
        "sesion_programada"
    )


def test_tabla_convocatoria():
    assert ConvocatoriaModel.__tablename__ == (
        "convocatoria"
    )


def test_tabla_notificacion():
    assert NotificacionModel.__tablename__ == (
        "notificacion"
    )


def test_tabla_evento_auditoria():
    assert EventoAuditoriaModel.__tablename__ == (
        "evento_auditoria"
    )


def test_sesion_relacionada_con_caso():
    claves = {
        fk.target_fullname
        for fk in SesionProgramadaModel.__table__.foreign_keys
    }

    assert "version_caso.id" in claves
    assert "espacio_academico.id" in claves


def test_convocatoria_relacionada_con_sesion():
    claves = {
        fk.target_fullname
        for fk in ConvocatoriaModel.__table__.foreign_keys
    }

    assert "sesion_programada.id" in claves


def test_auditoria_relacionada_con_sesion():
    claves = {
        fk.target_fullname
        for fk in EventoAuditoriaModel.__table__.foreign_keys
    }

    assert "sesion_programada.id" in claves
