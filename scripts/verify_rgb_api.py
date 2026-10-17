"""Verify the installed binding, not an assumed API from another RGB version."""
import inspect,json
from importlib.metadata import version
from pathlib import Path
import rgb_lib as r
assert version('rgb-lib')=='0.3.0b7'
required={
 'go_online':['online_options'],
 'issue_asset_nia':['ticker','name','precision','amounts'],
 'issue_asset_uda':['ticker','name','details','precision','media_file_path','attachments_file_paths'],
 'blind_receive':['asset_id','assignment','expiration_timestamp','transport_endpoints','min_confirmations'],
 'send':['online','recipient_map','donation','fee_rate','min_confirmations','expiration_timestamp'],
 'list_transfers':['asset_id'],
 'refresh':['online','asset_id','filter','skip_sync'],
}
result={}
for name,args in required.items():
 sig=inspect.signature(getattr(r.Wallet,name));assert list(sig.parameters)==['self']+args,(name,str(sig));result[name]=str(sig)
assert list(inspect.signature(r.OnlineOptions).parameters)==['indexer_url','skip_consistency_check','vanilla_sync_lookback']
for name in ('blind_receive','send'):assert inspect.signature(getattr(r.Wallet,name)).parameters['expiration_timestamp'].default is inspect.Parameter.empty
print(json.dumps({'package':'rgb-lib','version':version('rgb-lib'),'signatures':result},indent=2))
