#!/usr/bin/env bash
set -euo pipefail

# Preparación inicial de un VPS Ubuntu/Debian limpio (ej. InterServer KVM Slice)
# para ejecutar SPS con Docker Compose v2.
# Uso en el VPS como root:
#   bash deploy/vps/bootstrap-vps.sh

if [[ "$(id -u)" -ne 0 ]]; then
  echo "ERROR: Ejecuta este script como root (sudo bash deploy/vps/bootstrap-vps.sh)." >&2
  exit 1
fi

echo "==> 1. Verificando memoria Swap para compilación Docker (Angular/Node)..."
TOTAL_RAM_MB="$(awk '/MemTotal/ {print int($2/1024)}' /proc/meminfo)"
CURRENT_SWAP_MB="$(awk '/SwapTotal/ {print int($2/1024)}' /proc/meminfo)"

if [[ "$TOTAL_RAM_MB" -lt 3500 && "$CURRENT_SWAP_MB" -lt 1024 ]]; then
  if [[ ! -f /swapfile ]]; then
    echo "    RAM detectada: ${TOTAL_RAM_MB} MB. Creando /swapfile de 2 GB..."
    fallocate -l 2G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=2048
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    if ! grep -q '^/swapfile ' /etc/fstab; then
      echo '/swapfile none swap sw 0 0' >> /etc/fstab
    fi
  else
    swapon /swapfile || true
  fi
else
  echo "    RAM (${TOTAL_RAM_MB} MB) y Swap (${CURRENT_SWAP_MB} MB) suficientes."
fi

echo "==> 2. Instalando paquetes base (git, curl, ufw)..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq ca-certificates curl git ufw

echo "==> 3. Verificando Docker Engine y Docker Compose v2..."
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
  systemctl enable --now docker
fi

if ! docker compose version >/dev/null 2>&1; then
  apt-get install -y -qq docker-compose-plugin
fi

echo "==> 4. Configurando firewall UFW (SSH 22, HTTP 80, HTTPS 443)..."
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 443/udp
ufw --force enable

echo "==> Bootstrap del VPS completado."
docker --version
docker compose version
free -h
