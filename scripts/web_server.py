"""Loopback-only static game server and same-origin proxy to RuneForge's real API.
Never serves repository files, wallet files, profile credentials or arbitrary URLs.
"""
import argparse,errno,http.client,json,mimetypes,urllib.request
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlsplit,unquote
ROOT=Path(__file__).resolve().parents[1]
class Server(ThreadingHTTPServer):daemon_threads=True
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*_):pass  # Never log bearer credentials or bodies.
 def reply(self,status,data,kind='application/json'):
  self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(data)))
  self.send_header('X-Content-Type-Options','nosniff');self.send_header('Cache-Control','no-store');self.end_headers()
  if self.command!='HEAD':
   try:self.wfile.write(data)
   except (BrokenPipeError,ConnectionResetError):pass
 def run_request(self):
  path=unquote(urlsplit(self.path).path)
  if path=='/health' or path.startswith('/api/'):
   origin=self.headers.get('Origin')
   if origin and origin!=f'http://{self.headers.get("Host")}':return self.reply(403,b'{"detail":"Origin mismatch"}')
   try:
    size=int(self.headers.get('Content-Length','0'))
    if size<0 or size>65536:return self.reply(413,b'{"detail":"Request too large"}')
    headers={k:self.headers[k] for k in ('Authorization','Content-Type') if self.headers.get(k)}
    conn=http.client.HTTPConnection('127.0.0.1',self.server.backend_port,timeout=8)
    try:
     conn.request(self.command,self.path,body=self.rfile.read(size) if size else None,headers=headers)
     response=conn.getresponse();data=response.read()
     return self.reply(response.status,data,response.getheader('Content-Type','application/json'))
    finally:conn.close()
   except (OSError,ValueError,http.client.HTTPException):return self.reply(503,b'{"detail":"RuneForge backend offline. No simulated RGB operations."}')
  if self.command not in ('GET','HEAD'):return self.reply(405,b'{}')
  if path=='/runtime-config.json':return self.reply(200,json.dumps({'variant':self.server.variant,'qa':self.server.qa}).encode())
  root=self.server.public
  if path.startswith('/assets/'):
   root=ROOT/'game/assets';relative=path.removeprefix('/assets/')
  else:relative=path.lstrip('/') or 'index.html'
  target=(root/relative).resolve()
  if not target.is_relative_to(root.resolve()) or not target.is_file() or target.suffix not in ('.html','.css','.js','.json','.png','.wav','.wasm','.pck','.svg','.ico'):
   return self.reply(404,b'{}')
  return self.reply(200,target.read_bytes(),mimetypes.guess_type(target)[0] or 'application/octet-stream')
 do_GET=do_HEAD=do_POST=do_DELETE=run_request

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--port',type=int);parser.add_argument('--backend-port',type=int,default=8787);parser.add_argument('--qa',action='store_true');args=parser.parse_args()
 variant='WebAssembly' if (ROOT/'web/dist/index.wasm').exists() else 'JavaScript'
 public=ROOT/('web/dist' if variant=='WebAssembly' else 'web')
 port=args.port or (8081 if variant=='WebAssembly' else 8082)
 try:server=Server(('127.0.0.1',port),Handler)
 except OSError as exc:
  if exc.errno!=errno.EADDRINUSE:raise
  try:
   with urllib.request.urlopen(f'http://127.0.0.1:{port}/runtime-config.json',timeout=2) as response:current=json.load(response)
  except Exception:raise SystemExit(f'Port {port} belongs to another service; select --port.') from None
  if current!={'variant':variant,'qa':args.qa}:raise SystemExit(f'Port {port} has a different RuneForge variant or QA mode; select --port.')
  print(f'RuneForge {variant} already running: http://127.0.0.1:{port}',flush=True);return
 server.backend_port=args.backend_port;server.public=public;server.variant=variant;server.qa=args.qa
 print(f'RuneForge {variant}: http://127.0.0.1:{server.server_port} (real API :{args.backend_port})',flush=True)
 try:server.serve_forever()
 except KeyboardInterrupt:pass
 finally:server.server_close()
if __name__=='__main__':main()
