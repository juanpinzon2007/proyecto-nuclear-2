"""Paquetes firmados exclusivamente LAB con clave privada efímera en memoria."""
import base64
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from types import SimpleNamespace

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import pytest

from app.modules.identity.application.consent import DocumentoConsentimiento
from app.modules.identity.domain.errors import IntegracionPendiente
from app.modules.identity.infrastructure.consent_approval import PoliticaConsentimientoAtestado, canonico


AHORA = datetime(2026, 11, 11, tzinfo=timezone.utc)


def documento_lab():
    return DocumentoConsentimiento('LAB-1', 'LAB', '1', 'Documento sintetico LAB', True, 1,
        'a'*64, 'b'*64, 'OPERADOR FICTICIO LAB', AHORA, AHORA, AHORA)


def escribir_paquete(tmp_path, documentos, asignacion=1, ahora=AHORA, scope='LABORATORIO'):
    clave = Ed25519PrivateKey.generate()
    docs = []
    for d in documentos:
        docs.append(dict(id_version_documento=d.id_version_documento, referencia=d.referencia,
            documento_id=d.documento_id, version=d.version, sha256_texto=d.huella,
            sha256_original=d.sha256_original, sha256_aprobacion=d.sha256_aprobacion,
            autoridad_aprobadora=d.autoridad_aprobadora, aprobado_en=d.aprobado_en.isoformat(),
            publicado_en=d.publicado_en.isoformat(), vigente_desde=d.vigente_desde.isoformat(),
            asignaciones=[asignacion]))
    payload=dict(schema_version=1,scope=scope,valid_from=(ahora-timedelta(hours=1)).isoformat(),
        expires_at=(ahora+timedelta(hours=1)).isoformat(),documentos=docs)
    firma=clave.sign(canonico(payload))
    contenido=canonico(dict(payload=payload,signature=base64.b64encode(firma).decode()))
    ruta=tmp_path/'atestacion-lab.json';ruta.write_bytes(contenido)
    return SimpleNamespace(academic_runtime_scope=scope, identity_consent_approval_manifest=ruta,
        identity_consent_approval_sha256=sha256(contenido).hexdigest(),
        identity_consent_approval_public_key=base64.b64encode(clave.public_key().public_bytes_raw()).decode())


def test_firma_configurada_coteja_documento_y_ventana(tmp_path):
    d=documento_lab();s=escribir_paquete(tmp_path,[d]);p=PoliticaConsentimientoAtestado.desde_settings(s)
    assert p.autorizar(d,id_asignacion=1,ahora=AHORA) is None
    for cambio in ({'id_version_documento':2},{'referencia':'otra'},{'documento_id':'otro'},
                   {'version':'2'},{'texto':'otro'},{'sha256_original':'c'*64},
                   {'sha256_aprobacion':'c'*64},{'autoridad_aprobadora':'otra'},
                   {'aprobado_en':AHORA-timedelta(days=1)},
                   {'publicado_en':AHORA-timedelta(days=1)},
                   {'vigente_desde':AHORA-timedelta(days=1)},{'vigente':False}):
        with pytest.raises(IntegracionPendiente):p.autorizar(replace(d,**cambio),id_asignacion=1,ahora=AHORA)
    for asignacion, ahora in [(2,AHORA),(True,AHORA),(1,AHORA-timedelta(hours=2)),(1,AHORA+timedelta(hours=1))]:
        with pytest.raises(IntegracionPendiente):p.autorizar(d,id_asignacion=asignacion,ahora=ahora)


@pytest.mark.parametrize('problema',['scope','sin_scope','sin_archivo','pin','clave','firma','canonico','duplicado'])
def test_paquete_invalido_falla_cerrado(tmp_path,problema):
    d=documento_lab();s=escribir_paquete(tmp_path,[d,d] if problema=='duplicado' else [d])
    if problema=='scope':s.academic_runtime_scope='PRODUCCION'
    elif problema=='sin_scope':s.academic_runtime_scope=None
    elif problema=='sin_archivo':s.identity_consent_approval_manifest=tmp_path/'ausente'
    elif problema=='pin':s.identity_consent_approval_sha256='0'*64
    elif problema=='clave':s.identity_consent_approval_public_key=base64.b64encode(bytes(32)).decode()
    elif problema in ('firma','canonico'):
        contenido=s.identity_consent_approval_manifest.read_bytes()
        contenido=contenido.replace(b'Documento sintetico',b'alterado') if problema=='firma' else contenido+b'\n'
        # Cambiar el payload sin una firma nueva, incluso recalculando el pin.
        if problema=='firma':contenido=contenido.replace(b'"version":"1"',b'"version":"2"')
        s.identity_consent_approval_manifest.write_bytes(contenido)
        s.identity_consent_approval_sha256=sha256(contenido).hexdigest()
    with pytest.raises(IntegracionPendiente):PoliticaConsentimientoAtestado.desde_settings(s)


def test_sqlite_aislado_no_suplanta_selector_postgresql(tmp_path):
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import Session
    from app.modules.identity.infrastructure.consent_repository import FuenteConsentimientoSQLAlchemy
    p=PoliticaConsentimientoAtestado.desde_settings(escribir_paquete(tmp_path,[documento_lab()]))
    engine=create_engine('sqlite:///:memory:')
    sentencias=[]
    event.listen(engine,'before_cursor_execute',lambda conn,cursor,statement,*args:sentencias.append(statement))
    try:
        with Session(engine) as db, pytest.raises(IntegracionPendiente):
            FuenteConsentimientoSQLAlchemy(db,politica_aprobacion=p).vigente(id_asignacion=1,ahora=AHORA)
        assert sentencias==[]
    finally:
        engine.dispose()
