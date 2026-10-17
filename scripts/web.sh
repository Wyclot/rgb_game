#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
python3 scripts/build_web.py
exec python3 scripts/web_server.py --port 8081 "$@"
