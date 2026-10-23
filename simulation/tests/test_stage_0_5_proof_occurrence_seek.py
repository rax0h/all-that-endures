"""Retained root order must ignore unrelated newer source placements."""
from dataclasses import replace
import hashlib

import pytest

from ate_sim.incremental_store import StoreError, StoreConflictError, StoreIntegrityError
from ate_sim.persistence_lazy_store import IdentityOccurrenceChange,VersionChange,_identity_occurrence_checksum
from ate_sim.persistence_proof_occurrence import OwnerScope,GroupScope
from simulation.tests.proof_occurrence_fixtures import make_occurrence_store,metadata
from simulation.tests.proof_occurrence_seek_fixtures import seek_module,construct_seek_certificates
from simulation.tests.test_stage_0_5_proof_order import frame


def setup_source(tmp_path):
    s=seek_module();store,pin=make_occurrence_store(tmp_path/'seek-source.sqlite',3)
    certs=construct_seek_certificates(store,pin,(GroupScope(1),OwnerScope('people',store.codec.encode(0)),GroupScope(2)))
    return s,store,pin,certs


def read(s,store,pin,pair,**kwargs):return s.read_occurrence_seek_page(store,pin,*pair,**kwargs)


def test_exact_framing_and_arbitrary_middle_cursors(tmp_path):
    s,store,pin,certs=setup_source(tmp_path);cert,expected=certs[0]
    from ate_sim.persistence_proof_occurrence import occurrence_domain
    base=occurrence_domain(store.store_identity,1,cert.scope)
    domain=hashlib.sha256(frame(b'ate-occurrence-seek-domain/1',base)).digest()
    assert s.seek_domain(store.store_identity,1,cert.scope)==domain
    assert expected==hashlib.sha256(frame(b'ate-occurrence-seek-certificate/1',domain,
        (1).to_bytes(8,'big'),(6).to_bytes(8,'big'),cert.root.digest,cert.root.count.to_bytes(8,'big'))).digest()
    allrows=read(s,store,pin,certs[0]).rows
    for after in [('people',store.codec.encode(0),b'not-an-existing-position'),('people',b'',b''),('zz',b'',b'')]:
        expected_rows=tuple(r for r in allrows if (r.namespace,r.typed_key,r.path)>after)
        assert read(s,store,pin,certs[0],after=after).rows==expected_rows
    store.close()


def test_current_pages_owner_agreement_and_zero_payload_reads(tmp_path):
    s,store,pin,certs=setup_source(tmp_path);sql=[];store.reset_diagnostics();store.db.set_trace_callback(sql.append)
    rows=[];after=None
    while True:
        page=read(s,store,pin,certs[0],after=after,limit=3);rows.extend(page.rows)
        if page.next_after is None:break
        after=page.next_after
    assert len(rows)==8
    assert read(s,store,pin,certs[1]).rows==tuple(r for r in rows if r.typed_key==store.codec.encode(0))
    assert read(s,store,pin,certs[2]).rows==()
    store.db.set_trace_callback(None)
    assert store._payload_reads==0 and store._payload_check_reads==0
    assert not any('FROM '+t in q for q in sql for t in ('records','lazy_record_versions','segments'))
    store.close()


@pytest.mark.parametrize('count',[1000,10000])
def test_old_empty_and_nonempty_pages_return_exact_despite_newer_frontier(tmp_path,count):
    s,store,pin,certs=setup_source(tmp_path);old=store.capture_pin()
    original=read(s,store,old,certs[0]).rows
    def changes():
        yield IdentityOccurrenceChange('people',0,(('field','other'),),2)
        yield IdentityOccurrenceChange('people',1,(('field','shared'),),delete=True)
        for i in range(2*count):yield IdentityOccurrenceChange('archive',i+10,(),1 if i<count else 2)
    writer=store.commit(pin,commit_token='frontier',version_changes=(VersionChange('archive',i+10,i) for i in range(2*count)),
        identity_changes=changes(),next_incarnation_id=6,changes=(),new_segments=(),metadata=metadata(2)).pin
    assert store.db.execute(
        "SELECT incarnation_id,count(*) FROM lazy_identity_occurrence_versions "
        "WHERE owner_namespace='archive' AND valid_from=2 GROUP BY incarnation_id ORDER BY incarnation_id"
    ).fetchall()==[(1,count),(2,count)]
    steps=0
    def progress():
        nonlocal steps
        steps+=1;return 0
    store.db.set_progress_handler(progress,1)
    try:
        assert read(s,store,old,certs[0],limit=4).rows==original[:4]
        assert len(read(s,store,old,certs[1]).rows)==2
        assert read(s,store,old,certs[2]).rows==()
    finally:store.db.set_progress_handler(None,0)
    assert steps<20000
    current=construct_seek_certificates(store,writer,(GroupScope(1),))[0]
    assert current[0].root.count==count+6
    assert len(read(s,store,writer,current).rows)==128
    store.close()


@pytest.mark.parametrize('fault',['payload-row','missing','overlap','node'])
def test_selected_physical_or_proof_corruption_is_rejected(tmp_path,fault):
    s,store,pin,certs=setup_source(tmp_path)
    row=list(store.db.execute('SELECT owner_namespace,owner_key,occurrence_path,incarnation_id,valid_from,valid_to,row_checksum '
        'FROM lazy_identity_occurrence_versions WHERE owner_namespace=? AND owner_key=? LIMIT 1',('people',store.codec.encode(0))).fetchone())
    if fault=='node':store.db.execute('DELETE FROM ate_ordered_seek_nodes WHERE digest=?',(certs[0][0].root.digest,))
    elif fault=='missing':store.db.execute('DELETE FROM lazy_identity_occurrence_versions WHERE owner_namespace=? AND owner_key=? AND occurrence_path=?',row[:3])
    elif fault=='overlap':
        row[3:6]=[2,0,2];row[6]=_identity_occurrence_checksum(*row[:6]);store.db.execute('INSERT INTO lazy_identity_occurrence_versions VALUES(?,?,?,?,?,?,?)',row)
    else:
        row[3]=2;row[6]=_identity_occurrence_checksum(*row[:6]);store.db.execute('UPDATE lazy_identity_occurrence_versions SET incarnation_id=?,row_checksum=? '
            'WHERE owner_namespace=? AND owner_key=? AND occurrence_path=?',(2,row[6],*row[:3]))
    store.db.commit()
    with pytest.raises(StoreIntegrityError):read(s,store,pin,certs[0])
    store.close()


def test_unselected_surplus_never_enters_root_results_not_claimed_scrubbed(tmp_path):
    s,store,pin,certs=setup_source(tmp_path);original=read(s,store,pin,certs[0]).rows
    row=list(store.db.execute('SELECT owner_namespace,owner_key,occurrence_path,incarnation_id,valid_from,valid_to,row_checksum '
        'FROM lazy_identity_occurrence_versions WHERE incarnation_id=1 LIMIT 1').fetchone())
    row[2]=store.codec.encode((('field','forged-extra'),));row[6]=_identity_occurrence_checksum(*row[:6])
    store.db.execute('INSERT INTO lazy_identity_occurrence_versions VALUES(?,?,?,?,?,?,?)',row);store.db.commit()
    assert read(s,store,pin,certs[0]).rows==original
    # The forged physical row still exists: selection did not silently scrub it.
    assert store.db.execute('SELECT count(*) FROM lazy_identity_occurrence_versions WHERE incarnation_id=1').fetchone()[0]==9
    store.close()


@pytest.mark.parametrize('field',['store','generation','codec','scope','allocator','expected'])
def test_wrong_authority_and_context(tmp_path,field):
    s,store,pin,certs=setup_source(tmp_path);cert,expected=certs[0]
    if field=='store':cert=replace(cert,store_identity='other')
    elif field=='generation':cert=replace(cert,generation=0)
    elif field=='codec':cert=replace(cert,codec_version=2)
    elif field=='scope':cert=replace(cert,scope=GroupScope(2))
    elif field=='allocator':cert=replace(cert,next_incarnation_id=7);expected=s.certificate_commitment(cert)
    else:expected=b'x'*32
    with pytest.raises((StoreIntegrityError,StoreConflictError)):read(s,store,pin,(cert,expected))
    store.close()


def test_owned_nested_transactions_missing_interval_and_released_pin(tmp_path):
    s,store,pin,certs=setup_source(tmp_path)
    with store.read_transaction():
        with store.read_snapshot(pin):assert len(read(s,store,pin,certs[0]).rows)==8
        assert store.db.in_transaction
    store.db.execute('BEGIN')
    with pytest.raises(StoreError):read(s,store,pin,certs[0])
    assert store.db.in_transaction;store.db.rollback()
    store._interval_indexes.discard('lazy_identity_occurrence_interval')
    with pytest.raises(StoreError):read(s,store,pin,certs[0])
    store._interval_indexes.add('lazy_identity_occurrence_interval');store.release_pin(pin)
    with pytest.raises(StoreConflictError):read(s,store,pin,certs[0])
    store.close()


@pytest.mark.parametrize('fields,position',[
    (('n',b'',b''),b'n\x00\x00\x00\x00\x00\x00'),
    (('é界',b'a\x00',b'\x00a'),b'\xc3\xa9\xe7\x95\x8c\x00\x00a\x00\xff\x00\x00\x00\xffa\x00\x00'),
    (('n',b'a',b'ab'),b'n\x00\x00a\x00\x00ab\x00\x00'),
])
def test_group_position_exact_escape_and_utf8_vectors(fields,position):
    s=seek_module()
    from ate_sim.persistence_proof_occurrence import group_order_key
    assert group_order_key(*fields)==position
    assert s._decode_group_position(position)==fields


@pytest.mark.parametrize('position',[
    b'n\x00',b'n\x00\x01',b'n\x00\x00',b'n\x00\x00k\x00\x00p',
    b'n\x00\x00k\x00\x00p\x00\x00extra\x00\x00',
    b'\xff\x00\x00k\x00\x00p\x00\x00',
    b'n\x00\xff\x00\x00k\x00\x00p\x00\x00',
    b'\x00\x00k\x00\x00p\x00\x00',
])
def test_group_position_rejects_malformed_fields(position):
    with pytest.raises(StoreIntegrityError):seek_module()._decode_group_position(position)


@pytest.mark.parametrize('field',[0,1,2])
@pytest.mark.parametrize('length',[4096,4097])
def test_group_position_individual_field_budget(field,length):
    s=seek_module()
    from ate_sim.persistence_proof_occurrence import group_order_key,OccurrenceProofBudgetError
    fields=['n',b'k',b'p'];fields[field]='n'*length if field==0 else b'x'*length
    position=group_order_key(*fields)
    if length==4096:assert s._decode_group_position(position)==tuple(fields)
    else:
        with pytest.raises(OccurrenceProofBudgetError):s._decode_group_position(position)
