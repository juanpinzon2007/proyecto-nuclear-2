"""Fuente SQL explícita y operaciones internas sin commit ni permisos implícitos.

Publicar aquí persiste evidencia recibida de un proceso autorizado, no verifica
la autoridad institucional ni crea un endpoint de aprobación. No se compone por
defecto. Seleccionar no escribe en asignacion_caso ni toca sus guards de Cases.
"""
from hashlib import sha256
from sqlalchemy import select, text
from app.modules.identity.application.consent import DocumentoConsentimiento
from app.modules.identity.domain.errors import IntegracionPendiente
from app.modules.identity.infrastructure.consent_document_models import DocumentoConsentimientoVersionORM as D, SeleccionConsentimientoORM as S
from app.modules.scheduling.domain.ingress_policy import fecha_utc
from app.modules.scheduling.infrastructure.assignment_models import AsignacionCasoModel as A


def _hash(valor):
    return sha256(valor.encode('utf-8') if isinstance(valor,str) else valor).hexdigest()


def bloquear_selector(db, id_asignacion, *, escritura=False):
    if type(id_asignacion) is not int or id_asignacion<=0 or db.get_bind().dialect.name!='postgresql':
        raise IntegracionPendiente()
    if not escritura and db.connection().get_isolation_level()!='READ COMMITTED':
        # Un advisory no renueva snapshots ya fijados. Coincide con la UoW de P.
        raise IntegracionPendiente()
    # La FK también necesitará KEY SHARE de A. Adquirirla ANTES del advisory;
    # evita A->advisory / advisory->A con la UoW de provisión existente.
    fila=db.get(A,id_asignacion,with_for_update={'read':True,'key_share':True},populate_existing=True)
    if fila is None:raise IntegracionPendiente()
    funcion='pg_advisory_xact_lock' if escritura else 'pg_advisory_xact_lock_shared'
    db.execute(text(f'SELECT {funcion}(782061,:id)'),{'id':id_asignacion})


class RepositorioDocumentosConsentimientoSQLAlchemy:
    def __init__(self, db):self.db=db

    def publicar(self, *, referencia, documento_id, version, original, tipo_media, texto,
                 autoridad_aprobadora, aprobado_en, evidencia_aprobacion, publicado_por,
                 publicado_en, vigente_desde):
        if (self.db.get_bind().dialect.name!='postgresql' or
            not all(type(v) is str and v.strip() for v in (referencia,documento_id,version,tipo_media,texto,autoridad_aprobadora))
            or len(referencia)>30 or type(original) is not bytes or not original
            or type(evidencia_aprobacion) is not bytes or not evidencia_aprobacion
            or type(publicado_por) is not int or publicado_por<=0):raise IntegracionPendiente()
        fechas=[fecha_utc(v) for v in (aprobado_en,publicado_en,vigente_desde)]
        if fechas[1]<fechas[0]:raise IntegracionPendiente()
        fila=D(referencia=referencia,documento_id=documento_id,version=version,original=original,
            tipo_media=tipo_media,texto=texto,sha256_original=_hash(original),sha256_texto=_hash(texto),
            autoridad_aprobadora=autoridad_aprobadora,aprobado_en=fechas[0],
            evidencia_aprobacion=evidencia_aprobacion,sha256_aprobacion=_hash(evidencia_aprobacion),
            publicado_por=publicado_por,publicado_en=fechas[1],vigente_desde=fechas[2])
        self.db.add(fila);self.db.flush()
        return fila.id_version_documento

    def seleccionar(self, *, id_asignacion, id_version_documento, seleccionado_por, ahora):
        bloquear_selector(self.db,id_asignacion,escritura=True)
        fecha=fecha_utc(ahora)
        d=self.db.get(D,id_version_documento,with_for_update={'read':True},populate_existing=True)
        if d is None or fecha<fecha_utc(d.vigente_desde) or fecha<fecha_utc(d.publicado_en):raise IntegracionPendiente()
        actual=self.db.get(S,id_asignacion,with_for_update=True,populate_existing=True)
        if actual is not None and actual.id_version_documento==id_version_documento:return
        if actual is None:
            self.db.add(S(id_asignacion=id_asignacion,id_version_documento=id_version_documento,
                seleccionado_por=seleccionado_por,seleccionado_en=fecha))
        else:
            actual.id_version_documento=id_version_documento
            actual.seleccionado_por=seleccionado_por;actual.seleccionado_en=fecha
        self.db.flush()

    def historico(self, referencia):
        with self.db.no_autoflush:
            d=self.db.scalar(select(D).where(D.referencia==referencia).execution_options(populate_existing=True))
            return self._documento(d,False)

    @staticmethod
    def _documento(d, vigente):
        if (d is None or _hash(d.original)!=d.sha256_original or _hash(d.texto)!=d.sha256_texto
                or _hash(d.evidencia_aprobacion)!=d.sha256_aprobacion):raise IntegracionPendiente()
        return DocumentoConsentimiento(d.referencia,d.documento_id,d.version,d.texto,vigente,d.id_version_documento,
            d.sha256_original,d.sha256_aprobacion,d.autoridad_aprobadora,
            fecha_utc(d.aprobado_en),fecha_utc(d.publicado_en),fecha_utc(d.vigente_desde))


class FuenteConsentimientoSQLAlchemy(RepositorioDocumentosConsentimientoSQLAlchemy):
    def __init__(self, db, *, politica_aprobacion=None):
        super().__init__(db)
        self.politica_aprobacion = politica_aprobacion

    def vigente(self, *, id_asignacion, ahora):
        with self.db.no_autoflush:
            bloquear_selector(self.db,id_asignacion)
            s=self.db.get(S,id_asignacion,populate_existing=True)
            d=self.db.get(D,s.id_version_documento,populate_existing=True) if s is not None else None
            fecha=fecha_utc(ahora)
            if (d is None or fecha<fecha_utc(s.seleccionado_en) or fecha<fecha_utc(d.vigente_desde)
                    or fecha<fecha_utc(d.publicado_en)):raise IntegracionPendiente()
            documento = self._documento(d,True)
            if self.politica_aprobacion is not None:
                if self.politica_aprobacion.autorizar(documento,
                        id_asignacion=id_asignacion, ahora=fecha) is not None:
                    raise IntegracionPendiente()
            return documento
