"""Operator-only bridge from validated game rewards to real custodial RGB assets.

Run with the same DATABASE_URL as FastAPI. The HTTP process cannot invoke this module.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models import Player, InventoryEntry, LootReward, RGBAsset, RGBTransfer, Equipment, ItemInstance
from ..rgb.service import RGBError

def lock_player(db,player_id):
 # Operator uses PostgreSQL in deployment; SQLite is single local operator only.
 return db.scalar(select(Player).where(Player.id==player_id).with_for_update())

def mint_reward(engine,wallet,inventory_id,media):
 if wallet.mode!='real':raise RGBError('Mock issuance cannot verify ownership')
 with Session(engine) as db:
  entry=db.get(InventoryEntry,inventory_id)
  if not entry:raise RGBError('Inventory entry not found')
  lock_player(db,entry.player_id)
  reward=db.scalar(select(LootReward).where(LootReward.inventory_id==entry.id))
  if not reward or entry.item_id!='oath_relic':raise RGBError('A server-validated legendary reward is required')
  if db.scalar(select(ItemInstance).where(ItemInstance.reward_id==reward.id)):
   raise RGBError('Managed item: the automatic worker owns issuance and delivery; legacy mint is disabled')
  if entry.rgb_asset_id:
   asset=db.get(RGBAsset,entry.rgb_asset_id)
   return dict(asset_id=asset.asset_id,ownership=asset.ownership,already_issued=True)
  # Journal key survives process death between SDK issuance and DB commit.
  issued=wallet.issue('UDA','reward-'+entry.id,media)
  aid=issued['asset_id'];balance=wallet.balance(aid)
  if balance['settled']!=1 or balance['spendable']!=1:raise RGBError('Issuer custody not established')
  a=RGBAsset(asset_id=aid,category='UDA',item_id=entry.item_id,player_id=entry.player_id,mode='real',ownership='verified_custody',metadata_json={'inventory_id':entry.id,'source':'operator SDK balance','network':'regtest'})
  db.add(a);entry.rgb_asset_id=aid;db.commit()
  return dict(asset_id=aid,ownership='verified_custody',mode='real')

def process_transfer(engine,wallet,transfer_id):
 with Session(engine) as db:
  transfer=db.get(RGBTransfer,transfer_id)
  if not transfer or transfer.mode!='real':raise RGBError('Real withdrawal not found')
  lock_player(db,transfer.player_id)
  if transfer.state in ('settled','failed'):return dict(id=transfer.id,state=transfer.state,txid=transfer.txid)
  asset=db.get(RGBAsset,transfer.asset_id)
  if asset.player_id!=transfer.player_id or asset.ownership!='withdrawal_pending':raise RGBError('Custodial reservation not found')
  transfer.state='signing';db.commit()
  try:
   result=wallet.send(transfer.asset_id,transfer.recipient,'withdrawal-'+transfer.id)
  except Exception as exc:
   transfer.state='recovery_required';transfer.error_code=type(exc).__name__;db.commit()
   raise RGBError('Withdrawal held for recovery; inspect operator wallet journal') from None
  transfer.txid=result.get('txid');transfer.batch_idx=result.get('batch_idx');transfer.state='waiting_counterparty';transfer.error_code=None;db.commit()
  return reconcile_transfer(engine,wallet,transfer_id)

def reconcile_transfer(engine,wallet,transfer_id):
 with Session(engine) as db:
  transfer=db.get(RGBTransfer,transfer_id)
  if not transfer:raise RGBError('Withdrawal not found')
  lock_player(db,transfer.player_id)
  matches=[t for t in wallet.refresh(transfer.asset_id) if t['batch_idx']==transfer.batch_idx]
  if not matches:raise RGBError('SDK transfer not found; reservation retained')
  observed=matches[0]
  transfer.state=observed['state'].lower();transfer.txid=observed['txid']
  asset=db.get(RGBAsset,transfer.asset_id)
  if observed['state']=='SETTLED':asset.ownership='withdrawn'
  elif observed['state']=='FAILED':
   # A failed status alone does not release custody: check restored spendable allocation.
   balance=wallet.balance(transfer.asset_id)
   asset.ownership='verified_custody' if balance['settled']==1 and balance['spendable']==1 else 'pending_verification'
  db.commit();return dict(id=transfer.id,state=transfer.state,txid=transfer.txid,ownership=asset.ownership,mode='real')
