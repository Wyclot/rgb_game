"""Official rgb-lib 0.3.0b7 only. All keys, signing and SDK state are operator-local.

The binding signatures are checked by scripts/verify_rgb_api.py. No mainnet switch.
"""
import fcntl, hashlib, json, os, sqlite3, time
from importlib.metadata import version
from pathlib import Path
from urllib.parse import urlparse

class RGBError(RuntimeError):pass
class RecoveryRequired(RGBError):pass

def local_endpoint(value,schemes):
 u=urlparse(value)
 if u.scheme not in schemes or u.hostname not in ('127.0.0.1','localhost','electrs','proxy'):
  raise RGBError('Only local regtest infrastructure is supported')
 return value

def public_transfer(t):
 return dict(idx=t.idx,batch_idx=t.batch_transfer_idx,state=t.status.name,txid=t.txid,recipient_id=t.recipient_id)

class RealRGB:
 mode='real'
 def __init__(self,path,indexer=None,proxy=None):
  if version('rgb-lib')!='0.3.0b7':raise RGBError('Install exactly rgb-lib==0.3.0b7')
  import rgb_lib as r
  self.r=r
  self.indexer=local_endpoint(indexer or os.getenv('RGB_INDEXER','tcp://127.0.0.1:51001'),('tcp',))
  self.proxy=local_endpoint(proxy or os.getenv('RGB_PROXY','rpc://127.0.0.1:3100/json-rpc'),('rpc',))
  self.path=Path(path).resolve();self.path.mkdir(parents=True,exist_ok=True,mode=0o700);self.path.chmod(0o700)
  self.lock=open(self.path/'wallet.lock','a+')
  try:fcntl.flock(self.lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:raise RGBError('Wallet is already open in another process')
  old_umask=os.umask(0o077)
  try:
   secret=self.path/'mnemonic.txt'
   if secret.exists():keys=r.restore_keys(r.BitcoinNetwork.REGTEST,secret.read_text().strip(),r.WitnessVersion.SEG_WIT_V0)
   else:
    keys=r.generate_keys(r.BitcoinNetwork.REGTEST,r.WitnessVersion.SEG_WIT_V0)
    # Exclusive create: never overwrite existing wallet secrets.
    with secret.open('x') as out:out.write(keys.mnemonic)
   secret.chmod(0o600)
   data=r.WalletData(data_dir=str(self.path),bitcoin_network=r.BitcoinNetwork.REGTEST,database_type=r.DatabaseType.SQLITE,max_allocations_per_utxo=5,supported_schemas=[r.AssetSchema.NIA,r.AssetSchema.UDA])
   signing=r.SinglesigKeys(account_xpub_vanilla=keys.account_xpub_vanilla,account_xpub_colored=keys.account_xpub_colored,vanilla_keychain=None,master_fingerprint=keys.master_fingerprint,mnemonic=keys.mnemonic,witness_version=keys.witness_version)
   # These private directories are accessed only through this adapter's OS flock.
   # rgb-lib also uses an empty create_new marker, which survives SIGKILL. Archive
   # that stale marker only after the exclusive OS lock is held; keep all RGB data.
   stale=self.path/keys.master_fingerprint/'rgb_runtime.lock'
   if stale.exists():stale.rename(stale.with_name('rgb_runtime.stale-'+str(time.time_ns())))
   self.wallet=r.Wallet(data,signing)
   self.journal=sqlite3.connect(self.path/'operations.sqlite')
   self.journal.row_factory=sqlite3.Row
   self.journal.execute('CREATE TABLE IF NOT EXISTS operations (key TEXT PRIMARY KEY, intent TEXT NOT NULL, state TEXT NOT NULL, result TEXT, started INTEGER NOT NULL)');self.journal.commit()
  finally:os.umask(old_umask)
  self.online=None
 def close(self):
  self.wallet=None
  self.journal.close();fcntl.flock(self.lock,fcntl.LOCK_UN);self.lock.close()
 def __enter__(self):return self
 def __exit__(self,*_):self.close()
 def connect(self):
  if self.online is None:
   self.online=self.wallet.go_online(self.r.OnlineOptions(indexer_url=self.indexer,skip_consistency_check=False,vanilla_sync_lookback=20))
  return self.online
 def address(self):return self.wallet.get_address()
 def create_utxos(self):
  try:return self.wallet.create_utxos(self.connect(),True,8,1000,1,False)
  except self.r.RgbLibError.AllocationsAlreadyAvailable:return 0
 def assets(self):
  assets=self.wallet.list_assets([])
  out=[]
  for category in ('nia','uda'):
   for a in getattr(assets,category) or []:
    balance=self.wallet.get_asset_balance(a.asset_id)
    out.append(dict(asset_id=a.asset_id,category=category.upper(),ticker=a.ticker,name=a.name,settled=balance.settled,spendable=balance.spendable))
  return out
 def reserve(self,key,intent):
  canonical=json.dumps(intent,sort_keys=True,separators=(',',':'))
  row=self.journal.execute('SELECT * FROM operations WHERE key=?',(key,)).fetchone()
  if row:
   if row['intent']!=canonical:raise RGBError('Operation key reused for different intent')
   return dict(row)
  self.journal.execute('INSERT INTO operations VALUES (?,?,?,?,?)',(key,canonical,'started',None,int(time.time())));self.journal.commit();return None
 def finish(self,key,result,state='submitted'):
  self.journal.execute('UPDATE operations SET state=?,result=? WHERE key=?',(state,json.dumps(result),key));self.journal.commit();return result
 def issue(self,category,key,media=None):
  if category not in ('NIA','UDA'):raise RGBError('Unsupported asset category')
  # Content digest binds media to issuance and repeat recovery.
  digest=hashlib.sha256(Path(media).read_bytes()).hexdigest() if media else None
  intent=dict(operation='issue',category=category,media_sha256=digest)
  prior=self.reserve(key,intent)
  if prior and prior['result']:return json.loads(prior['result'])
  ticker='RF'+hashlib.sha256(key.encode()).hexdigest()[:6].upper()
  if prior:
   found=[a for a in self.assets() if a['ticker']==ticker and a['category']==category and (not key.startswith('managed-') or self.wallet.get_asset_metadata(a['asset_id']).details=='RuneForge registered instance. Issue key: '+key)]
   if len(found)==1:return self.finish(key,found[0],'issued')
   raise RecoveryRequired('Ambiguous issuance: inspect SDK state; do not issue again with a new key')
  try:
   if category=='NIA':asset=self.wallet.issue_asset_nia(ticker,'RuneForge Embers',0,[1000000])
   else:asset=self.wallet.issue_asset_uda(ticker,'RuneForge Flame Sword',('RuneForge registered instance. Issue key: '+key) if key.startswith('managed-') else 'RuneForge legendary relic. Bitcoin regtest only.',0,str(Path(media).resolve()) if media else None,[])
   if os.getenv('RUNEFORGE_FAULT')=='issue_native' and key.startswith('managed-'):os._exit(91)
   return self.finish(key,dict(asset_id=asset.asset_id,category=category,ticker=ticker,mode='real',network='regtest'),'issued')
  except Exception:
   # Keep started marker: SDK effect may have occurred before exception.
   raise
 def receive(self,category='UDA',asset_id=None,amount=1):
  assignment=(self.r.Assignment.NON_FUNGIBLE() if asset_id else self.r.Assignment.ANY()) if category=='UDA' else self.r.Assignment.FUNGIBLE(amount)
  received=self.wallet.blind_receive(asset_id,assignment,int(time.time())+86400,[self.proxy],1)
  return dict(invoice=received.invoice,recipient_id=received.recipient_id,expiration_timestamp=received.expiration_timestamp,batch_idx=received.batch_transfer_idx,mode='real',network='regtest')
 def receive_once(self,key):
  intent={'operation':'managed_receive','category':'UDA'}
  prior=self.reserve(key,intent)
  if prior:
   result=json.loads(prior['result']) if prior['result'] else {}
   if prior['state']=='received':return result
   if 'before' not in result:raise RecoveryRequired('Receive intent incomplete; reservation retained')
   matches=[t for t in self.wallet.list_transfers(None) if t.idx not in result['before'] and t.invoice_string]
   if len(matches)!=1:raise RecoveryRequired('Receive outcome ambiguous; reservation retained')
   t=matches[0]
   return self.finish(key,dict(invoice=t.invoice_string,recipient_id=t.recipient_id,expiration_timestamp=t.expiration_timestamp,batch_idx=t.batch_transfer_idx),'received')
  self.finish(key,{'before':[t.idx for t in self.wallet.list_transfers(None)]},'receive_started')
  result=self.receive()
  return self.finish(key,result,'received')
 def send(self,asset_id,invoice,key):
  data=self.r.Invoice(invoice).invoice_data()
  if data.network!=self.r.BitcoinNetwork.REGTEST:raise RGBError('Invoice is not regtest')
  if data.asset_id not in (None,asset_id):raise RGBError('Invoice asset mismatch')
  intent=dict(operation='send',asset_id=asset_id,recipient=data.recipient_id,invoice=invoice)
  existing=self.journal.execute('SELECT * FROM operations WHERE key=?',(key,)).fetchone()
  if existing:
   prior=self.reserve(key,intent)
   if prior['result']:return json.loads(prior['result'])
   found=[t for t in self.wallet.list_transfers(asset_id) if t.recipient_id==data.recipient_id and t.created_at>=prior['started']-2]
   if len(found)==1:return self.finish(key,public_transfer(found[0]))
   raise RecoveryRequired('Ambiguous send: keep reservation; inspect SDK transfers before any retry')
  expiry=data.expiration_timestamp
  if expiry is None or expiry<=time.time():raise RGBError('A future invoice expiration is required')
  for endpoint in data.transport_endpoints:local_endpoint(endpoint,('rpc',))
  if not data.transport_endpoints:raise RGBError('Transport endpoint required')
  metadata=self.wallet.get_asset_metadata(asset_id)
  assignment=data.assignment
  if metadata.asset_schema==self.r.AssetSchema.UDA:
   if not (assignment.is_non_fungible() or assignment.is_any()):raise RGBError('UDA requires a non-fungible or open invoice assignment')
   assignment=self.r.Assignment.NON_FUNGIBLE()
  elif metadata.asset_schema==self.r.AssetSchema.NIA:
   if not data.assignment.is_fungible():raise RGBError('NIA requires a fungible invoice assignment')
  else:raise RGBError('Unsupported asset schema')
  intent=dict(operation='send',asset_id=asset_id,recipient=data.recipient_id,invoice=invoice)
  prior=self.reserve(key,intent)
  if prior and prior['result']:return json.loads(prior['result'])
  if prior:
   found=[t for t in self.wallet.list_transfers(asset_id) if t.recipient_id==data.recipient_id and t.created_at>=prior['started']-2]
   if len(found)==1:return self.finish(key,public_transfer(found[0]))
   raise RecoveryRequired('Ambiguous send: keep reservation; inspect SDK transfers before any retry')
  recipient=self.r.Recipient(recipient_id=data.recipient_id,witness_data=None,assignment=assignment,transport_endpoints=data.transport_endpoints)
  result=self.wallet.send(self.connect(),{asset_id:[recipient]},False,1,1,expiry)
  if os.getenv('RUNEFORGE_FAULT')=='send_native' and key.startswith('managed-'):os._exit(92)
  return self.finish(key,dict(txid=result.txid,batch_idx=result.batch_transfer_idx,state='WAITING_COUNTERPARTY',mode='real',network='regtest'))
 def refresh(self,asset_id=None):
  self.wallet.refresh(self.connect(),asset_id,[],False)
  return [public_transfer(t) for t in self.wallet.list_transfers(asset_id)]
 def balance(self,asset_id):
  b=self.wallet.get_asset_balance(asset_id)
  return dict(settled=b.settled,future=b.future,spendable=b.spendable)

class MockRGB:
 """Test adapter: deliberately incapable of returning a Bitcoin txid or verified ownership."""
 mode='mock'
 def issue(self,category,key,media=None):return dict(asset_id='mock:'+hashlib.sha256(key.encode()).hexdigest(),category=category,mode='mock',ownership='pending_verification')
 def receive(self,*_,**__):return dict(mode='mock',invoice=None,message='Mock mode cannot create a real RGB invoice')
 def send(self,*_,**__):return dict(mode='mock',state='MOCK_ONLY',txid=None,ownership='pending_verification')
 def refresh(self,*_,**__):return []
