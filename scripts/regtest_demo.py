"""Real RGB regtest end-to-end test using isolated RuneForge compose services.

Uses only newly generated local wallets. Never imports external mnemonics.
"""
import json,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.app.rgb.service import RealRGB

def rpc(*args):
 result=subprocess.run(['docker','compose','exec','-T','-u','blits','bitcoind','bitcoin-cli','-regtest',*map(str,args)],check=True,capture_output=True,text=True)
 try:return json.loads(result.stdout)
 except json.JSONDecodeError:return result.stdout.strip()
def mine(count=2):
 rpc('-rpcwallet=runeforge-miner','generatetoaddress',count,rpc('-rpcwallet=runeforge-miner','getnewaddress'))
 time.sleep(1)
def main():
 assert rpc('getblockchaininfo')['chain']=='regtest'
 loaded=rpc('listwallets')
 if 'runeforge-miner' not in loaded:
  existing=[w['name'] for w in rpc('listwalletdir')['wallets']]
  rpc('loadwallet' if 'runeforge-miner' in existing else 'createwallet','runeforge-miner')
 if rpc('getblockcount')<110:mine(111)
 with RealRGB('.state/issuer') as issuer,RealRGB('.state/receiver') as receiver:
  # Existing wallet funding is preserved; repeat only prepares missing UTXOs.
  for wallet in (issuer,receiver):
   funding_marker=wallet.path/'funded'
   if not funding_marker.exists():
    rpc('-rpcwallet=runeforge-miner','sendtoaddress',wallet.address(),'0.01');funding_marker.write_text('regtest only')
  mine(2)
  for wallet in (issuer,receiver):wallet.create_utxos()
  mine(2)
  nia=issuer.issue('NIA','runeforge-demo-token-v1')
  uda=issuer.issue('UDA','runeforge-demo-legendary-v1','game/assets/legendary.png')
  print('Real NIA and UDA issued',flush=True)
  evidence={'mode':'real','network':'regtest','library':'rgb-lib==0.3.0b7','assets':[]}
  for category,asset,amount in [('NIA',nia,25),('UDA',uda,1)]:
   aid=asset['asset_id']
   receipt_path=receiver.path/(category+'-invoice.json')
   if receipt_path.exists():receipt=json.loads(receipt_path.read_text())
   else:
    receipt=receiver.receive(category,None,amount);receipt_path.write_text(json.dumps(receipt))
   result=issuer.send(aid,receipt['invoice'],'runeforge-demo-send-'+category)
   for attempt in range(20):
    receiver.refresh();issuer.refresh(aid)
    mine(2)
    receiver.refresh();issuer.refresh(aid)
    balance=receiver.balance(aid)
    if balance['settled']==amount:break
   assert balance['settled']==amount,(category,balance)
   remaining=issuer.balance(aid)
   assert remaining['settled']==(1000000-amount if category=='NIA' else 0),remaining
   # Same intent returns same operation without signing or broadcasting again.
   replay=issuer.send(aid,receipt['invoice'],'runeforge-demo-send-'+category)
   assert replay['txid']==result['txid']
   transfers=receiver.refresh(aid)
   evidence['assets'].append({'category':category,'asset_id':aid,'txid':result['txid'],'receiver_settled':balance['settled'],'issuer_settled':remaining['settled'],'receiver_states':[t['state'] for t in transfers],'same_key_replayed':True})
   print(category,'settled on both wallets; replay returned same txid',flush=True)
  evidence['block_height']=rpc('getblockcount')
  Path('docs/evidence/rgb-regtest.json').write_text(json.dumps(evidence,indent=2)+'\n')
 print('REAL_RGB_REGTEST_PASS',flush=True)
if __name__=='__main__':main()
