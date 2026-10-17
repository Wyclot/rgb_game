"""Isolated-stack outage checks; always restart the service stopped by this test."""
import json,os,signal,subprocess,sys,time
from pathlib import Path
import httpx
ROOT=Path(__file__).resolve().parents[1];os.chdir(ROOT)
BASE='http://127.0.0.1:8787'
profiles=json.loads((ROOT/'.state/managed-e2e-crash-profiles.json').read_text())
b=httpx.Client(base_url=BASE,headers={'Authorization':'Bearer '+profiles[1]['token']},timeout=10)
evidence=json.loads((ROOT/'docs/evidence/managed-e2e.json').read_text());serial=evidence['serial']
checks=[]
def wait_status(available):
 for _ in range(240):
  d=b.get('/api/relics').json()
  if d['service']['available']==available:
   if not available or any(i['serial']==serial and i['can_equip'] for i in d['items']):return d
  time.sleep(.5)
 raise AssertionError('Service did not reach expected availability')
for service in ('electrs','proxy'):
 wait_status(True)
 assert b.post(f'/api/relics/{serial}/equip').status_code==200
 try:
  subprocess.run(['docker','compose','stop',service],check=True,capture_output=True)
  d=wait_status(False)
  assert d['equipment'] is None
  assert b.post(f'/api/relics/{serial}/equip').status_code==503
  assert b.post(f'/api/relics/{serial}/transfer',json={'recipient_id':profiles[0]['id'],'confirm':True,'idempotency_key':'outage-'+service}).status_code==503
  checks.append(service+'_offline_blocks_use_and_transfer')
 finally:subprocess.run(['docker','compose','start',service],check=True,capture_output=True)
 wait_status(True)
 assert b.post(f'/api/relics/{serial}/equip').status_code==200
 checks.append(service+'_restored_real_wallet_rechecked')
 print(service,'outage/recovery PASS',flush=True)
# Observe the actual Godot client before and after its API disappears.
env=dict(os.environ,RUNEFORGE_EVIDENCE_DIR=str(ROOT/'docs/evidence'))
game=subprocess.Popen([str(ROOT/'scripts/play.sh'),'--','--outage-game-check'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,env=env)
stopped=False
try:
 for line in game.stdout:
  print(line.strip(),flush=True)
  if 'OUTAGE_READY' in line:
   state=json.loads((ROOT/'.state/processes.json').read_text());pid=state['api']
   command=subprocess.check_output(['ps','-p',str(pid),'-o','command='],text=True)
   assert 'uvicorn backend.app.main:app' in command
   os.kill(pid,signal.SIGTERM);stopped=True
  if 'RUNEFORGE_BACKEND_OUTAGE PASS' in line:checks.append('godot_backend_offline_revokes_52_damage')
 assert game.wait(timeout=30)==0 and stopped
finally:
 if game.poll() is None:game.terminate();game.wait(timeout=10)
 if stopped:subprocess.run([str(ROOT/'scripts/start.sh'),'--no-game'],check=True)
assert len(checks)==5
(ROOT/'docs/evidence/outages.json').write_text(json.dumps({'mode':'real','network':'regtest','checks':checks},indent=2)+'\n')
print('OUTAGES_PASS',flush=True)
