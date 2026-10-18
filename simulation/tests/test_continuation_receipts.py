"""New stage receipts cannot substitute foreign authority or partial files."""
import copy
from dataclasses import replace
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path

import pytest


def module():
    assert importlib.util.find_spec('simulation.continuation_receipts'), 'continuation receipt boundary missing'
    return importlib.import_module('simulation.continuation_receipts')


def artifact(m, name='published', identity=1):
    return m.ArtifactRef(artifact_id=identity, run_id=1, workflow_sha='c'*40,
        workflow_path='.github/workflows/proof.yml', producer_job=name, name=name,
        archive_sha256='d'*64, archive_bytes=100, harness_sha='e'*40,
        runtime_sha='b'*40, runtime_tree='f'*40)


def producer(stage='save', job='save1'):
    return dict(harness_sha='e'*40, workflow_sha='c'*40, run_id=1, job=job, stage=stage)


def authority(m, root):
    config=dict(seed=843000, milestones=[1,2], bootstrap_year=0,
        rules_id='receipt-test', product_sha='a'*40, complete_format=True,
        initialization='founders', simulation_schema='ate-world-p2a/1')
    original=dict(schema=1, stage='complete', config=dict(config,product_sha='b'*40),
        workflow_sha='c'*40,product_sha='b'*40,checkpoint_product_sha='a'*40,
        database=dict(name='p5-long-complete.sqlite',sha256=hashlib.sha256(b'closed db').hexdigest()),
        source_checkpoint=dict(stage='lazy',product_sha='a'*40),
        state=dict(conversion_result=dict(generation=2,source_generation=1,
            store_identity='store-1',complete_format=True,source_preserved=True),
            controls={str(y):dict(digest=str(y)*64,counters={'next_person':1},
                audit=dict(year=y,event_count=0)) for y in (1,2)}))
    checkpoint=root/'checkpoint.json'; checkpoint.write_text(json.dumps(original))
    return m.Authority(checkpoint_sha256=hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
        checkpoint_bytes=checkpoint.stat().st_size,
        context=dict(runtime_sha='b'*40,harness_sha='e'*40,
            source_artifact=dict(id=9,run_id=7,archive_sha256='9'*64)),
        source_config=config,publication=artifact(m),
        published_database_sha256=original['database']['sha256'],published_database_bytes=9,
        checkpoint_runtime_sha='b'*40, execution_runtime_sha='b'*40,
        execution_runtime_tree='f'*40,bootstrap_generation=2,store_identity='store-1',
        output_max_bytes=1000)


def saved_bundle(m, root):
    root.mkdir(); a=authority(m,root)
    db=root/'candidate.sqlite'; db.write_bytes(b'saved db')
    previous=dict(kind='publication',artifact=a.publication.to_dict())
    counters=dict(year=1,counters={'next_person':1})
    saved=dict(schema='ate-validation-continuation/1',stage='year-saved-unverified',
        authority=a.to_dict(),producer=producer(),previous_year=0,year=1,
        previous_generation=2,generation=3,store_identity='store-1',
        database=dict(name='candidate.sqlite',bytes=8,sha256=hashlib.sha256(b'saved db').hexdigest()),
        checkpoint=dict(name='checkpoint.json',bytes=a.checkpoint_bytes,sha256=a.checkpoint_sha256),
        predecessor=previous,live_before=counters,live_after=copy.deepcopy(counters),
        metrics=dict(phases={},io={},working_set={}))
    (root/'save.json').write_text(json.dumps(saved))
    return a,saved,previous


def test_checked_saved_bundle_keeps_original_controls_and_rejects_overwrite(tmp_path):
    m=module();a,saved,previous=saved_bundle(m,tmp_path/'saved')
    result=m.validate_saved(tmp_path/'saved',authority=a,expected_year=1,
        expected_predecessor=previous,producer=producer())
    assert result==saved
    assert m.validate_original(tmp_path/'saved/checkpoint.json',a)['state']['controls']['2']['digest']=='2'*64
    receipt=tmp_path/'receipt.json'; m.publish_receipt(receipt,{'exact':'first'})
    with pytest.raises(FileExistsError):m.publish_receipt(receipt,{'exact':'second'})
    assert m.load_receipt(receipt)=={'exact':'first'}


@pytest.mark.parametrize('field,value', [
    ('year',True),('year',2),('previous_year',-1),('generation',True),('generation',4),
    ('previous_generation',0),('store_identity','foreign'),('stage','year-verified'),
    ('schema','foreign'),('extra',1),('live_after',{'year':1,'counters':{'next_person':2}}),
    ('producer',producer(job='foreign')),
])
def test_saved_manifest_rejects_foreign_or_malformed_authority(tmp_path,field,value):
    m=module();a,saved,previous=saved_bundle(m,tmp_path/'saved');saved[field]=value
    (tmp_path/'saved/save.json').write_text(json.dumps(saved))
    with pytest.raises(ValueError):m.validate_saved(tmp_path/'saved',authority=a,
        expected_year=1,expected_predecessor=previous,producer=producer())


@pytest.mark.parametrize('damage',['database','checkpoint','missing','extra','symlink','runtime','predecessor','db-size'])
def test_saved_files_reject_before_a_world_can_open(tmp_path,damage):
    m=module();root=tmp_path/'saved';a,saved,previous=saved_bundle(m,root)
    if damage=='database':(root/'candidate.sqlite').write_bytes(b'corrupt!')
    elif damage=='checkpoint':(root/'checkpoint.json').write_text('{}')
    elif damage=='missing':(root/'candidate.sqlite').unlink()
    elif damage=='extra':(root/'extra').write_text('unexpected')
    elif damage=='symlink':
        retained=tmp_path/'retained';(root/'candidate.sqlite').rename(retained)
        (root/'candidate.sqlite').symlink_to(retained)
    elif damage=='runtime':saved['authority']['execution_runtime_sha']='1'*40
    elif damage=='predecessor':saved['predecessor']['artifact']['artifact_id']=99
    else:saved['database']['bytes']=True
    (root/'save.json').write_text(json.dumps(saved))
    with pytest.raises(ValueError):m.validate_saved(root,authority=a,
        expected_year=1,expected_predecessor=previous,producer=producer())


@pytest.mark.parametrize('data',['{"a":1,"a":2}','{"a":NaN}','{"a":Infinity}','[]'])
def test_metadata_parser_rejects_ambiguous_or_nonfinite_values(tmp_path,data):
    m=module();path=tmp_path/'bad.json';path.write_text(data)
    with pytest.raises(ValueError):m.load_receipt(path)


def test_metadata_limits_and_defensive_authority_copy(tmp_path):
    m=module();a=authority(m,tmp_path)
    original=a.to_dict();original['context']['source_artifact']['id']=100
    assert a.to_dict()['context']['source_artifact']['id']==9
    oversized=tmp_path/'oversized';
    with oversized.open('wb') as f:f.truncate(16*1024**2+1)
    with pytest.raises(ValueError):m.load_receipt(oversized)
    with pytest.raises(ValueError):replace(a,bootstrap_generation=True)
    with pytest.raises(ValueError):m.ArtifactRef.from_dict(dict(artifact(m).to_dict(),extra=True))


def test_failed_publication_does_not_leave_a_completed_receipt(tmp_path,monkeypatch):
    m=module();path=tmp_path/'out.json'
    def failed(*args):raise OSError('fsync interrupted')
    monkeypatch.setattr(m.os,'fsync',failed)
    with pytest.raises(OSError,match='interrupted'):m.publish_receipt(path,{'passed':True})
    assert not path.exists()


@pytest.mark.parametrize('damage',['config','product','controls','generation','schema'])
def test_refreshed_hash_cannot_excuse_invalid_original_authority(tmp_path,damage):
    m=module();a=authority(m,tmp_path);path=tmp_path/'checkpoint.json';row=json.loads(path.read_text())
    if damage=='config':row['config']['seed']=7
    elif damage=='product':row['product_sha']='9'*40
    elif damage=='controls':del row['state']['controls']['2']
    elif damage=='generation':row['state']['conversion_result']['generation']=True
    else:row['schema']=True
    path.write_text(json.dumps(row))
    a=replace(a,checkpoint_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),checkpoint_bytes=path.stat().st_size)
    with pytest.raises(ValueError):m.validate_original(path,a)


def test_directory_fsync_failure_removes_only_new_receipt(tmp_path,monkeypatch):
    m=module();path=tmp_path/'out.json'
    def failed(*args):raise OSError('directory fsync failed')
    monkeypatch.setattr(m,'fsync_dir',failed)
    with pytest.raises(OSError,match='directory'):m.publish_receipt(path,{'passed':True})
    assert not path.exists()


@pytest.mark.parametrize('live,stored', [
    ({2: 1, 10: 3}, {'2': 1, '10': 3}),
    ({0: 2, 100: 4, 1001: 6, 9: 8}, {'0': 2, '100': 4, '1001': 6, '9': 8}),
])
def test_json_object_year_keys_compare_after_json_key_conversion(live,stored):
    assert module().same({'years':live},{'years':stored})


@pytest.mark.parametrize('actual,expected', [
    ({2: 1, 10: 4}, {'2': 1, '10': 3}),
    ({2: True}, {'2': 1}),
    ({2: 1.0}, {'2': 1}),
    ({2: [1, 2]}, {'2': [2, 1]}),
    ({2: 1}, {'2': 1, '10': 3}),
])
def test_json_key_normalization_keeps_value_types_order_and_fields_strict(actual,expected):
    assert not module().same(actual,expected)


def test_json_key_conversion_rejects_colliding_object_keys():
    with pytest.raises(ValueError,match='duplicate'):
        module().canonical({1:'first','1':'second'})


def test_real_complete_audit_with_multi_digit_history_matches_stored_control(tmp_path):
    from ate_sim.core import World,Layer
    from ate_sim.persistence_session import write_cold_snapshot
    from ate_sim.persistence_lazy import convert_cold_to_lazy,open_lazy_world_session
    from ate_sim.persistence_complete_format import upgrade_lazy_snapshot
    from persistence_p5_long_validation import _audit
    m=module();world=World(843000)
    for year in (2,10):
        world.year=year
        world.emit('rank_advanced',Layer.SOCIETY,from_rank=0,to_rank=1)
    original=_audit(world)
    assert original['new_irons_by_year']=={2:1,10:1}
    control=json.loads(json.dumps(original))
    assert control['new_irons_by_year']=={'2':1,'10':1}
    cold,lazy,complete=(tmp_path/name for name in ('cold.sqlite','lazy.sqlite','complete.sqlite'))
    rules='audit-json-year-keys'
    write_cold_snapshot(world,cold,rules_id=rules)
    convert_cold_to_lazy(cold,lazy,rules_id=rules,native_graph_buckets=True)
    upgrade_lazy_snapshot(lazy,complete,rules_id=rules)
    with open_lazy_world_session(complete,rules_id=rules) as session:
        actual=_audit(session.world)
        assert actual['new_irons_by_year']=={2:1,10:1}
        assert m.same(m.normalized_audit(actual),m.normalized_audit(control))
