"""Reproducible Godot 4.4.1 single-threaded WASM export using official templates."""
import hashlib,json,os,shutil,subprocess,urllib.request,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
COMMON=Path(subprocess.check_output(['git','rev-parse','--git-common-dir'],cwd=ROOT,text=True).strip())
if not COMMON.is_absolute():COMMON=ROOT/COMMON
SHARED=COMMON.resolve().parent
cache=SHARED/'.state/web-tools';cache.mkdir(parents=True,exist_ok=True)
archive=cache/'export_templates.tpz'
url='https://github.com/godotengine/godot-builds/releases/download/4.4.1-stable/Godot_v4.4.1-stable_export_templates.tpz'
if not archive.exists():
 print('Downloading official Godot 4.4.1 export templates (~1.15 GiB)…',flush=True)
 urllib.request.urlretrieve(url,archive.with_suffix('.part'));archive.with_suffix('.part').replace(archive)
target=ROOT/'.state/web-templates';target.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(archive) as z:
 for variant in ['debug','release']:
  (target/f'web_{variant}.zip').write_bytes(z.read(f'templates/web_nothreads_{variant}.zip'))
engine=os.getenv('GODOT_BIN') or str(SHARED/'tools/godot/Godot.app/Contents/MacOS/Godot')
if not Path(engine).exists():engine=shutil.which('godot') or shutil.which('godot4') or ''
if not engine:raise SystemExit('Install Godot 4.4.1 or set GODOT_BIN')
version=subprocess.check_output([engine,'--version'],text=True).strip()
if not version.startswith('4.4.1.'):raise SystemExit('Expected Godot 4.4.1, got '+version)
out=ROOT/'web/dist';out.mkdir(parents=True,exist_ok=True)
subprocess.run([engine,'--headless','--path',str(ROOT/'game'),'--editor','--import','--quit'],check=True)
subprocess.run([engine,'--headless','--path',str(ROOT/'game'),'--export-release','Web',str(out/'index.html')],check=True)
assert (out/'index.wasm').read_bytes()[:4]==b'\0asm'
(out/'build.json').write_text(json.dumps({'engine':version,'template_url':url,'threaded':False,'wasm_sha256':hashlib.sha256((out/'index.wasm').read_bytes()).hexdigest(),'wasm_bytes':(out/'index.wasm').stat().st_size},indent=2)+'\n')
print('WASM export ready:',out,flush=True)
