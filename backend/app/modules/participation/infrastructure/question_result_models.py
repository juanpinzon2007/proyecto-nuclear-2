"""Detalles específicos, con una única cabecera canónica resultado_intento."""
from decimal import Decimal
from uuid import UUID
from sqlalchemy import Integer, Uuid, Numeric, String, ForeignKey, ForeignKeyConstraint, CheckConstraint, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from app.modules.cases.infrastructure.models import OpcionRespuestaModel

Index('uq_8c_opcion_pregunta',OpcionRespuestaModel.id,OpcionRespuestaModel.pregunta_id,unique=True)


class ResultadoCalculoPreguntasModel(Base):
    __tablename__='resultado_calculo_preguntas'
    __table_args__=(CheckConstraint('preguntas_exigidas > 0 AND preguntas_respondidas >= 0 AND preguntas_pendientes >= 0 AND preguntas_respondidas + preguntas_pendientes = preguntas_exigidas',name='ck_rp_cantidades'),
        CheckConstraint('suma_puntajes >= 0 AND suma_puntajes <= 100 * preguntas_exigidas',name='ck_rp_suma'),
        CheckConstraint('length(configuracion_sha256)=64',name='ck_rp_config_hash'))
    id_resultado: Mapped[int]=mapped_column(ForeignKey('resultado_intento.id_resultado'),primary_key=True)
    suma_puntajes: Mapped[Decimal]=mapped_column(Numeric(),nullable=False)
    preguntas_exigidas: Mapped[int]=mapped_column(Integer,nullable=False)
    preguntas_respondidas: Mapped[int]=mapped_column(Integer,nullable=False)
    preguntas_pendientes: Mapped[int]=mapped_column(Integer,nullable=False)
    configuracion_sha256: Mapped[str]=mapped_column(String(64),nullable=False)


class ResultadoPreguntaModel(Base):
    __tablename__='resultado_pregunta'
    __table_args__=(ForeignKeyConstraint(['opcion_id','pregunta_id'],['opcion_respuesta.id','opcion_respuesta.pregunta_id'],name='fk_rp_opcion_pregunta'),
        UniqueConstraint('id_resultado','numero_paso',name='uq_rp_numero'),
        CheckConstraint('puntaje >= 0 AND puntaje <= 100 AND numero_paso > 0',name='ck_rp_puntaje'))
    id_resultado: Mapped[int]=mapped_column(ForeignKey('resultado_intento.id_resultado'),primary_key=True)
    pregunta_id: Mapped[UUID]=mapped_column(Uuid,ForeignKey('pregunta.id'),primary_key=True)
    opcion_id: Mapped[UUID]=mapped_column(Uuid,nullable=False)
    puntaje: Mapped[Decimal]=mapped_column(Numeric(),nullable=False)
    numero_paso: Mapped[int]=mapped_column(Integer,nullable=False)


class ResultadoCriterioExactoModel(Base):
    __tablename__='resultado_criterio_exacto'
    __table_args__=(ForeignKeyConstraint(['id_resultado','rubrica_id'],['resultado_intento.id_resultado','resultado_intento.rubrica_id'],name='fk_rce_resultado'),
        ForeignKeyConstraint(['criterio_id','rubrica_id'],['criterio_rubrica.id','criterio_rubrica.rubrica_id'],name='fk_rce_criterio'),
        CheckConstraint('preguntas_evaluables > 0 AND suma_puntajes >= 0 AND suma_puntajes <= 100 * preguntas_evaluables',name='ck_rce_suma'),
        CheckConstraint("numerador >= 0 AND denominador > 0 AND numerador = round(numerador,0) AND denominador = round(denominador,0) AND numerador NOT IN ('NaN','Infinity','-Infinity') AND denominador NOT IN ('NaN','Infinity','-Infinity')",name='ck_rce_fraccion'))
    id_resultado: Mapped[int]=mapped_column(Integer,primary_key=True)
    criterio_id: Mapped[UUID]=mapped_column(Uuid,primary_key=True)
    rubrica_id: Mapped[UUID]=mapped_column(Uuid,nullable=False)
    suma_puntajes: Mapped[Decimal]=mapped_column(Numeric(),nullable=False)
    preguntas_evaluables: Mapped[int]=mapped_column(Integer,nullable=False)
    numerador: Mapped[Decimal]=mapped_column(Numeric(),nullable=False)
    denominador: Mapped[Decimal]=mapped_column(Numeric(),nullable=False)
