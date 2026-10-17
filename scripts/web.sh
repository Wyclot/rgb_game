#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
exec python3 scripts/web_server.py --port 8082 "$@"
