"""Called inside the same locked transaction as authoritative victory."""
from sqlalchemy import select
from ..models import LootReward,InventoryEntry,ItemInstance,ItemOperation,ItemEvent,ManagedWallet

def ensure_reward(db,player_id,session_id,key):
 reward=db.scalar(select(LootReward).where(LootReward.session_id==session_id))
 if reward is None:
  entry=InventoryEntry(player_id=player_id,item_id='oath_relic',source_session=session_id)
  db.add(entry);db.flush()
  reward=LootReward(player_id=player_id,session_id=session_id,idempotency_key=key,inventory_id=entry.id)
  db.add(reward);db.flush()
 instance=db.scalar(select(ItemInstance).where(ItemInstance.reward_id==reward.id))
 if instance is None:
  entry=db.get(InventoryEntry,reward.inventory_id)
  # Preserve legacy manually issued/withdrawn contracts; never reissue their rewards.
  if entry.rgb_asset_id:return reward,None
  if not db.get(ManagedWallet,player_id):db.add(ManagedWallet(player_id=player_id))
  instance=ItemInstance(type_id='oath_relic',reward_id=reward.id,beneficiary_id=player_id,state='earned')
  db.add(instance);db.flush()
  op=ItemOperation(serial=instance.serial,kind='award',requester_id=player_id,recipient_id=player_id,request_key='award-'+reward.id,state='earned')
  db.add(op);db.flush();db.add(ItemEvent(operation_id=op.id,state='earned'))
 return reward,instance
