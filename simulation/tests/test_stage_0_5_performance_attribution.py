"""Bounded diagnostic attribution must observe real checked work and restore hooks."""
from dataclasses import replace

import pytest

from ate_sim.persistence_lazy import open_lazy_world_session
from ate_sim.persistence_lazy_store import LazyRecordStore
from simulation.tests.test_stage_0_5_final_identity_only_headers import complete, RULES
from simulation.tests.test_stage_0_5_packed_action_reconciliation_cost import fixture
from simulation.tests.test_stage_0_5_performance_runner import source_authority


def attribution(**kwargs):
    from simulation.performance_attribution import PerformanceAttribution
    return PerformanceAttribution(**kwargs)


def test_attributes_real_reads_and_bounded_repeat_sample(tmp_path):
    path = complete(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        for key in (2, 3):
            session.people[key] = replace(session.people[1], id=key)
        session.save()
        with attribution(key_limit=2) as trace:
            with trace.phase('reads'):
                for key in (1, 1, 2, 1, 3, 2):
                    session.store.read_version(session.pin, 'world.people', key,
                                               expected_record_schema=1)
            row = trace.snapshot()
        ns = row['reads']['world.people']
        assert ns['requests'] == 6
        assert ns['sample_hits'] == 2
        assert row['key_sample']['entries'] <= 2
        assert row['key_sample']['limit'] == 2
        assert row['spans']['store.read_version']['calls'] == 6
        assert row['spans']['store.check_record_row']['calls'] == 6
        assert row['physical_io']['available'] in (True, False)


def test_exclusive_spans_do_not_double_count_nested_work():
    with attribution() as trace:
        with trace.phase('nested'):
            with trace.span('outer'):
                sum(range(10000))
                with trace.span('inner'):
                    sum(range(20000))
        row = trace.snapshot()
    spans = row['spans']
    total = sum(v['exclusive_wall_seconds'] for v in spans.values())
    assert abs(total-row['wall_seconds']) < .001
    assert spans['outer']['inclusive_wall_seconds'] >= spans['inner']['inclusive_wall_seconds']
    assert all(v['exclusive_wall_seconds'] >= 0 for v in spans.values())


def test_exception_preserves_partial_evidence_and_restores_methods(tmp_path):
    path = complete(tmp_path)
    before = LazyRecordStore.read_version
    trace = attribution()
    with pytest.raises(RuntimeError, match='interrupt'):
        with trace:
            with trace.phase('interrupted'):
                with open_lazy_world_session(path, rules_id=RULES):
                    raise RuntimeError('interrupt')
    row = trace.snapshot()
    assert row['status'] == 'incomplete'
    assert row['wall_seconds'] > 0 and row['reads']
    assert LazyRecordStore.read_version is before


def test_attributed_mature_runner_captures_open_io_and_separates_instrumentation(tmp_path):
    from simulation import stage_0_5_mature_step_save as runner
    path = fixture(tmp_path, 16)
    authority = source_authority(path)
    result = runner.run(path, tmp_path/'result', seconds=30,
        expected_sha256=authority['database']['sha256'], authority=authority, attributed=True)
    assert result['status'] == 'complete', result
    assert result['instrumentation'] == 'attribution-v1'
    assert result['phases']['open']['io']['payload_reads'] > 0
    assert result['phases']['open']['attribution']['reads']
    assert result['phases']['save']['attribution']['spans']['save.commit']['calls'] == 1
    changed = dict(result, instrumentation='none')
    with pytest.raises(ValueError, match='instrumentation'):
        runner.compare_receipts(result, changed)


@pytest.mark.parametrize('runner_name', ['stage_0_5_mature_step_save', 'profile_stage_0_5_performance'])
def test_completed_phase_evidence_survives_a_later_hard_process_exit(tmp_path, runner_name):
    import json
    import os
    from pathlib import Path
    import subprocess
    import sys
    from simulation import continuation_receipts as receipts
    path=fixture(tmp_path,16);authority=source_authority(path)
    authority_path=tmp_path/'authority.json';receipts.publish_receipt(authority_path,authority)
    output=tmp_path/'interrupted'
    code='''
import os,sys
from pathlib import Path
import importlib
runner=importlib.import_module('simulation.'+sys.argv[4])
from simulation import continuation_receipts as r
runner.Simulation.run=lambda self,years:os._exit(23)
a=r.load_receipt(sys.argv[2])
kwargs=dict(seconds=30,expected_sha256=a['database']['sha256'],authority=a)
if hasattr(runner,'run_phase'):
 runner.run_phase(Path(sys.argv[1]),Path(sys.argv[3]),phase='step',**kwargs)
else:
 runner.run(Path(sys.argv[1]),Path(sys.argv[3]),**kwargs)
'''
    process=subprocess.run([sys.executable,'-c',code,str(path),str(authority_path),str(output),runner_name],
        cwd=Path(__file__).resolve().parents[2],env=os.environ.copy(),capture_output=True,text=True,timeout=30)
    assert process.returncode == 23,process.stderr
    progress=json.load(open(output/'phase-progress-open.json'))
    assert progress['schema'] == 'ate-performance-progress/1'
    assert progress['measurement']['phases']['open']['status'] == 'complete'
    assert progress['measurement']['phases']['open']['io']['payload_reads'] > 0
    assert progress['measurement']['status'] != 'complete'
    assert not (output/'result.json').exists()


@pytest.mark.parametrize('runner_name', ['stage_0_5_mature_step_save', 'profile_stage_0_5_performance'])
def test_attributed_receipts_bind_the_instrumentation_helper(tmp_path, runner_name):
    import copy
    import importlib
    from pathlib import Path
    from simulation import continuation_receipts as receipts
    runner = importlib.import_module('simulation.' + runner_name)
    path = fixture(tmp_path, 16)
    authority = source_authority(path)
    kwargs = dict(seconds=30, expected_sha256=authority['database']['sha256'],
                  authority=authority, attributed=True)
    if hasattr(runner, 'run_phase'):
        result = runner.run_phase(path, tmp_path/'result', phase='open', **kwargs)
    else:
        result = runner.run(path, tmp_path/'result', **kwargs)
    assert result['status'] == 'complete', result
    helper = Path(runner.__file__).with_name('performance_attribution.py')
    assert result.get('attribution_helper_sha256') == receipts.file_hash(helper)
    assert runner.compare_receipts(result, result)
    changed = copy.deepcopy(result)
    changed['attribution_helper_sha256'] = '0'*64
    with pytest.raises(ValueError, match='attribution helper'):
        runner.compare_receipts(result, changed)
    del changed['attribution_helper_sha256']
    with pytest.raises(ValueError, match='attribution helper'):
        runner.compare_receipts(changed, changed)


def test_phase_snapshot_retains_route_proof_work_and_residency(tmp_path):
    from simulation.profile_stage_0_5_performance import _diagnostics
    path = complete(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        person = session.people[1]
        person.wealth = .25
        person.wealth = .5
        row = _diagnostics(session)['identity_coordinator']
        assert row['value_routes']['hits'] >= 1
        assert row['value_routes']['entries'] > 0
        assert row['value_routes']['bytes'] <= row['value_routes']['byte_limit']
        assert row['dirty_owners'] > 0


def test_opt_in_proof_save_spans_nest_and_restore_without_runtime_change():
    """Proof guard/manifest costs remain separate from the inner store commit."""
    from unittest.mock import patch
    from ate_sim.persistence_proof_world_session import _WorldProofAuthority

    original_execute = _WorldProofAuthority.execute
    original_manifest = _WorldProofAuthority.commit
    original_store = LazyRecordStore.commit

    def fake_store_commit(self):
        return 'committed'

    def fake_manifest(self):
        return LazyRecordStore.commit(object.__new__(LazyRecordStore))

    def fake_execute(self):
        return self.commit()

    with (patch.object(_WorldProofAuthority, 'execute', fake_execute),
          patch.object(_WorldProofAuthority, 'commit', fake_manifest),
          patch.object(LazyRecordStore, 'commit', fake_store_commit)):
        with attribution() as trace:
            with trace.phase('proof-save'):
                assert _WorldProofAuthority.execute(object.__new__(_WorldProofAuthority)) == 'committed'
            result = trace.snapshot()
        assert _WorldProofAuthority.execute is fake_execute
        assert _WorldProofAuthority.commit is fake_manifest
        assert LazyRecordStore.commit is fake_store_commit

    assert _WorldProofAuthority.execute is original_execute
    assert _WorldProofAuthority.commit is original_manifest
    assert LazyRecordStore.commit is original_store
    spans = result['spans']
    for label in ('save.proof_execute', 'save.proof_manifest', 'save.commit'):
        assert spans[label]['calls'] == 1
    assert spans['save.proof_execute']['inclusive_wall_seconds'] >= spans['save.proof_manifest']['inclusive_wall_seconds']
    assert spans['save.proof_manifest']['inclusive_wall_seconds'] >= spans['save.commit']['inclusive_wall_seconds']
    assert abs(sum(v['exclusive_wall_seconds'] for v in spans.values()) - result['wall_seconds']) < .001
