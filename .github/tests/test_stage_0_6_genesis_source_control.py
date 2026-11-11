"""Reuse an actual accepted source commitment without repeating its World walk."""
import copy
from dataclasses import replace
import importlib
import importlib.util
from pathlib import Path
import pytest
from simulation import continuation_receipts as r
from simulation import stage_0_6_genesis_checkpoint as c
from simulation.tests.test_continuation_checkpoint import publication
from simulation.tests.test_continuation_verifiers import saved_template
from simulation.tests.test_continuation_acceptance import verified_template,accept_pair


def api():
    name='simulation.stage_0_6_genesis_source_control'
    assert importlib.util.find_spec(name) is not None,'authenticated accepted-source control is missing'
    return importlib.import_module(name)


def test_reviewed_compatibility_pair_checks_all_model_and_codec_bytes(tmp_path):
    import json,shutil
    m=api();assert hasattr(m,'check_compatibility'),'reviewed canonical compatibility fence is missing'
    root=Path(__file__).resolve().parents[2]
    manifest=json.loads((root/m.COMPATIBILITY).read_text())
    pairs=dict(historical_runtime_sha='2cbf3510ef1f0ad8ddd712a1c4174ccfa518291a',
        historical_runtime_tree='76dee76973928dbce72860156feb32f2d7f02f86',
        current_runtime_tree='94267bb00a219702a4bd1700a2fc0600a5c5aa56')
    (tmp_path/m.COMPATIBILITY).parent.mkdir(parents=True)
    shutil.copyfile(root/m.COMPATIBILITY,tmp_path/m.COMPATIBILITY)
    for name in manifest['files']:
        target=tmp_path/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(root/name,target)
    result=m.check_compatibility(tmp_path,**pairs)
    assert result['historical_runtime_tree']==pairs['historical_runtime_tree']
    for key in pairs:
        with pytest.raises(ValueError):m.check_compatibility(tmp_path,**{**pairs,key:'0'*len(pairs[key])})
    # Changing a stored model definition, codec, schema or ordering must reject,
    # even when a caller still declares the reviewed runtime tuple.
    for name in ('materials.py','social.py','persistence_schema.py','incremental_store.py',
                 'canonical_stream.py','persistence_adapters.py','persistence_event_ids.py'):
        path=tmp_path/'simulation/ate_sim'/name;before=path.read_bytes();path.write_bytes(before+b'\n# changed definition\n')
        with pytest.raises(ValueError):m.check_compatibility(tmp_path,**pairs)
        path.write_bytes(before)


def test_mature_import_requires_the_actual_original_member_and_source(accepted_case):
    m=api();assert hasattr(m,'mature_control'),'mature accepted-member integration is missing'
    root=Path(__file__).resolve().parents[2]
    member,_,options,_=accepted_case
    with pytest.raises(ValueError):
        m.mature_control(root,member,options['source'],current_runtime_tree='94267bb00a219702a4bd1700a2fc0600a5c5aa56')
    contract=m.mature_control_contract(root,current_runtime_tree='94267bb00a219702a4bd1700a2fc0600a5c5aa56')
    assert contract['digest']=='57f60fdf49e221af24ffc0a1f2d5a3885dd37c07db00d153171adcb91c579eed'
    assert contract['acceptance_member_bytes']==570001
    assert contract['acceptance_member_sha256']=='5e54ce0e4e27b6d3a17cb22ce4fda887e5f1ee9cde6c052ab2d270144367ef45'
    # Merely possessing a valid small accepted receipt cannot promote it into
    # this mature source context, even if the caller declares its original DB.
    with pytest.raises(ValueError):
        m.mature_control(root,member,contract['source'],current_runtime_tree='94267bb00a219702a4bd1700a2fc0600a5c5aa56')


@pytest.mark.parametrize('damage',['digest','method','source_artifact','member','compatibility'])
def test_checkpoint_consumption_rejects_relabelled_imported_control(damage):
    m=api();assert hasattr(m,'validate_control_chain'),'imported baseline authority is not checked on consumption'
    root=Path(__file__).resolve().parents[2];runtime='94267bb00a219702a4bd1700a2fc0600a5c5aa56'
    control=m.mature_control_contract(root,current_runtime_tree=runtime)
    context=dict(mode='mature',runtime_tree=runtime,critical_blobs={'test.py':'a'*40},
        source=control['source'],rules_id=control['rules_id'],rank_proofs=True,
        execution_runtime=dict(python='test',sqlite='test',signature='a'*64),expected_saved_digest='b'*64)
    producer=lambda stage:dict(run_id=1,head_sha='e'*40,job=c.JOB[stage],attempt=1)
    source=c.record('source',context,control['source'],producer('source'),data_ref={'kind':'retained-original'})
    imported=c.record('source_digest',context,control['source'],producer('source_digest'),parent=source,
        baseline_digest=control['digest'],metrics=dict(source_control=control))
    m.validate_control_chain(root,imported,current_runtime_tree=runtime)
    if damage=='digest':imported['baseline_digest']='0'*64
    elif damage=='method':imported['metrics']['source_control']['method']='computed-current-digest'
    elif damage=='source_artifact':imported['metrics']['source_control']['source_artifact']['artifact_id']=99
    elif damage=='member':imported['metrics']['source_control']['acceptance_member_sha256']='0'*64
    else:imported['metrics']['source_control']['compatibility']['manifest_sha256']='0'*64
    with pytest.raises(ValueError):m.validate_control_chain(root,imported,current_runtime_tree=runtime)


@pytest.fixture
def accepted_case(tmp_path,verified_template):
    path,authority,_,candidate,*_=verified_template
    row=r.decode_receipt(r.receipt_bytes(accept_pair(verified_template)));member=tmp_path/'accepted.json'
    r.publish_receipt(member,row)
    source=c.describe(path/'candidate.sqlite',rules_id=authority.source_config['rules_id'])
    accepted=replace(candidate,artifact_id=13,name='accept1',producer_job='accept1')
    options=dict(source=source,rules_id=authority.source_config['rules_id'],authority=authority,
        source_ref=candidate,acceptance_ref=accepted,
        expected_member_bytes=member.stat().st_size,expected_member_sha256=r.file_hash(member))
    return member,row,options,path/'candidate.sqlite'


def test_actual_accepted_source_reuses_its_digest_without_opening_world(accepted_case,monkeypatch):
    m=api();member,row,options,_=accepted_case
    from ate_sim import core,persistence_lazy
    def forbidden(*a,**k):raise AssertionError('accepted source control repeated World work')
    monkeypatch.setattr(core.World,'digest',forbidden)
    monkeypatch.setattr(persistence_lazy,'open_lazy_world_session',forbidden)
    result=m.read_accepted_control(member,**options)
    assert result['method']=='historical-control-reused'
    assert result['digest']==row['digest']['observation']['digest']
    assert result['source']==options['source']
    assert result['acceptance_member_sha256']==options['expected_member_sha256']
    assert result['acceptance']==options['acceptance_ref'].to_dict()


@pytest.mark.parametrize('damage',['hash','size','source_hash','source_bytes','uuid','generation','year',
    'seed','rules','format','acceptance_producer','candidate','digest','digest_proof','original','symlink'])
def test_control_rejects_unaccepted_or_differently_bound_values(accepted_case,tmp_path,damage):
    m=api();member,row,options,_=accepted_case
    options={**options,'source':copy.deepcopy(options['source'])}
    if damage=='hash':options['expected_member_sha256']='0'*64
    elif damage=='size':options['expected_member_bytes']+=1
    elif damage=='source_hash':options['source']['sha256']='0'*64
    elif damage=='source_bytes':options['source']['bytes']+=1
    elif damage=='uuid':options['source']['store_identity']='00000000-0000-0000-0000-000000000000'
    elif damage=='generation':options['source']['generation']+=1
    elif damage=='year':options['source']['year']+=1
    elif damage=='seed':options['source']['seed']+=1
    elif damage=='rules':options['rules_id']='foreign'
    elif damage=='format':options['source']['format']=7
    elif damage=='acceptance_producer':options['acceptance_ref']=replace(options['acceptance_ref'],producer_job='foreign')
    elif damage=='candidate':options['source_ref']=replace(options['source_ref'],artifact_id=99)
    elif damage=='symlink':
        link=tmp_path/'alias.json';link.symlink_to(member);member=link
    else:
        if damage=='digest':row['digest']['observation']['digest']='0'*64
        elif damage=='digest_proof':row['proofs']['digest']['receipt_sha256']='0'*64
        else:row['original_checkpoint']='{}'
        member=tmp_path/'changed.json';r.publish_receipt(member,row)
        options.update(expected_member_bytes=member.stat().st_size,expected_member_sha256=r.file_hash(member))
    with pytest.raises(ValueError):m.read_accepted_control(member,**options)


def test_imported_control_preserves_actual_post_rebase_check(tmp_path,monkeypatch):
    # Receipt authentication above uses a real legacy saved/accepted pair. This
    # stage-composition case uses the admitted checked-genesis fixture; it makes
    # no claim that a synthetic local control is a remote acceptance producer.
    from simulation.tests.test_stage_0_5_final_complete_format import upgraded
    from simulation.tests.test_stage_0_5_final_catalog_copy import RULES
    from ate_sim.persistence_lazy import open_lazy_world_session
    from simulation import stage_0_6_genesis_stages as stages
    import shutil
    source=upgraded(tmp_path);desc=c.describe(source,rules_id=RULES)
    disposable=tmp_path/'control.sqlite';shutil.copyfile(source,disposable)
    with open_lazy_world_session(disposable,rules_id=RULES) as session:expected=session.world.digest()
    control=dict(method='historical-control-reused',digest=expected,source=desc,rules_id=RULES)
    ctx=dict(mode='smoke',runtime_tree='a'*40,critical_blobs={'test.py':'b'*40},source=desc,
        rules_id=RULES,rank_proofs=True,execution_runtime=dict(python='test',sqlite='test',signature='a'*64),expected_saved_digest='d'*64)
    producer=lambda stage:dict(run_id=1,head_sha='e'*40,job=c.JOB[stage],attempt=1)
    row=c.record('source',ctx,desc,producer('source'),data_ref={'kind':'local'})
    before=c.file_hash(source)
    original=stages._digest
    def forbidden(*a,**k):raise AssertionError('source digest repeated despite accepted control')
    with monkeypatch.context() as change:
        change.setattr(stages,'_digest',forbidden)
        row=stages.run_stage('source_digest',row,source,tmp_path/'source-control',producer=producer('source_digest'),budget=60,source_control=control)
    assert row['baseline_digest']==expected
    assert row['metrics']['source_control']['method']=='historical-control-reused' and c.file_hash(source)==before
    for stage in ('capture','catalog','rebase'):
        out=tmp_path/stage
        row=stages.run_stage(stage,row,source,out,producer=producer(stage),budget=60)
        source=out/'candidate.sqlite'
    # Actual comparison must reject a changed World; patch only the slow reader
    # boundary to return a distinct computed value, not the acceptance helper.
    with monkeypatch.context() as change:
        change.setattr(stages,'_digest',lambda *a,**k:'0'*64)
        with pytest.raises(ValueError,match='canonical World'):
            stages.run_stage('after_digest',row,source,tmp_path/'wrong',producer=producer('after_digest'),budget=60)
    out=tmp_path/'after'
    actual=stages.run_stage('after_digest',row,source,out,producer=producer('after_digest'),budget=60)
    assert actual['baseline_digest']==control['digest'] and original is stages._digest
