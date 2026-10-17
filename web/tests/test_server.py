"""Static/proxy tests with a tiny HTTP fixture. Not an RGB integration test."""
import importlib.util,json,threading,unittest,urllib.request,urllib.error
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('web_server',ROOT/'scripts/web_server.py');web=importlib.util.module_from_spec(spec);spec.loader.exec_module(web)
class Upstream(BaseHTTPRequestHandler):
 def log_message(self,*_):pass
 def do_GET(self):
  body=json.dumps({'path':self.path,'authorized':self.headers.get('Authorization')=='Bearer unit-token'}).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(body)
class ProxyTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.upstream=ThreadingHTTPServer(('127.0.0.1',0),Upstream);threading.Thread(target=cls.upstream.serve_forever,daemon=True).start()
  cls.server=web.Server(('127.0.0.1',0),web.Handler);cls.server.backend_port=cls.upstream.server_port;cls.server.public=ROOT/('web/dist' if (ROOT/'web/dist/index.html').exists() else 'web');cls.server.variant='unit-test';cls.server.qa=False;threading.Thread(target=cls.server.serve_forever,daemon=True).start();cls.url=f'http://127.0.0.1:{cls.server.server_port}'
 @classmethod
 def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.upstream.shutdown();cls.upstream.server_close()
 def request(self,path,headers=None):
  try:
   with urllib.request.urlopen(urllib.request.Request(self.url+path,headers=headers or {})) as r:return r.status,r.headers,r.read()
  except urllib.error.HTTPError as e:
   try:return e.code,e.headers,e.read()
   finally:e.close()
 def test_public_assets(self):
  status,headers,body=self.request('/assets/player.png');self.assertEqual(status,200);self.assertEqual(headers['Content-Type'],'image/png');self.assertTrue(body.startswith(b'\x89PNG'))
 def test_private_files_never_served(self):
  for path in ['/../.env','/%2e%2e/.state/profiles.json','/assets/../../.env','/scripts/start.py','/.git/config']:
   self.assertEqual(self.request(path)[0],404,path)
 def test_runtime_has_no_credentials(self):
  status,_,body=self.request('/runtime-config.json');self.assertEqual(status,200);self.assertEqual(json.loads(body),{'variant':'unit-test','qa':False})
 def test_proxy_forwards_auth(self):
  status,_,body=self.request('/api/relics',{'Authorization':'Bearer unit-token'});self.assertEqual(status,200);self.assertEqual(json.loads(body),{'path':'/api/relics','authorized':True})
 def test_cross_origin_rejected(self):self.assertEqual(self.request('/api/relics',{'Origin':'https://untrusted.example'})[0],403)
 def test_offline_reports_503(self):
  old=self.server.backend_port;self.server.backend_port=1
  try:self.assertEqual(self.request('/api/relics')[0],503)
  finally:self.server.backend_port=old
if __name__=='__main__':unittest.main()
