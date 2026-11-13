#!/usr/bin/env bash
# Actualiza el código y reconstruye los contenedores de producción
set -euo pipefail

RAIZ="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$RAIZ"
ENV_FILE=infra/vps/.env.vps

if [ ! -f "$ENV_FILE" ]; then
  echo "Falta $ENV_FILE (copiar desde .env.vps.example y completar)" >&2
  exit 1
fi

# Un .env.vps anterior a la orientación y el digest no tiene sus variables. Se completan sin tocar
# las que ya tienen valor y sin mostrar secretos:
#   - con un n8n externo (N8N_CHAT_WEBHOOK_URL con otra URL), se sigue usando ese n8n;
#   - sin n8n configurado, se activa el n8n del compose (perfil "n8n") por la red interna.
valor() { grep -E "^$1=" "$ENV_FILE" | tail -n 1 | cut -d= -f2- || true; }
aleatorio() { LC_ALL=C tr -dc 'A-Za-z0-9' </dev/urandom | head -c 40 || true; }
fijar() {
  if grep -qE "^$1=" "$ENV_FILE"; then
    sed -i "s|^$1=.*|$1=$2|" "$ENV_FILE"
  else
    printf '%s=%s\n' "$1" "$2" >> "$ENV_FILE"
  fi
  echo "Se completó $1 en $ENV_FILE"
}

CHAT_URL="$(valor N8N_CHAT_WEBHOOK_URL)"
if [ -z "$CHAT_URL" ] && [ -z "$(valor COMPOSE_PROFILES)" ]; then
  fijar COMPOSE_PROFILES n8n
  fijar N8N_CHAT_WEBHOOK_URL "http://n8n:5678/webhook/udela-chat"
  fijar CHAT_DATOS_URL "http://backend:3000/api/chat/datos"
  CHAT_URL="http://n8n:5678/webhook/udela-chat"
fi
if [ -z "$(valor N8N_ORIENTACION_WEBHOOK_URL)" ] && [ -n "$CHAT_URL" ]; then
  # Mismo n8n que el chat: solo cambia la ruta del webhook
  fijar N8N_ORIENTACION_WEBHOOK_URL "${CHAT_URL%/udela-chat}/udela-orientacion"
fi
if [[ ",$(valor COMPOSE_PROFILES)," == *",n8n,"* ]] && [ -z "$(valor N8N_ENCRYPTION_KEY)" ]; then
  fijar N8N_ENCRYPTION_KEY "$(aleatorio)"
fi
SECRETO="$(valor N8N_AUTOMATION_SECRET)"
if [ -z "$SECRETO" ]; then
  # Los tres workflows usan la misma credencial Header Auth: se reutiliza el secreto del chat si había
  SECRETO="$(valor N8N_CHAT_SECRET)"
  [ -n "$SECRETO" ] || SECRETO="$(aleatorio)"
  fijar N8N_AUTOMATION_SECRET "$SECRETO"
fi
if [ -z "$(valor N8N_CHAT_SECRET)" ]; then
  fijar N8N_CHAT_SECRET "$SECRETO"
fi

git pull --ff-only
docker compose -f infra/vps/docker-compose.prod.yml --env-file "$ENV_FILE" up -d --build
docker image prune -f
docker compose -f infra/vps/docker-compose.prod.yml --env-file "$ENV_FILE" ps
