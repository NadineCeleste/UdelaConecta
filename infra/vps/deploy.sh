#!/usr/bin/env bash
# Actualiza el código y reconstruye los contenedores de producción
set -euo pipefail

RAIZ="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$RAIZ"

if [ ! -f infra/vps/.env.vps ]; then
  echo "Falta infra/vps/.env.vps (copiar desde .env.vps.example y completar)" >&2
  exit 1
fi

git pull --ff-only
docker compose -f infra/vps/docker-compose.prod.yml --env-file infra/vps/.env.vps up -d --build
docker image prune -f
docker compose -f infra/vps/docker-compose.prod.yml --env-file infra/vps/.env.vps ps
