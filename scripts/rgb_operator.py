"""Issue only server-earned relics or process previously authenticated withdrawals."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.app.database import make_engine
from backend.app.rgb.service import RealRGB
from backend.app.services.operator import mint_reward, process_transfer, reconcile_transfer
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--wallet',default='.state/issuer')
s=p.add_subparsers(dest='cmd',required=True)
m=s.add_parser('mint-reward');m.add_argument('inventory_id');m.add_argument('--media',default='game/assets/legendary.png')
t=s.add_parser('process-transfer');t.add_argument('transfer_id')
r=s.add_parser('reconcile');r.add_argument('transfer_id')
a=p.parse_args()
with RealRGB(a.wallet) as wallet:
 engine=make_engine()
 if a.cmd=='mint-reward':result=mint_reward(engine,wallet,a.inventory_id,a.media)
 elif a.cmd=='process-transfer':result=process_transfer(engine,wallet,a.transfer_id)
 else:result=reconcile_transfer(engine,wallet,a.transfer_id)
 print(json.dumps(result,indent=2))
