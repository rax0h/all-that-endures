import importlib.util
import json
import subprocess
import sys
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location('real_year_probe', Path(__file__).with_name('run_proof_real_year_probe.py'))
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


@pytest.mark.parametrize('exc', [subprocess.CalledProcessError(7, ['python'], output='partial', stderr='child traceback'),
    subprocess.TimeoutExpired(['python'], 1, output=b'partial', stderr=b'child timed out')])
def test_failed_child_evidence_survives_json_serialization(exc):
    result = json.loads(json.dumps(probe.failure_details(exc)))
    assert result['stdout'] == 'partial'
    assert result['stderr'].startswith('child')
    assert 'returncode' in result or 'timeout' in result


def test_restore_mismatch_preserves_actual_digest():
    with pytest.raises(ValueError) as caught:
        probe.check_restored('[3,"actual"]', 'expected')
    assert probe.failure_details(caught.value)['actual'] == [3, 'actual']


def test_restore_accepts_exact_eager_control():
    probe.check_restored('[3,"expected"]', 'expected')


@pytest.mark.parametrize('rank,proof_only', [(False,True),(True,1),(1,False),(False,None)])
def test_invalid_opening_mode_rejects_before_output_creation(tmp_path,rank,proof_only):
    output=tmp_path/'evidence'
    with pytest.raises(ValueError):
        probe.run(output,rank_proofs=rank,proof_only=proof_only)
    assert not output.exists()


def test_cli_proof_only_requires_rank_authority(tmp_path):
    output=tmp_path/'evidence'
    result=subprocess.run([sys.executable,str(Path(probe.__file__)),'--output',str(output),
        '--proof-only'],capture_output=True,text=True)
    assert result.returncode==2
    assert '--proof-only requires --rank-proofs' in result.stderr
    assert not output.exists()


def test_fresh_child_rejects_nonboolean_mode_before_io(tmp_path):
    with pytest.raises(ValueError,match='proof_only must be boolean'):
        probe.restore_in_fresh_process(tmp_path/'absent.sqlite','rules',b'0'*32,'expected',proof_only=1)


@pytest.mark.parametrize('proof_only',[False,True])
def test_fresh_child_uses_actual_selected_opener_and_audit_counter(tmp_path,proof_only):
    from simulation.tests.test_stage_0_6_proof_open import ranked_fixture,opened,RULES
    path,pair=ranked_fixture(tmp_path,size=4,configure=lambda w:setattr(w,'year',3))
    with opened(path,pair) as session:expected=session.world.digest()
    result=probe.restore_in_fresh_process(path,RULES,pair[1],expected,proof_only=proof_only)
    assert result['state']==[3,expected]
    assert result['opener']==('open_proof_world_session' if proof_only else 'open_audited_proof_world_session')
    if proof_only:assert result['world_audit_calls']==0
    else:assert result['world_audit_calls']>0


def test_fresh_proof_child_cannot_silently_audit_six_root_snapshot(tmp_path):
    from simulation.tests.test_stage_0_5_proof_world_session import fixture,opened
    path,pair=fixture(tmp_path,size=4,configure=lambda w:setattr(w,'year',3))
    with opened(path,pair) as session:expected=session.world.digest()
    with pytest.raises(subprocess.CalledProcessError) as caught:
        probe.restore_in_fresh_process(path,'private-catalog-copy',pair[1],expected,proof_only=True)
    assert 'proof opening requires complete seven-root scope certification' in caught.value.stderr
