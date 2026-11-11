import copy
import importlib
import importlib.util
from pathlib import Path
from unittest.mock import patch
import pytest
from simulation import stage_0_6_genesis_checkpoint as c
from ate_sim.persistence_lazy import open_lazy_world_session
from simulation.tests.test_stage_0_5_final_complete_format import upgraded
from simulation.tests.test_stage_0_5_final_catalog_copy import RULES


def api():
    name='simulation.stage_0_6_genesis_stages'
    assert importlib.util.find_spec(name) is not None,'independently recoverable genesis stages are missing'
    return importlib.import_module(name)


def setup_source(tmp_path):
    m=api();source=upgraded(tmp_path)
    desc=c.describe(source,rules_id=RULES)
    context=dict(mode='smoke',runtime_tree='a'*40,critical_blobs={'simulation/stage_0_6_genesis_stages.py':'b'*40},
        source=desc,rules_id=RULES,rank_proofs=True,execution_runtime=dict(python='test',sqlite='test',signature='a'*64),expected_saved_digest='d'*64)
    row=c.record('source',context,desc,producer('source'),data_ref={'kind':'local'})
    return source,row


def producer(stage):return dict(run_id=1,head_sha='e'*40,job=c.JOB[stage],attempt=1)


def advance(m,tmp_path,row,path,stage):
    out=tmp_path/('stage-'+stage)
    result=m.run_stage(stage,row,path,out,producer=producer(stage),budget=120)
    return result,(out/'candidate.sqlite' if (out/'candidate.sqlite').exists() else path)


def test_small_stage_chain_preserves_source_aliases_and_full_audits(tmp_path):
    m=api();source,row=setup_source(tmp_path);original=c.file_hash(source);path=source
    from ate_sim.persistence_lazy_store import LazyRecordStore
    with patch.object(LazyRecordStore,'_verify_all_in_snapshot',autospec=True,side_effect=LazyRecordStore._verify_all_in_snapshot) as audits:
        for stage in c.STAGES[:c.STAGES.index('proofs')+1]:row,path=advance(m,tmp_path,row,path,stage)
        assert audits.call_count==3
    assert c.file_hash(source)==original
    from ate_sim.persistence_proof_world_session import open_proof_world_session
    import shutil
    working=tmp_path/'fresh.sqlite';shutil.copyfile(path,working)
    with open_proof_world_session(working,rules_id=RULES,expected_commitment=bytes.fromhex(row['proof_commitment'])) as s:
        assert s.world.digest()==row['baseline_digest']
        assert s.skills[1,'craft'].provenance is s.skills[2,'craft'].provenance


def test_late_failure_resumes_without_capture_or_catalog_replay(tmp_path,monkeypatch):
    m=api();path,row=setup_source(tmp_path)
    for stage in ('source_digest','capture','catalog'):row,path=advance(m,tmp_path,row,path,stage)
    retained=c.file_hash(path);before=copy.deepcopy(row)
    from ate_sim import persistence_proof_world_copy as worldcopy,persistence_catalog_copy as catalog
    real=worldcopy._rebase_private_snapshot
    def failure(*a,**k):raise TimeoutError('controlled interruption before rebase')
    monkeypatch.setattr(worldcopy,'_rebase_private_snapshot',failure)
    with pytest.raises(TimeoutError):advance(m,tmp_path,row,path,'rebase')
    assert c.file_hash(path)==retained and row==before and not (tmp_path/'stage-rebase').exists()
    monkeypatch.setattr(worldcopy,'_rebase_private_snapshot',real)
    def no_replay(*a,**k):raise AssertionError('completed expensive preparation replayed')
    monkeypatch.setattr(catalog,'_copy_current_checked_catalog',no_replay)
    from ate_sim.persistence_lazy_store import LazyRecordStore
    monkeypatch.setattr(LazyRecordStore,'copy_current_head',no_replay)
    for stage in ('rebase','after_digest','proofs'):row,path=advance(m,tmp_path,row,path,stage)
    assert row['stage']=='proofs'


def test_field_progress_keeps_exact_canonical_digest(tmp_path):
    m=api();source,row=setup_source(tmp_path)
    events=[]
    with open_lazy_world_session(source,rules_id=RULES) as s:
        expected=s.world.digest()
        actual=m.canonical_digest(s.world,events.append)
    assert actual==expected
    from ate_sim.core import _canonical_fields
    assert events==['canonical.field.'+name for _,name in _canonical_fields(type(s.world))]


def test_catalog_adapter_is_one_shot_and_source_bound(tmp_path):
    m=api();path,row=setup_source(tmp_path)
    for stage in ('source_digest','capture'):row,path=advance(m,tmp_path,row,path,stage)
    from ate_sim.persistence_lazy_store import LazyRecordStore
    from ate_sim.persistence_adapters import WorldCodec,SCHEMA
    root=tmp_path/'owned';root.mkdir();private=root/'.ate-checked-current-copy-test';private.mkdir()
    options=dict(codec=WorldCodec(identity_links_recorded=True),expected_simulation_schema=SCHEMA,
        expected_rules_id=RULES,_defer_target_audit=True)
    from ate_sim import persistence_lazy_store as lazy
    with lazy._bounded_conversion_audits(),m.captured_transfer(path,row,root):
        LazyRecordStore.copy_current_head(path,private/'destination.sqlite',**options)
        with pytest.raises(ValueError):LazyRecordStore.copy_current_head(path,private/'other.sqlite',**options)


def measured_source(tmp_path):
    from ate_sim.engine import Simulation
    from ate_sim.worldgen import generate_world
    from ate_sim.persistence_session import write_cold_snapshot
    from ate_sim.persistence_lazy import convert_cold_to_lazy
    from ate_sim.persistence_complete_format import upgrade_lazy_snapshot
    world=generate_world(843000,width=4,height=3,settlements=1,mature=True)
    Simulation(world).run(1);control=copy.deepcopy(world);Simulation(control).run(1)
    cold=tmp_path/'cold.sqlite';legacy=tmp_path/'legacy.sqlite';path=tmp_path/'complete.sqlite'
    write_cold_snapshot(world,cold,rules_id=RULES)
    convert_cold_to_lazy(cold,legacy,rules_id=RULES,native_graph_buckets=True)
    upgrade_lazy_snapshot(legacy,path,rules_id=RULES)
    desc=c.describe(path,rules_id=RULES)
    ctx=dict(mode='smoke',runtime_tree='a'*40,critical_blobs={'simulation/stage_0_6_genesis_stages.py':'b'*40},
        source=desc,rules_id=RULES,rank_proofs=True,execution_runtime=dict(python='test',sqlite='test',signature='a'*64),expected_saved_digest=control.digest())
    return path,c.record('source',ctx,desc,producer('source'),data_ref={'kind':'local'})


def test_saved_world_is_durable_before_fresh_process_validation(tmp_path,monkeypatch):
    m=api();path,row=measured_source(tmp_path)
    for stage in c.STAGES[:-1]:row,path=advance(m,tmp_path,row,path,stage)
    assert row['stage']=='measure' and row['database']['generation']==1
    saved=c.file_hash(path);prior=copy.deepcopy(row)
    real=m.restore_in_fresh_process
    def timeout(*a,**k):raise TimeoutError('fresh validation interrupted')
    monkeypatch.setattr(m,'restore_in_fresh_process',timeout)
    with pytest.raises(TimeoutError):advance(m,tmp_path,row,path,'fresh_restore')
    assert c.file_hash(path)==saved and row==prior
    monkeypatch.setattr(m,'restore_in_fresh_process',real)
    restored,db=advance(m,tmp_path,row,path,'fresh_restore')
    assert db==path and restored['metrics']['restored']['digest']==row['context']['expected_saved_digest']


@pytest.mark.parametrize('alias',['source','destination_parent'])
def test_capture_replay_rejects_symlink_boundaries(tmp_path,alias):
    m=api();path,row=setup_source(tmp_path)
    for stage in ('source_digest','capture'):row,path=advance(m,tmp_path,row,path,stage)
    from ate_sim import persistence_lazy_store as lazy
    from ate_sim.persistence_adapters import WorldCodec,SCHEMA
    root=tmp_path/'owned';root.mkdir()
    if alias=='source':
        link=tmp_path/'source-link.sqlite';link.symlink_to(path)
        with pytest.raises(ValueError,match='regular'):
            with lazy._bounded_conversion_audits(),m.captured_transfer(link,row,root):pass
    else:
        outside=tmp_path/'outside';outside.mkdir();parent=root/'.ate-checked-current-copy-link';parent.symlink_to(outside,target_is_directory=True)
        with pytest.raises(ValueError,match='transfer'):
            with lazy._bounded_conversion_audits(),m.captured_transfer(path,row,root):
                lazy.LazyRecordStore.copy_current_head(path,parent/'destination.sqlite',codec=WorldCodec(identity_links_recorded=True),
                    expected_simulation_schema=SCHEMA,expected_rules_id=RULES,_defer_target_audit=True)
        assert not (outside/'destination.sqlite').exists()


def test_failed_proof_transaction_restarts_only_proofs_with_a_fresh_audit(tmp_path,monkeypatch):
    m=api();path,row=setup_source(tmp_path)
    for stage in ('source_digest','capture','catalog','rebase','after_digest'):row,path=advance(m,tmp_path,row,path,stage)
    before=c.file_hash(path)
    from ate_sim import persistence_proof_inventory as inventory,persistence_lazy_store as lazy,persistence_proof_world_copy as worldcopy
    original=inventory.bootstrap_inventory
    def fail(*a,**k):raise RuntimeError('controlled failure after earlier proof builders')
    monkeypatch.setattr(inventory,'bootstrap_inventory',fail)
    with patch.object(lazy.LazyRecordStore,'_verify_all_in_snapshot',autospec=True,side_effect=lazy.LazyRecordStore._verify_all_in_snapshot) as audits:
        with pytest.raises(RuntimeError):advance(m,tmp_path,row,path,'proofs')
        assert c.file_hash(path)==before and not (tmp_path/'stage-proofs').exists()
        monkeypatch.setattr(inventory,'bootstrap_inventory',original)
        def no_rebase(*a,**k):raise AssertionError('completed rebase replayed')
        monkeypatch.setattr(worldcopy,'_rebase_private_snapshot',no_rebase)
        result,_=advance(m,tmp_path,row,path,'proofs')
        assert result['stage']=='proofs' and audits.call_count==2
    assert c.file_hash(path)==before


def test_requested_measure_budget_is_enforced_and_recorded(tmp_path,monkeypatch):
    import json,time
    from simulation.profile_stage_0_5_performance import BudgetExpired
    m=api();path,row=setup_source(tmp_path)
    for stage in ('source_digest','capture','catalog','rebase','after_digest','proofs'):row,path=advance(m,tmp_path,row,path,stage)
    retained=c.file_hash(path)
    from ate_sim import persistence_proof_world_session as session_api
    real=session_api.open_proof_world_session
    def slow_open(*a,**k):
        time.sleep(2)
        raise AssertionError('requested aggregate deadline did not interrupt open')
    monkeypatch.setattr(session_api,'open_proof_world_session',slow_open)
    with pytest.raises(BudgetExpired):
        m.run_stage('measure',row,path,tmp_path/'stage-measure',producer=producer('measure'),budget=1)
    records=list(tmp_path.glob('evidence-measure-*/phase-progress-measure.json'))
    assert len(records)==1
    phase=json.loads(records[0].read_text())['phases']['measure']
    assert phase['status']=='timeout' and phase['censored'] is True and phase['budget_seconds']==1
    assert c.file_hash(path)==retained and not (tmp_path/'stage-measure').exists()
