"""Repositorio SQLAlchemy del agregado Caso."""

import uuid
from decimal import Decimal, Context, localcontext
from dataclasses import asdict
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, contains_eager, selectinload

from app.modules.cases.domain.entities.caso import (
    CriterioRubrica,
    Escenario,
    NivelRubrica,
    OpcionRespuesta,
    Pregunta,
    ResumenVersion,
    Rubrica,
    VersionCaso,
)
from app.modules.cases.domain.exceptions import ErrorPersistenciaCaso, ErrorConstruccionCaso
from app.modules.cases.domain.enums import EstadoCaso
from app.modules.cases.domain.repositories import ICasoRepository
from app.modules.cases.domain.validators.eslabones import construir_cadena_publicacion
from app.modules.cases.infrastructure.models import (
    CasoModel,
    CriterioRubricaModel,
    EscenarioModel,
    NivelRubricaModel,
    OpcionRespuestaModel,
    PreguntaModel,
    RubricaModel,
    ValoracionOpcionModel,
    VersionCasoModel,
)


class CasoRepository(ICasoRepository):
    """Mapea entidades puras a modelos ORM y las guarda en una sola transacción."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def guardar(self, version: VersionCaso) -> None:
        self._validar_precision_puntajes(version)
        with self._transaccion():
            self._session.add(self._mapear(version))

    def obtener_version(
        self, version_id: uuid.UUID, docente_creador_id: uuid.UUID
    ) -> VersionCaso | None:
        modelo = self._session.get(VersionCasoModel, version_id)
        if modelo is None or modelo.caso.docente_creador_id != docente_creador_id:
            return None
        return self._a_dominio(modelo)

    def listar_por_docente(self, docente_creador_id: uuid.UUID) -> list[ResumenVersion]:
        consulta = (
            select(VersionCasoModel)
            .join(VersionCasoModel.caso)
            .options(contains_eager(VersionCasoModel.caso))
            .where(CasoModel.docente_creador_id == docente_creador_id)
            .order_by(CasoModel.creado_en.desc(), VersionCasoModel.numero.desc())
        )
        return [
            ResumenVersion(
                version_id=m.id,
                caso_id=m.caso_id,
                numero=m.numero,
                nombre=m.nombre,
                tiempo_estimado_min=m.tiempo_estimado_min,
                estado=m.estado,
                creado_en=m.caso.creado_en,
            )
            for m in self._session.scalars(consulta).unique()
        ]

    def reemplazar(self, version: VersionCaso) -> None:
        with self._transaccion():
            modelo = self._para_escritura(version)
            self._a_dominio(modelo).asegurar_editable()
            version.asegurar_editable()
            self._validar_precision_puntajes(version)
            from app.modules.cases.infrastructure.repositories.graph_repository import RepositorioGrafoSQLAlchemy
            if RepositorioGrafoSQLAlchemy(self._session).configurado(version.id):
                raise ErrorPersistenciaCaso("El reemplazo de contenido descartaría el grafo; edite el borrador antes de configurarlo.")
            # Borra la estructura anterior y la confirma en la BD antes de insertar la nueva
            # (las restricciones únicas de orden y de rúbrica lo exigen).
            modelo.escenarios.clear()
            modelo.rubrica = None
            self._session.flush()
            modelo.nombre = version.nombre
            modelo.desarrollo_situacional = version.desarrollo_situacional
            modelo.contexto_historia = version.contexto_historia
            modelo.tiempo_estimado_min = version.tiempo_estimado_min
            modelo.estado = version.estado
            modelo.escenarios = [self._mapear_escenario(e) for e in version.escenarios]
            modelo.rubrica = self._mapear_rubrica(version.rubrica) if version.rubrica else None

    def actualizar_estado(self, version: VersionCaso) -> None:
        with self._transaccion():
            self._aplicar_estado(version)

    @staticmethod
    def _validar_precision_puntajes(version: VersionCaso) -> None:
        from app.modules.cases.application.scoring import REGLA_PREGUNTAS
        if version.rubrica is None or version.rubrica.version_regla != REGLA_PREGUNTAS:
            return
        for escena in version.escenarios:
            for pregunta in escena.preguntas:
                for opcion in pregunta.opciones:
                    for p in opcion.valoraciones.values():
                        error = "Puntaje explícito 0–100 representable exactamente con dos decimales requerido; no se redondea al guardar."
                        if not isinstance(p, Decimal) or not p.is_finite() or not Decimal(0) <= p <= Decimal(100):
                            raise ErrorConstruccionCaso(error)
                        with localcontext(Context(prec=32)):
                            if p != p.quantize(Decimal('.01')):
                                raise ErrorConstruccionCaso(error)

    def publicar_ejecutable(self, version: VersionCaso) -> None:
        with self._transaccion():
            self._aplicar_estado(version, exigir_recorrido=True)

    def _aplicar_estado(self, version: VersionCaso, *, exigir_recorrido=False) -> None:
        modelo = self._para_escritura(version)
        actual = self._a_dominio(modelo)
        if self._contenido(actual) != self._contenido(version):
            raise ErrorPersistenciaCaso("El contenido cambió desde su lectura; vuelva a consultar la versión.")
        if version.estado == EstadoCaso.PUBLICADO:
            actual.publicar(construir_cadena_publicacion())
            # Opt-in explícito en la rúbrica de NUEVAS ediciones. El mismo lock
            # raíz protege contenido/grafo/puntajes hasta confirmar publicación.
            from app.modules.cases.application.scoring import REGLA_PREGUNTAS
            if actual.rubrica and actual.rubrica.version_regla == REGLA_PREGUNTAS:
                from app.modules.cases.infrastructure.scoring import consultar_configuracion_preguntas
                consultar_configuracion_preguntas(self._session, version_id=version.id, solo_publicada=False)
            if exigir_recorrido:
                # Mismo lock raíz que configurar y los guards históricos.
                self.obtener_recorrido(version).validar_ejecutable()
        elif version.estado == EstadoCaso.ARCHIVADO and not exigir_recorrido:
            actual.archivar()
        else:
            raise ErrorPersistenciaCaso("Transición de estado no permitida.")
        modelo.estado = actual.estado

    def obtener_recorrido(self, version: VersionCaso):
        from app.modules.cases.infrastructure.repositories.graph_repository import RepositorioGrafoSQLAlchemy
        return RepositorioGrafoSQLAlchemy(self._session).leer(version.id, solo_publicada=False)

    def configurar_recorrido(self, version: VersionCaso, *, inicial_id, transiciones):
        from app.modules.cases.infrastructure.repositories.graph_repository import RepositorioGrafoSQLAlchemy
        with self._transaccion():
            modelo = self._para_escritura(version)
            self._a_dominio(modelo).asegurar_editable()
            grafo = RepositorioGrafoSQLAlchemy(self._session)
            previo = grafo.leer(version.id, solo_publicada=False)
            configuradas = {opcion for opcion, _, _ in transiciones}
            # PUT representa una configuración completa: lo omitido queda sin
            # configurar, nunca se conservan aristas antiguas silenciosamente.
            omitidas = tuple((o.opcion_id, None, None) for e in previo.escenas
                             for p in e.preguntas for o in p.opciones
                             if o.opcion_id not in configuradas)
            grafo.configurar(version_id=version.id, docente_id=version.docente_creador_id,
                            inicial_id=inicial_id, transiciones=(*transiciones, *omitidas))
            resultado = grafo.leer(version.id, solo_publicada=False)
            resultado.validar_ejecutable()
        return resultado

    def _para_escritura(self, version: VersionCaso) -> VersionCasoModel:
        # Serializa escritores de este repositorio sobre la misma fila raíz.
        # populate_existing evita confiar en el identity map de una lectura anterior.
        modelo = self._session.scalar(
            select(VersionCasoModel).where(VersionCasoModel.id == version.id)
            .with_for_update().execution_options(populate_existing=True)
            .options(
                selectinload(VersionCasoModel.escenarios).selectinload(EscenarioModel.preguntas)
                .selectinload(PreguntaModel.opciones).selectinload(OpcionRespuestaModel.valoraciones),
                selectinload(VersionCasoModel.rubrica).selectinload(RubricaModel.criterios)
                .selectinload(CriterioRubricaModel.niveles),
            )
        )
        if modelo is None:
            raise ErrorPersistenciaCaso("La versión a modificar no existe.")
        propietario = self._session.scalar(select(CasoModel.docente_creador_id).where(CasoModel.id == modelo.caso_id))
        if (modelo.caso_id != version.caso_id or modelo.numero != version.numero
                or propietario != version.docente_creador_id):
            raise ErrorPersistenciaCaso("La identidad de la versión no corresponde a la almacenada.")
        return modelo

    @staticmethod
    def _contenido(version: VersionCaso):
        # Comparación estructural, sin estado; orden lógico conservado en `orden`.
        # El orden físico de criterios/niveles sin ORDER BY no crea conflictos falsos.
        def normalizar(valor):
            if isinstance(valor, dict):
                return tuple(sorted((str(k), normalizar(v)) for k, v in valor.items()))
            if isinstance(valor, list):
                return tuple(sorted((normalizar(v) for v in valor), key=repr))
            return valor
        datos = asdict(version)
        datos.pop("estado")
        return normalizar(datos)

    @contextmanager
    def _transaccion(self) -> Iterator[None]:
        """Commit al salir sin errores; rollback ante cualquier excepción."""
        try:
            with self._session.no_autoflush:
                yield
            self._session.commit()
        except SQLAlchemyError as exc:
            self._session.rollback()
            raise ErrorPersistenciaCaso("No se pudo guardar el caso.") from exc
        except Exception:
            self._session.rollback()
            raise

    # --- mapeo ORM -> dominio -------------------------------------------------

    @staticmethod
    def _a_dominio(m: VersionCasoModel) -> VersionCaso:
        rubrica = None
        if m.rubrica is not None:
            rubrica = Rubrica(
                id=m.rubrica.id,
                nombre=m.rubrica.nombre,
                version_regla=m.rubrica.version_regla,
                criterios=[
                    CriterioRubrica(
                        id=c.id,
                        nombre=c.nombre,
                        peso=c.peso,
                        niveles=[
                            NivelRubrica(
                                id=n.id, nombre=n.nombre, puntaje=n.puntaje, descriptor=n.descriptor
                            )
                            for n in c.niveles
                        ],
                    )
                    for c in m.rubrica.criterios
                ],
            )
        return VersionCaso(
            id=m.id,
            caso_id=m.caso_id,
            docente_creador_id=m.caso.docente_creador_id,
            numero=m.numero,
            nombre=m.nombre,
            desarrollo_situacional=m.desarrollo_situacional,
            contexto_historia=m.contexto_historia,
            tiempo_estimado_min=m.tiempo_estimado_min,
            estado=m.estado,
            rubrica=rubrica,
            escenarios=[
                Escenario(
                    id=e.id,
                    orden=e.orden,
                    contexto_situacional=e.contexto_situacional,
                    preguntas=[
                        Pregunta(
                            id=p.id,
                            orden=p.orden,
                            enunciado=p.enunciado,
                            opciones=[
                                OpcionRespuesta(
                                    id=o.id,
                                    orden=o.orden,
                                    texto=o.texto,
                                    es_correcta=o.es_correcta,
                                    justificacion=o.justificacion,
                                    valoraciones={v.criterio_id: v.puntaje for v in o.valoraciones},
                                )
                                for o in p.opciones
                            ],
                        )
                        for p in e.preguntas
                    ],
                )
                for e in m.escenarios
            ],
        )

    # --- mapeo dominio -> ORM -------------------------------------------------

    def _mapear(self, version: VersionCaso) -> CasoModel:
        caso = CasoModel(id=version.caso_id, docente_creador_id=version.docente_creador_id)
        caso.versiones.append(
            VersionCasoModel(
                id=version.id,
                numero=version.numero,
                nombre=version.nombre,
                desarrollo_situacional=version.desarrollo_situacional,
                contexto_historia=version.contexto_historia,
                tiempo_estimado_min=version.tiempo_estimado_min,
                estado=version.estado,
                escenarios=[self._mapear_escenario(e) for e in version.escenarios],
                rubrica=self._mapear_rubrica(version.rubrica) if version.rubrica else None,
            )
        )
        return caso

    def _mapear_escenario(self, escenario: Escenario) -> EscenarioModel:
        return EscenarioModel(
            id=escenario.id,
            orden=escenario.orden,
            contexto_situacional=escenario.contexto_situacional,
            preguntas=[self._mapear_pregunta(p) for p in escenario.preguntas],
        )

    def _mapear_pregunta(self, pregunta: Pregunta) -> PreguntaModel:
        return PreguntaModel(
            id=pregunta.id,
            orden=pregunta.orden,
            enunciado=pregunta.enunciado,
            opciones=[self._mapear_opcion(o) for o in pregunta.opciones],
        )

    def _mapear_opcion(self, opcion: OpcionRespuesta) -> OpcionRespuestaModel:
        return OpcionRespuestaModel(
            id=opcion.id,
            orden=opcion.orden,
            texto=opcion.texto,
            es_correcta=opcion.es_correcta,
            justificacion=opcion.justificacion,
            valoraciones=[
                ValoracionOpcionModel(criterio_id=criterio_id, puntaje=puntaje)
                for criterio_id, puntaje in opcion.valoraciones.items()
            ],
        )

    def _mapear_rubrica(self, rubrica: Rubrica) -> RubricaModel:
        return RubricaModel(
            id=rubrica.id,
            nombre=rubrica.nombre,
            version_regla=rubrica.version_regla,
            criterios=[
                CriterioRubricaModel(
                    id=c.id,
                    nombre=c.nombre,
                    peso=c.peso,
                    niveles=[
                        NivelRubricaModel(
                            id=n.id, nombre=n.nombre, puntaje=n.puntaje, descriptor=n.descriptor
                        )
                        for n in c.niveles
                    ],
                )
                for c in rubrica.criterios
            ],
        )
