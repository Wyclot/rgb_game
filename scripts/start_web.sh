#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
# Worktrees share the original persistent backend, chain and managed wallets.
common_dir="$(git rev-parse --path-format=absolute --git-common-dir)"
service_root="$(dirname "$common_dir")"
"$service_root/scripts/start.sh" --no-game
exec ./scripts/web.sh "$@"
