"""Resultados oficiales versionados, separados de la cabecera técnica existente."""
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from sqlalchemy import Boolean,CheckConstraint,DateTime,ForeignKey,Integer,Numeric,String,Text,UniqueConstraint,Uuid
from sqlalchemy.orm import Mapped,mapped_column
from app.db.base import Base


class AusenciaAcademicaModel(Base):
    __tablename__='ausencia_academica'
    __table_args__=(UniqueConstraint('convocatoria_id','revision',name='uq_aa_revision'),CheckConstraint("revision>0 AND length(trim(motivo))>0",name='ck_aa_datos'))
    id:Mapped[UUID]=mapped_column(Uuid,primary_key=True)
    convocatoria_id:Mapped[UUID]=mapped_column(ForeignKey('convocatoria.id'),nullable=False)
    sesion_id:Mapped[UUID]=mapped_column(ForeignKey('sesion_programada.id'),nullable=False)
    id_estudiante:Mapped[int]=mapped_column(ForeignKey('usuario.id_usuario'),nullable=False)
    id_profesor:Mapped[int]=mapped_column(ForeignKey('usuario.id_usuario'),nullable=False)
    version_caso_id:Mapped[UUID]=mapped_column(ForeignKey('version_caso.id'),nullable=False)
    revision:Mapped[int]=mapped_column(Integer,nullable=False)
    confirmada:Mapped[bool]=mapped_column(Boolean,nullable=False)
    anterior_id:Mapped[UUID|None]=mapped_column(ForeignKey('ausencia_academica.id'))
    motivo:Mapped[str]=mapped_column(Text,nullable=False)
    fecha:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)


class PublicacionEvaluacionModel(Base):
    __tablename__='publicacion_evaluacion'
    __table_args__=(UniqueConstraint('sesion_id','version',name='uq_pe_version'),CheckConstraint('version>0 AND length(fuente_sha256)=64',name='ck_pe_datos'))
    id:Mapped[UUID]=mapped_column(Uuid,primary_key=True)
    sesion_id:Mapped[UUID]=mapped_column(ForeignKey('sesion_programada.id'),nullable=False)
    id_profesor:Mapped[int]=mapped_column(ForeignKey('usuario.id_usuario'),nullable=False)
    version:Mapped[int]=mapped_column(Integer,nullable=False)
    fecha:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)
    fuente_documento:Mapped[str]=mapped_column(Text,nullable=False)
    fuente_sha256:Mapped[str]=mapped_column(String(64),nullable=False)


class ResultadoParticipacionModel(Base):
    __tablename__='resultado_participacion'
    __table_args__=(UniqueConstraint('publicacion_id','convocatoria_id',name='uq_rp_publicacion_convocatoria'),
        CheckConstraint("nota_definitiva>=0 AND nota_definitiva<=100 AND situacion IN ('COMPLETA','PARCIAL','AUSENTE')",name='ck_rp_oficial_nota'),
        CheckConstraint("(situacion='AUSENTE' AND id_ausencia IS NOT NULL AND id_resultado_intento IS NULL AND nota_definitiva=0) OR (situacion IN ('COMPLETA','PARCIAL') AND id_ausencia IS NULL AND id_resultado_intento IS NOT NULL AND id_participacion IS NOT NULL)",name='ck_rp_oficial_origen'))
    id_resultado_participacion:Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    publicacion_id:Mapped[UUID]=mapped_column(ForeignKey('publicacion_evaluacion.id'),nullable=False)
    convocatoria_id:Mapped[UUID]=mapped_column(ForeignKey('convocatoria.id'),nullable=False)
    id_participacion:Mapped[int|None]=mapped_column(ForeignKey('participacion.id_participacion'))
    id_estudiante:Mapped[int]=mapped_column(ForeignKey('usuario.id_usuario'),nullable=False)
    id_asignacion:Mapped[int]=mapped_column(ForeignKey('asignacion_caso.id_asignacion'),nullable=False)
    id_resultado_intento:Mapped[int|None]=mapped_column(ForeignKey('resultado_intento.id_resultado'))
    id_ausencia:Mapped[UUID|None]=mapped_column(ForeignKey('ausencia_academica.id'))
    situacion:Mapped[str]=mapped_column(String(20),nullable=False)
    nota_definitiva:Mapped[Decimal]=mapped_column(Numeric(5,2),nullable=False)
    detalle:Mapped[str]=mapped_column(Text,nullable=False)
