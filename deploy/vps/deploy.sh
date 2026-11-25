#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

USE_TLS=0
SKIP_BUILD=0
SEED_DEMO=0

for arg in "$@"; do
  case "$arg" in
    --tls) USE_TLS=1 ;;
    --no-build) SKIP_BUILD=1 ;;
    --seed-demo) SEED_DEMO=1 ;;
    -h|--help)
      cat <<'EOF'
Uso: bash deploy/vps/deploy.sh [--tls] [--no-build] [--seed-demo]

Opciones:
  --tls         Activa Caddy HTTPS automático (--profile tls) usando SPS_DOMAIN de .env
  --no-build    Omite la reconstrucción de imágenes Docker
  --seed-demo   Ejecuta scripts/seed_demo_data.py tras migrar la base de datos
EOF
      exit 0
      ;;
    *)
      echo "Opción no reconocida: $arg" >&2
      exit 1
      ;;
  esac
done

if [[ ! -f .env ]]; then
  echo "ERROR: Falta el archivo .env en la raíz ($ROOT_DIR)." >&2
  echo "Copia deploy/vps/env.vps.example a .env y completa las variables antes de desplegar." >&2
  exit 1
fi

read_env() {
  local key="$1"
  local line
  line="$(grep -E "^${key}=" .env | tail -n 1 || true)"
  line="${line#*=}"
  line="${line%\"}"
  line="${line#\"}"
  printf '%s' "${line%$'\r'}"
}

require_nonempty() {
  local key="$1"
  local val
  val="$(read_env "$key")"
  if [[ -z "$val" ]]; then
    echo "ERROR: La variable obligatoria $key está vacía en .env." >&2
    exit 1
  fi
}

require_nonempty POSTGRES_DB
require_nonempty POSTGRES_USER
require_nonempty POSTGRES_PASSWORD
require_nonempty IDENTITY_JWT_SECRET
require_nonempty PARTICIPATION_TIMESTAMP_ZONE

JWT_SECRET="$(read_env IDENTITY_JWT_SECRET)"
if [[ ${#JWT_SECRET} -lt 32 ]]; then
  echo "ERROR: IDENTITY_JWT_SECRET debe tener al menos 32 caracteres." >&2
  exit 1
fi

MAIL_ENABLED="$(read_env SCHEDULING_MAIL_ENABLED)"
if [[ "$MAIL_ENABLED" == "true" ]]; then
  require_nonempty SCHEDULING_MAIL_HOST
  require_nonempty SCHEDULING_MAIL_PORT
  require_nonempty SCHEDULING_MAIL_FROM
  require_nonempty SCHEDULING_MAIL_ENCRYPTION_KEY
  require_nonempty SCHEDULING_MAIL_PUBLIC_URL
fi

COMPOSE_ARGS=(-f docker-compose.yml -f docker-compose.vps.yml)
if [[ "$USE_TLS" -eq 1 ]]; then
  require_nonempty SPS_DOMAIN
  SPS_DOMAIN_VAL="$(read_env SPS_DOMAIN)"
  if [[ "$SPS_DOMAIN_VAL" == "sps.tudominio.edu.co" || "$SPS_DOMAIN_VAL" == "localhost" ]]; then
    echo "ERROR: Configura un dominio público real en SPS_DOMAIN para usar --tls." >&2
    exit 1
  fi
  COMPOSE_ARGS+=(--profile tls)
fi

echo "==> Validando configuración de Docker Compose..."
docker compose "${COMPOSE_ARGS[@]}" config --quiet

if [[ "$SKIP_BUILD" -eq 0 ]]; then
  echo "==> Construyendo imágenes (api, frontend, worker, migrate)..."
  docker compose "${COMPOSE_ARGS[@]}" build --pull api frontend worker
fi

echo "==> Levantando PostgreSQL y ejecutando migraciones Alembic..."
docker compose "${COMPOSE_ARGS[@]}" up -d --wait db
docker compose "${COMPOSE_ARGS[@]}" run --rm --no-deps migrate

if [[ "$SEED_DEMO" -eq 1 ]]; then
  echo "==> Cargando datos iniciales de demostración..."
  docker compose "${COMPOSE_ARGS[@]}" run --rm --no-deps \
    -v "$ROOT_DIR/scripts:/srv/scripts:ro" \
    api python /srv/scripts/seed_demo_data.py
fi

echo "==> Iniciando servicios SPS..."
docker compose "${COMPOSE_ARGS[@]}" up -d --wait --remove-orphans

echo "==> Verificando salud de la plataforma..."
API_PORT_VAL="$(read_env API_PORT)"
API_PORT_VAL="${API_PORT_VAL:-8000}"
API_BIND_VAL="$(read_env API_BIND_HOST)"
API_BIND_VAL="${API_BIND_VAL:-127.0.0.1}"

if command -v curl >/dev/null 2>&1; then
  curl -fsS "http://${API_BIND_VAL}:${API_PORT_VAL}/ready" >/dev/null
fi

docker compose "${COMPOSE_ARGS[@]}" ps
echo "Despliegue de SPS completado correctamente."
