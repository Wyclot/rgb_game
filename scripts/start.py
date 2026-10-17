"""Persistent local stack; repeat launch preserves chain, wallets, profiles and database."""
import argparse,fcntl,hashlib,json,os,subprocess,sys,time
from pathlib import Path
import httpx
ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT)
STATE=ROOT/'.state';STATE.mkdir(exist_ok=True,mode=0o700)
DB='postgresql+psycopg://runeforge:runeforge_local_only@127.0.0.1:55432/runeforge'
ENV=dict(os.environ,DATABASE_URL=DB,RGB_MODE='real',RUNEFORGE_API_URL='http://127.0.0.1:8787')
ENV.pop('RUNEFORGE_FAULT',None)

def running(pid,marker):
 if not pid:return False
 r=subprocess.run(['ps','-p',str(pid),'-o','command='],capture_output=True,text=True)
 return r.returncode==0 and marker in r.stdout

def spawn(name,args):
 log=open(STATE/(name+'.log'),'a')
 p=subprocess.Popen(args,cwd=ROOT,env=ENV,stdout=log,stderr=log,start_new_session=True);log.close();return p.pid

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--no-game',action='store_true');parser.add_argument('--profile',choices=['A','B']);args=parser.parse_args()
 lock=open(STATE/'launcher.lock','a+');fcntl.flock(lock,fcntl.LOCK_EX)
 subprocess.run(['docker','compose','--profile','rgb','up','-d','postgres','bitcoind','electrs','proxy'],check=True)
 for _ in range(60):
  check=subprocess.run(['docker','compose','exec','-T','postgres','pg_isready','-U','runeforge'],capture_output=True)
  if check.returncode==0:break
  time.sleep(.5)
 subprocess.run([sys.executable,'-m','alembic','-c','backend/alembic.ini','upgrade','head'],env=ENV,check=True)
 statefile=STATE/'processes.json';state=json.loads(statefile.read_text()) if statefile.exists() else {}
 digest=hashlib.sha256(b''.join(p.read_bytes() for p in sorted((ROOT/'backend/app').rglob('*.py')))).hexdigest()
 changed=state.get('digest')!=digest
 for name,marker,command in [('api','uvicorn backend.app.main:app',[sys.executable,'-m','uvicorn','backend.app.main:app','--host','127.0.0.1','--port','8787','--no-access-log']),('worker','backend.app.services.worker',[sys.executable,'-m','backend.app.services.worker'])]:
  pid=state.get(name)
  if running(pid,marker) and changed:
   os.kill(pid,15)
   for _ in range(60):
    if not running(pid,marker):break
    time.sleep(.2)
   if running(pid,marker):raise RuntimeError(name+' did not stop; no duplicate process started')
  if not running(pid,marker):
   if name=='api':
    try:response=httpx.get(ENV['RUNEFORGE_API_URL']+'/health',timeout=1)
    except httpx.TransportError:response=None
    if response is not None:raise RuntimeError('Port 8787 already has an unmanaged service. Stop that RuneForge API before launching.')
   if name=='worker':
    walletlock=open(ROOT/'.state/managed-v2/worker.lock','a+') if (ROOT/'.state/managed-v2').exists() else None
    if walletlock:
     try:fcntl.flock(walletlock,fcntl.LOCK_EX|fcntl.LOCK_NB)
     except BlockingIOError:raise RuntimeError('A manually launched RuneForge worker is running; stop it before using the launcher') from None
     finally:walletlock.close()
   state[name]=spawn(name,command)
  state['digest']=digest
  statefile.write_text(json.dumps(state));statefile.chmod(0o600)
 for _ in range(60):
  try:
   if httpx.get(ENV['RUNEFORGE_API_URL']+'/health',timeout=1).json().get('application')=='runeforge-managed-v2':break
  except (httpx.TransportError,ValueError):pass
  time.sleep(.3)
 else:raise RuntimeError('API failed to start; see .state/api.log')
 print('RuneForge: real regtest infrastructure, API :8787 and managed wallet worker are running.',flush=True)
 if not args.no_game:
  gamepid=state.get('game')
  if not running(gamepid,'--path game'):
   cmd=[str(ROOT/'scripts/play.sh')]
   if args.profile:cmd+=['--','--profile='+args.profile]
   state['game']=spawn('game',cmd);statefile.write_text(json.dumps(state))
  print('Game launched. Begin/Continue → R → Испытание. Switch Игрок A / Игрок B in the item screen.',flush=True)
 lock.close()
if __name__=='__main__':main()
