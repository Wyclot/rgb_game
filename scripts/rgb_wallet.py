#!/usr/bin/env python3
"""Local operator wallet. No API endpoint accepts wallet secrets."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.app.rgb.service import RealRGB
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--wallet',default='.state/issuer')
s=p.add_subparsers(dest='command',required=True)
s.add_parser('address');s.add_parser('prepare');s.add_parser('assets');s.add_parser('refresh')
issue=s.add_parser('issue');issue.add_argument('category',choices=['NIA','UDA']);issue.add_argument('--key',required=True);issue.add_argument('--media')
recv=s.add_parser('receive');recv.add_argument('--category',choices=['NIA','UDA'],default='UDA');recv.add_argument('--asset');recv.add_argument('--amount',type=int,default=1)
send=s.add_parser('send');send.add_argument('--asset',required=True);send.add_argument('--invoice-file',required=True);send.add_argument('--key',required=True)
a=p.parse_args()
with RealRGB(a.wallet) as w:
 if a.command=='address':result={'network':'regtest','address':w.address()}
 elif a.command=='prepare':result={'created_utxos':w.create_utxos()}
 elif a.command=='assets':result={'mode':'real','assets':w.assets()}
 elif a.command=='refresh':result={'mode':'real','transfers':w.refresh()}
 elif a.command=='issue':result=w.issue(a.category,a.key,a.media)
 elif a.command=='receive':result=w.receive(a.category,a.asset,a.amount)
 elif a.command=='send':
  raw=Path(a.invoice_file).read_text().strip()
  invoice=json.loads(raw)['invoice'] if raw.startswith('{') else raw
  result=w.send(a.asset,invoice,a.key)
 print(json.dumps(result,indent=2))
