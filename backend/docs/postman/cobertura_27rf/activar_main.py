"""Configuración efímera LAB del main real. No aprueba documentos institucionales."""
from app.core.config import get_settings
from app.modules.identity.infrastructure.consent_repository import FuenteConsentimientoSQLAlchemy


def activar(p, stack):
    """Reutiliza exclusivamente la BD nueva y el directorio privado del preparador."""
    from pytest import MonkeyPatch
    from tests.unit.identity.test_consent_approval_attestation import escribir_paquete
    from tests.unit.participation.test_start_policy_file import archivo_politica, decision_lab
    from app.main import app
    from app.modules.participation.api.dependencies import obtener_reloj_escenario
    from app.modules.scheduling.api.router import obtener_reloj_ingreso
    h = p.contexto
    with h.sesiones() as sesion:
        documento = FuenteConsentimientoSQLAlchemy(sesion).vigente(id_asignacion=h.aid, ahora=h.ahora)
    configuracion = escribir_paquete(p.carpeta, [documento], h.aid, h.ahora)
    politica, huella = archivo_politica(p.carpeta, decision_lab(documento.referencia))
    patch = MonkeyPatch()
    anteriores = dict(app.dependency_overrides)
    app.dependency_overrides.pop(obtener_reloj_escenario, None)
    app.dependency_overrides.pop(obtener_reloj_ingreso, None)
    assert app.dependency_overrides == {}

    def limpiar():
        patch.undo()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(anteriores)
        get_settings.cache_clear()
        for ruta in (configuracion.identity_consent_approval_manifest, politica):
            assert ruta.parent.resolve() == p.carpeta.resolve()
            ruta.unlink(missing_ok=True)
    stack.callback(limpiar)
    for nombre, valor in vars(configuracion).items():
        patch.setenv(nombre.upper(), str(valor))
    patch.setenv('PARTICIPATION_START_POLICY_FILE', str(politica))
    patch.setenv('PARTICIPATION_START_POLICY_SHA256', huella)
    get_settings.cache_clear()
    assert get_settings().academic_runtime_scope == 'LABORATORIO'
    # Consentimiento e inicio usan el mismo reloj real del servidor. La fixture
    # histórica usa un reloj fijo que precede a la aceptación HTTP del main.
    # No se sustituyen proveedores, JWT, autorizaciones ni políticas de main.
    return dict(ambito='LABORATORIO', superficie='app.main', consentimiento_institucional=False)
