"""Local RuneForge regtest only; real readiness checks and mined confirmations."""
import json,socket,subprocess,time
from pathlib import Path
from urllib.parse import urlparse
import httpx
ROOT=Path(__file__).resolve().parents[3]

def rpc(*args):
 r=subprocess.run(['docker','compose','exec','-T','-u','blits','bitcoind','bitcoin-cli','-regtest',*[json.dumps(x) if isinstance(x,bool) else str(x) for x in args]],cwd=ROOT,capture_output=True,text=True,timeout=20)
 if r.returncode:raise RuntimeError('bitcoin_rpc_unavailable')
 try:return json.loads(r.stdout)
 except json.JSONDecodeError:return r.stdout.strip()
def chain():
 result=rpc('getblockchaininfo')
 if result['chain']!='regtest':raise RuntimeError('regtest_required')
 return result['blocks']
def ensure_miner():
 chain()
 if 'runeforge-miner' not in rpc('listwallets'):
  existing=[w['name'] for w in rpc('listwalletdir')['wallets']]
  rpc('loadwallet' if 'runeforge-miner' in existing else 'createwallet','runeforge-miner')
 if chain()<110:mine(111)
def mine(n=2):
 chain()
 rpc('-rpcwallet=runeforge-miner','generatetoaddress',n,rpc('-rpcwallet=runeforge-miner','getnewaddress'))
def index_height(url='tcp://127.0.0.1:51001'):
 u=urlparse(url)
 with socket.create_connection((u.hostname,u.port),timeout=3) as s:
  s.settimeout(3);s.sendall(b'{"id":1,"method":"blockchain.headers.subscribe","params":[]}\n')
  payload=b''
  while b'\n' not in payload:payload+=s.recv(8192)
  return json.loads(payload.split(b'\n')[0])['result']['height']
def probe(indexer,proxy):
 height=chain()
 try:
  if index_height(indexer)<height:raise RuntimeError('indexer_syncing')
 except RuntimeError:raise
 except Exception:raise RuntimeError('indexer_unavailable') from None
 try:
  url=proxy.replace('rpc://','http://',1)
  result=httpx.post(url,json={'jsonrpc':'2.0','id':1,'method':'server.info','params':[]},timeout=3).json()
  if result.get('result',{}).get('protocol_version')!='0.2':raise ValueError()
 except Exception:raise RuntimeError('proxy_unavailable') from None
 return height

def fund_and_prepare(wallet):
 """Stable public funding address allows recovery after sendtoaddress but before local marker."""
 path=wallet.path/'funding-address.txt'
 if not path.exists():
  temp=path.with_suffix('.tmp');temp.write_text(wallet.address());temp.replace(path)
 address=path.read_text().strip()
 # SDK balance read is online and actually synchronizes vanilla funds.
 balance=wallet.wallet.get_btc_balance(wallet.connect(),False)
 if balance.vanilla.settled<10000 and balance.vanilla.future<10000:
  transactions=rpc('-rpcwallet=runeforge-miner','listtransactions','*',10000,0,True)
  previous=[t for t in transactions if t.get('address')==address and t.get('category')=='send']
  if not previous:rpc('-rpcwallet=runeforge-miner','sendtoaddress',address,'0.02')
  elif balance.vanilla.settled<1000:raise RuntimeError('wallet_funding_needs_review')
 if rpc('getrawmempool'):mine(2)
 for _ in range(30):
  if index_height(wallet.indexer)>=chain():break
  time.sleep(.2)
 wallet.create_utxos()
 if rpc('getrawmempool'):mine(2)
 for _ in range(30):
  if index_height(wallet.indexer)>=chain():break
  time.sleep(.2)
 wallet.refresh()
