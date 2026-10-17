"""Player-facing managed item API. No client-supplied contract can establish ownership."""
import time
from typing import Literal
from fastapi import Depends, HTTPException
from pydantic import BaseModel,ConfigDict,Field
from sqlalchemy import select,or_,delete
from ..models import (Player,ManagedWallet,ItemInstance,ItemOperation,ItemEvent,WorkerState,
                      RelicEquipment,Item,GameSession,InventoryEntry,LootReward)

LEASE_SECONDS=4.0
VERIFY_SECONDS=8.0
HEARTBEAT_SECONDS=8.0

class TransferRequest(BaseModel):
 model_config=ConfigDict(extra='forbid')
 recipient_id:str=Field(min_length=36,max_length=36)
 idempotency_key:str=Field(min_length=8,max_length=128)
 confirm:Literal[True]

LABELS={
 'earned':'Награда заработана','issuing':'Кузнец выпускает уникальный меч',
 'preparing':'Подготавливаем получение','delivering':'Передаём меч в ваш кошелёк',
 'requested':'Предмет зарезервирован','signing':'Передача отправляется',
 'waiting_counterparty':'Получатель проверяет предмет','waiting_safe_height':'Ожидаем безопасную высоту блока',
 'waiting_broadcast':'Ожидаем публикацию транзакции','waiting_confirmations':'Ожидаем подтверждение Bitcoin',
 'waiting_receiver':'Проверяем получение в кошельке','settled':'Предмет получен','owned':'Владение подтверждено','transferring':'Предмет передаётся',
 'recovery_required':'Проверяем незавершённую операцию','verification_required':'Проверяем кошелёк',
 'failed':'Передача не завершена; владение перепроверено'
}
def service_status(db):
 row=db.get(WorkerState,'managed')
 ok=bool(row and row.available and time.time()-row.heartbeat<HEARTBEAT_SECONDS)
 return {'available':ok,'mode':'real','network':'regtest','custody':'Ключи отдельных кошельков игроков хранит локальный сервис RuneForge.',
         'message':'Кошельки подключены · Bitcoin regtest' if ok else 'Нет связи с сервисом кошельков или RGB-инфраструктурой. Предметы временно недоступны.',
         'error_code':None if ok else (row.error_code if row else 'worker_offline'),'block_height':row.block_height if row else None}

def usable(db,i,pid):
 return bool(i and i.owner_id==pid and i.asset_id and i.state=='owned' and time.time()-i.verified_at<VERIFY_SECONDS and service_status(db)['available'])

def install(app,db_session,auth,lock_player):
 def locked_instance(db,serial):
  return db.scalar(select(ItemInstance).where(ItemInstance.serial==serial).with_for_update())
 def require_ready(db):
  if not service_status(db)['available']:raise HTTPException(503,'Кошельки недоступны. Дождитесь восстановления соединения; имитация не используется.')
 @app.get('/api/relics')
 def relics(p=Depends(auth),db=Depends(db_session)):
  # The same instance row lock serializes lease renewal and transfer reservation.
  lock_player(db,p)
  if not db.get(ManagedWallet,p.id):db.add(ManagedWallet(player_id=p.id));db.flush()
  status=service_status(db)
  ops=db.scalars(select(ItemOperation).where(or_(ItemOperation.requester_id==p.id,ItemOperation.recipient_id==p.id)).order_by(ItemOperation.created_at.desc())).all()
  related={o.serial for o in ops}
  instances=db.scalars(select(ItemInstance).where(or_(ItemInstance.owner_id==p.id,ItemInstance.beneficiary_id==p.id,ItemInstance.serial.in_(related))).order_by(ItemInstance.serial.desc()).with_for_update()).all()
  eq=db.get(RelicEquipment,p.id)
  equipment=None
  items=[]
  for i in instances:
   t=db.get(Item,i.type_id);allowed=usable(db,i,p.id)
   equipped=bool(eq and eq.serial==i.serial and allowed)
   if equipped:
    # Grant an absolute expiry, bounded by the freshness of the observed SDK state.
    i.use_until=min(time.time()+LEASE_SECONDS,i.verified_at+VERIFY_SECONDS)
    equipment={'serial':i.serial,'name':t.name,'damage':t.damage,'lease_until':i.use_until,'asset_id':i.asset_id}
   items.append(dict(serial=i.serial,type_id=t.id,name=t.name,damage=t.damage,rarity=t.rarity,slot=t.slot,description=t.description,
    asset_id=i.asset_id,state=i.state,status=LABELS.get(i.state,i.state),owner_id=i.owner_id,is_owner=i.owner_id==p.id,
    can_equip=allowed,equipped=equipped,revision=i.revision,verified_at=i.verified_at))
  if eq and equipment is None:db.delete(eq)
  profiles=db.scalars(select(Player).join(ManagedWallet,ManagedWallet.player_id==Player.id).where(Player.is_test==p.is_test).order_by(Player.created_at.desc()).limit(100)).all()
  history=[]
  for o in ops[:20]:
   history.append(dict(id=o.id,serial=o.serial,kind=o.kind,state=o.state,status=LABELS.get(o.state,o.state),recipient_id=o.recipient_id,
    recipient_name=db.get(Player,o.recipient_id).name,txid=o.txid,error_code=o.error_code,
    events=[{'state':e.state,'status':LABELS.get(e.state,e.state)} for e in db.scalars(select(ItemEvent).where(ItemEvent.operation_id==o.id).order_by(ItemEvent.id))]))
  last=db.scalar(select(GameSession).where(GameSession.player_id==p.id).order_by(GameSession.created_at.desc()).limit(1))
  trial={'id':last.id,**last.state} if last else None
  db.commit()
  return dict(profile={'id':p.id,'name':p.name,'is_test':p.is_test},service=status,items=items,equipment=equipment,history=history,
              players=[dict(id=q.id,name=q.name) for q in profiles if q.id!=p.id],trial=trial,server_time=time.time())
 @app.post('/api/relics/{serial}/equip')
 def equip(serial:int,p=Depends(auth),db=Depends(db_session)):
  lock_player(db,p);require_ready(db);i=locked_instance(db,serial)
  if not usable(db,i,p.id):raise HTTPException(409,'Меч не принадлежит вашему кошельку, зарезервирован или ещё проверяется.')
  eq=db.get(RelicEquipment,p.id)
  if eq:eq.serial=serial
  else:db.add(RelicEquipment(player_id=p.id,serial=serial))
  db.commit();return {'message':'Меч экипирован. Характеристики обновлены сервером.'}
 @app.delete('/api/relics/equipment')
 def unequip(p=Depends(auth),db=Depends(db_session)):
  lock_player(db,p);db.execute(delete(RelicEquipment).where(RelicEquipment.player_id==p.id));db.commit()
  return {'message':'Обычное оружие экипировано.'}
 @app.post('/api/relics/{serial}/transfer',status_code=202)
 def transfer(serial:int,body:TransferRequest,p=Depends(auth),db=Depends(db_session)):
  lock_player(db,p)
  prior=db.scalar(select(ItemOperation).where(ItemOperation.requester_id==p.id,ItemOperation.request_key==body.idempotency_key))
  if prior:
   if prior.serial!=serial or prior.recipient_id!=body.recipient_id:raise HTTPException(409,'Ключ запроса уже использован для другой передачи.')
   return {'id':prior.id,'state':prior.state,'message':LABELS.get(prior.state,prior.state)}
  require_ready(db);i=locked_instance(db,serial)
  if not usable(db,i,p.id):raise HTTPException(409,'Предмет недоступен для передачи или принадлежит другому игроку.')
  if body.recipient_id==p.id:raise HTTPException(409,'Выберите другого игрока.')
  receiver=db.get(Player,body.recipient_id)
  if not receiver or receiver.is_test!=p.is_test or not db.get(ManagedWallet,body.recipient_id):raise HTTPException(404,'Получатель недоступен. Тестовые и обычные профили разделены.')
  i.state='transferring';i.verified_at=0;i.revision+=1
  db.execute(delete(RelicEquipment).where(RelicEquipment.serial==serial))
  op=ItemOperation(serial=serial,kind='transfer',requester_id=p.id,sender_id=p.id,recipient_id=body.recipient_id,request_key=body.idempotency_key,state='requested')
  db.add(op);db.flush();db.add(ItemEvent(operation_id=op.id,state='requested'));db.commit()
  return {'id':op.id,'state':op.state,'message':'Меч снят с экипировки и зарезервирован. Передача выполняется автоматически.'}
