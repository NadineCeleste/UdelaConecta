#!/usr/bin/env bash
# Backup comprimido de PostgreSQL y de las imágenes subidas (volumen storage). Uso: infra/vps/backup-db.sh [dias_a_conservar]
# Sugerido en cron: 0 3 * * * /ruta/al/repo/infra/vps/backup-db.sh 14
set -euo pipefail

RAIZ="$(cd "$(dirname "$0")/../.." && pwd)"
ENV_FILE="$RAIZ/infra/vps/.env.vps"
DESTINO="$RAIZ/infra/vps/backups"
DIAS="${1:-14}"

set -a
# shellcheck source=/dev/null
. "$ENV_FILE"
set +a

mkdir -p "$DESTINO"
FECHA="$(date +%Y-%m-%d_%H%M)"
ARCHIVO="$DESTINO/${POSTGRES_DB}_${FECHA}.sql.gz"
ARCHIVO_STORAGE="$DESTINO/storage_${FECHA}.tar.gz"
COMPOSE=(docker compose -f "$RAIZ/infra/vps/docker-compose.prod.yml" --env-file "$ENV_FILE")

"${COMPOSE[@]}" exec -T postgres pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner | gzip > "$ARCHIVO"
"${COMPOSE[@]}" exec -T backend tar -czf - -C /data storage > "$ARCHIVO_STORAGE"

find "$DESTINO" \( -name '*.sql.gz' -o -name 'storage_*.tar.gz' \) -mtime +"$DIAS" -delete
echo "Backup generado: $ARCHIVO y $ARCHIVO_STORAGE"
