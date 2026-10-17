"""One local worker: managed keys, resumable UDA issuance and real wallet-to-wallet delivery."""
import argparse,fcntl,os,time,signal
from pathlib import Path
from sqlalchemy import select,delete
from sqlalchemy.orm import Session
from ..database import make_engine
from ..models import (ItemInstance,ItemOperation,ItemEvent,RGBAsset,ManagedWallet,WorkerState,
                      RelicEquipment,InventoryEntry,LootReward)
from ..rgb.service import RealRGB,RecoveryRequired
from ..rgb.infrastructure import ensure_miner,fund_and_prepare,probe,rpc,mine

TERMINAL=('settled','failed')
def wallet_root():return Path(os.getenv('RUNEFORGE_WALLET_ROOT','.state/managed-v2')).resolve()
def transition(db,op,state):
 if op.state!=state:
  op.state=state;db.add(ItemEvent(operation_id=op.id,state=state))
 op.error_code=None

class Worker:
 def __init__(self,engine=None):
  self.engine=engine or make_engine();self.root=wallet_root();self.root.mkdir(parents=True,exist_ok=True,mode=0o700)
  self.lock=open(self.root/'worker.lock','a+')
  try:fcntl.flock(self.lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:raise RuntimeError('Another managed worker is already running') from None
  self.wallets={};self.prepared=set();self.miner_ready=False
  self.indexer=os.getenv('RGB_INDEXER','tcp://127.0.0.1:51001');self.proxy=os.getenv('RGB_PROXY','rpc://127.0.0.1:3100/json-rpc')
 def discard_connections(self):
  for w in self.wallets.values():w.close()
  self.wallets.clear()
 def close(self):
  self.discard_connections();self.lock.close()
 def wallet(self,player_id=None):
  key=player_id or 'issuer'
  if key not in self.wallets:self.wallets[key]=RealRGB(self.root/key,self.indexer,self.proxy)
  return self.wallets[key]
 def prepare(self,player_id=None):
  key=player_id or 'issuer';w=self.wallet(player_id)
  if key not in self.prepared:
   fund_and_prepare(w);self.prepared.add(key)
   if player_id:
    with Session(self.engine) as db:
     row=db.get(ManagedWallet,player_id)
     row.status='ready';row.fingerprint=w.wallet.get_keys().master_fingerprint;db.commit()
  return w
 def health(self,available,error=None,height=None):
  with Session(self.engine) as db:
   row=db.get(WorkerState,'managed')
   if not row:row=WorkerState(id='managed');db.add(row)
   row.heartbeat=time.time();row.available=int(available);row.error_code=error
   if height is not None:row.block_height=height
   db.commit()
 def tick(self):
  try:
   if not self.miner_ready:ensure_miner();self.miner_ready=True
   height=probe(self.indexer,self.proxy)
  except Exception as exc:
   code=str(exc) if str(exc) in ('indexer_syncing','indexer_unavailable','proxy_unavailable','bitcoin_rpc_unavailable','regtest_required') else 'infrastructure_unavailable'
   self.health(False,code);self.discard_connections();return
  self.health(True,height=height)
  with Session(self.engine) as db:
   ids=list(db.scalars(select(ItemOperation.id).where(ItemOperation.state.not_in(TERMINAL)).order_by(ItemOperation.created_at)))
  for oid in ids:
   try:self.process(oid)
   except Exception as exc:
    with Session(self.engine) as db:
     op=db.get(ItemOperation,oid)
     if op:
      op.error_code='ambiguous_operation' if isinstance(exc,RecoveryRequired) else type(exc).__name__
      # Preserve operation stage and reservation; never release on timeout/exception.
      db.commit()
    self.health(False,'operation_recovery_required')
  # Mine only real outstanding transactions on this isolated regtest chain.
  try:
   if rpc('getrawmempool'):mine(2)
   # Verify actual allocations before refreshing any right-to-use evidence.
   self.verify_owned()
   height=probe(self.indexer,self.proxy)
   self.health(True,height=height)
  except Exception:
   self.health(False,'wallet_verification_unavailable');self.discard_connections()
 def process(self,oid):
  with Session(self.engine) as db:
   op=db.get(ItemOperation,oid);i=db.get(ItemInstance,op.serial)
   if op.state in TERMINAL:return
   recipient=self.prepare(op.recipient_id)
   sender=self.prepare(op.sender_id)
   if not i.asset_id:
    transition(db,op,'issuing');i.state='issuing';db.commit()
    issued=sender.issue('UDA','managed-instance-'+str(i.serial),str(Path(__file__).resolve().parents[3]/'game/assets/legendary.png'))
    if os.getenv('RUNEFORGE_FAULT')=='issue_database':os._exit(93)
    aid=issued['asset_id']
    # Register only a contract issued for this exact server reward.
    a=db.get(RGBAsset,aid)
    if not a:db.add(RGBAsset(asset_id=aid,category='UDA',item_id=i.type_id,player_id=None,mode='real',ownership='delivery_pending',metadata_json={'serial':i.serial,'issuance_key':'managed-instance-'+str(i.serial)}));db.flush()
    i.asset_id=aid;i.state='delivering';transition(db,op,'preparing');db.commit();return
   if op.invoice is None:
    receipt=recipient.receive_once('managed-receive-'+op.id)
    op.invoice=receipt['invoice'];transition(db,op,'preparing');db.commit();return
   if op.txid is None:
    transition(db,op,'signing');db.commit()
    result=sender.send(i.asset_id,op.invoice,'managed-send-'+op.id)
    if os.getenv('RUNEFORGE_FAULT')=='send_database':os._exit(94)
    op.txid=result['txid'];op.batch_idx=result['batch_idx'];transition(db,op,'waiting_counterparty');db.commit();return
   recipient.refresh()
   try:received=recipient.refresh(i.asset_id)
   except recipient.r.RgbLibError.AssetNotFound:received=[]
   sent=sender.refresh(i.asset_id)
   sends=[t for t in sent if t['batch_idx']==op.batch_idx and t['txid']==op.txid]
   receives=[t for t in received if t['txid']==op.txid]
   if not sends:raise RecoveryRequired('SDK transfer not found')
   observed=sends[0]['state']
   if observed=='SETTLED' and any(t['state']=='SETTLED' for t in receives):
    rb=recipient.balance(i.asset_id);sb=sender.balance(i.asset_id)
    if rb['settled']!=1 or rb['spendable']!=1 or sb['settled']!=0:raise RecoveryRequired('Ownership reconciliation failed')
    # A previously issued client lease must expire before the new owner can equip.
    db.refresh(i,with_for_update=True)
    if i.use_until>time.time():return
    i.owner_id=op.recipient_id;i.state='owned';i.verified_at=time.time();i.revision+=1
    a=db.get(RGBAsset,i.asset_id);a.player_id=i.owner_id;a.ownership='verified_managed_wallet'
    reward=db.get(LootReward,i.reward_id);entry=db.get(InventoryEntry,reward.inventory_id)
    entry.player_id=i.owner_id;entry.rgb_asset_id=i.asset_id
    db.execute(delete(RelicEquipment).where(RelicEquipment.serial==i.serial))
    transition(db,op,'settled');db.commit()
   elif observed=='FAILED':
    sb=sender.balance(i.asset_id)
    try:rb=recipient.balance(i.asset_id)
    except recipient.r.RgbLibError.AssetNotFound:rb={'settled':0,'future':0}
    if op.kind=='transfer' and sb['settled']==1 and sb['spendable']==1 and rb['settled']==0 and rb['future']==0:
     db.refresh(i,with_for_update=True);i.state='owned';i.verified_at=time.time();transition(db,op,'failed');db.commit()
    else:raise RecoveryRequired('Failed transfer ownership requires review')
   else:transition(db,op,'waiting_receiver' if observed=='SETTLED' else observed.lower());db.commit()
 def verify_owned(self):
  with Session(self.engine) as db:
   ids=list(db.scalars(select(ItemInstance.serial).where(ItemInstance.state.in_(('owned','verification_required')))))
  for serial in ids:
   with Session(self.engine) as db:
    i=db.get(ItemInstance,serial);owner=i.owner_id;aid=i.asset_id
   wallet=self.wallet(owner);wallet.refresh(aid);balance=wallet.balance(aid)
   with Session(self.engine) as db:
    i=db.scalar(select(ItemInstance).where(ItemInstance.serial==serial).with_for_update())
    if i.state not in ('owned','verification_required') or i.owner_id!=owner:continue
    if balance['settled']==1 and balance['spendable']==1:i.verified_at=time.time();i.state='owned'
    else:
     i.state='verification_required';i.verified_at=0;db.execute(delete(RelicEquipment).where(RelicEquipment.serial==serial))
    db.commit()

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--once',action='store_true');args=parser.parse_args()
 w=Worker()
 stopping=False
 def stop(*_):
  nonlocal stopping
  stopping=True
 signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
 try:
  while True:
   w.tick()
   if args.once or stopping:break
   time.sleep(1)
 finally:w.health(False,'worker_stopped');w.close()
if __name__=='__main__':main()
