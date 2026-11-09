import copy,json,os,subprocess,tempfile
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
from simulation import stage_0_6_proof_mature_preflight as m
root=Path('/tmp/ate-mature-preflight-review')
config=json.loads(Path('simulation/stage_0_6_proof_mature_request.json').read_text())
head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
results={}
identity=m.check_source(Path.cwd(),config,head)
results['real_source_check']=identity
class ReachedTransport(Exception):pass
for name,key,value in [('wrong_seed','seed',-1),('wrong_year','year',-1),('missing_seed','seed',None)]:
    c=copy.deepcopy(config)
    if name=='missing_seed':del c['world'][key]
    else:c['world'][key]=value
    target=root/name;target.mkdir(exist_ok=True)
    def transport(*a,**k):raise ReachedTransport('large transport reached')
    with patch.dict(os.environ,{'GITHUB_RUN_ATTEMPT':'1'}),patch.object(m.shutil,'disk_usage',return_value=SimpleNamespace(free=100*1024**3)),patch.object(m,'prepare_retained',side_effect=transport):
        try:m.launch(target,c,expected_sha=head)
        except Exception as exc:results[name]=dict(error=type(exc).__name__,message=str(exc))
for name,key,value in [('wrong_store','store_identity','other'),('wrong_head','captured_head',-1),('missing_pin','captured_head',None)]:
    c=copy.deepcopy(config)
    if name=='missing_pin':del c['pin'][key]
    else:c['pin'][key]=value
    target=root/name;target.mkdir(exist_ok=True)
    with patch.dict(os.environ,{'GITHUB_RUN_ATTEMPT':'1'}),patch.object(m.shutil,'disk_usage',return_value=SimpleNamespace(free=100*1024**3)),patch.object(m,'prepare_retained',side_effect=transport):
        try:m.launch(target,c,expected_sha=head)
        except Exception as exc:results[name]=dict(error=type(exc).__name__,message=str(exc))
(root/'request-probes.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2))
