"""Authorized one-item repair: existing sword #4, test A -> ordinary player A.
Uses profile bearer credentials locally; never issues assets or changes DB ownership.
"""
import json,time
from pathlib import Path
import httpx
ROOT=Path(__file__).resolve().parents[1]
USERDATA=Path.home()/'Library/Application Support/Godot/app_userdata/RuneForge — Ashes of the Covenant'
EXPECTED_ASSET='rgb:HMuDmE2i-aknsETo-4mmIZrS-hrK12HK-Qn_Yi1F-kY5jYa8'
SOURCE='fbb6f7f7-31dc-4275-ba03-856ea737add6'
DESTINATION='e2bc20f0-4fc2-49f4-8363-799560e64378'

def main():
 src=json.loads((USERDATA/'managed_test_profiles.json').read_text())['profiles']['A']
 dst=json.loads((USERDATA/'managed_profiles.json').read_text())['profiles']['A']
 assert src['id']==SOURCE and dst['id']==DESTINATION
 clients=[httpx.Client(base_url='http://127.0.0.1:8787',headers={'Authorization':'Bearer '+p['token']},timeout=15) for p in (src,dst)]
 a,b=clients
 assert a.get('/api/profile').json()['id']==SOURCE
 assert b.get('/api/profile').json()['id']==DESTINATION
 item=next(i for i in a.get('/api/relics').json()['items'] if i['serial']==4)
 assert item['asset_id']==EXPECTED_ASSET
 if item['owner_id']==SOURCE:
  assert item['can_equip'],'Live worker must verify source wallet before recovery transfer'
  r=a.post('/api/relics/4/transfer',json={'recipient_id':DESTINATION,'confirm':True,'idempotency_key':'authorized-return-sword-4-to-ordinary-A-v1'})
  assert r.status_code==202,r.text
  operation_id=r.json()['id'];print('Real RGB return queued:',operation_id,flush=True)
 else:
  assert item['owner_id']==DESTINATION
  operation_id=next(o['id'] for o in b.get('/api/relics').json()['history'] if o['serial']==4 and o['recipient_id']==DESTINATION)
 for _ in range(240):
  state=b.get('/api/relics').json()
  item=next((i for i in state['items'] if i['serial']==4),None)
  op=next((o for o in state['history'] if o['id']==operation_id),None)
  if item and item['can_equip'] and op and op['state']=='settled':break
  time.sleep(1)
 else:raise AssertionError('Return pending; do not replace asset or change ownership manually')
 assert item['asset_id']==EXPECTED_ASSET and item['owner_id']==DESTINATION
 assert b.post('/api/relics/4/equip').status_code==200
 equipment=b.get('/api/relics').json()['equipment']
 assert equipment['serial']==4 and equipment['damage']==52 and equipment['asset_id']==EXPECTED_ASSET
 assert a.post('/api/relics/4/equip').status_code==409
 proof={'mode':'real','network':'regtest','serial':4,'asset_id':EXPECTED_ASSET,'source_profile':{'id':SOURCE,'name':src['name']},'destination_profile':{'id':DESTINATION,'name':dst['name']},'operation_id':operation_id,'txid':op['txid'],'state':op['state'],'ordinary_A_equipped':True,'damage':equipment['damage'],'test_A_equip_rejected':True}
 path=ROOT/'docs/evidence/sword4-return.json'
 if path.exists():proof={**json.loads(path.read_text()),**proof}
 path.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
 print('SWORD4_RETURN_PASS',op['txid'],flush=True)
if __name__=='__main__':main()
