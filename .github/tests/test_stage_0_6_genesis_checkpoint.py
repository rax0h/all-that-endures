"""A timeout must not invalidate an earlier closed, exact checkpoint."""
import copy
import importlib
import importlib.util
import json
from pathlib import Path
import pytest


def api():
    name='simulation.stage_0_6_genesis_checkpoint'
    assert importlib.util.find_spec(name) is not None, 'durable genesis checkpoint contract is missing'
    return importlib.import_module(name)


def descriptor():
    return dict(bytes=100,sha256='a'*64,store_identity='06d24556-2bb1-4086-93f7-448f23b7eb5a',
        generation=126,format=6,year=1001,seed=843000)


def context():
    return dict(mode='smoke',runtime_tree='b'*40,critical_blobs={'simulation/stage_0_6_genesis_checkpoint.py':'c'*40},
        source=descriptor(),rules_id='checkpoint-test',rank_proofs=True,execution_runtime=dict(python='test',sqlite='test',signature='a'*64),expected_saved_digest='d'*64)


def producer(stage='source'):
    return dict(run_id=123,head_sha='e'*40,job=api().JOB[stage],attempt=1)


def source():
    m=api()
    return m.record('source',context(),descriptor(),producer(),data_ref={'kind':'local'})


def test_checkpoint_parent_hash_and_read_only_database_binding():
    m=api();a=source()
    b=m.record('source_digest',context(),descriptor(),producer('source_digest'),parent=a,baseline_digest='f'*64)
    assert m.validate(b,expected_context=context())==b
    assert b['parent']['sha256']==m.receipt_hash(a)
    assert b['data_ref']==a['data_ref']


@pytest.mark.parametrize('damage',['hash','context','stage','database','baseline','extra'])
def test_mixed_or_incomplete_checkpoint_cannot_advance(damage):
    m=api();a=source();b=m.record('source_digest',context(),descriptor(),producer('source_digest'),parent=a,baseline_digest='f'*64)
    bad=copy.deepcopy(b)
    if damage=='hash':bad['parent']['sha256']='0'*64
    elif damage=='context':bad['context']['rules_id']='other'
    elif damage=='stage':bad['stage']='proofs'
    elif damage=='database':bad['database']['sha256']='0'*64
    elif damage=='baseline':bad['baseline_digest']=None
    else:bad['extra']=1
    with pytest.raises(ValueError):m.validate(bad,expected_context=context())


def test_failed_publication_keeps_existing_checkpoint(tmp_path):
    m=api();out=tmp_path/'checkpoint';a=source()
    m.publish(out,a)
    original=(out/'checkpoint.json').read_bytes()
    with pytest.raises(FileExistsError):m.publish(out,a)
    assert (out/'checkpoint.json').read_bytes()==original
    assert m.load(out,expected_context=context())==a


def test_local_receipt_requires_explicit_remote_transport_before_resume():
    m=api()
    with pytest.raises(ValueError,match='authenticated'):
        m.validate(source(),expected_context=context(),require_remote=True)


def test_saved_checkpoint_survives_separate_fresh_restore_validation():
    m=api()
    assert 'fresh_restore' in m.STAGES,'fresh verification must not discard the completed saved checkpoint'
    row=source();db=descriptor()
    for stage in m.STAGES:
        if stage=='rebase':db={**db,'generation':0,'sha256':'1'*64}
        if stage=='proofs':db={**db,'format':7,'sha256':'2'*64}
        if stage=='measure':db={**db,'generation':1,'year':1002,'sha256':'3'*64}
        row=m.record(stage,context(),db,producer(stage),parent=row,
            data_ref={'kind':'local'},baseline_digest='f'*64 if stage=='source_digest' else None,
            proof_commitment='4'*64 if stage in ('proofs','measure','fresh_restore') else None)
    assert row['stage']=='fresh_restore' and row['database']==row['parent']['receipt']['database']


def test_owned_closed_database_publishes_without_a_second_full_copy(tmp_path):
    m=api();assert 'move_owned' in __import__('inspect').signature(m.publish).parameters,'large closed outputs need an owned transfer, not another full copy'
    retained=tmp_path/'retained.sqlite';retained.write_bytes(b'checked')
    owned=tmp_path/'.proof-stage-owned';owned.mkdir();working=owned/'working.sqlite';working.write_bytes(retained.read_bytes())
    db={**descriptor(),'bytes':7,'sha256':m.file_hash(working)};ctx=context();ctx['source']=db
    row=m.record('source',ctx,db,producer(),data_ref={'kind':'local'})
    m.publish(tmp_path/'output',row,database=working,move_owned=True)
    assert not working.exists() and retained.read_bytes()==b'checked'
    assert (tmp_path/'output/candidate.sqlite').read_bytes()==b'checked'
