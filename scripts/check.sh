#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
.venv/bin/python -m pytest backend/tests ml -q
.venv/bin/python scripts/verify_rgb_api.py
scripts/play.sh --headless --editor --import --quit
scripts/play.sh --headless -- --smoke
