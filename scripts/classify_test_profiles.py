"""Classify existing local test accounts using saved authenticated identities, not names.
Does not touch inventory, wallet state or asset ownership.
"""
import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sqlalchemy.orm import Session
from backend.app.database import make_engine
from backend.app.models import Player
ROOT=Path(__file__).resolve().parents[1]
USERDATA=Path.home()/'Library/Application Support/Godot/app_userdata/RuneForge — Ashes of the Covenant'
def main():
 sources=[USERDATA/'managed_test_profiles.json',*sorted((ROOT/'.state').glob('managed-e2e*-profiles.json'))]
 normal_path=USERDATA/'managed_profiles.json'
 normal_ids={p['id'] for p in json.loads(normal_path.read_text())['profiles'].values() if 'id' in p} if normal_path.exists() else set()
 matched=set()
 with Session(make_engine()) as db:
  for path in sources:
   if not path.exists():continue
   data=json.loads(path.read_text());profiles=data['profiles'].values() if isinstance(data,dict) else data
   for p in profiles:
    if 'id' not in p or 'token' not in p:continue
    assert p['id'] not in normal_ids,'Refusing to classify an ordinary local profile as test'
    row=db.get(Player,p['id'])
    if row is None:continue
    assert row.token_hash==hashlib.sha256(p['token'].encode()).hexdigest(),'Saved credential does not match profile'
    row.is_test=True;matched.add(row.id)
  db.commit()
 print('Authenticated test profiles classified:',len(matched))
if __name__=='__main__':main()
