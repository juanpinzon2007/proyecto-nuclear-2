"""Configuración temporal de la imagen real y HTTP main, con datos solo LAB."""
from contextlib import contextmanager
import csv
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import tempfile
import time
from uuid import uuid4

import httpx
import pytest

from tests.integration.test_main_current_scenario import (
    principal, integracion, autor, pg_autoria, payload_valido,
)  # noqa: F401 - fixtures PostgreSQL reales existentes
from tests.integration.test_current_scenario_http import snapshot


ROOT = Path(__file__).resolve().parents[3]


def docker(*args, timeout=30, env=None):
    completed = subprocess.run(
        ['docker', *args], cwd=ROOT, env=env, capture_output=True,
        text=True, encoding='utf-8', errors='replace', timeout=timeout,
    )
    if completed.returncode:
        # Las credenciales de laboratorio quedan fuera de diagnósticos y JUnit.
        raise AssertionError(f'Falló Docker {args[0]} (código {completed.returncode}).')
    return completed.stdout.strip()


@contextmanager
def environment_privado(values):
    with tempfile.TemporaryDirectory(prefix='nuclear-docker-zone-') as directory:
        path = Path(directory)
        if os.name == 'nt':
            output = subprocess.check_output(['whoami', '/user', '/fo', 'csv', '/nh'], text=True)
            sid = next(value for row in csv.reader(output.splitlines()) for value in row
                       if re.fullmatch(r'S-1-[0-9-]+', value))
            subprocess.run(
                ['icacls', str(path), '/inheritance:r', '/grant:r', f'*{sid}:(OI)(CI)F'],
                check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
        else:
            path.chmod(0o700)
        environment = path / 'container.env'
        environment.write_text(''.join(f'{key}={value}\n' for key, value in values.items()), encoding='utf-8')
        yield environment


def compose_config(zone):
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith(('POSTGRES_', 'PARTICIPATION_', 'IDENTITY_'))}
    environment.update(POSTGRES_DB='compose_zone_test', POSTGRES_USER='compose_zone_test',
                       POSTGRES_PASSWORD=secrets.token_urlsafe(32))
    if zone is not None:
        environment['PARTICIPATION_TIMESTAMP_ZONE'] = zone
    with environment_privado({}) as empty_environment:
        return subprocess.run(
            ['docker', 'compose', '--env-file', str(empty_environment), '-f',
             str(ROOT / 'docker-compose.yml'), 'config', '--format', 'json'],
            cwd=ROOT, env=environment, capture_output=True, text=True, timeout=30,
        )


@pytest.mark.parametrize('zone', [None, ''])
def test_compose_exige_zona_explicita_antes_de_crear_recursos(zone):
    completed = compose_config(zone)
    assert completed.returncode != 0
    assert 'PARTICIPATION_TIMESTAMP_ZONE' in completed.stderr


def test_compose_pasa_zona_configurada_sin_predeterminarla():
    completed = compose_config('America/Bogota')
    assert completed.returncode == 0
    config = json.loads(completed.stdout)
    assert config['services']['api']['environment']['PARTICIPATION_TIMESTAMP_ZONE'] == 'America/Bogota'
    example = (ROOT / '.env.example').read_text(encoding='utf-8')
    assert re.search(r'^PARTICIPATION_TIMESTAMP_ZONE=$', example, re.MULTILINE)
    env = config['services']['api']['environment']
    for name in ('ACADEMIC_RUNTIME_SCOPE', 'IDENTITY_CONSENT_APPROVAL_MANIFEST',
                 'IDENTITY_CONSENT_APPROVAL_SHA256', 'IDENTITY_CONSENT_APPROVAL_PUBLIC_KEY',
                 'PARTICIPATION_START_POLICY_FILE', 'PARTICIPATION_START_POLICY_SHA256'):
        assert name in env


@pytest.fixture(scope='module')
def imagen_api():
    image = 'nuclear-qa-timestamp:' + uuid4().hex
    docker('build', '--tag', image, str(ROOT / 'backend'), timeout=360)
    try:
        yield image
    finally:
        docker('image', 'rm', image, timeout=30)


def test_imagen_reconstruye_timestamp_con_zona_iana_explicita(imagen_api):
    script = (
        'from datetime import datetime;'
        'from app.modules.participation.api.dependencies import obtener_fechas_escenario;'
        'f=obtener_fechas_escenario();'
        'print(f.desde_db(datetime(2026,11,2,7,0)).isoformat())'
    )
    result = docker('run', '--rm', '--env', 'PARTICIPATION_TIMESTAMP_ZONE=America/Bogota',
                    imagen_api, 'python', '-c', script)
    assert result == '2026-11-02T12:00:00+00:00'


def direccion_postgresql_propio(engine):
    candidates = docker('ps', '--filter', 'label=sps.identity.mapping.lab=true', '--format', '{{.ID}}')
    for container in candidates.splitlines():
        data = json.loads(docker('inspect', '--format', '{{json .NetworkSettings}}', container))
        bindings = data['Ports'].get('5432/tcp') or []
        if any(int(port['HostPort']) == engine.url.port for port in bindings):
            return data['Networks']['bridge']['IPAddress']
    raise AssertionError('No se encontró el PostgreSQL desechable propio de esta fixture.')


@contextmanager
def servidor_api(image, values):
    container = 'nuclear-api-zone-' + uuid4().hex[:12]
    created = None
    try:
        with environment_privado(values) as envfile:
            created = docker('create', '--name', container, '--label', 'sps.docker.timestamp.lab=true',
                             '--env-file', str(envfile), '--publish', '127.0.0.1::8000', image)
        assert re.fullmatch(r'[0-9a-f]{64}', created)
        docker('start', created)
        settings = json.loads(docker('inspect', '--format', '{{json .NetworkSettings}}', created))
        binding = settings['Ports']['8000/tcp'][0]
        assert binding['HostIp'] == '127.0.0.1'
        with httpx.Client(base_url='http://127.0.0.1:' + binding['HostPort'], timeout=5) as client:
            deadline = time.monotonic() + 30
            while True:
                try:
                    if client.get('/health').status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                if time.monotonic() >= deadline:
                    raise AssertionError('La imagen de API no alcanzó su healthcheck.')
                time.sleep(0.1)
            yield client
    finally:
        if created:
            docker('rm', '--force', created)


def test_http_imagen_main_zona_ausente_invalida_y_valida(imagen_api, principal, record_property):
    h = principal
    engine = h.sesiones.kw['bind']
    values = dict(
        POSTGRES_HOST=direccion_postgresql_propio(engine), POSTGRES_PORT='5432',
        POSTGRES_DB=engine.url.database, POSTGRES_USER=engine.url.username,
        POSTGRES_PASSWORD=engine.url.password,
        IDENTITY_JWT_SECRET=os.environ['IDENTITY_JWT_SECRET'],
        IDENTITY_JWT_ISSUER=os.environ['IDENTITY_JWT_ISSUER'],
        IDENTITY_JWT_AUDIENCE=os.environ['IDENTITY_JWT_AUDIENCE'],
        IDENTITY_INSTITUTIONAL_DOMAINS='["universidad.test"]',
    )
    before = snapshot(h, h.ik)
    observed = []
    for zone, status in [(None, 503), ('Zona/NoExiste', 503), ('UTC', 200)]:
        environment = dict(values)
        if zone is not None:
            environment['PARTICIPATION_TIMESTAMP_ZONE'] = zone
        with servidor_api(imagen_api, environment) as client:
            login = client.post('/api/v1/identity/auth/estudiantes', json={
                'correo': f'autor{h.estudiante}@universidad.test', 'codigo_convocatoria': h.codigo})
            assert login.status_code == 200
            auth = {'Authorization': 'Bearer ' + login.json()['access_token']}
            path = f'/api/v1/attempts/{h.ik}/progress'
            result = client.get(path, headers=auth)
            assert result.status_code == status
            observed.append(dict(zona=zone, login=200, progreso=status))
            if status == 200:
                assert result.json()['intento']['id_intento'] == h.ik
                assert result.json()['intento']['estado'] == 'VENCIDO'
                assert result.json()['intento']['fin'] == result.json()['intento']['vence_en']
                assert client.get(path).status_code == 401
                assert client.get(path, headers={'Authorization': 'Bearer token-invalido-LAB'}).status_code == 401
            assert result.headers['cache-control'] == 'no-store'
        assert snapshot(h, h.ik) == before
    record_property('imagen_main_configuracion_temporal', json.dumps(observed))
