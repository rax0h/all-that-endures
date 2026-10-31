import importlib.util
import json
import subprocess
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
