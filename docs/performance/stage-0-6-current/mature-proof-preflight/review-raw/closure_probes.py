"""Same-seat R1 closure, actual source fence and actual original metadata."""
import copy,json,os,subprocess
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
from simulation import stage_0_6_proof_mature_preflight as m
from simulation import construction_mature_continuation_stages as stages
out=Path('/tmp/ate-mature-preflight-review')
config=m.r.load_receipt('simulation/stage_0_6_proof_mature_request.json')
head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
assert head=='cf3ed0d875bd0b97eeb107d29cc5f108425c0a84'
original=m.r.load_receipt(m.ORIGINAL_LAUNCH);authority=stages.mature_authority()
expected_world=dict(seed=authority.source_config['seed'],year=original['expected_previous_year'])
expected_pin=dict(store_identity=authority.store_identity,captured_head=original['expected_previous_generation'])
assert m.r.same(config['world'],expected_world) and m.r.same(config['pin'],expected_pin)
results=dict(head=head,real_source_check=m.check_source(Path.cwd(),config,head),expected_world=expected_world,expected_pin=expected_pin,cases={})
class ReachedTransport(Exception):pass
cases={
 'wrong_seed':lambda c:c['world'].__setitem__('seed',-1),
 'wrong_year':lambda c:c['world'].__setitem__('year',-1),
 'wrong_store':lambda c:c['pin'].__setitem__('store_identity','other'),
 'wrong_head':lambda c:c['pin'].__setitem__('captured_head',-1),
 'missing_seed':lambda c:c['world'].__delitem__('seed'),
 'missing_head':lambda c:c['pin'].__delitem__('captured_head'),
 'missing_world':lambda c:c.__delitem__('world'),
 'missing_pin':lambda c:c.__delitem__('pin'),
 'extra_world':lambda c:c['world'].__setitem__('extra',1),
 'extra_pin':lambda c:c['pin'].__setitem__('extra',1),
 'float_seed':lambda c:c['world'].__setitem__('seed',float(c['world']['seed'])),
 'float_year':lambda c:c['world'].__setitem__('year',float(c['world']['year'])),
 'float_head':lambda c:c['pin'].__setitem__('captured_head',float(c['pin']['captured_head'])),
 'bool_seed':lambda c:c['world'].__setitem__('seed',True),
 'bool_head':lambda c:c['pin'].__setitem__('captured_head',True),
}
for name,mutate in cases.items():
    c=copy.deepcopy(config);mutate(c);root=out/('closure-'+name);root.mkdir(exist_ok=True);calls=[]
    def transport(*a,**k):calls.append(True);raise ReachedTransport('large transport reached')
    with patch.dict(os.environ,{'GITHUB_RUN_ATTEMPT':'1'}),patch.object(m.shutil,'disk_usage',return_value=SimpleNamespace(free=100*1024**3)),patch.object(m,'prepare_retained',side_effect=transport):
        try:m.launch(root,c,expected_sha=head)
        except ValueError as exc:
            assert 'world/pin' in str(exc),(name,str(exc))
            assert not calls,name
            receipt=m.r.load_receipt(root/'evidence/launch-error.json')
            assert receipt['status']=='error' and receipt['acceptance']=='not-run'
            results['cases'][name]=dict(status='rejected-before-transport',error=str(exc),transport_calls=len(calls))
        else:raise AssertionError(name+' accepted')
valid_root=out/'closure-valid';valid_root.mkdir(exist_ok=True);calls=[]
def valid_transport(*args,**kwargs):
    calls.append(True)
    assert args[-1] is authority
    assert args[-2]==original['candidate_database']
    assert args[3].to_dict()==original['inputs']['candidate']
    assert args[4].to_dict()==original['inputs']['previous']
    raise ReachedTransport('valid request reaches unchanged transport')
with patch.dict(os.environ,{'GITHUB_RUN_ATTEMPT':'1'}),patch.object(m.shutil,'disk_usage',return_value=SimpleNamespace(free=100*1024**3)),patch.object(stages,'mature_authority',return_value=authority),patch.object(m,'prepare_retained',side_effect=valid_transport):
    try:m.launch(valid_root,config,expected_sha=head)
    except ReachedTransport as exc:results['valid_control']=dict(status='reached-transport',transport_calls=len(calls),same_original_authority=True)
    else:raise AssertionError('valid control did not reach transport')
assert len(calls)==1
(out/'closure-probes.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(dict(rejected_cases=len(results['cases']),valid_control=results['valid_control'],head=head)))
