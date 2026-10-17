"""HTTP integration of the browser's same-origin proxy with REAL RGB regtest.
No browser automation, no mocks, no worker interruption. Uses only dedicated test profiles.
"""
import argparse,json,secrets,time,urllib.request,urllib.error
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--url',default='http://127.0.0.1:18082');parser.add_argument('--label',default='javascript');args=parser.parse_args()
 statepath=ROOT/'.state'/('web-api-'+args.label+'.json');statepath.parent.mkdir(exist_ok=True)
 state=json.loads(statepath.read_text()) if statepath.exists() else {'profiles':[{ 'name':f'Тест HTTP {args.label} {slot}','key':secrets.token_hex(32)} for slot in ('A','B')]}
 def save():statepath.write_text(json.dumps(state));statepath.chmod(0o600)
 save()
 def request(path,method='GET',body=None,profile=0,expected=200):
  headers={'Content-Type':'application/json'}
  if state['profiles'][profile].get('token'):headers['Authorization']='Bearer '+state['profiles'][profile]['token']
  req=urllib.request.Request(args.url+path,data=json.dumps(body).encode() if body is not None else None,headers=headers,method=method)
  try:
   with urllib.request.urlopen(req,timeout=20) as r:status,data=r.status,json.load(r)
  except urllib.error.HTTPError as e:status,data=e.code,json.load(e)
  assert status==expected,(path,status,expected)
  return data
 for slot,p in enumerate(state['profiles']):
  if not p.get('token'):p.update(request('/api/players','POST',{'name':p['name'],'registration_key':p['key'],'is_test':True},slot,201));save()
 a,b=state['profiles'];assert a['id']!=b['id']
 def wait(predicate,profile=0):
  for _ in range(180):
   data=request('/api/relics',profile=profile)
   if predicate(data):return data
   time.sleep(1)
  raise AssertionError('Real RGB operation did not reach expected state')
 trial=request('/api/relics').get('trial')
 if not trial or trial['status']=='lost':trial=request('/api/sessions','POST',{},expected=201)
 for _ in range(60):
  if trial['status']!='active':break
  action='guard' if trial['intent']=='heavy' else 'rest' if trial['stamina']<24 else 'attack';time.sleep(.4)
  trial=request('/api/sessions/'+trial['id']+'/commands','POST',{'action':action,'turn':trial['turn'],'idempotency_key':f"web-{trial['id']}-{trial['turn']}"})
 assert trial['status']=='won'
 body={'idempotency_key':'web-reward-'+trial['id']}
 award=request('/api/sessions/'+trial['id']+'/result','POST',body);serial=award['serial']
 assert request('/api/sessions/'+trial['id']+'/result','POST',body)['serial']==serial
 print(args.label,'server victory, unique reward',serial,flush=True)
 data=wait(lambda d:any(h['serial']==serial and h['kind']=='award' and h['state']=='settled' for h in d['history']))
 previous=next((h for h in data['history'] if h['serial']==serial and h['kind']=='transfer'),None)
 if not previous:
  data=wait(lambda d:any(i['serial']==serial and i['can_equip'] for i in d['items']))
  item=next(i for i in data['items'] if i['serial']==serial);aid=item['asset_id'];state['asset_id']=aid;save()
  request(f'/api/relics/{serial}/equip','POST',{});assert request('/api/relics')['equipment']['damage']==52
  request(f'/api/relics/{serial}/equip','POST',{},1,409)
  request(f'/api/relics/{serial}/transfer','POST',{'recipient_id':b['id'],'confirm':True,'idempotency_key':'forged','asset_id':aid},expected=422)
  transfer={'recipient_id':b['id'],'confirm':True,'idempotency_key':f'web-transfer-{serial}'}
  op=request(f'/api/relics/{serial}/transfer','POST',transfer,expected=202)
  assert request(f'/api/relics/{serial}/transfer','POST',transfer,expected=202)['id']==op['id']
  request(f'/api/relics/{serial}/transfer','POST',{**transfer,'idempotency_key':'double-transfer'},expected=409)
  assert request('/api/relics')['equipment'] is None
 data=wait(lambda d:any(h['serial']==serial and h['kind']=='transfer' and h['state']=='settled' for h in d['history']))
 op=next(h for h in data['history'] if h['serial']==serial and h['kind']=='transfer');aid=state['asset_id']
 request(f'/api/relics/{serial}/equip','POST',{},expected=409)
 recipient=wait(lambda d:any(i['serial']==serial and i['can_equip'] for i in d['items']),1)
 assert next(i for i in recipient['items'] if i['serial']==serial)['asset_id']==aid
 request(f'/api/relics/{serial}/equip','POST',{},1);assert request('/api/relics',profile=1)['equipment']['damage']==52
 assert request('/api/relics')['equipment'] is None
 evidence={'test':'HTTP proxy + real RGB (not visual/browser QA)','variant':args.label,'network':'regtest','mode':'real','serial':serial,'asset_id':aid,'txid':op['txid'],'player_a':a['id'],'player_b':b['id'],'checks':['server_victory','one_reward','real_UDA','equip_52','foreign_equip_rejected','forged_asset_id_rejected','idempotent_transfer','double_transfer_rejected','real_A_to_B','same_asset_id','sender_revoked','recipient_equipped']}
 out=ROOT/'docs/evidence'/('web-api-'+args.label+'.json');out.parent.mkdir(exist_ok=True);out.write_text(json.dumps(evidence,indent=2,ensure_ascii=False)+'\n');print(args.label,'REAL_HTTP_RGB_PASS',serial,aid,op['txid'],flush=True)
if __name__=='__main__':main()
