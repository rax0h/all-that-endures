"""Adversarial writes between postcommit audit and final native acknowledgement."""
import sqlite3

import pytest

from ate_sim.incremental_store import StoreError
from simulation.tests.test_stage_0_5_proof_world_session import fixture, opened


@pytest.mark.parametrize('corrupt', [False, True])
def test_external_write_after_verified_audit_requires_fresh_audit(tmp_path, monkeypatch, corrupt):
    path, pair = fixture(tmp_path)
    session = opened(path, pair)
    authority = session.store._world_proof_authority
    original = authority._audit
    calls = []
    checksum = None

    def mutate_after_audit(pin):
        nonlocal checksum
        verified = original(pin)
        calls.append(verified)
        if len(calls) == 1:
            # The original audit transaction has committed. A separate writer
            # changes the actual database, while the returned receipt stays old.
            with sqlite3.connect(path) as external:
                if corrupt:
                    checksum = external.execute(
                        "SELECT payload_checksum FROM records WHERE namespace='world.settlements'"
                    ).fetchone()[0]
                    external.execute("UPDATE records SET payload_checksum='corrupt' "
                                     "WHERE namespace='world.settlements'")
                else:
                    external.execute('CREATE TABLE unrelated_diagnostic(value INTEGER)')
            assert authority._epoch() != verified
        return verified

    try:
        session.world.settlements[1].memory['new'] = [1, 2, 3]
        with monkeypatch.context() as patch:
            patch.setattr(authority, '_audit', mutate_after_audit)
            if corrupt:
                with pytest.raises(StoreError):
                    session.save()
                assert authority.uncertain
                assert authority._postcommit_verified_epoch is None
            else:
                assert session.save() == 1
                assert len(calls) == 2
                assert not authority.uncertain
                assert authority._postcommit_verified_epoch is None
        child = authority.pair
        if corrupt:
            # Restore only the injected checksum, then recover the already
            # committed attempt through the public recovery interface.
            with sqlite3.connect(path) as external:
                external.execute("UPDATE records SET payload_checksum=? "
                                 "WHERE namespace='world.settlements'", (checksum,))
            assert session.resolve_save() == 1
            assert not authority.uncertain
            child = session.proof_manifest
        assert session.save() == 1
    finally:
        session.close()
    with opened(path, child) as restored:
        assert list(restored.world.settlements[1].memory['new']) == [1, 2, 3]


def test_matching_epoch_does_not_admit_in_place_codec_hook(tmp_path, monkeypatch):
    from types import MethodType

    path, pair = fixture(tmp_path)
    session = opened(path, pair)
    authority = session.store._world_proof_authority
    codec = session.store.codec
    original_audit, original_decode = authority._audit, codec.decode
    calls = []

    def hooked_decode(self, payload):
        return original_decode(payload)

    def mutate_codec_after_audit(pin):
        verified = original_audit(pin)
        calls.append(verified)
        if len(calls) == 1:
            codec.decode = MethodType(hooked_decode, codec)
            assert authority._epoch() == verified
        return verified

    try:
        session.world.settlements[1].memory['new'] = [1, 2, 3]
        with monkeypatch.context() as patch:
            patch.setattr(authority, '_audit', mutate_codec_after_audit)
            with pytest.raises(StoreError, match='closed codec'):
                session.save()
        assert authority.uncertain
        assert authority._postcommit_verified_epoch is None
        del codec.decode
        assert session.resolve_save() == 1
        child = session.proof_manifest
    finally:
        if 'decode' in vars(codec):
            del codec.decode
        session.close()
    with opened(path, child) as restored:
        assert list(restored.world.settlements[1].memory['new']) == [1, 2, 3]


def test_matching_epoch_does_not_admit_acknowledgement_transaction(tmp_path, monkeypatch):
    path, pair = fixture(tmp_path)
    session = opened(path, pair)
    publish = session._publish_committed_hybrid

    def leave_read_transaction(*args):
        result = publish(*args)
        session.store.db.execute('BEGIN')
        return result

    try:
        session.world.settlements[1].memory['new'] = [1, 2, 3]
        with monkeypatch.context() as patch:
            patch.setattr(session, '_publish_committed_hybrid', leave_read_transaction)
            with pytest.raises(StoreError, match='open transaction'):
                session.save()
        assert session.store._world_proof_authority.uncertain
        assert session.store._world_proof_authority._postcommit_verified_epoch is None
        session.store.db.rollback()
        assert session.resolve_save() == 1
        child = session.proof_manifest
    finally:
        if session.store.db.in_transaction:
            session.store.db.rollback()
        session.close()
    with opened(path, child) as restored:
        assert list(restored.world.settlements[1].memory['new']) == [1, 2, 3]


def _probe_module():
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / 'docs/performance/stage-0-6-current/audit_probe.py'
    spec = importlib.util.spec_from_file_location('audit_probe_under_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_probe_recovery_epoch_counts_exclude_earlier_admission():
    from types import SimpleNamespace

    tracker = _probe_module().CallAttribution()

    def frame(name, local=None):
        return SimpleNamespace(f_code=SimpleNamespace(
            co_filename='persistence_proof_world_session.py', co_name=name),
            f_locals=local or {})

    admission = frame('_audit')
    tracker(admission, 'call', None)
    tracker(admission, 'return', ('db', 'codec', 1, 0, 0, 0))
    for revision in (2, 3):
        epoch = ('db', 'codec', revision, 0, 0, 0)
        execute = frame('execute', dict(observed=epoch, verified=epoch,
                                        self=SimpleNamespace(_can_settle=False)))
        tracker(execute, 'call', None)
        audit = frame('_audit')
        tracker(audit, 'call', None)
        tracker(audit, 'return', epoch)
        tracker(execute, 'return', 1)
    checks = tracker.snapshot()['execution_epoch_checks']
    assert len(checks) == 2
    for check in checks:
        assert check['authority_audit_count'] == 1
        assert check['first_audit_equals_observed']
        assert check['first_audit_to_final_epoch_delta'] == {}


@pytest.mark.parametrize('signal_name', ['SIGTERM', 'SIGKILL'])
def test_probe_preserves_finished_case_when_later_case_is_killed(tmp_path, signal_name):
    import json
    import os
    from pathlib import Path
    import signal
    import subprocess
    import sys
    import time

    root = Path(__file__).resolve().parents[2]
    tests = tmp_path / 'simulation/tests/test_cases.py'
    tests.parent.mkdir(parents=True)
    tests.write_text('import time\ndef test_first(): pass\ndef test_blocked(): time.sleep(30)\n')
    report = tmp_path / 'result.json'
    selectors = [str(tests.relative_to(tmp_path)) + '::test_' + name
                 for name in ('first', 'blocked')]
    command = [sys.executable, str(root / 'docs/performance/stage-0-6-current/audit_probe.py'),
               '--output', str(report), *selectors]
    with (tmp_path / 'output.log').open('w') as log:
        child = subprocess.Popen(command, cwd=tmp_path, stdout=log, stderr=log,
                                 env=dict(os.environ, PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'))
        try:
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                value = json.loads(report.read_text()) if report.exists() else {}
                if (value.get('active_selector') or '').endswith('test_blocked'):
                    break
                assert child.poll() is None, (tmp_path / 'output.log').read_text()
                time.sleep(.05)
            else:
                pytest.fail('probe did not checkpoint the blocked case')
            child.send_signal(getattr(signal, signal_name))
            child.wait(timeout=5)
            value = json.loads(report.read_text())
            assert value['status'] == 'running'
            assert value['pytest_exit_code'] is None
            assert value['active_selector'].endswith('test_blocked')
            assert [row['nodeid'] for row in value['tests']] == [selectors[0]]
        finally:
            if child.poll() is None:
                child.kill()
                child.wait(timeout=5)
