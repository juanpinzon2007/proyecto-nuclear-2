"""Agregado completo de Participation sobre las tablas reales; sin commit propio.

PostgreSQL proporciona IDs de secuencia y locks. SQLite se reserva a DDL/lecturas:
este escritor no simula allí una asignación concurrente de identificadores.
"""
from dataclasses import replace
from decimal import Decimal

from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from app.modules.participation.application.errors import ConflictoActualizacion, ReglaPendiente
from app.modules.participation.domain.entities import EstadoIntento, Intento
from app.modules.participation.domain.errors import RespuestaInmutable
from app.modules.participation.infrastructure.codecs import FechasPersistencia
from app.modules.participation.infrastructure.models import ParticipacionModel, IntentoModel, PasoSimulacionModel
from app.modules.participation.infrastructure.queries import TablasLecturaParticipacion, LecturasParticipacionSQLAlchemy, consultar_duracion_historica


class RepositorioParticipacionSQLAlchemy(LecturasParticipacionSQLAlchemy):
    def __init__(self,sesion:Session,*,fechas:FechasPersistencia):
        super().__init__(sesion,TablasLecturaParticipacion(ParticipacionModel.__table__,IntentoModel.__table__,PasoSimulacionModel.__table__),
            fechas=fechas,estados={e.value:e for e in EstadoIntento},duracion_historica=consultar_duracion_historica,bloquear=True)

    def _escritor(self):
        if self.sesion.get_bind().dialect.name!="postgresql" or not self.sesion.in_transaction():
            raise ReglaPendiente("El escritor exige una transacción PostgreSQL real.")

    def nuevo_id_intento(self):
        self._escritor()
        return self.sesion.scalar(text("SELECT nextval(pg_get_serial_sequence('public.intento','id_intento'))"))

    def obtener_por_convocatoria(self, convocatoria_id):
        self._escritor()
        pk = self.sesion.scalar(select(ParticipacionModel.id_participacion).where(
            ParticipacionModel.convocatoria_id==convocatoria_id).with_for_update())
        return self.obtener_participacion(pk) if pk is not None else None

    def agregar_participacion(self, *, id_asignacion, id_grupo_estudiante,
                             convocatoria_id, estado, fecha_registro):
        """Inserta referencias acreditadas; no elige estado ni confirma la UoW."""
        self._escritor()
        pk = self.sesion.scalar(ParticipacionModel.__table__.insert().values(
            id_asignacion=id_asignacion,id_grupo_estudiante=id_grupo_estudiante,
            convocatoria_id=convocatoria_id,estado=estado,
            fecha_registro=self.fechas.hacia_db(fecha_registro,sin_offset=True))
            .returning(ParticipacionModel.id_participacion))
        return self.obtener_participacion(pk)

    def nuevo_id_paso(self):
        self._escritor()
        return self.sesion.scalar(text("SELECT nextval(pg_get_serial_sequence('public.paso_simulacion','id_paso'))"))

    def _datos_paso(self,paso,id_intento):
        return dict(id_paso=paso.id_paso,id_intento=id_intento,id_decision=paso.id_decision,id_opcion=paso.id_opcion,
            numero_paso=paso.numero_paso,registrado_en=self.fechas.hacia_db(paso.registrado_en,sin_offset=True),
            tiempo_segundos=paso.tiempo_segundos,reflexion_estudiante=paso.reflexion_estudiante)

    def agregar_intento(self,intento:Intento):
        self._escritor()
        self.obtener_participacion(intento.id_participacion)
        t=intento.tiempo_maximo
        duracion=Decimal(t.days*86400+t.seconds)+Decimal(t.microseconds)/Decimal(1000000)
        self.sesion.execute(IntentoModel.__table__.insert().values(id_intento=intento.id_intento,
            id_participacion=intento.id_participacion,id_consentimiento=intento.id_consentimiento,
            id_permiso_extra=intento.id_permiso_extra,numero_intento=intento.numero_intento,
            estado=intento.estado.value,inicio=self.fechas.hacia_db(intento.inicio,sin_offset=True),
            fin=self.fechas.hacia_db(intento.fin,sin_offset=True) if intento.fin else None,duracion_concedida_segundos=duracion))
        for paso in intento.pasos:
            self.sesion.execute(PasoSimulacionModel.__table__.insert().values(**self._datos_paso(paso,intento.id_intento)))

    def guardar_intento(self,intento:Intento,*,esperado:Intento):
        self._escritor()
        actual=self.obtener_intento(intento.id_intento)
        if actual!=esperado:
            raise ConflictoActualizacion("El intento cambió; vuelva a leer.")
        if replace(intento,pasos=esperado.pasos,estado=esperado.estado,fin=esperado.fin)!=esperado:
            raise ConflictoActualizacion("No se puede reasignar identidad ni duración.")
        anteriores={p.id_paso:p for p in esperado.pasos}
        nuevos={p.id_paso:p for p in intento.pasos}
        if not anteriores.keys()<=nuevos.keys():
            raise RespuestaInmutable("No está autorizada la eliminación de respuestas.")
        if any(nuevos[id_paso] != paso for id_paso, paso in anteriores.items()):
            raise RespuestaInmutable("No se puede actualizar ningún campo de una respuesta persistida.")
        tabla=PasoSimulacionModel.__table__
        for paso in intento.pasos:
            previo=anteriores.get(paso.id_paso)
            if previo==paso:
                continue
            datos=self._datos_paso(paso,intento.id_intento)
            if previo is None:
                self.sesion.execute(tabla.insert().values(**datos))
        if (intento.estado,intento.fin)!=(esperado.estado,esperado.fin):
            r=self.sesion.execute(update(IntentoModel).where(IntentoModel.id_intento==intento.id_intento,IntentoModel.estado==esperado.estado.value,
                IntentoModel.fin==self.fechas.hacia_db(esperado.fin,sin_offset=True) if esperado.fin else IntentoModel.fin.is_(None)).values(
                estado=intento.estado.value,fin=self.fechas.hacia_db(intento.fin,sin_offset=True) if intento.fin else None))
            if r.rowcount!=1:
                raise ConflictoActualizacion("El cierre cambió.")
