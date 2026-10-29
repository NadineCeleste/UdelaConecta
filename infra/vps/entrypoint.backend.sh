#!/bin/sh
# Arranque en producción: migra una sola vez y después levanta los workers
set -e

alembic upgrade head

if [ "${AUTO_SEED:-false}" = "true" ]; then
  python -m app.seeds.seed_demo
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 3000 \
  --workers "${WEB_CONCURRENCY:-4}" --proxy-headers --forwarded-allow-ips="*"
