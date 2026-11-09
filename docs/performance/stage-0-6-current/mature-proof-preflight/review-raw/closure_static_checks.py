import ast,hashlib,json,subprocess,yaml
from pathlib import Path
root=Path.cwd();out=Path('/tmp/ate-mature-preflight-review')
c=json.loads(Path('simulation/stage_0_6_proof_mature_request.json').read_text())
workflow=Path('.github/workflows/stage-0-6-proof-mature-preflight.yml');w=yaml.safe_load(workflow.read_text())
assert 'on' in w and set(w['on'])=={'push','workflow_dispatch'}
assert w['on']['push']['paths']==['simulation/stage_0_6_proof_mature_request.json']
assert w['jobs']['inventory']['timeout-minutes']==45
blocks=[]
for i,step in enumerate(w['jobs']['inventory']['steps']):
    if 'run' not in step:continue
    b=out/f'workflow-step-{i}.sh';b.write_text(step['run']+'\n')
    p=subprocess.run(['bash','-n',str(b)],text=True,capture_output=True)
    assert p.returncode==0,p.stderr
    blocks.append(str(b))
for p in (Path('simulation/stage_0_6_proof_mature_preflight.py'),Path('.github/tests/test_stage_0_6_proof_mature_preflight.py')):ast.parse(p.read_text())
fingerprints={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in c['fingerprints']}
assert fingerprints==c['fingerprints']
diff=subprocess.check_output(['git','diff','--name-only','b9196f9885fed0323c473bcc148f6b9dad9da9eb','cf3ed0d875bd0b97eeb107d29cc5f108425c0a84'],text=True).splitlines()
assert not any(p.startswith('simulation/ate_sim/') for p in diff)
report=dict(ast='pass',yaml='pass',bash_blocks=len(blocks),request_fingerprints=fingerprints,changed_paths=diff,head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),base='b9196f9885fed0323c473bcc148f6b9dad9da9eb',candidate='cf3ed0d875bd0b97eeb107d29cc5f108425c0a84',runtime_tree=subprocess.check_output(['git','rev-parse','HEAD:simulation/ate_sim'],text=True).strip(),status=subprocess.check_output(['git','status','--porcelain'],text=True))
(out/'closure-static-checks.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ('ast','yaml','bash_blocks','head','runtime_tree','status')}))
