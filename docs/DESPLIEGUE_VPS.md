# Guía de Despliegue en VPS — SPS

Esta guía describe el despliegue en producción o staging de **SPS (Simulador de Psicología Social)** sobre un servidor VPS Linux (Ubuntu 22.04/24.04 o Debian 12+) usando Docker Compose v2, PostgreSQL 17, FastAPI, Worker asíncrono, Nginx y HTTPS automático.

## 1. Requisitos del servidor y preparación inicial (`bootstrap`)

- **Hardware mínimo recomendado:** 2 vCPU, 2–4 GB RAM (con **2 GB de Swap** si usas un plan de 1–2 GB como *InterServer KVM Slice*), 20 GB SSD.
- **Software en el VPS:** Ubuntu 22.04/24.04 o Debian 12+, Docker Engine y plugin `docker compose` v2, Git y `curl`.
- **DNS y HTTPS:**
  - **Con dominio propio:** Crea un registro `A` en tu proveedor DNS (o en *DNS Manager* de InterServer) apuntando tu subdominio (ejemplo: `sps.tudominio.edu.co`) a la IP pública del VPS (en tu panel actual: `163.245.218.74`).
  - **Sin dominio propio (IP directa con HTTPS automático):** Puedes usar `163-245-218-74.sslip.io` como `SPS_DOMAIN` y `SCHEDULING_MAIL_PUBLIC_URL=https://163-245-218-74.sslip.io`; es necesario usar `https://` cuando `SCHEDULING_MAIL_ENABLED=true`, ya que SPS exige HTTPS para cualquier URL pública distinta de `localhost`.
- **Firewall y preparación automática en VPS limpio (`root`):**

```bash
bash deploy/vps/bootstrap-vps.sh
```

Este script crea automáticamente `/swapfile` de **2 GB** (si la RAM es menor a 3,5 GB, evitando cierres por memoria al compilar Angular), instala Docker + Compose v2 y habilita `ufw` dejando abiertos únicamente los puertos `22` (SSH), `80/tcp`, `443/tcp` y `443/udp`.

No expongas el puerto `5432` ni el puerto `8000` al exterior; en la configuración por defecto, PostgreSQL vive solo en la red privada de Docker y `api` / `frontend` escuchan en `127.0.0.1`.

## 2. Preparar variables de entorno y secretos

Clona o actualiza el repositorio en el VPS (por ejemplo en `/opt/sps`) y crea `.env` desde la plantilla específica de VPS:

```bash
cp deploy/vps/env.vps.example .env
chmod 600 .env
```

Genera secretos aleatorios reales en el propio VPS (nunca los subas a Git):

```bash
# Contraseña de PostgreSQL
openssl rand -hex 24

# Clave JWT (mínimo 32 bytes)
openssl rand -hex 32

# Clave Fernet para cifrado durable de correos en espera
python3 - <<'PY'
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
PY
```

Completa en `.env`:

- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- `IDENTITY_JWT_SECRET` y `IDENTITY_INSTITUTIONAL_DOMAINS` (por ejemplo `["@unihumboldt.edu.co"]`)
- `PARTICIPATION_TIMESTAMP_ZONE=America/Bogota`
- `SPS_DOMAIN` (si usas Caddy automático) y `SCHEDULING_MAIL_PUBLIC_URL=https://<tu-dominio>`
- Configuración SMTP en `SCHEDULING_MAIL_*`

### Ámbito académico (`PRODUCCION` vs `LABORATORIO`)

- **Producción real (`ACADEMIC_RUNTIME_SCOPE=PRODUCCION`):** Deposita el manifiesto firmado de consentimiento y la política de inicio en [`deploy/vps/trust/`](../deploy/vps/trust/.gitkeep) (se monta en `/etc/sps/trust` en modo solo lectura dentro de `api` y `worker`) y configura sus rutas `/etc/sps/trust/...` y hashes SHA-256 en `.env`.
- **Demostración / Staging (`ACADEMIC_RUNTIME_SCOPE=LABORATORIO`):** Permite ejecutar el consentimiento sintético de laboratorio para pruebas funcionales sin atestación externa. No usar para operación clínica o institucional real sin aprobación formal.

## 3. Desplegar el proyecto

El repositorio incluye [docker-compose.yml](../docker-compose.yml) (base común), [docker-compose.vps.yml](../docker-compose.vps.yml) (overlay con migración previa automática, reinicio automático, healthchecks, rotación de logs, `--proxy-headers` y perfil HTTPS opcional con Caddy) y el script [deploy/vps/deploy.sh](../deploy/vps/deploy.sh).

### Opción A — HTTPS automático integrado con Caddy (recomendada en VPS nuevo)

1. Verifica que `SPS_DOMAIN` en `.env` apunta ya por DNS al VPS y los puertos `80`/`443` están libres.
2. Ejecuta:

```bash
bash deploy/vps/deploy.sh --tls
```

Si deseas poblar usuarios y un caso inicial de demostración en un entorno nuevo (`LABORATORIO`), añade `--seed-demo` solo la primera vez:

```bash
bash deploy/vps/deploy.sh --tls --seed-demo
```

### Opción B — Detrás de Nginx + Certbot ya instalado en el VPS

Si el host ya tiene Nginx sirviendo otros sitios en `80`/`443`:

1. Copia [deploy/vps/nginx-reverse-proxy.conf](../deploy/vps/nginx-reverse-proxy.conf) a `/etc/nginx/sites-available/sps.conf`, sustituye el dominio, enlázalo en `sites-enabled` y emite certificado con `sudo certbot --nginx -d <tu-dominio>`.
2. Ejecuta sin `--tls`:

```bash
bash deploy/vps/deploy.sh
```

Nginx del host reenviará el tráfico HTTPS hacia `127.0.0.1:4200`, y el contenedor `frontend` reenviará `/api/`, `/scheduling/`, `/health` y `/ready` al backend FastAPI en la red interna.

## 4. Verificación posterior al despliegue

```bash
docker compose -f docker-compose.yml -f docker-compose.vps.yml ps
curl -sS https://<tu-dominio>/health
curl -sS https://<tu-dominio>/ready
```

Para comprobar entrega SMTP del correo remitente configurado en `.env`:

```bash
docker compose -f docker-compose.yml -f docker-compose.vps.yml run --rm --no-deps \
  api python -m app.modules.scheduling.infrastructure.mail_delivery --test-to-sender
```

## 5. Actualizaciones, respaldos y logs

- **Actualizar versión:**
  ```bash
  git pull origin develop
  bash deploy/vps/deploy.sh --tls   # o sin --tls si usas Nginx en host
  ```
  El servicio `migrate` aplica automáticamente `alembic upgrade head` antes de reiniciar `api` y `worker`.

- **Respaldo diario de PostgreSQL (`cron` recomendado):**
  ```bash
  docker compose -f docker-compose.yml -f docker-compose.vps.yml exec -T db \
    pg_dump -U "$POSTGRES_USER" -Fc "$POSTGRES_DB" > "sps_$(date +%F_%H%M).dump"
  ```

- **Inspeccionar logs en vivo (rotación configurada a 5×10 MB por servicio):**
  ```bash
  docker compose -f docker-compose.yml -f docker-compose.vps.yml logs -f --tail=100 api worker
  ```
