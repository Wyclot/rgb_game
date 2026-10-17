import inspect,json,sqlite3,time
from pathlib import Path
import pytest
from backend.app.rgb.service import RealRGB,MockRGB,RGBError,RecoveryRequired,local_endpoint

def test_mock_never_claims_chain_success():
 m=MockRGB()
 assert m.issue('UDA','test')['asset_id'].startswith('mock:')
 assert m.send('x','y','z')['txid'] is None
 assert m.receive()['invoice'] is None
 assert m.issue('UDA','test')['ownership']=='pending_verification'

def test_only_local_endpoints():
 assert local_endpoint('tcp://127.0.0.1:51001',('tcp',))
 for value in ['tcp://mainnet.example:50001','ssl://localhost:50001','tcp://evil.localhost:123']:
  with pytest.raises(RGBError):local_endpoint(value,('tcp',))

def test_exact_pinned_binding_signatures():
 r=pytest.importorskip('rgb_lib')
 from importlib.metadata import version
 assert version('rgb-lib')=='0.3.0b7'
 assert list(inspect.signature(r.Wallet.go_online).parameters)==['self','online_options']
 for name in ['blind_receive','send']:
  assert inspect.signature(getattr(r.Wallet,name)).parameters['expiration_timestamp'].default is inspect.Parameter.empty

def test_real_wallet_keys_private_and_lock(tmp_path):
 pytest.importorskip('rgb_lib')
 with RealRGB(tmp_path/'wallet') as wallet:
  assert wallet.address().startswith('bcrt1')
  assert (tmp_path/'wallet/mnemonic.txt').stat().st_mode & 0o777==0o600
  with pytest.raises(RGBError,match='already open'):RealRGB(tmp_path/'wallet')

@pytest.fixture
def journal(tmp_path):
 # Exercise persistent intent logic without pretending the stub is a real wallet.
 service=RealRGB.__new__(RealRGB)
 service.journal=sqlite3.connect(tmp_path/'journal.sqlite');service.journal.row_factory=sqlite3.Row
 service.journal.execute('CREATE TABLE operations (key TEXT PRIMARY KEY,intent TEXT,state TEXT,result TEXT,started INTEGER)')
 yield service
 service.journal.close()

def test_intent_journal_conflict_and_reopen(journal):
 assert journal.reserve('once',{'operation':'send','asset':'a'}) is None
 journal.finish('once',{'txid':None,'state':'test-only'})
 path=journal.journal.execute('PRAGMA database_list').fetchone()[2]
 journal.journal.close()
 journal.journal=sqlite3.connect(path);journal.journal.row_factory=sqlite3.Row
 assert json.loads(journal.reserve('once',{'asset':'a','operation':'send'})['result'])['state']=='test-only'
 with pytest.raises(RGBError):journal.reserve('once',{'operation':'send','asset':'b'})

def test_ambiguous_issue_never_reissues(journal):
 journal.reserve('ambiguous',{'operation':'issue','category':'UDA','media_sha256':None})
 journal.assets=lambda:[]
 with pytest.raises(RecoveryRequired):journal.issue('UDA','ambiguous')

def test_interrupted_send_reconciles_without_resigning(journal):
 from types import SimpleNamespace
 data=SimpleNamespace(network='regtest',asset_id='asset',recipient_id='receiver',expiration_timestamp=0)
 journal.r=SimpleNamespace(Invoice=lambda _:SimpleNamespace(invoice_data=lambda:data),BitcoinNetwork=SimpleNamespace(REGTEST='regtest'))
 intent=dict(operation='send',asset_id='asset',recipient='receiver',invoice='test-invoice')
 journal.reserve('recover-send',intent)
 transfer=SimpleNamespace(idx=1,batch_transfer_idx=2,status=SimpleNamespace(name='WAITING_CONFIRMATIONS'),txid='test-fixture-only',recipient_id='receiver',created_at=int(time.time()))
 journal.wallet=SimpleNamespace(list_transfers=lambda _: [transfer])
 result=journal.send('asset','test-invoice','recover-send')
 assert result['state']=='WAITING_CONFIRMATIONS'
 # A completed journal replay works after invoice expiry, without querying or signing.
 journal.wallet=SimpleNamespace()
 assert journal.send('asset','test-invoice','recover-send')==result


def test_interrupted_send_keeps_unknown_outcome_reserved(journal):
 from types import SimpleNamespace
 data=SimpleNamespace(network='regtest',asset_id='asset',recipient_id='receiver',expiration_timestamp=0)
 journal.r=SimpleNamespace(Invoice=lambda _:SimpleNamespace(invoice_data=lambda:data),BitcoinNetwork=SimpleNamespace(REGTEST='regtest'))
 journal.reserve('unknown-send',dict(operation='send',asset_id='asset',recipient='receiver',invoice='test-invoice'))
 journal.wallet=SimpleNamespace(list_transfers=lambda _: [])
 with pytest.raises(RecoveryRequired):journal.send('asset','test-invoice','unknown-send')
 assert journal.journal.execute('SELECT state FROM operations WHERE key=?',('unknown-send',)).fetchone()['state']=='started'
