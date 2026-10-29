#!/bin/sh
# Arranque del backend en desarrollo: migraciones, seed opcional y uvicorn con hot-reload
set -e

alembic upgrade head

if [ "${AUTO_SEED:-false}" = "true" ]; then
  python -m app.seeds.seed_demo
fi

exec uvicorn app.main:app --reload --host 0.0.0.0 --port 3000
