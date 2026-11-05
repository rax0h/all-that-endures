"""Native fetches join actual bytes to accepted roots before decoding."""
from dataclasses import replace
import pytest

from ate_sim.incremental_store import StoreIntegrityError, _record_checksum, _framed_sha
from ate_sim.persistence_lazy_store import _version_checksum
from simulation.tests.test_stage_0_5_proof_world_session import fixture, opened


@pytest.mark.parametrize('kind', ['version', 'record', 'records'])
@pytest.mark.parametrize('damage', ['forged', 'missing', 'extra'])
@pytest.mark.parametrize('busy', [False, True])
def test_native_byte_reads_reject_checksum_consistent_root_disagreement(tmp_path, monkeypatch, kind, damage, busy):
    path, pair = fixture(tmp_path)
    session = opened(path, pair)
    store = session.store
    try:
        ns = 'world.skills.skills' if kind == 'version' else 'world.year'
        key = (1, 'craft') if kind == 'version' else 0
        typed = store.codec.encode(key)
        if kind == 'version':
            old = store._visible_record_row(0, ns, typed)
            start, end, payload, _, codec, schema, members, _ = old
            value = replace(store.codec.decode(payload), level=.999)
            payload = store.codec.encode(value)
            if damage == 'extra':key = (99, 'craft');typed = store.codec.encode(key)
            if damage == 'missing':
                store.db.execute('DELETE FROM lazy_record_versions WHERE namespace=? AND typed_key=?', (ns, typed))
            else:
                store.db.execute('INSERT OR REPLACE INTO lazy_record_versions VALUES(?,?,?,?,?,?,?,?,?,?)',
                    (ns, typed, start, end, payload, _framed_sha(b'lazy-payload-v1', payload), codec, schema, members,
                     _version_checksum(ns, typed, schema, codec, start, end, members, payload)))
            read = lambda:store.read_version(session.pin, ns, key, expected_record_schema=1)
        else:
            payload = store.codec.encode((0, 999))
            if damage == 'extra':key = 99;typed = store.codec.encode(key)
            if damage == 'missing':store.db.execute('DELETE FROM records WHERE namespace=? AND typed_key=?', (ns, typed))
            else:
                store.db.execute('INSERT OR REPLACE INTO records VALUES(?,?,?,?,?,?,?)',
                    (ns, typed, payload, _record_checksum(ns, typed, 1, store.codec.version, 0, payload), store.codec.version, 1, 0))
            read = (lambda:store.read_records(ns, expected_record_schema=1)) if kind == 'records' else (
                lambda:store.read_record(ns, key, expected_record_schema=1))
        store.db.commit()
        # Isolate the root join from the coarse SQL epoch guard. Real callers
        # still get the normal epoch rejection; no production bypass is added.
        store._world_proof_authority.epoch = store._world_proof_authority._epoch()
        monkeypatch.setattr(store._world_proof_authority, 'busy', busy)
        decode = store.codec.decode
        decoded_forgery = []
        def checked(raw):
            if raw == payload:decoded_forgery.append(True)
            return decode(raw)
        monkeypatch.setattr(store.codec, 'decode', checked)
        if kind == 'records' and damage == 'missing':
            # Roster completeness is a separate admission gate; this adapter
            # certifies fetched bodies, not a whole ordinary namespace listing.
            assert read() == ()
        else:
            with pytest.raises(StoreIntegrityError, match='accepted.*source|source.*accepted'):read()
        assert not decoded_forgery
        assert not store.db.in_transaction
    finally:store.close()


@pytest.mark.parametrize('busy', [False, True])
def test_native_valid_reads_and_absence_keep_existing_shapes(tmp_path, monkeypatch, busy):
    path, pair = fixture(tmp_path)
    with opened(path, pair) as session:
        authority = session.store._world_proof_authority
        with monkeypatch.context() as patch:
            patch.setattr(authority, 'busy', busy)
            assert session.store.read_record('world.year', 0) == (0, 0)
            assert session.store.read_records('world.year') == ((0, (0, 0), 1),)
            assert session.store.read_version(session.pin, 'world.skills.skills', (1, 'craft'), expected_record_schema=1).value.person == 1
            with pytest.raises(KeyError):session.store.read_version(session.pin, 'world.skills.skills', (99, 'craft'), expected_record_schema=1)
        session.skills[1, 'craft'].level = .25
        assert session.save() == 1
        assert session.store.read_record('world.year', 0) == (0, 0)
        assert session.store.read_version(session.pin, 'world.skills.skills', (1, 'craft'), expected_record_schema=1).value.level == .25


@pytest.fixture(scope='module')
def sealed_fixture(tmp_path_factory):
    from ate_sim.event_log import EventLog
    from ate_sim.core import Layer
    def configure(w):
        w.events = EventLog()
        for i in range(EventLog.chunk_size):w.emit('proof-source', Layer.REALITY, n=i)
        w.events.seal_before(1);w.year=1
    return fixture(tmp_path_factory.mktemp('native-sealed-source'), configure=configure)


@pytest.mark.parametrize('damage', ['forged', 'missing', 'extra', None])
def test_native_sealed_segment_reads_join_accepted_root(tmp_path, monkeypatch, sealed_fixture, damage):
    import shutil
    from ate_sim.incremental_store import _segment_checksum
    path, pair = sealed_fixture
    target = tmp_path/'proof.sqlite';shutil.copyfile(path, target)
    session = opened(target, pair);store = session.store
    try:
        ns, ordinal, payload, checksum, codec, count, first, last, created = store.db.execute('SELECT * FROM segments LIMIT 1').fetchone()
        if damage is None:
            value = store.read_segment_checked(ns, ordinal)
            assert value.element_count == count
            with pytest.raises(KeyError):store.read_segment_checked(ns, ordinal+999)
            return
        if damage == 'extra':ordinal += 999
        if damage == 'missing':store.db.execute('DELETE FROM segments WHERE namespace=? AND ordinal=?', (ns, ordinal))
        else:
            payload=store.codec.encode(())
            store.db.execute('INSERT OR REPLACE INTO segments VALUES(?,?,?,?,?,?,?,?,?)',
                (ns, ordinal, payload, _segment_checksum(ns, ordinal, first, last, count, codec, created, payload),
                 codec, count, first, last, created))
        store.db.commit()
        store._world_proof_authority.epoch = store._world_proof_authority._epoch()
        decode=store.codec.decode
        def checked(raw):
            assert raw != payload, 'forged archive decoded before root check'
            return decode(raw)
        monkeypatch.setattr(store.codec, 'decode', checked)
        with pytest.raises(StoreIntegrityError, match='source.*accepted'):store.read_segment_checked(ns, ordinal)
        assert not store.db.in_transaction
    finally:store.close()


@pytest.mark.parametrize('column', ['payload_checksum', 'codec_version', 'record_schema', 'last_changed_generation'])
def test_native_ordinary_metadata_is_bounded_before_transfer(tmp_path, monkeypatch, column):
    path, pair = fixture(tmp_path);session = opened(path, pair);store = session.store
    try:
        store.db.execute('UPDATE records SET '+column+'=? WHERE namespace=?', ('x'*1048576, 'world.year'));store.db.commit()
        store._world_proof_authority.epoch = store._world_proof_authority._epoch()
        def text(raw):
            assert len(raw) < 8192, 'oversized native metadata transferred'
            return raw.decode()
        store.db.text_factory=text
        with pytest.raises(StoreIntegrityError):store.read_record('world.year', 0)
        assert not store.db.in_transaction
    finally:store.close()


def test_native_ordinary_decode_failure_closes_its_snapshot(tmp_path, monkeypatch):
    path, pair = fixture(tmp_path)
    with opened(path, pair) as session:
        store=session.store;payload=store.codec.encode((0,0));decode=store.codec.decode
        def fail(raw):
            if raw==payload:raise ValueError('injected ordinary decode failure')
            return decode(raw)
        with monkeypatch.context() as patch:
            patch.setattr(store.codec, 'decode', fail)
            with pytest.raises(ValueError, match='injected ordinary'):store.read_records('world.year')
        assert not store.db.in_transaction
        assert session.save()==0


def test_native_version_overlap_and_budget_reject_before_body_fetch(tmp_path, monkeypatch):
    from ate_sim import persistence_proof_publication as content, persistence_proof_native_sources as native
    from ate_sim.incremental_store import StoreError
    path, pair = fixture(tmp_path)
    with opened(path, pair) as session:
        store=session.store
        def body(*args,**kwargs):pytest.fail('native source body fetched before budget/overlap rejection')
        with monkeypatch.context() as patch:
            patch.setattr(content, '_source_version', body)
            patch.setattr(native, 'MAX_BODY_BYTES', 1)
            with pytest.raises(StoreError, match='budget'):
                store.read_version(session.pin, 'world.skills.skills',(1,'craft'), expected_record_schema=1)
        assert not store.db.in_transaction


def test_native_overlapping_versions_reject_before_source_body_fetch(tmp_path, monkeypatch):
    from ate_sim import persistence_proof_publication as content
    path, pair=fixture(tmp_path);session=opened(path,pair);store=session.store
    try:
        session.world.year=1
        assert session.save()==1
        ns,typed='world.skills.skills',store.codec.encode((1,'craft'))
        store.db.execute('INSERT INTO lazy_record_versions SELECT namespace,typed_key,1,valid_to,payload,payload_checksum,codec_version,record_schema,memberships,row_checksum FROM lazy_record_versions WHERE namespace=? AND typed_key=?',(ns,typed));store.db.commit()
        store._world_proof_authority.epoch=store._world_proof_authority._epoch()
        monkeypatch.setattr(content,'_source_version',lambda *a,**k:pytest.fail('overlap fetched a body'))
        with pytest.raises(StoreIntegrityError,match='overlapping'):
            store.read_version(session.pin,ns,(1,'craft'),expected_record_schema=1)
        assert not store.db.in_transaction
    finally:store.close()


def test_native_source_rejects_proof_node_corruption_before_decode(tmp_path,monkeypatch):
    from ate_sim import persistence_proof_publication as content
    path,pair=fixture(tmp_path);session=opened(path,pair);store=session.store
    try:
        domain=content._map(store).map_domain
        store.db.execute('UPDATE ate_proof_nodes SET node_bytes=? WHERE map_domain=? AND digest=?',
            (b'broken',domain,pair[0].roots[0].digest));store.db.commit()
        store._world_proof_authority.epoch=store._world_proof_authority._epoch()
        monkeypatch.setattr(content,'_source_version',lambda *a,**k:pytest.fail('corrupt proof fetched a body'))
        with pytest.raises(StoreIntegrityError):store.read_version(session.pin,'world.skills.skills',(1,'craft'),expected_record_schema=1)
        assert not store.db.in_transaction
    finally:store.close()


def test_native_source_rejects_unaccepted_generation_and_wrong_schema(tmp_path):
    from ate_sim.incremental_store import StoreConflictError,StoreFormatError
    path,pair=fixture(tmp_path)
    with opened(path,pair) as session:
        store=session.store
        with pytest.raises(StoreConflictError,match='generation'):
            store._visible_record_row(1,'world.skills.skills',store.codec.encode((1,'craft')))
        with pytest.raises(StoreFormatError):store.read_version(session.pin,'world.skills.skills',(1,'craft'),expected_record_schema=2)
        with pytest.raises(StoreFormatError):store.read_record('world.year',0,expected_record_schema=2)
        assert not store.db.in_transaction


@pytest.mark.parametrize('size',[1000,10000])
def test_native_point_reads_do_not_fetch_unrelated_history_bodies(tmp_path,monkeypatch,record_property,size):
    import time
    import sqlite3
    from ate_sim import persistence_proof_publication as content
    from ate_sim.persistence_lazy_nested_history import PAGE_NAMESPACE,ENTRY_NAMESPACE
    path,pair=fixture(tmp_path,size=size)
    with opened(path,pair) as session:
        store=session.store;original=content._source_version;calls=[];unexpected=[]
        def source(s,g,ns,key,**kw):
            assert ns not in (PAGE_NAMESPACE,ENTRY_NAMESPACE), 'point read fetched unrelated archive body'
            calls.append((ns,key))
            return original(s,g,ns,key,**kw)
        def trace(sql):
            normalized=sql.lower()
            if 'select' in normalized and 'payload' in normalized:
                if 'from segments' in normalized or 'from records' in normalized:
                    unexpected.append(sql)
                elif 'from lazy_record_versions' in normalized and "namespace='world.skills.skills'" not in normalized:
                    unexpected.append(sql)
        def authorize(action,table,column,database,source):
            # Column authorization also sees quoted/schema-qualified SQL and
            # statements served from the prepared-statement cache.
            if action==sqlite3.SQLITE_READ and table in ('records','segments') and column=='payload':
                unexpected.append((table,column,database))
            return sqlite3.SQLITE_OK
        store.db.set_trace_callback(trace);store.db.set_authorizer(authorize)
        try:
            with monkeypatch.context() as patch:
                patch.setattr(content,'_source_version',source)
                start=time.perf_counter()
                for _ in range(20):
                    assert store.read_version(session.pin,'world.skills.skills',(1,'craft'),expected_record_schema=1).value.person==1
                elapsed=time.perf_counter()-start
        finally:
            store.db.set_trace_callback(None);store.db.set_authorizer(None)
        assert not unexpected, unexpected
        assert calls==[('world.skills.skills',store.codec.encode((1,'craft')))]*20
        record_property('history_values',size);record_property('point_read_count',20)
        record_property('point_read_seconds',elapsed);record_property('unrelated_version_body_reads',0)
        record_property('unexpected_physical_body_selects',len(unexpected))


def test_phase_callback_cannot_read_staged_native_source(tmp_path):
    from ate_sim.incremental_store import StoreError
    path,pair=fixture(tmp_path)
    with opened(path,pair) as session:
        session.world.year=1;seen=[]
        def phase(at):
            if at=='before_commit':
                with pytest.raises(StoreError):session.store.read_record('world.year',0)
                seen.append(True)
                raise RuntimeError('callback rollback')
        session.store._phase_hook=phase
        with pytest.raises(RuntimeError,match='callback rollback'):session.save()
        session.store._phase_hook=lambda _:None
        assert seen and session.resolve_save()==0
        assert session.store.read_record('world.year',0)==(0,0)


def test_unowned_native_guard_does_not_bypass_source_authority(tmp_path):
    from ate_sim.persistence_proof_native_guard import NativeWriteGuard
    from ate_sim.incremental_store import StoreError
    path,pair=fixture(tmp_path);session=opened(path,pair);store=session.store
    try:
        p=store.codec.encode((0,999));k=store.codec.encode(0)
        store.db.execute('UPDATE records SET payload=?,payload_checksum=? WHERE namespace=? AND typed_key=?',
            (p,_record_checksum('world.year',k,1,store.codec.version,0,p),'world.year',k));store.db.commit()
        with NativeWriteGuard(store.db) as foreign:
            with foreign.publisher():
                with pytest.raises(StoreError):store.read_record('world.year',0)
    finally:store.close()


def test_native_epoch_checked_inside_actual_sqlite_snapshot(tmp_path):
    import sqlite3
    from ate_sim.incremental_store import StoreConflictError
    path,pair=fixture(tmp_path);session=opened(path,pair);store=session.store
    other=sqlite3.connect(path);written=[]
    try:
        def trace(sql):
            if sql=='BEGIN' and not written:
                written.append(True)
                # A real write is required: this SQLite build elides no-op
                # UPDATEs and does not advance data_version for them.
                other.execute("UPDATE records SET payload_checksum='epoch-race' WHERE namespace='world.seed'");other.commit()
        store.db.set_trace_callback(trace)
        with pytest.raises(StoreConflictError):store.read_record('world.year',0)
        assert written and not store.db.in_transaction
    finally:store.db.set_trace_callback(None);other.close();store.close()


@pytest.mark.parametrize('isolate_epoch',[False,True])
def test_native_operational_metadata_guard_precedes_lazy_snapshot_transfer(tmp_path,isolate_epoch):
    from ate_sim.incremental_store import StoreError
    path,pair=fixture(tmp_path);session=opened(path,pair);store=session.store;seen=[]
    try:
        store.db.execute('UPDATE save_head SET namespace_inventory=zeroblob(4194304)');store.db.commit()
        if isolate_epoch:store._world_proof_authority.epoch=store._world_proof_authority._epoch()
        def observe(cursor,row):
            if any(type(v) is bytes and len(v)==4194304 for v in row):seen.append(True)
            return row
        store.db.row_factory=observe
        with pytest.raises(StoreError):store.read_version(session.pin,'world.skills.skills',(1,'craft'),expected_record_schema=1)
        assert not seen and not store.db.in_transaction
    finally:store.close()


def test_native_future_interval_is_not_part_of_accepted_source(tmp_path,monkeypatch):
    path,pair=fixture(tmp_path);session=opened(path,pair);store=session.store
    try:
        ns='world.skills.skills';typed=store.codec.encode((1,'craft'))
        start,end,p,checksum,c,s,m,r=store._visible_record_row(0,ns,typed)
        store.db.execute('UPDATE lazy_record_versions SET valid_to=13,row_checksum=? WHERE namespace=? AND typed_key=?',
            (_version_checksum(ns,typed,s,c,start,13,m,p),ns,typed));store.db.commit()
        store._world_proof_authority.epoch=store._world_proof_authority._epoch()
        with pytest.raises(StoreIntegrityError):store.read_version(session.pin,ns,(1,'craft'),expected_record_schema=1)
    finally:store.close()


def test_native_source_cannot_borrow_a_different_generation_snapshot(tmp_path):
    from ate_sim.incremental_store import StoreConflictError
    from simulation.tests.test_stage_0_5_final_catalog_copy import opened as raw_open
    path,pair=fixture(tmp_path)
    with raw_open(path) as raw:old=raw.capture_pin()
    with opened(path,pair) as session:
        store=session.store;session.world.year=1;assert session.save()==1
        with pytest.raises(StoreConflictError):
            with store.read_snapshot(old):store.read_record('world.year',0)
        with store.read_snapshot(session.pin):assert store.read_record('world.year',0)==(0,1)
        store.release_pin(old)


@pytest.mark.parametrize('kind',['version','record','records','segment','segment-ids'])
def test_native_invalid_metadata_prevents_large_body_transfer(tmp_path,monkeypatch,sealed_fixture,kind):
    import shutil
    from ate_sim.incremental_store import StoreError
    path,pair=sealed_fixture;target=tmp_path/'proof.sqlite';shutil.copyfile(path,target)
    session=opened(target,pair);store=session.store;seen=[]
    try:
        if kind=='version':
            store.db.execute("UPDATE lazy_record_versions SET payload=zeroblob(4194304),record_schema='bad' WHERE namespace='world.skills.skills'")
            read=lambda:store.read_version(session.pin,'world.skills.skills',(1,'craft'),expected_record_schema=1)
        elif kind in ('record','records'):
            if kind=='record':store.db.execute("UPDATE records SET payload=zeroblob(4194304),record_schema='bad' WHERE namespace='world.year'")
            else:store.db.execute("UPDATE records SET payload=zeroblob(4194304),typed_key=zeroblob(2097152) WHERE namespace='world.year'")
            read=(lambda:store.read_record('world.year',0)) if kind=='record' else (lambda:store.read_records('world.year'))
        else:
            ns,ordinal=store.db.execute('SELECT namespace,ordinal FROM segments LIMIT 1').fetchone()
            if kind=='segment':store.db.execute("UPDATE segments SET payload=zeroblob(4194304),codec_version='bad'")
            else:store.db.execute("UPDATE segments SET payload=zeroblob(4194304),first_id=zeroblob(2097152)")
            read=lambda:store.read_segment_checked(ns,ordinal)
        store.db.commit();store._world_proof_authority.epoch=store._world_proof_authority._epoch()
        def observe(cursor,row):
            if any(type(v) is bytes and len(v)==4194304 for v in row):seen.append(True)
            return row
        store.db.row_factory=observe
        with pytest.raises(StoreError):read()
        assert not seen and not store.db.in_transaction
    finally:store.close()


@pytest.mark.parametrize('kind',['version','record'])
def test_native_point_fetch_does_not_repeat_identical_epoch_checks(tmp_path,kind):
    path,pair=fixture(tmp_path)
    with opened(path,pair) as session:
        store=session.store;epochs=[]
        def trace(sql):
            if sql.lower()=='pragma data_version':epochs.append(sql)
        store.db.set_trace_callback(trace)
        try:
            if kind=='version':store.read_version(session.pin,'world.skills.skills',(1,'craft'),expected_record_schema=1)
            else:store.read_record('world.year',0)
        finally:store.db.set_trace_callback(None)
        # One entry check, one pinned-view check, and at most one compatible
        # nested-source check. Actual bytes/proof paths are still reread.
        assert len(epochs)<=3, len(epochs)
