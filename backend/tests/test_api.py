import os,uuid
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import select,func,create_engine,text
from backend.app.main import create_app
from backend.app.models import Base,InventoryEntry,RGBAsset,RGBTransfer,Equipment, LootReward

@pytest.fixture
def api(tmp_path):
 test_url=os.getenv('TEST_DATABASE_URL')
 schema=None
 if test_url:
  admin=create_engine(test_url);schema='runeforge_test_'+uuid.uuid4().hex
  with admin.begin() as conn:conn.execute(text('CREATE SCHEMA '+schema))
  test_url=str(admin.url.set(query={'options':'-csearch_path='+schema}).render_as_string(hide_password=False))
 app=create_app(test_url or f'sqlite:///{tmp_path}/test.db',testing=True)
 if schema:Base.metadata.create_all(app.state.engine)
 with TestClient(app) as c:
  r=c.post('/api/players',json={'name':'Warden'});assert r.status_code==201
  c.headers['Authorization']='Bearer '+r.json()['token']
  c.player_id=r.json()['id']
  yield c
 if schema:
  with admin.begin() as conn:conn.execute(text('DROP SCHEMA '+schema+' CASCADE'))
  admin.dispose()

def win(api):
 s=api.post('/api/sessions',json={}).json()
 for _ in range(60):
  if s['status']!='active':break
  action='guard' if s['intent']=='heavy' else ('rest' if s['stamina']<24 else 'attack')
  result=api.post(f"/api/sessions/{s['id']}/commands",json={'action':action,'turn':s['turn'],'idempotency_key':f"command-{s['turn']:04}"})
  assert result.status_code==200,result.text
  s=result.json()
 assert s['status']=='won',s
 return s

def test_auth_and_input(api):
 assert api.get('/health').json()['status']=='ok'
 assert api.get('/api/profile',headers={'Authorization':'Bearer wrong'}).status_code==401
 assert api.post('/api/players',json={'name':'X','token':'injected'}).status_code==422
 assert api.post('/api/sessions',json={}).status_code==201

def test_no_client_victory_or_loot(api):
 s=api.post('/api/sessions',json={}).json()
 url=f"/api/sessions/{s['id']}/result"
 assert api.post(url,json={'idempotency_key':'unearned'}).status_code==409
 assert api.post(url,json={'idempotency_key':'forged-claim','victory':True}).status_code==422
 assert len(api.get('/api/inventory').json()['items'])==1

def test_reward_idempotency_concurrency_and_restart(api):
 s=win(api);url=f"/api/sessions/{s['id']}/result"
 def claim(_):return api.post(url,json={'idempotency_key':'reward-key-123'}).json()
 with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(claim,range(8)))
 assert len({r['reward_id'] for r in results})==1
 assert api.post(url,json={'idempotency_key':'different-key'}).json()['reward_id']==results[0]['reward_id']
 assert len(api.get('/api/inventory').json()['items'])==2
 with Session(api.app.state.engine) as db:
  assert db.scalar(select(func.count()).select_from(LootReward).where(LootReward.session_id==s['id']))==1
  assert db.scalar(select(InventoryEntry).where(InventoryEntry.id==results[0]['inventory_id'])) is not None

def test_replayed_command_and_key_conflict(api):
 s=api.post('/api/sessions',json={}).json();url=f"/api/sessions/{s['id']}/commands"
 body={'action':'attack','turn':0,'idempotency_key':'command-once'}
 first=api.post(url,json=body)
 assert first.status_code==200
 assert api.post(url,json=body).json()==first.json()
 assert api.post(url,json={**body,'action':'rest'}).status_code==409
 assert api.post(url,json={**body,'idempotency_key':'another-key'}).status_code==409

def test_cross_player_access(api):
 s=api.post('/api/sessions',json={}).json()
 other=api.post('/api/players',json={'name':'Other'}).json()
 headers={'Authorization':'Bearer '+other['token']}
 assert api.get('/api/sessions/'+s['id'],headers=headers).status_code==404
 entry=api.get('/api/inventory').json()['items'][0]
 assert api.post('/api/equipment',json={'inventory_id':entry['id']},headers=headers).status_code==404

def test_rgb_claim_cannot_equip_or_transfer(api):
 with Session(api.app.state.engine) as db:
  a=RGBAsset(asset_id='mock-unverified-'+api.player_id,category='UDA',item_id='oath_relic',player_id=api.player_id,mode='mock',ownership='pending_verification');db.add(a)
  e=InventoryEntry(player_id=api.player_id,item_id='oath_relic',source_session='fixture',rgb_asset_id=a.asset_id);db.add(e);db.commit();eid=e.id;aid=a.asset_id
 assert api.post('/api/equipment',json={'inventory_id':eid}).status_code==409
 assert api.post('/api/rgb/transfers',json={'asset_id':aid,'recipient':'rgb:recipient','idempotency_key':'send-mock'}).status_code==410
 assert api.post('/api/rgb/transfers',json={'asset_id':'claimed-other-asset','recipient':'rgb:recipient','idempotency_key':'send-fake'}).status_code==410
 assert api.get('/api/ownership/'+aid).json()['equippable'] is False

def test_legacy_paths_are_retired(api):
 assert api.post('/api/rgb/receive').status_code==410
 assert api.get('/api/vault').json()['mode']=='real'
 assert api.get('/api/relics').json()['service']['available'] is False
 assert api.post('/api/relics/1/equip').status_code==503


def test_registration_replay(api):
 body={'name':'Repeat','registration_key':'a'*64}
 first=api.post('/api/players',json=body).json()
 second=api.post('/api/players',json=body).json()
 assert first==second
 assert api.post('/api/players',json={**body,'name':'Changed'}).status_code==409
