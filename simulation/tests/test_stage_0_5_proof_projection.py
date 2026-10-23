"""Catch independent authority mismatch and payload-to-placement divergence."""
from dataclasses import replace
import struct
import pytest
from ate_sim.incremental_store import Membership,StoreError,StoreIntegrityError,StoreConflictError
from ate_sim.persistence_adapters import WorldCodec
from ate_sim.persistence_lazy_store import VersionChange,IdentityOccurrenceChange,_version_checksum
from ate_sim.persistence_lazy_nested_history import HistoryReference
from ate_sim.persistence_record_headers import RecordReference
from ate_sim.persistence_nonreflexive_keys import NonreflexiveKeyReference
from ate_sim.core import Ref,Layer
from simulation.tests.proof_projection_fixtures import (
    PAGE,PAGE_VALUE,PAGE_PLACEMENTS,make_projection_store,read_projection,projection_module,authorities,metadata)


def test_selected_body_references_match_exact_root_without_child_reads(tmp_path):
    store,pin,pairs=make_projection_store(tmp_path/'p.sqlite',30);sql=[];store.reset_diagnostics();store.db.set_trace_callback(sql.append)
    checked=read_projection(store,pin,pairs)
    store.db.set_trace_callback(None)
    assert checked.reference_count==4 and checked.source.payload==store.codec.encode(PAGE_VALUE)
    assert checked.source.memberships==b'["tuple",[]]'
    assert store._payload_check_reads==1 and store._payload_reads==0
    payloads=[q for q in sql if 'FROM lazy_record_versions' in q and 'THEN payload END' in q]
    assert len(payloads)==1 and 'aux.lazy.nested.list_pages' in payloads[0]
    store.close()


@pytest.mark.parametrize('namespace,key,value,placements,memberships',[
    ('aux.lazy.nested.entries',(1,'a'),(0,'a',RecordReference(2)),(((('index',2),),2),),(Membership('incarnation',1,0),)),
    ('aux.lazy.sequence.nodes',(1,1),('leaf',((17,HistoryReference('list',2)),(19,RecordReference(3)))),
        (((('key',17),),2),((('key',19),),3)),()),
    ('aux.lazy.records.headers',(1,0),('recursive-record/v1','core.Event/v1',
        (1,0,'fixture',Layer.REALITY,(),None,(),HistoryReference('map',2)),(True,True)),
        (((('field','data'),),2),),()),
    ('aux.lazy.keys.nan_atoms',(1,0),('native-nan-key/v1',bytes.fromhex('fff8000000000042')),(),()),
])
def test_all_existing_physical_adapters(namespace,key,value,placements,memberships,tmp_path):
    store,pin,pairs=make_projection_store(tmp_path/'p.sqlite',namespace=namespace,key=key,value=value,placements=placements,memberships=memberships)
    result=read_projection(store,pin,pairs)
    assert result.reference_count==len(placements) and result.source.payload==store.codec.encode(value)
    store.close()


def test_key_side_nan_frozenset_and_repeated_references_keep_raw_paths(tmp_path):
    atom=NonreflexiveKeyReference(2);key=frozenset((atom,3));value=(0,key,(HistoryReference('list',4),HistoryReference('list',4),-0.0))
    paths=(((('index',1),('key',atom)),2),((('index',2),('index',0)),4),((('index',2),('index',1)),4))
    store,pin,pairs=make_projection_store(tmp_path/'p.sqlite',namespace='aux.lazy.nested.entries',key=(1,key),value=value,
        placements=paths,memberships=(Membership('incarnation',1,0),))
    result=read_projection(store,pin,pairs)
    assert result.reference_count==3 and result.source.payload==store.codec.encode(value)
    assert b'8000000000000000' in result.source.payload
    store.close()


@pytest.mark.parametrize('fault',['missing','surplus','replacement'])
def test_independently_valid_authorities_must_agree_on_all_references(tmp_path,fault):
    placements=PAGE_PLACEMENTS[:-1] if fault=='missing' else PAGE_PLACEMENTS+(((('index',9),),2),) if fault=='surplus' else PAGE_PLACEMENTS[:-1]+((PAGE_PLACEMENTS[-1][0],6),)
    store,pin,pairs=make_projection_store(tmp_path/'p.sqlite',placements=placements)
    with pytest.raises(StoreIntegrityError):read_projection(store,pin,pairs)
    store.close()


@pytest.mark.parametrize('present,placements,valid',[(False,(),True),(False,PAGE_PLACEMENTS,False),(True,(),True)])
def test_empty_and_absent_owner_do_not_hide_orphans(tmp_path,present,placements,valid):
    store,pin,pairs=make_projection_store(tmp_path/'p.sqlite',present=present,value=(1,-0.0),placements=placements)
    if valid:
        r=read_projection(store,pin,pairs);assert r.reference_count==0 and (r.source is None)==(not present)
    else:
        with pytest.raises(StoreIntegrityError):read_projection(store,pin,pairs)
    store.close()


@pytest.mark.parametrize('value,memberships',[
    ([1],()),(({'a':1},),()),((set((1,)),),()),((RecordReference(10),),()),
    ((1,),(Membership('wrong',2,0),)),
])
def test_invalid_storage_values_memberships_and_unallocated_targets_rejected(tmp_path,value,memberships):
    store,pin,pairs=make_projection_store(tmp_path/'p.sqlite',value=value,placements=(),memberships=memberships)
    with pytest.raises(StoreIntegrityError):read_projection(store,pin,pairs)
    store.close()


def test_multiple_root_pages_and_reference_budget(tmp_path):
    value=(tuple(HistoryReference('list',2) for i in range(130)),)
    placements=tuple(((('index',0),('index',i)),2) for i in range(130))
    store,pin,pairs=make_projection_store(tmp_path/'p.sqlite',value=value,placements=placements)
    assert read_projection(store,pin,pairs).reference_count==130
    with pytest.raises(projection_module().ProjectionProofBudgetError):read_projection(store,pin,pairs,max_references=129)
    store.close()


@pytest.mark.parametrize('kind',['body','depth','nodes','path'])
def test_explicit_work_budgets_fail_closed(tmp_path,kind):
    value=(1,);placements=()
    if kind=='depth':
        for _ in range(66):value=(value,)
    elif kind=='nodes':value=(tuple(1 for _ in range(17000)),)
    elif kind=='path':
        value=(frozenset((Ref('x'*4200,NonreflexiveKeyReference(2)),)),)
        placements=(((('index',0),('key',next(iter(value[0]))),('field','id')),2),)
    store,pin,pairs=make_projection_store(tmp_path/'p.sqlite',value=value,placements=placements)
    with pytest.raises(StoreError):read_projection(store,pin,pairs,**({'max_bytes':1} if kind=='body' else {}))
    assert not store.db.in_transaction;store.close()


def test_authority_context_and_codec_hooks_are_rejected(tmp_path):
    store,pin,pairs=make_projection_store(tmp_path/'p.sqlite')
    with pytest.raises(StoreIntegrityError):read_projection(store,pin,((pairs[0][0],b'x'*32),pairs[1]))
    with pytest.raises(StoreIntegrityError):read_projection(store,pin,(pairs[0],(pairs[1][0],b'x'*32)))
    wrong=replace(pairs[0][0],generation=0)
    from ate_sim.persistence_proof_version import certificate_commitment
    with pytest.raises(StoreConflictError):read_projection(store,pin,((wrong,certificate_commitment(wrong)),pairs[1]))
    class Custom(WorldCodec):
        def decode(self,payload):raise AssertionError('caller decode hook executed')
    original=store.codec;store.codec=Custom()
    with pytest.raises(StoreError):read_projection(store,pin,pairs)
    store.codec=original;store.close()


@pytest.mark.parametrize('fault',['cached','missing','definition','transaction','released','payload'])
def test_capability_snapshot_and_fetched_corruption(tmp_path,fault):
    store,pin,pairs=make_projection_store(tmp_path/'p.sqlite')
    if fault=='cached':store._interval_indexes.discard('lazy_record_interval')
    elif fault=='missing':store.db.execute('DROP INDEX lazy_record_interval')
    elif fault=='definition':
        store.db.execute('DROP INDEX lazy_record_interval');store.db.execute('CREATE INDEX lazy_record_interval ON lazy_record_versions(namespace,typed_key,valid_from,valid_to)')
    elif fault=='transaction':store.db.execute('BEGIN')
    elif fault=='released':store.release_pin(pin)
    else:store.db.execute("UPDATE lazy_record_versions SET payload=? WHERE namespace=?",(b'corrupt',PAGE))
    if fault!='transaction':store.db.commit()
    with pytest.raises(StoreError):read_projection(store,pin,pairs)
    if fault=='transaction':assert store.db.in_transaction;store.db.rollback()
    else:assert not store.db.in_transaction
    store.close()


def test_retained_source_and_placements_after_replacement_and_delete(tmp_path):
    store,pin,pairs=make_projection_store(tmp_path/'p.sqlite');old=store.capture_pin()
    writer=store.commit(pin,commit_token='change',version_changes=(VersionChange(PAGE,(1,0),(HistoryReference('list',6),)),),
        identity_changes=tuple(IdentityOccurrenceChange(PAGE,(1,0),path,delete=True) for path,_ in PAGE_PLACEMENTS[1:])+
            (IdentityOccurrenceChange(PAGE,(1,0),PAGE_PLACEMENTS[0][0],6),),
        next_incarnation_id=10,changes=(),new_segments=(),metadata=metadata(2)).pin
    assert read_projection(store,old,pairs).source.payload==store.codec.encode(PAGE_VALUE)
    current=authorities(store,writer)
    with store.read_transaction():
        with store.read_snapshot(writer):assert read_projection(store,writer,current).reference_count==1
    assert read_projection(store,writer,current).source.payload==store.codec.encode((HistoryReference('list',6),))
    store.close()


def test_native_record_envelopes_never_restore_world_objects(tmp_path):
    from ate_sim.core import Event
    value=(Event(1,0,'fixture',Layer.REALITY),)
    store,pin,pairs=make_projection_store(tmp_path/'p.sqlite',value=value,placements=())
    with pytest.raises(StoreIntegrityError):read_projection(store,pin,pairs)
    store.close()


@pytest.mark.parametrize('budget,value',[('max_bytes',0),('max_references',0),('max_metadata_bytes',False),('max_references',4097)])
def test_invalid_budgets_do_not_open_snapshot(tmp_path,budget,value):
    store,pin,pairs=make_projection_store(tmp_path/'p.sqlite')
    with pytest.raises(StoreIntegrityError):read_projection(store,pin,pairs,**{budget:value})
    assert not store.db.in_transaction;store.close()


def test_unknown_scope_and_unallocated_owner_rejected(tmp_path):
    from ate_sim.persistence_proof_occurrence import GroupScope
    from ate_sim.persistence_proof_occurrence_seek import certificate_commitment
    store,pin,pairs=make_projection_store(tmp_path/'p.sqlite',key=(10,0),value=(1,),placements=())
    with pytest.raises(StoreIntegrityError):read_projection(store,pin,pairs)
    for scope in (GroupScope(1),replace(pairs[1][0].scope,namespace='world.people')):
        cert=replace(pairs[1][0],scope=scope)
        with pytest.raises(StoreError):read_projection(store,pin,(pairs[0],(cert,certificate_commitment(cert))))
    store.close()


@pytest.mark.parametrize('column',['simulation_position','next_ids'])
def test_changed_head_metadata_cannot_restore_native_records(tmp_path,column):
    from ate_sim.core import Event
    from ate_sim.incremental_store import _head_checksum
    store,pin,pairs=make_projection_store(tmp_path/'p.sqlite')
    blob=store.codec.encode(Event(99,0,'metadata',Layer.REALITY))
    store.db.execute(f'UPDATE save_head SET {column}=? WHERE singleton=1',(blob,))
    row=store.db.execute('SELECT generation,parent_generation,simulation_position,seed,next_ids,namespace_inventory,namespace_counts FROM save_head').fetchone()
    store.db.execute('UPDATE save_head SET head_checksum=?',(_head_checksum(*row),));store.db.commit()
    with pytest.raises(StoreIntegrityError):read_projection(store,pin,pairs)
    assert not store.db.in_transaction;store.close()


def test_instance_codec_hooks_are_never_invoked(tmp_path):
    store,pin,pairs=make_projection_store(tmp_path/'p.sqlite');calls=[];original=store.codec.decode
    store.codec.decode=lambda payload:(calls.append(payload),original(payload))[1]
    with pytest.raises(StoreError):read_projection(store,pin,pairs)
    assert calls==[] and not store.db.in_transaction;store.close()


def test_surrogate_schema_encoding_is_an_integrity_failure(tmp_path):
    from ate_sim.incremental_store import _framed_sha
    value=(frozenset((Ref('x',NonreflexiveKeyReference(2)),)),)
    paths=(((('index',0),('key',next(iter(value[0]))),('field','id')),2),)
    store,pin,_pairs=make_projection_store(tmp_path/'p.sqlite',value=value,placements=paths)
    ns,key,start,end,schema,codec,members,payload=store.db.execute(
        'SELECT namespace,typed_key,valid_from,valid_to,record_schema,codec_version,memberships,payload FROM lazy_record_versions').fetchone()
    payload=payload.replace(b'"x"',b'"\\ud800"')
    store.db.execute('UPDATE lazy_record_versions SET payload=?,payload_checksum=?,row_checksum=?',
        (payload,_framed_sha(b'lazy-payload-v1',payload),_version_checksum(ns,key,schema,codec,start,end,members,payload)))
    store.db.commit();pairs=authorities(store,pin)
    with pytest.raises(StoreIntegrityError):read_projection(store,pin,pairs)
    assert not store.db.in_transaction;store.close()


@pytest.mark.parametrize('kwargs',[{'max_bytes':1},{'max_metadata_bytes':1}])
def test_delegated_budgets_have_projection_error_type(tmp_path,kwargs):
    store,pin,pairs=make_projection_store(tmp_path/'p.sqlite')
    with pytest.raises(projection_module().ProjectionProofBudgetError):read_projection(store,pin,pairs,**kwargs)
    assert not store.db.in_transaction;store.close()


def test_delegated_occurrence_field_budget_has_projection_error_type(tmp_path):
    placement=(((('index',0),('key','x'*4200)),2),)
    store,pin,pairs=make_projection_store(tmp_path/'p.sqlite',value=(HistoryReference('list',2),),placements=placement)
    with pytest.raises(projection_module().ProjectionProofBudgetError):read_projection(store,pin,pairs)
    assert not store.db.in_transaction;store.close()
