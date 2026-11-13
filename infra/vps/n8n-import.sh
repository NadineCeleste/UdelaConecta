#!/usr/bin/env bash
# Importa en el n8n de producción los workflows de infra/n8n/*.json (chatbot, orientación y digest).
# Saltea los que ya existen con el mismo nombre, así que se puede correr de nuevo sin duplicar.
# Uso: infra/vps/n8n-import.sh            (después de infra/vps/deploy.sh)
# Los workflows quedan inactivos: falta asignar las credenciales y activarlos desde el editor.
set -euo pipefail

RAIZ="$(cd "$(dirname "$0")/../.." && pwd)"
COMPOSE=(docker compose -f "$RAIZ/infra/vps/docker-compose.prod.yml" --env-file "$RAIZ/infra/vps/.env.vps")

EXISTENTES="$("${COMPOSE[@]}" exec -T n8n n8n list:workflow 2>/dev/null || true)"

for ARCHIVO in "$RAIZ"/infra/n8n/*.json; do
  BASE="$(basename "$ARCHIVO")"
  NOMBRE="$("${COMPOSE[@]}" exec -T n8n node -e "console.log(require('/workflows/$BASE').name)")"
  if printf '%s\n' "$EXISTENTES" | grep -qF "|$NOMBRE"; then
    echo "Ya existe: $NOMBRE (no se importa)"
    continue
  fi
  "${COMPOSE[@]}" exec -T n8n n8n import:workflow --input="/workflows/$BASE"
  echo "Importado: $NOMBRE"
done

cat <<'EOF'

Pasos que faltan en el editor de n8n (túnel: ssh -L 5678:127.0.0.1:5678 usuario@servidor,
después abrir http://localhost:5678):
  1. Crear la credencial Header Auth "Udela-Secret": Name = X-Udela-Secret,
     Value = N8N_AUTOMATION_SECRET de infra/vps/.env.vps.
  2. Crear la credencial "DeepSeek account" con la API key de DeepSeek.
  3. Asignarlas en los nodos que las piden y activar los tres workflows.
  4. Probar: el webhook sin header responde 403 y el chat del sitio contesta.
EOF
