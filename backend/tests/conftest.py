import os

import pytest
from cryptography.fernet import Fernet


# Material efímero para las convocatorias de laboratorio y sus subprocesos.
os.environ.setdefault("SCHEDULING_MAIL_ENCRYPTION_KEY", Fernet.generate_key().decode())


@pytest.fixture
def cola_convocatorias():
    from app.core.config import get_settings

    with pytest.MonkeyPatch.context() as entorno:
        configuracion = {
            "SCHEDULING_MAIL_ENABLED": "true",
            "SCHEDULING_MAIL_HOST": "127.0.0.1",
            "SCHEDULING_MAIL_PORT": "2525",
            "SCHEDULING_MAIL_TLS": "LAB_LOOPBACK",
            "SCHEDULING_MAIL_FROM": "nuclear@universidad.test",
            "SCHEDULING_MAIL_PUBLIC_URL": "http://127.0.0.1/simulador",
            "SCHEDULING_MAIL_USERNAME": "",
            "SCHEDULING_MAIL_PASSWORD": "",
        }
        for nombre, valor in configuracion.items():
            entorno.setenv(nombre, valor)
        get_settings.cache_clear()
        yield
    get_settings.cache_clear()
