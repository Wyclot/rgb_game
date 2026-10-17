#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
if [ -n "${GODOT_BIN:-}" ]; then
  engine="$GODOT_BIN"
elif [ -x ./tools/godot/Godot.app/Contents/MacOS/Godot ]; then
  engine=./tools/godot/Godot.app/Contents/MacOS/Godot
elif command -v godot >/dev/null 2>&1; then
  engine=godot
elif command -v godot4 >/dev/null 2>&1; then
  engine=godot4
else
  echo 'Godot 4.4+ is required. Install Godot, then set GODOT_BIN=/path/to/godot.' >&2
  exit 1
fi
exec "$engine" --path game "$@"
