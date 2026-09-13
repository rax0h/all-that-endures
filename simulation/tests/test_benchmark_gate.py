import json
import pytest
from run_long_history import main


def test_benchmark_gate_reports_failure_and_success(monkeypatch,capsys):
    monkeypatch.delenv('ATE_PROFILE_TAIL',raising=False)
    with pytest.raises(SystemExit,match='exceeded'):
        main(17,1,max_seconds=1e-12)
    failed=json.loads(capsys.readouterr().out.splitlines()[-1])
    assert failed['performance_passed'] is False
    assert failed['simulation_seconds']>failed['max_seconds']
    main(17,1,max_seconds=120)
    passed=json.loads(capsys.readouterr().out.splitlines()[-1])
    assert passed['performance_passed'] is True
    assert passed['digest']==failed['digest']


def test_gate_rejects_profiled_measurement(monkeypatch):
    monkeypatch.setenv('ATE_PROFILE_TAIL','10')
    with pytest.raises(ValueError,match='unprofiled'):
        main(17,1,max_seconds=120)
