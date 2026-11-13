#!/usr/bin/env bash
# Genera infra/vps/.env.vps pidiendo el subdominio y token de DuckDNS
# y generando automáticamente contraseñas seguras para Postgres y JWT.
set -euo pipefail

RAIZ="$(cd "$(dirname "$0")/../.." && pwd)"
ENV_FILE="$RAIZ/infra/vps/.env.vps"

if [ -f "$ENV_FILE" ]; then
  read -r -p "Ya existe infra/vps/.env.vps. ¿Querés sobrescribirlo? [s/N]: " RESP
  if [[ ! "$RESP" =~ ^[sS]$ ]]; then
    echo "Cancelado. Se conserva el archivo actual."
    exit 0
  fi
fi

read -r -p "Subdominio de DuckDNS (ej. udelaconecta, sin .duckdns.org): " RAW_SUBDOMAIN
SUBDOMAIN="${RAW_SUBDOMAIN%.duckdns.org}"
if [ -z "$SUBDOMAIN" ]; then
  echo "Error: el subdominio no puede estar vacío." >&2
  exit 1
fi

printf "Token de DuckDNS (lo que escribas no se verá en pantalla): "
read -r -s DUCKDNS_TOKEN
echo ""
if [ -z "$DUCKDNS_TOKEN" ]; then
  echo "Error: el token de DuckDNS no puede estar vacío." >&2
  exit 1
fi

read -r -p "¿Cargar datos de prueba iniciales (AUTO_SEED)? [s/N]: " SEED_RESP
if [[ "$SEED_RESP" =~ ^[sS]$ ]]; then
  AUTO_SEED="true"
else
  AUTO_SEED="false"
fi

# n8n: por defecto el del compose (red interna). Con un n8n externo se piden sus URLs y su secreto
read -r -p "URL base de un n8n externo (ej. https://n8n.midominio.com; Enter = usar el n8n del compose): " N8N_EXTERNO
N8N_EXTERNO="${N8N_EXTERNO%/}"
N8N_SECRETO=""
if [ -n "$N8N_EXTERNO" ]; then
  printf "Secreto de la credencial Header Auth \"Udela-Secret\" de ese n8n (no se verá en pantalla): "
  read -r -s N8N_SECRETO
  echo ""
  if [ -z "$N8N_SECRETO" ]; then
    echo "Error: con un n8n externo hace falta el secreto." >&2
    exit 1
  fi
fi

# Si un Caddy del host ya ocupa 80/443, ese Caddy maneja el HTTPS
# y el Caddy de Udela queda en HTTP, publicado solo en 127.0.0.1
read -r -p "¿El servidor ya tiene un Caddy usando los puertos 80/443? [s/N]: " PROXY_RESP
if [[ "$PROXY_RESP" =~ ^[sS]$ ]]; then
  read -r -p "Puerto local para Udela Conecta [8081]: " LOCAL_PORT
  LOCAL_PORT="${LOCAL_PORT:-8081}"
  if [[ ! "$LOCAL_PORT" =~ ^[0-9]+$ ]] || [ "$LOCAL_PORT" -lt 1024 ] || [ "$LOCAL_PORT" -gt 65534 ]; then
    echo "Error: el puerto tiene que ser un número entre 1024 y 65534." >&2
    exit 1
  fi
  DOMAIN_VALUE=":80"
  PUERTOS="CADDY_HTTP_PORT=127.0.0.1:${LOCAL_PORT}
CADDY_HTTPS_PORT=127.0.0.1:$((LOCAL_PORT + 1))"
else
  LOCAL_PORT=""
  DOMAIN_VALUE="${SUBDOMAIN}.duckdns.org"
  PUERTOS="CADDY_HTTP_PORT=80
CADDY_HTTPS_PORT=443"
fi

# Generar secretos aleatorios seguros (sin caracteres especiales que rompan la URI de Postgres).
# "|| true": al cortar head, tr recibe SIGPIPE y con pipefail el script terminaría acá
aleatorio() { LC_ALL=C tr -dc "$1" </dev/urandom | head -c "$2" || true; }
DB_PASS="$(aleatorio 'A-Za-z0-9' 32)"
JWT_SECRET="$(aleatorio 'A-Za-z0-9_-' 64)"
N8N_CLAVE="$(aleatorio 'A-Za-z0-9' 40)"
if [ -z "$N8N_SECRETO" ]; then
  N8N_SECRETO="$(aleatorio 'A-Za-z0-9' 40)"
fi
if [ "${#DB_PASS}" -ne 32 ] || [ "${#JWT_SECRET}" -ne 64 ] || [ "${#N8N_CLAVE}" -ne 40 ]; then
  echo "Error: no se pudieron generar las claves aleatorias." >&2
  exit 1
fi

if [ -n "$N8N_EXTERNO" ]; then
  N8N_URLS="COMPOSE_PROFILES=
N8N_CHAT_WEBHOOK_URL=${N8N_EXTERNO}/webhook/udela-chat
N8N_ORIENTACION_WEBHOOK_URL=${N8N_EXTERNO}/webhook/udela-orientacion
CHAT_DATOS_URL=https://${SUBDOMAIN}.duckdns.org/api/chat/datos"
else
  N8N_URLS="COMPOSE_PROFILES=n8n
N8N_CHAT_WEBHOOK_URL=http://n8n:5678/webhook/udela-chat
N8N_ORIENTACION_WEBHOOK_URL=http://n8n:5678/webhook/udela-orientacion
CHAT_DATOS_URL=http://backend:3000/api/chat/datos"
fi

umask 077
cat > "$ENV_FILE" <<EOF
DUCKDNS_SUBDOMAIN=${SUBDOMAIN}
DUCKDNS_TOKEN=${DUCKDNS_TOKEN}
DOMAIN=${DOMAIN_VALUE}
${PUERTOS}
POSTGRES_USER=udela_prod
POSTGRES_PASSWORD=${DB_PASS}
POSTGRES_DB=udelaconecta_prod
DATABASE_URL=postgresql+asyncpg://udela_prod:${DB_PASS}@postgres:5432/udelaconecta_prod
JWT_SECRET_KEY=${JWT_SECRET}
STORAGE_DIR=/data/storage
PUBLIC_STORAGE_BASE_URL=/storage
CORS_ORIGINS=https://${SUBDOMAIN}.duckdns.org
WEB_CONCURRENCY=4
AUTO_SEED=${AUTO_SEED}
N8N_ENCRYPTION_KEY=${N8N_CLAVE}
N8N_CHAT_SECRET=${N8N_SECRETO}
N8N_AUTOMATION_SECRET=${N8N_SECRETO}
N8N_HOST_PORT=5678
${N8N_URLS}
N8N_CHAT_TIMEOUT_SEGUNDOS=60
N8N_ORIENTACION_TIMEOUT_SEGUNDOS=30
EOF

echo "Listo: se creó infra/vps/.env.vps para https://${SUBDOMAIN}.duckdns.org (permisos 600)."
if [ -n "$N8N_EXTERNO" ]; then
  cat <<EOF

n8n externo: importar infra/n8n/udela-*.json en ${N8N_EXTERNO}, asignar las credenciales y publicarlos.
En el digest, poner backend_url = https://${SUBDOMAIN}.duckdns.org en el nodo "Configuración"
(ver context_agent/n8n.md).
EOF
else
  cat <<EOF

n8n: después del deploy, importar los workflows y cargar las credenciales (ver context_agent/n8n.md):
  infra/vps/n8n-import.sh
El valor de la credencial "Udela-Secret" es N8N_AUTOMATION_SECRET de infra/vps/.env.vps
(leerlo con: grep ^N8N_AUTOMATION_SECRET= infra/vps/.env.vps).
EOF
fi

if [ -n "$LOCAL_PORT" ]; then
  cat <<EOF

Falta que el Caddy del servidor reenvíe el dominio a Udela Conecta (127.0.0.1:${LOCAL_PORT}).
Después de ./infra/vps/deploy.sh, agregar a /etc/caddy/Caddyfile:

${SUBDOMAIN}.duckdns.org {
	reverse_proxy 127.0.0.1:${LOCAL_PORT}
}

y recargar: sudo caddy validate --config /etc/caddy/Caddyfile && sudo systemctl reload caddy
EOF
fi
