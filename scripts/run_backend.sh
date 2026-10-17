#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
mkdir -p .state
if [ ! -x .venv/bin/python ]; then python3 -m venv .venv; fi
.venv/bin/python -m alembic -c backend/alembic.ini upgrade head
exec .venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port "${PORT:-8787}"
