"""Explicit opening authenticates before canonical restoration without a full audit."""
import importlib
import sqlite3
import sys
from pathlib import Path
import pytest

from ate_sim.incremental_store import StoreError, _head_checksum, TypedCodec
from simulation.tests.proof_world_fixtures import make_world
from simulation.tests.test_stage_0_5_proof_world_session import fixture, opened

RULES='private-catalog-copy'


def ranked_fixture(tmp_path,**kwargs):
    from ate_sim.persistence_proof_world_copy import copy_world_with_proofs
    store,pin,*_rest=make_world(tmp_path/'source',**kwargs)
    source=store.path;store.release_pin(pin);store.close()
    path=tmp_path/'ranked.sqlite'
    result=copy_world_with_proofs(source,path,rules_id=RULES,rank_proofs=True)
    return path,(result.manifest,result.commitment)


def fast_open(path,pair,**kwargs):
    api=importlib.import_module('ate_sim.persistence_proof_world_session')
    return api.open_proof_world_session(path,rules_id=kwargs.pop('rules_id',RULES),
        expected_commitment=pair[1],**kwargs)


def pin_count(path):
    db=sqlite3.connect(path)
    try:return db.execute('SELECT count(*) FROM generation_pins').fetchone()[0]
    finally:db.close()


def forbid_audits(monkeypatch):
    from ate_sim import persistence_proof_world as world,persistence_catalog_copy as catalog
    from ate_sim.persistence_lazy_store import LazyRecordStore
    def forbidden(*args,**kwargs):raise AssertionError('proof opening ran a full audit')
    monkeypatch.setattr(world,'_audit_world',forbidden)
    monkeypatch.setattr(catalog,'_verify_catalog',forbidden)
    monkeypatch.setattr(LazyRecordStore,'verify_all',forbidden)


def test_existing_audited_six_root_opener_remains_compatible(tmp_path):
    path,pair=fixture(tmp_path,size=4)
    with opened(path,pair) as session:
        assert session.skills[1,'craft'].provenance is session.skills[2,'craft'].provenance
    assert pin_count(path)==0


def test_proof_open_restores_shared_identity_without_full_audit(tmp_path,monkeypatch):
    path,pair=ranked_fixture(tmp_path,size=4)
    forbid_audits(monkeypatch)
    with fast_open(path,pair) as session:
        assert session.proof_manifest==pair
        assert session.skills[1,'craft'].provenance is session.skills[2,'craft'].provenance
        assert not session.store.db.in_transaction
    assert pin_count(path)==0


def test_proof_open_scalar_save_and_fresh_reopen_use_existing_publisher(tmp_path,monkeypatch):
    path,pair=ranked_fixture(tmp_path,size=4)
    forbid_audits(monkeypatch)
    with fast_open(path,pair) as session:
        assert session.save()==0
        session.skills[1,'craft'].level=.375
        assert session.save()==1
        child=session.proof_manifest
    with fast_open(path,child) as restored:
        assert restored.skills[1,'craft'].level==.375
        assert restored.skills[1,'craft'].provenance is restored.skills[2,'craft'].provenance
    assert pin_count(path)==0


def test_six_root_proof_open_rejects_without_implicit_audit(tmp_path,monkeypatch):
    path,pair=fixture(tmp_path,size=4)
    forbid_audits(monkeypatch)
    with pytest.raises(StoreError):fast_open(path,pair)
    assert pin_count(path)==0


@pytest.mark.parametrize('bad',[None,False,1,b'bad','a'*64,b'\0'*32])
def test_proof_open_requires_exact_external_commitment(tmp_path,bad):
    path,pair=ranked_fixture(tmp_path,size=4)
    with pytest.raises(StoreError):fast_open(path,(pair[0],bad))
    assert pin_count(path)==0


@pytest.mark.parametrize('field',['seed','position','counts','inventory','next_ids'])
def test_proof_open_rejects_coherent_head_forgery_before_decode(tmp_path,monkeypatch,field):
    from ate_sim.persistence_adapters import WorldCodec
    path,pair=ranked_fixture(tmp_path,size=4)
    codec=WorldCodec(identity_links_recorded=True);db=sqlite3.connect(path)
    row=list(db.execute('SELECT generation,parent_generation,simulation_position,seed,next_ids,namespace_inventory,namespace_counts,head_checksum FROM save_head').fetchone())
    slot={'seed':3,'position':2,'next_ids':4,'inventory':5,'counts':6}[field]
    row[slot]=row[3]+1 if field=='seed' else codec.encode(777 if field=='position' else {} if field=='next_ids' else ())
    forged=row[slot];row[-1]=_head_checksum(*row[:-1])
    db.execute('UPDATE save_head SET simulation_position=?,seed=?,next_ids=?,namespace_inventory=?,namespace_counts=?,head_checksum=?',(*row[2:7],row[-1]));db.commit();db.close()
    decode=TypedCodec.decode;seen=[]
    def observe(self,raw):
        if raw==forged:seen.append(True)
        return decode(self,raw)
    monkeypatch.setattr(TypedCodec,'decode',observe)
    with pytest.raises(StoreError):fast_open(path,pair)
    assert not seen
    assert pin_count(path)==0


@pytest.mark.parametrize('damage',['rules','format','metadata-size','manifest-size','scope-roots'])
def test_proof_open_fixed_context_and_budget_failures_leave_no_pin(tmp_path,damage):
    path,pair=ranked_fixture(tmp_path,size=4);db=sqlite3.connect(path)
    if damage=='rules':db.execute("UPDATE store_metadata SET value='other-rules' WHERE key='rules_id'")
    elif damage=='format':db.execute("UPDATE store_metadata SET value='6' WHERE key='format_version'")
    elif damage=='metadata-size':db.execute("UPDATE store_metadata SET value=? WHERE key='rules_id'",('x'*1048577,))
    elif damage=='manifest-size':db.execute('UPDATE ate_generation_manifests SET manifest=?',(b'x'*(2*1048576+1),))
    else:db.execute("UPDATE ate_scope_generations SET roots=x'00'")
    db.commit();db.close()
    with pytest.raises(StoreError):fast_open(path,pair)
    assert pin_count(path)==0


def forge_head(store,position):
    row=list(store.db.execute('SELECT generation,parent_generation,simulation_position,seed,next_ids,namespace_inventory,namespace_counts,head_checksum FROM save_head').fetchone())
    row[2]=store.codec.encode(position);row[-1]=_head_checksum(*row[:-1])
    store.db.execute('UPDATE save_head SET simulation_position=?,head_checksum=?',(row[2],row[-1]))
    return row[2]


def test_head_change_after_pin_capture_releases_exact_owned_lease(tmp_path,monkeypatch):
    from ate_sim.persistence_lazy_store import LazyRecordStore
    path,pair=ranked_fixture(tmp_path,size=4);capture=LazyRecordStore.capture_pin;changed=[]
    def advance(store,*a,**k):
        pin=capture(store,*a,**k)
        if not changed:
            changed.append(True);forge_head(store,901);store.db.commit()
        return pin
    monkeypatch.setattr(LazyRecordStore,'capture_pin',advance)
    with pytest.raises(StoreError):fast_open(path,pair)
    assert changed and pin_count(path)==0


def test_private_fast_admission_rejects_foreign_capability_before_callback(tmp_path):
    from ate_sim.persistence_lazy import open_lazy_world_session
    path,pair=ranked_fixture(tmp_path,size=4);called=[]
    class ForeignAdmission:
        proof_only=True
        expected=pair[1]
        def bind(self,store):
            called.append(True)
            raise AssertionError('foreign admission callback executed')
    with pytest.raises(StoreError):open_lazy_world_session(path,rules_id=RULES,_proof_admission=ForeignAdmission())
    assert not called and pin_count(path)==0


@pytest.mark.parametrize('damage',['epoch','epoch-rebind','pin','components','codec-method'])
def test_last_restore_context_drift_rejects_without_audit_or_lease_leak(tmp_path,monkeypatch,damage):
    from ate_sim import persistence_proof_world_session as api
    path,pair=ranked_fixture(tmp_path,size=4);original=api._restore_current_event_aliases;reached=[];returned=None
    def drift(session):
        original(session);store=session.store;authority=store._world_proof_authority;reached.append(True)
        if damage in ('epoch','epoch-rebind'):
            store.db.execute("UPDATE records SET payload_checksum='changed' WHERE namespace='world.year'")
            if damage=='epoch-rebind':authority.epoch=authority._epoch()
        elif damage=='pin':
            from dataclasses import replace
            authority.read_pin=replace(authority.read_pin,token='f'*32)
        elif damage=='components':authority.read_components=tuple(reversed(authority.read_components))
        else:store.codec.decode=lambda raw:None
    monkeypatch.setattr(api,'_restore_current_event_aliases',drift)
    forbid_audits(monkeypatch)
    try:
        with pytest.raises(StoreError):returned=fast_open(path,pair)
    finally:
        if returned is not None:
            if damage=='codec-method':del returned.store.codec.decode
            returned.close()
    assert reached and pin_count(path)==0


def test_restore_error_preserves_primary_exception_and_avoids_forged_head_decode(tmp_path,monkeypatch):
    from ate_sim import persistence_proof_world_session as api
    path,pair=ranked_fixture(tmp_path,size=4);original=api._restore_current_event_aliases;forged=[];seen=[];decode=TypedCodec.decode
    def fail(session):
        original(session);forged.append(forge_head(session.store,902))
        raise ValueError('injected final restoration failure')
    def observe(self,raw):
        if forged and raw==forged[0]:seen.append(True)
        return decode(self,raw)
    monkeypatch.setattr(TypedCodec,'decode',observe)
    monkeypatch.setattr(api,'_restore_current_event_aliases',fail)
    forbid_audits(monkeypatch)
    with pytest.raises(ValueError,match='injected final restoration failure'):fast_open(path,pair)
    assert forged and not seen and pin_count(path)==0


def test_restore_cleanup_rechecks_original_pin_after_snapshot_release(tmp_path,monkeypatch):
    from dataclasses import replace
    from ate_sim.persistence_lazy_store import LazyRecordStore
    path,pair=ranked_fixture(tmp_path,size=4);capture=LazyRecordStore.capture_pin;reached=[]
    def observe(store,*a,**k):
        pin=capture(store,*a,**k)
        def trace(sql):
            authority=store._world_proof_authority
            if sql.strip()=='ROLLBACK' and authority is not None and authority._opening_admitted and not reached:
                reached.append(True);authority.read_pin=replace(authority.read_pin,token='e'*32)
        store.db.set_trace_callback(trace)
        return pin
    monkeypatch.setattr(LazyRecordStore,'capture_pin',observe)
    with pytest.raises(StoreError):fast_open(path,pair)
    assert reached and pin_count(path)==0


def test_restore_connection_rebinding_does_not_rollback_or_close_foreign_connection(tmp_path,monkeypatch):
    from ate_sim import persistence_proof_world_session as api
    path,pair=ranked_fixture(tmp_path,size=4);original=api._restore_current_event_aliases;handles=[]
    foreign=sqlite3.connect(tmp_path/'foreign.sqlite',timeout=.05)
    foreign.execute('CREATE TABLE user_work(value INTEGER)')
    foreign.execute('INSERT INTO user_work VALUES(123)')
    def replace_connection(session):
        original(session);handles.append(session.store.db);session.store.db=foreign
    monkeypatch.setattr(api,'_restore_current_event_aliases',replace_connection)
    try:
        with pytest.raises(StoreError):fast_open(path,pair)
        assert foreign.in_transaction
        assert foreign.execute('SELECT value FROM user_work').fetchall()==[(123,)]
        with pytest.raises(sqlite3.ProgrammingError):handles[0].execute('SELECT 1')
        assert pin_count(path)==0
    finally:
        foreign.close()
        for db in handles:db.close()


@pytest.mark.parametrize('namespace,key,value',[
    ('world.year',0,(0,999)),
    ('snapshot.meta','manifest',{'schema':'coherent-but-unaccepted'}),
])
def test_selected_ordinary_source_forgery_rejects_before_body_decode(tmp_path,monkeypatch,namespace,key,value):
    from ate_sim.persistence_adapters import WorldCodec
    from ate_sim.incremental_store import _record_checksum
    path,pair=ranked_fixture(tmp_path,size=4);codec=WorldCodec(identity_links_recorded=True);db=sqlite3.connect(path)
    if namespace=='snapshot.meta':
        from ate_sim.persistence_adapters import META
        namespace=META
    encoded=codec.encode(key);payload=codec.encode(value)
    old=db.execute('SELECT record_schema,codec_version,last_changed_generation FROM records WHERE namespace=? AND typed_key=?',(namespace,encoded)).fetchone()
    assert old is not None
    checksum=_record_checksum(namespace,encoded,*old,payload)
    db.execute('UPDATE records SET payload=?,payload_checksum=? WHERE namespace=? AND typed_key=?',(payload,checksum,namespace,encoded));db.commit();db.close()
    decode=TypedCodec.decode;seen=[]
    def observe(self,raw):
        if raw==payload:seen.append(True)
        return decode(self,raw)
    monkeypatch.setattr(TypedCodec,'decode',observe)
    forbid_audits(monkeypatch)
    with pytest.raises(StoreError):fast_open(path,pair)
    assert not seen and pin_count(path)==0


@pytest.mark.parametrize('damage',['store-identity','session-pin','session-pin-cleanup'])
def test_restore_preserves_store_identity_and_session_owned_pin(tmp_path,monkeypatch,damage):
    from dataclasses import replace
    from ate_sim import persistence_proof_world_session as api
    path,pair=ranked_fixture(tmp_path,size=4);original=api._restore_current_event_aliases;reached=[];returned=None
    def drift(session):
        original(session);store=session.store
        if damage=='store-identity':
            reached.append(True);store.store_identity='foreign-store'
        elif damage=='session-pin':
            reached.append(True);session.pin=replace(session.pin,token='c'*32)
        else:
            def trace(sql):
                if sql.strip()=='ROLLBACK' and store._owned_open_read is None and not reached:
                    reached.append(True);session.pin=replace(session.pin,token='b'*32)
            store.db.set_trace_callback(trace)
    monkeypatch.setattr(api,'_restore_current_event_aliases',drift)
    try:
        with pytest.raises(StoreError):returned=fast_open(path,pair)
    finally:
        if returned is not None:
            returned.store.store_identity=pair[0].store_identity
            returned.pin=returned.store._world_proof_authority.read_pin
            returned.close()
    assert reached and pin_count(path)==0


@pytest.mark.parametrize('phase',['before_head','before_commit','after_commit'])
def test_proof_open_failed_save_resolves_original_receipt_and_reopens(tmp_path,phase):
    path,pair=ranked_fixture(tmp_path,size=4)
    with fast_open(path,pair) as session:
        session.skills[1,'craft'].level=.125
        def interrupt(at):
            if at==phase:raise RuntimeError('proof opening recovery control')
        session.store._phase_hook=interrupt
        with pytest.raises(RuntimeError,match='proof opening recovery control'):session.save()
        session.store._phase_hook=lambda at:None
        assert session.resolve_save()==(1 if phase=='after_commit' else 0)
        assert session.skills[1,'craft'].level==.125
        assert session.save()==1
        child=session.proof_manifest
    with fast_open(path,child) as restored:
        assert restored.skills[1,'craft'].level==.125
        assert restored.skills[1,'craft'].provenance is restored.skills[2,'craft'].provenance
    assert pin_count(path)==0


@pytest.fixture(scope='module',params=[1,4])
def sealed_ranked_fixture(request,tmp_path_factory):
    from ate_sim.event_log import EventLog
    from ate_sim.core import Layer
    segments=request.param
    def configure(world):
        world.events=EventLog()
        for number in range(segments*EventLog.chunk_size):world.emit('archived-open-control',Layer.REALITY,n=number)
        world.events.seal_before(1);world.year=1
        shared=[7]
        world.emit('current-open-control',Layer.REALITY,shared=shared)
        world.emit('current-open-alias',Layer.REALITY,shared=shared)
    path,pair=ranked_fixture(tmp_path_factory.mktemp('proof-open-sealed-'+str(segments)),size=4,configure=configure)
    return segments,path,pair


def segment_payload_reads(monkeypatch):
    """Observe actual returned segment BLOBs, including iterators and fetch APIs."""
    import re
    from ate_sim.persistence_sqlite_guard import _NativeGuardCursor
    reads=[];execute=_NativeGuardCursor.execute
    def executed(cursor,sql,*args,**kwargs):
        cursor._opening_probe_sql=sql
        return execute(cursor,sql,*args,**kwargs)
    def observe(cursor,row):
        if row is not None and re.search(r'\b(?:from|join)\s+(?:main\.)?segments\b',getattr(cursor,'_opening_probe_sql',''),re.I):
            for value in row:
                if type(value) is bytes:reads.append(len(value))
        return row
    monkeypatch.setattr(_NativeGuardCursor,'execute',executed)
    for name in ('fetchone','__next__'):
        original=getattr(_NativeGuardCursor,name)
        def fetched(cursor,*a,_original=original,**k):return observe(cursor,_original(cursor,*a,**k))
        monkeypatch.setattr(_NativeGuardCursor,name,fetched)
    for name in ('fetchall','fetchmany'):
        original=getattr(_NativeGuardCursor,name)
        def fetched_many(cursor,*a,_original=original,**k):
            rows=_original(cursor,*a,**k)
            for row in rows:observe(cursor,row)
            return rows
        monkeypatch.setattr(_NativeGuardCursor,name,fetched_many)
    return reads


def test_proof_open_does_not_fetch_unselected_archived_segment_bodies(
    tmp_path,monkeypatch,sealed_ranked_fixture,record_property
):
    import shutil
    segments,source,pair=sealed_ranked_fixture;path=tmp_path/'copy.sqlite';shutil.copyfile(source,path)
    reads=segment_payload_reads(monkeypatch)
    with fast_open(path,pair) as session:
        assert reads==[]
        record_property('archive_segments',segments)
        record_property('proof_open_segment_payload_bytes',sum(reads))
        assert session.world.events[-1].data['shared'] is session.world.events[-2].data['shared']
        assert reads==[]
        assert session.world.events[0].id==1
        assert sum(reads)>0
        first_read=sum(reads)
        assert session.world.events[0].id==1 and sum(reads)==first_read
        record_property('first_selected_segment_bytes',first_read)
    reads.clear()
    with opened(path,pair):assert sum(reads)>0
    record_property('audited_open_segment_payload_bytes',sum(reads))


def test_dormant_coherently_corrupt_segment_is_rejected_on_first_access(
    tmp_path,monkeypatch,sealed_ranked_fixture
):
    import shutil
    from ate_sim.persistence_adapters import WorldCodec
    from ate_sim.incremental_store import _segment_checksum
    segments,source,pair=sealed_ranked_fixture;path=tmp_path/'corrupt.sqlite';shutil.copyfile(source,path)
    codec=WorldCodec(identity_links_recorded=True);db=sqlite3.connect(path)
    ns,ordinal,old,checksum,version,count,first,last,created=db.execute('SELECT * FROM segments WHERE ordinal=0').fetchone()
    forged=codec.encode(('coherent-cold-corruption-control',segments))
    db.execute('UPDATE segments SET payload=?,payload_checksum=? WHERE namespace=? AND ordinal=?',
        (forged,_segment_checksum(ns,ordinal,first,last,count,version,created,forged),ns,ordinal));db.commit();db.close()
    reads=segment_payload_reads(monkeypatch)
    forbid_audits(monkeypatch)
    with fast_open(path,pair) as session:
        assert reads==[] and session.save()==0
        decode=TypedCodec.decode;seen=[]
        def observe(self,raw):
            if raw==forged:seen.append(True)
            return decode(self,raw)
        monkeypatch.setattr(TypedCodec,'decode',observe)
        with pytest.raises(StoreError):session.world.events[0]
        assert sum(reads)>0 and not seen
        with pytest.raises(StoreError):session.world.events._disk_prefix.verify_full()
    assert pin_count(path)==0


@pytest.mark.parametrize('error',[KeyboardInterrupt,SystemExit])
def test_cancelled_proof_restore_releases_its_owned_pin_and_connection(tmp_path,monkeypatch,error):
    from ate_sim import persistence_proof_world_session as api
    path,pair=ranked_fixture(tmp_path,size=4);owned=[]
    def cancelled(session):
        owned.append(session.store.db)
        raise error('cancelled restore')
    monkeypatch.setattr(api,'_restore_current_event_aliases',cancelled)
    with pytest.raises(error,match='cancelled restore'):fast_open(path,pair)
    assert pin_count(path)==0
    with pytest.raises(sqlite3.ProgrammingError,match='closed'):owned[0].execute('SELECT 1')


@pytest.mark.parametrize('error',[KeyboardInterrupt,SystemExit])
def test_cancelled_committed_capture_cleans_only_its_owned_lease(tmp_path,monkeypatch,error):
    from ate_sim.persistence_lazy_store import LazyRecordStore,GenerationPin
    from ate_sim.persistence_adapters import WorldCodec,SCHEMA
    path,pair=ranked_fixture(tmp_path,size=4)
    foreign=LazyRecordStore.open(path,codec=WorldCodec(identity_links_recorded=True),
        expected_simulation_schema=SCHEMA,expected_rules_id=RULES)
    foreign_pin=foreign.capture_pin();row=foreign.db.execute('SELECT * FROM generation_pins').fetchone()
    forbid_audits(monkeypatch);held=[];code=LazyRecordStore.capture_pin.__code__
    def cancelled(frame,event,value):
        if frame.f_code is code and event=='return' and type(value) is GenerationPin and not held:
            db=frame.f_locals['self'].db
            assert not db.in_transaction
            held.append(db)
            raise error('cancelled committed capture')
        return cancelled
    try:
        sys.settrace(cancelled)
        try:
            with pytest.raises(error,match='cancelled committed capture'):fast_open(path,pair)
        finally:sys.settrace(None)
        assert held and pin_count(path)==1
        assert foreign.db.execute('SELECT * FROM generation_pins').fetchall()==[row]
        with pytest.raises(sqlite3.ProgrammingError,match='closed'):held[0].execute('SELECT 1')
    finally:
        foreign.release_pin(foreign_pin,cleanup_budget=0);foreign.close()
    assert pin_count(path)==0


@pytest.mark.parametrize('point',['registry-allocated','constructor-return'])
def test_cancelled_session_construction_closes_its_registry(tmp_path,monkeypatch,point):
    from ate_sim.persistence_lazy import LazyWorldSession
    path,pair=ranked_fixture(tmp_path,size=4);held=[];code=LazyWorldSession.__init__.__code__
    forbid_audits(monkeypatch)
    def cancelled(frame,event,value):
        if frame.f_code is code and not held:
            session=frame.f_locals.get('self')
            if (point=='constructor-return' and event=='return' or
                    point=='registry-allocated' and event=='line' and hasattr(session,'_registry')):
                held.append(session)
                raise KeyboardInterrupt('cancelled session construction')
        return cancelled
    sys.settrace(cancelled)
    try:
        with pytest.raises(KeyboardInterrupt,match='cancelled session construction'):fast_open(path,pair)
    finally:sys.settrace(None)
    session=held[0]
    assert session._registry._closed and not session._active and session._state=='closed'
    assert pin_count(path)==0
    with pytest.raises(sqlite3.ProgrammingError,match='closed'):session.store.db.execute('SELECT 1')


def test_rejected_duplicate_capture_token_never_owns_a_foreign_pin(tmp_path,monkeypatch):
    from ate_sim import persistence_lazy_store as pins
    from ate_sim.persistence_adapters import WorldCodec,SCHEMA
    path,pair=ranked_fixture(tmp_path,size=4)
    foreign=pins.LazyRecordStore.open(path,codec=WorldCodec(identity_links_recorded=True),
        expected_simulation_schema=SCHEMA,expected_rules_id=RULES)
    foreign_pin=foreign.capture_pin();before=foreign.db.execute('SELECT * FROM generation_pins').fetchall()
    forbid_audits(monkeypatch)
    monkeypatch.setattr(pins.uuid,'uuid4',lambda:foreign_pin.token)
    try:
        with pytest.raises(sqlite3.IntegrityError,match='UNIQUE'):fast_open(path,pair)
        assert foreign.db.execute('SELECT * FROM generation_pins').fetchall()==before
        assert foreign.db.execute('SELECT 1').fetchone()==(1,)
    finally:
        foreign.release_pin(foreign_pin,cleanup_budget=0);foreign.close()
    assert pin_count(path)==0
