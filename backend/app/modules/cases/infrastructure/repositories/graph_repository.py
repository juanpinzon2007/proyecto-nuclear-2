"""Lectura/escritura interna de aristas, sin commits ni autenticación alternativa."""
from sqlalchemy import select, update, inspect, or_

from app.modules.cases.application.graph import (
    GrafoVersion, EscenaGrafo, PreguntaGrafo, Transicion, GrafoNoDisponible,
)
from app.modules.cases.domain.enums import EstadoCaso
from app.modules.cases.infrastructure.models import (
    CasoModel, VersionCasoModel, EscenarioModel, PreguntaModel, OpcionRespuestaModel,
)


class RepositorioGrafoSQLAlchemy:
    """El llamador acredita el actor y conserva la transacción.

    configurar comprueba además propietario y BORRADOR. No es un endpoint ni
    permite tratar un UUID recibido del cliente como identidad autenticada.
    """
    def __init__(self, sesion):
        self.sesion = sesion

    def instalado(self):
        # Compatibilidad con lectores/escritores sobre revisiones históricas.
        # Una BD aún no migrada nunca tiene un recorrido ejecutable.
        return "es_inicial" in {c["name"] for c in inspect(self.sesion.connection()).get_columns("escenario")}

    def configurado(self, version_id):
        if not self.instalado():
            return False
        e, p, o = EscenarioModel, PreguntaModel, OpcionRespuestaModel
        return self.sesion.scalar(select(e.id).where(e.version_caso_id == version_id, e.es_inicial).limit(1)) is not None or \
            self.sesion.scalar(select(o.id).join(p, p.id == o.pregunta_id).join(e, e.id == p.escenario_id)
                .where(e.version_caso_id == version_id, or_(o.tipo_transicion.is_not(None), o.escenario_destino_id.is_not(None)))
                .limit(1)) is not None

    def leer(self, version_id, *, solo_publicada=True):
        if not self.instalado():
            raise GrafoNoDisponible("El esquema de recorrido no está instalado.")
        s, v, e, p, o = self.sesion, VersionCasoModel, EscenarioModel, PreguntaModel, OpcionRespuestaModel
        with s.no_autoflush:
            estado = s.scalar(select(v.estado).where(v.id == version_id))
            if estado is None or (solo_publicada and estado not in (EstadoCaso.PUBLICADO, EstadoCaso.ARCHIVADO)):
                raise GrafoNoDisponible("Versión histórica no disponible.")
            escenas = s.execute(select(e.id, e.es_inicial, e.contexto_situacional)
                                 .where(e.version_caso_id == version_id).order_by(e.orden)).all()
            preguntas = s.execute(select(p.id, p.escenario_id, p.enunciado).join(e, e.id == p.escenario_id)
                                   .where(e.version_caso_id == version_id).order_by(p.orden)).all()
            opciones = s.execute(select(o.id, o.pregunta_id, o.tipo_transicion, o.escenario_destino_id, o.texto)
                .join(p, p.id == o.pregunta_id).join(e, e.id == p.escenario_id)
                .where(e.version_caso_id == version_id).order_by(o.orden)).all()
        return GrafoVersion(version_id, tuple(EscenaGrafo(x.id, x.es_inicial, x.contexto_situacional,
            tuple(PreguntaGrafo(q.id, q.enunciado, tuple(Transicion(a.id, a.tipo_transicion,
                a.escenario_destino_id, a.texto) for a in opciones if a.pregunta_id == q.id))
                for q in preguntas if q.escenario_id == x.id)) for x in escenas))

    def configurar(self, *, version_id, docente_id, inicial_id, transiciones):
        """transiciones: tupla (opcion_id, tipo, destino_id), explícita del autor.

        Permite guardar un borrador incompleto; ejecutabilidad es otra validación.
        No rellena aristas ni cambia versiones históricas. Sin commit propio.
        """
        s, v, e, p, o = self.sesion, VersionCasoModel, EscenarioModel, PreguntaModel, OpcionRespuestaModel
        if not s.in_transaction():
            raise GrafoNoDisponible("La escritura exige una transacción del llamador.")
        with s.no_autoflush:
            fila = s.execute(select(v.estado, CasoModel.docente_creador_id).join(CasoModel, CasoModel.id == v.caso_id)
                .where(v.id == version_id).with_for_update(of=v)).one_or_none()
            if fila is None or fila.docente_creador_id != docente_id or fila.estado != EstadoCaso.BORRADOR:
                raise GrafoNoDisponible("Solo el propietario puede configurar un borrador.")
            ids = set(s.scalars(select(e.id).where(e.version_caso_id == version_id)))
            opciones = set(s.scalars(select(o.id).join(p, p.id == o.pregunta_id)
                .where(p.escenario_id.in_(ids))))
            if inicial_id not in ids or len({a[0] for a in transiciones}) != len(transiciones):
                raise GrafoNoDisponible("Entrada ajena o aristas duplicadas.")
            for opcion, tipo, destino in transiciones:
                if opcion not in opciones or not ((tipo is None and destino is None) or
                    (tipo == "FIN" and destino is None) or (tipo == "ESCENA" and destino in ids)):
                    raise GrafoNoDisponible("Transición incoherente o de otra versión.")
            # Validar todo antes de escribir, también en SQLite sin triggers PG.
            s.execute(update(e).where(e.version_caso_id == version_id).values(es_inicial=False))
            s.execute(update(e).where(e.id == inicial_id).values(es_inicial=True))
            for opcion, tipo, destino in transiciones:
                s.execute(update(o).where(o.id == opcion).values(tipo_transicion=tipo, escenario_destino_id=destino))
