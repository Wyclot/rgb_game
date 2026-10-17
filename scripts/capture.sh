#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
GODOT_BIN=${GODOT_BIN:-./tools/godot/Godot.app/Contents/MacOS/Godot}
RUNEFORGE_CAPTURE="$PWD/docs/evidence/${1:-hub}.png" "$GODOT_BIN" --path game -- --capture --capture-exit "--view=${1:-hub}"
