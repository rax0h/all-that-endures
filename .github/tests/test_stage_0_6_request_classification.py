"""Execute the real workflow detector; invalid ancestry must fail closed."""
import os
from pathlib import Path
import subprocess

import pytest
import yaml


@pytest.mark.parametrize('change', ['engine', 'harness', 'gate_workflow', 'proof_script', 'legacy_request', 'unchanged', 'zero', 'missing'])
def test_real_request_detector_distinguishes_cost_and_refuses_unknown_base(tmp_path, change):
    root=Path(__file__).resolve().parents[2]
    workflow=yaml.safe_load((root/'.github/workflows/stage-0-5-proof-map-validation.yml').read_text())
    script=next(s['run'] for s in workflow['jobs']['mature-genesis-request']['steps'] if s.get('id')=='request')
    def git(*args):
        return subprocess.check_output(['git',*args],cwd=tmp_path,text=True,stderr=subprocess.DEVNULL).strip()
    git('init');git('config','user.email','fixture@example.invalid');git('config','user.name','Fixture')
    (tmp_path/'seed').write_text('fixture\n');git('add','.');git('commit','-m','base')
    before=git('rev-parse','HEAD')
    if change in ('engine','harness','gate_workflow','proof_script','legacy_request'):
        target=tmp_path/{'engine':'simulation/ate_sim/module.py','harness':'.github/tests/test_helper.py',
            'gate_workflow':'.github/workflows/stage-0-5-proof-map-validation.yml',
            'proof_script':'.github/tests/run_proof_fixture.py',
            'legacy_request':'simulation/stage_0_6_proof_genesis_request.json'}[change]
        target.parent.mkdir(parents=True);target.write_text('value=1\n')
        git('add','.');git('commit','-m',change)
    if change in ('zero','missing'):before=('0' if change=='zero' else 'f')*40
    output=tmp_path/'outputs';output.touch()
    run=subprocess.run(['bash','-e','-o','pipefail','-c',script],cwd=tmp_path,
        env=dict(os.environ,BEFORE=before,GITHUB_SHA=git('rev-parse','HEAD'),GITHUB_OUTPUT=str(output)),
        capture_output=True,text=True,timeout=10)
    if change in ('zero','missing'):
        assert run.returncode!=0
        assert output.read_text()==''
    else:
        assert run.returncode==0,run.stderr
        values=dict(line.split('=',1) for line in output.read_text().splitlines())
        assert values==dict(engine_changed='true' if change=='engine' else 'false',
            proof_changed='true' if change=='proof_script' else 'false',
            enabled='true' if change=='legacy_request' else 'false')
