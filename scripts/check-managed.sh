#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
export DATABASE_URL='postgresql+psycopg://runeforge:runeforge_local_only@127.0.0.1:55432/runeforge'
export RUNEFORGE_E2E_PROFILES=.state/managed-e2e-crash-profiles.json
export RUNEFORGE_EVIDENCE_DIR="$PWD/docs/evidence"
./scripts/start.sh --no-game
# Only the launcher-owned worker is stopped. The test needs exclusive native wallets.
.venv/bin/python - <<'PY'
import json,os,signal,subprocess,time
from pathlib import Path
p=Path('.state/processes.json');state=json.loads(p.read_text());pid=state['worker']
r=subprocess.run(['ps','-p',str(pid),'-o','command='],capture_output=True,text=True)
if 'backend.app.services.worker' not in r.stdout:raise SystemExit('Worker PID no longer belongs to RuneForge')
os.kill(pid,signal.SIGTERM)
for _ in range(120):
 r=subprocess.run(['ps','-p',str(pid),'-o','command='],capture_output=True,text=True)
 if 'backend.app.services.worker' not in r.stdout:break
 time.sleep(.5)
else:raise SystemExit('Worker did not stop; test will not open its wallets')
PY
trap './scripts/start.sh --no-game' EXIT
.venv/bin/python scripts/managed_e2e.py
./scripts/start.sh --no-game
./scripts/play.sh -- --managed-game-check
.venv/bin/python scripts/check_outages.py
