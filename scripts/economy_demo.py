"""Verify server-earned relic -> real UDA -> authenticated withdrawal -> receiver settlement."""
import json,os,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from backend.app.main import create_app
from backend.app.rgb.service import RealRGB
from backend.app.services.operator import mint_reward,process_transfer,reconcile_transfer
from scripts.regtest_demo import rpc,mine

def main():
 assert rpc('getblockchaininfo')['chain']=='regtest'
 app=create_app(testing=True)
 with TestClient(app) as api,RealRGB('.state/issuer') as issuer,RealRGB('.state/receiver') as receiver:
  player=api.post('/api/players',json={'name':'Economy QA','is_test':True}).json();api.headers['Authorization']='Bearer '+player['token']
  trial=api.post('/api/sessions',json={}).json()
  for i in range(60):
   if trial['status']!='active':break
   action='guard' if trial['intent']=='heavy' else ('rest' if trial['stamina']<24 else 'attack')
   result=api.post('/api/sessions/'+trial['id']+'/commands',json={'action':action,'turn':trial['turn'],'idempotency_key':f'economy-turn-{i}'})
   assert result.status_code==200,result.text
   trial=result.json()
  assert trial['status']=='won'
  reward=api.post('/api/sessions/'+trial['id']+'/result',json={'idempotency_key':'economy-reward'}).json()
  issued=mint_reward(app.state.engine,issuer,reward['inventory_id'],'game/assets/legendary.png')
  duplicate=mint_reward(app.state.engine,issuer,reward['inventory_id'],'game/assets/legendary.png')
  assert issued['asset_id']==duplicate['asset_id']
  aid=issued['asset_id']
  assert api.get('/api/ownership/'+aid).json()['equippable'] is True
  assert api.post('/api/equipment',json={'inventory_id':reward['inventory_id']}).status_code==200
  receipt=receiver.receive()
  body={'asset_id':aid,'recipient':receipt['invoice'],'idempotency_key':'economy-withdrawal'}
  requested=api.post('/api/rgb/transfers',json=body)
  assert requested.status_code==202,requested.text
  tid=requested.json()['id']
  assert api.post('/api/rgb/transfers',json=body).json()['id']==tid
  assert api.post('/api/equipment',json={'inventory_id':reward['inventory_id']}).status_code==409
  submitted=process_transfer(app.state.engine,issuer,tid)
  for _ in range(20):
   receiver.refresh();reconcile_transfer(app.state.engine,issuer,tid);mine(2)
   receiver.refresh();settled=reconcile_transfer(app.state.engine,issuer,tid)
   if settled['state']=='settled':break
  assert settled['state']=='settled',settled
  assert receiver.balance(aid)['settled']==1
  assert api.get('/api/ownership/'+aid).json()['ownership']=='withdrawn'
  assert process_transfer(app.state.engine,issuer,tid)['txid']==settled['txid']
  evidence={'mode':'real','network':'regtest','profile_id':player['id'],'session_id':trial['id'],'reward_id':reward['reward_id'],'asset_id':aid,'transfer_id':tid,'txid':settled['txid'],'state':'settled','receiver_settled':1,'issuance_idempotent':True,'withdrawal_idempotent':True,'equip_blocked_after_reservation':True,'equippable_after_withdrawal':False}
  Path('docs/evidence/economy-regtest.json').write_text(json.dumps(evidence,indent=2)+'\n')
  print('ECONOMY_REGTEST_PASS: server victory -> unique reward -> real UDA -> reserved withdrawal -> settled receiver ownership')
if __name__=='__main__':main()
