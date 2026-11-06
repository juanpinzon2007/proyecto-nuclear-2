"""Fuente EXCLUSIVA LAB, sin configuración ni adaptador productivo."""
from app.modules.identity.application.consent import DocumentoConsentimiento
from app.modules.identity.domain.errors import IntegracionPendiente


class FuenteConsentimientoLaboratorio:
    def __init__(self):
        self.definiciones={}
        self.publicar(DocumentoConsentimiento('sintetico','documento-LAB','1',
            'Texto sintético exclusivamente de laboratorio. NO aprobado.',True))

    def publicar(self, documento):
        anterior=self.definiciones.get(documento.referencia)
        if anterior is not None and anterior!=documento: raise IntegracionPendiente()
        self.definiciones[documento.referencia]=documento
        self.actual=documento

    def vigente(self, *, id_asignacion, ahora):
        return self.actual
