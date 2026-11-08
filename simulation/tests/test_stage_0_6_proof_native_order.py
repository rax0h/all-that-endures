"""Native counts and key order are accepted facts, not row checksums."""
import pytest
from ate_sim.incremental_store import StoreIntegrityError,StoreConflictError
from ate_sim.persistence_lazy_store import _namespace_checksum,_order_checksum
from simulation.tests.test_stage_0_5_proof_world_session import fixture,opened

NS='world.skills.skills'


def reset_epoch(store):
    # Isolate the authenticated relation from the earlier coarse SQL guard.
    store._world_proof_authority.epoch=store._world_proof_authority._epoch()


@pytest.mark.parametrize('damage',['count','next','missing-order','ordinal','extra-order'])
def test_native_collection_rejects_checksum_consistent_relation_forgery(tmp_path,damage):
    path,pair=fixture(tmp_path);session=opened(path,pair);store=session.store
    try:
        key=store.codec.encode((1,'craft'))
        if damage in ('count','next'):
            count,next_id,start,end=store._namespace_state_at(NS,0)
            count=0 if damage=='count' else count
            next_id=99 if damage=='next' else next_id
            store.db.execute('UPDATE lazy_namespace_state SET member_count=?,next_ordinal=?,row_checksum=? WHERE namespace=?',
                (count,next_id,_namespace_checksum(NS,count,next_id,start,end),NS))
            read=lambda:store.namespace_size(session.pin,NS)
        else:
            ordinal,start,end=store._visible_order(NS,key,0)
            if damage=='missing-order':store.db.execute('DELETE FROM lazy_order_versions WHERE namespace=? AND typed_key=?',(NS,key))
            elif damage=='ordinal':
                store.db.execute('UPDATE lazy_order_versions SET ordinal=99,row_checksum=? WHERE namespace=? AND typed_key=?',
                    (_order_checksum(NS,key,99,start,end),NS,key))
            else:
                key=store.codec.encode((99,'craft'))
                store.db.execute('INSERT INTO lazy_order_versions VALUES(?,?,?,?,?,?)',
                    (NS,key,99,0,None,_order_checksum(NS,key,99,0,None)))
            read=lambda:store._visible_order(NS,key,0)
        store.db.commit();reset_epoch(store)
        with pytest.raises(StoreIntegrityError):read()
        assert not store.db.in_transaction
    finally:store.close()


@pytest.mark.parametrize('damage',['count','missing','swap','extra'])
def test_native_key_page_rejects_before_decoding_mismatched_window(tmp_path,monkeypatch,damage):
    path,pair=fixture(tmp_path);session=opened(path,pair);store=session.store
    try:
        a,b=(store.codec.encode((p,'craft')) for p in (1,2))
        if damage=='count':
            _,n,s,e=store._namespace_state_at(NS,0)
            store.db.execute('UPDATE lazy_namespace_state SET member_count=0,row_checksum=? WHERE namespace=?',
                (_namespace_checksum(NS,0,n,s,e),NS))
        elif damage=='missing':store.db.execute('DELETE FROM lazy_order_versions WHERE namespace=? AND typed_key=?',(NS,a))
        elif damage=='swap':
            for key,ordinal in ((a,99),(b,0),(a,1)):
                store.db.execute('UPDATE lazy_order_versions SET ordinal=?,row_checksum=? WHERE namespace=? AND typed_key=?',
                    (ordinal,_order_checksum(NS,key,ordinal,0,None),NS,key))
        else:
            k=store.codec.encode((99,'craft'))
            store.db.execute('INSERT INTO lazy_order_versions VALUES(?,?,?,?,?,?)',
                (NS,k,99,0,None,_order_checksum(NS,k,99,0,None)))
        store.db.commit();reset_epoch(store)
        decode=store.codec.decode;decoded=[]
        def observed(raw):
            if raw in (a,b):decoded.append(raw)
            return decode(raw)
        monkeypatch.setattr(store.codec,'decode',observed)
        with pytest.raises(StoreIntegrityError):list(store.iter_keys(session.pin,NS))
        assert not decoded
        assert not store.db.in_transaction
    finally:store.close()


@pytest.mark.parametrize('page_size',[1,2,128])
def test_native_order_iteration_preserves_keys_and_releases_before_yield(tmp_path,page_size):
    path,pair=fixture(tmp_path)
    with opened(path,pair) as session:
        store=session.store;it=store.iter_keys(session.pin,NS,page_size=page_size)
        assert next(it)==(1,'craft');assert not store.db.in_transaction
        assert list(it)==[(2,'craft')];assert not store.db.in_transaction
        assert store.namespace_size(session.pin,NS)==2
        assert store._visible_order(NS,store.codec.encode((1,'craft')),0)[0]==0
        assert store._visible_order(NS,store.codec.encode((99,'craft')),0) is None
        assert store.namespace_size(session.pin,'world.not-present')==0
        assert list(store.iter_keys(session.pin,'world.not-present'))==[]
        session.skills[1,'craft'].level=.4
        assert session.save()==1
        assert list(store.iter_keys(session.pin,NS))==[(1,'craft'),(2,'craft')]


@pytest.mark.parametrize('change',['save','local-write','external-write'])
def test_paused_native_key_page_rechecks_before_each_yield(tmp_path,change):
    import sqlite3
    path,pair=fixture(tmp_path);session=opened(path,pair);store=session.store
    try:
        it=store.iter_keys(session.pin,NS,page_size=128)
        assert next(it)==(1,'craft') and not store.db.in_transaction
        if change=='save':
            session.world.year=1;assert session.save()==1
        else:
            db=sqlite3.connect(path) if change=='external-write' else store.db
            db.execute("UPDATE records SET payload_checksum='paused-write' WHERE namespace='world.seed'");db.commit()
            if db is not store.db:db.close()
        with pytest.raises(StoreConflictError):next(it)
        assert not store.db.in_transaction
    finally:store.close()


def test_native_key_page_rejects_overlapping_future_closed_order(tmp_path):
    path,pair=fixture(tmp_path);session=opened(path,pair);store=session.store
    try:
        session.world.year=1;assert session.save()==1
        key=store.codec.encode((1,'craft'))
        store.db.execute('INSERT INTO lazy_order_versions VALUES(?,?,?,?,?,?)',
            (NS,key,0,1,2,_order_checksum(NS,key,0,1,2)))
        store.db.commit();reset_epoch(store)
        with pytest.raises(StoreIntegrityError):list(store.iter_keys(session.pin,NS))
        assert not store.db.in_transaction
    finally:store.close()


@pytest.mark.parametrize('width',[12,3950])
def test_native_key_windows_paginate_and_shrink_without_skipping(tmp_path,monkeypatch,record_property,width):
    from ate_sim.skills import SkillHistory
    from ate_sim import persistence_proof_native_order as native
    keys=[(1,str(i).zfill(4)+'x'*width) for i in range(132)]
    def configure(w):
        w.skills.skills.clear()
        for person,name in keys:w.skills.skills[person,name]=SkillHistory(person,name)
    path,pair=fixture(tmp_path,configure=configure)
    with opened(path,pair) as session:
        store=session.store;original=native._physical_window;windows=[];plans=[]
        def window(s,g,ns,after,limit,positions):
            windows.append((limit,len(positions)))
            return original(s,g,ns,after,limit,positions)
        def trace(sql):
            if sql.startswith('WITH physical AS MATERIALIZED'):
                plans.extend(row[3] for row in store.db.execute('EXPLAIN QUERY PLAN '+sql))
        store.db.set_trace_callback(trace)
        try:
            with monkeypatch.context() as patch:
                patch.setattr(native,'_physical_window',window)
                actual=list(store.iter_keys(session.pin,NS,page_size=128))
        finally:store.db.set_trace_callback(None)
        assert actual==keys and len(set(actual))==132
        assert len(windows)>=2 and all(limit<=130 for limit,_ in windows)
        if width>1000:assert windows[0][1]<129
        assert any('lazy_order_current' in p and 'SEARCH' in p for p in plans)
        assert not any('SCAN lazy_order_versions' in p for p in plans)
        assert not store.db.in_transaction
        record_property('key_width',width);record_property('physical_windows',windows);record_property('query_plans',plans)
        assert sum('USE TEMP B-TREE FOR ORDER BY' in p for p in plans)<=2*len(windows)


@pytest.mark.parametrize('damage',['huge-key','huge-checksum','future-state','missing-body','seek','directory'])
def test_native_order_rejects_bad_metadata_and_proofs_before_key_decode(tmp_path,monkeypatch,damage):
    from ate_sim import persistence_proof_collection as collection,persistence_proof_collection_directory as directory
    path,pair=fixture(tmp_path);session=opened(path,pair);store=session.store
    try:
        a=store.codec.encode((1,'craft'))
        if damage=='huge-key':
            k=b'x'*1048576
            store.db.execute('INSERT INTO lazy_order_versions VALUES(?,?,?,?,?,?)',(NS,k,99,0,None,_order_checksum(NS,k,99,0,None)))
        elif damage=='huge-checksum':store.db.execute('UPDATE lazy_order_versions SET row_checksum=? WHERE namespace=?',('x'*1048576,NS))
        elif damage=='future-state':
            count,n,start,_=store._namespace_state_at(NS,0)
            store.db.execute('UPDATE lazy_namespace_state SET valid_to=1,row_checksum=? WHERE namespace=?',(_namespace_checksum(NS,count,n,start,1),NS))
        elif damage=='missing-body':store.db.execute('DELETE FROM lazy_record_versions WHERE namespace=? AND typed_key=?',(NS,a))
        elif damage=='seek':
            domain=collection.domain(store.store_identity,store.codec.version,NS)
            store.db.execute('UPDATE ate_ordered_seek_nodes SET raw=? WHERE domain=?',(b'bad',domain))
        else:
            domain=directory.domain(store.store_identity,store.codec.version)
            store.db.execute('UPDATE ate_collection_directory_bodies SET raw=? WHERE domain=?',(b'bad',domain))
        store.db.commit();reset_epoch(store);seen=[]
        def row(cursor,values):
            assert not any(isinstance(v,(str,bytes)) and len(v)>=1048576 for v in values),'oversized metadata transferred'
            return values
        store.db.row_factory=row
        decode=store.codec.decode
        def observed(raw):
            if raw==a:seen.append(True)
            return decode(raw)
        monkeypatch.setattr(store.codec,'decode',observed)
        with pytest.raises(StoreIntegrityError):list(store.iter_keys(session.pin,NS))
        assert not seen and not store.db.in_transaction
    finally:store.close()


def test_native_key_decode_error_releases_snapshot(tmp_path,monkeypatch):
    path,pair=fixture(tmp_path)
    with opened(path,pair) as session:
        store=session.store;decode=store.codec.decode;typed=store.codec.encode((1,'craft'))
        def failed(raw):
            if raw==typed:raise ValueError('injected key decode')
            return decode(raw)
        with monkeypatch.context() as patch:
            patch.setattr(store.codec,'decode',failed)
            with pytest.raises(ValueError,match='injected key'):next(store.iter_keys(session.pin,NS))
        assert not store.db.in_transaction
        assert list(store.iter_keys(session.pin,NS))==[(1,'craft'),(2,'craft')]


def test_native_scoped_summary_never_reuses_physical_state_after_write(tmp_path):
    from ate_sim.persistence_validation_scope import checked_read_operation
    path,pair=fixture(tmp_path);session=opened(path,pair);store=session.store
    try:
        with checked_read_operation(store,session.pin) as scope:
            assert store.namespace_size(session.pin,NS)==2 and scope.entries>0
            assert list(store.iter_keys(session.pin,NS))==[(1,'craft'),(2,'craft')]
            count,n,start,_=store._namespace_state_at(NS,0)
            store.db.execute('UPDATE lazy_namespace_state SET valid_to=1,row_checksum=? WHERE namespace=?',
                (_namespace_checksum(NS,count,n,start,1),NS))
            reset_epoch(store)
            with pytest.raises(StoreIntegrityError):list(store.iter_keys(session.pin,NS))
            assert scope.entries==0
        assert not store.db.in_transaction
    finally:store.close()


def test_native_component_refresh_failure_requires_original_parent_recovery(tmp_path,monkeypatch):
    from ate_sim import persistence_proof_manifest_publish as manifests
    from ate_sim.incremental_store import StoreError
    path,pair=fixture(tmp_path)
    with opened(path,pair) as session:
        store=session.store;authority=store._world_proof_authority;load=manifests._load;failed=[]
        def interrupted(s,pin,accepted):
            if pin.captured_head==1 and authority.pair[0].generation==1 and not failed:
                failed.append(True);raise RuntimeError('lost component acknowledgement')
            return load(s,pin,accepted)
        session.skills[1,'craft'].provenance.append(99)
        with monkeypatch.context() as patch:
            patch.setattr(manifests,'_load',interrupted)
            with pytest.raises(RuntimeError,match='component acknowledgement'):session.save()
        assert failed and store.db.execute('SELECT generation FROM main.save_head WHERE singleton=1').fetchone()==(1,) and session._pending_save is not None
        with pytest.raises(StoreError):store.generation
        with pytest.raises(StoreError):store.namespace_size(session.pin,NS)
        assert session.resolve_save()==1 and session.save()==1
        assert authority.read_components[4][0].generation==1
        assert list(store.iter_keys(session.pin,NS))==[(1,'craft'),(2,'craft')]
        assert session.skills[1,'craft'].provenance is session.skills[2,'craft'].provenance
        child=session.proof_manifest
    with opened(path,child) as restored:
        assert restored.skills[2,'craft'].provenance[-1]==99
        assert list(restored.store.iter_keys(restored.pin,NS))==[(1,'craft'),(2,'craft')]


def test_paused_native_iterator_rejects_reaccepted_same_generation_epoch(tmp_path):
    path,pair=fixture(tmp_path)
    with opened(path,pair) as session:
        store=session.store;authority=store._world_proof_authority
        it=store.iter_keys(session.pin,NS);assert next(it)==(1,'craft');epoch=authority.epoch
        session.world.year=1
        def fault(phase):
            if phase=='before_commit':raise RuntimeError('rollback before acknowledgement')
        store._phase_hook=fault
        with pytest.raises(RuntimeError):session.save()
        store._phase_hook=lambda _:None
        assert session.resolve_save()==0 and authority.epoch!=epoch
        with pytest.raises(StoreConflictError):next(it)
        assert not store.db.in_transaction


@pytest.mark.parametrize('kind',['row','text','scalar'])
def test_postcommit_sqlite_customization_callbacks_cannot_borrow_publisher(tmp_path,kind):
    from ate_sim import persistence_proof_native_sources as sources
    from ate_sim.incremental_store import StoreError
    path,pair=fixture(tmp_path);session=opened(path,pair);store=session.store;seen=[]
    try:
        authority=store._world_proof_authority
        def probe():
            guard=getattr(store.db,'_native_write_guard',None)
            if seen or guard is None or not guard.depth or authority.pair[0].generation!=1:return
            seen.append('entered')
            try:sources.active(store)
            except StoreError:seen.append('source-blocked')
            else:seen.append('source-borrowed')
            try:store.db.execute("UPDATE records SET payload_checksum='callback-poison' WHERE namespace='world.seed'");store.db.commit()
            except StoreError:seen.append('write-blocked')
            else:seen.append('write-published')
        def row(cursor,values):probe();return values
        def text(raw):probe();return raw.decode()
        def length(value):
            probe()
            return None if value is None else len(value if type(value) is bytes else str(value).split(chr(0),1)[0])
        if kind=='row':store.db.row_factory=row
        elif kind=='text':store.db.text_factory=text
        else:store.db.create_function('length',1,length)
        session.world.year=1
        # A denied callback poisons this operation even if the callback catches it.
        with pytest.raises(StoreError):session.save()
        assert seen==['entered','source-blocked','write-blocked']
        store.db.row_factory=None;store.db.text_factory=str
        assert session.resolve_save()==1
        child=session.proof_manifest
    finally:store.db.row_factory=None;store.db.text_factory=str;store.close()
    with opened(path,child) as restored:assert restored.world.year==1


@pytest.mark.parametrize('kind',['aggregate','window','collation','cursor','execute-cursor','script-cursor'])
def test_registered_sqlite_callbacks_cannot_write_from_publisher(kind):
    import sqlite3
    from ate_sim.persistence_sqlite_guard import GuardedConnection
    from ate_sim.persistence_proof_native_guard import NativeWriteGuard
    from ate_sim.incremental_store import StoreError
    db=sqlite3.connect(':memory:',factory=GuardedConnection);seen=[]
    try:
        db.execute('CREATE TABLE protected(value)');db.commit()
        def probe():
            if seen:return
            seen.append('entered')
            try:db.execute('INSERT INTO protected VALUES(1)')
            except StoreError:seen.append('blocked')
        class Total:
            def __init__(self):self.total=0
            def step(self,value):probe();self.total+=value
            def inverse(self,value):probe();self.total-=value
            def value(self):probe();return self.total
            def finalize(self):probe();return self.total
        if kind=='aggregate':
            db.create_aggregate('custom_total',1,Total);sql='SELECT custom_total(1)'
        elif kind=='window':
            db.create_window_function('custom_total',1,Total);sql='SELECT custom_total(1) OVER ()'
        elif kind=='collation':
            def compare(a,b):probe();return (a>b)-(a<b)
            db.create_collation('custom_order',compare)
            sql="SELECT x FROM (SELECT 'b' AS x UNION ALL SELECT 'a') ORDER BY x COLLATE custom_order"
        else:
            cursor=db.cursor() if kind=='cursor' else db.executescript('SELECT 1;') if kind=='script-cursor' else db.execute('SELECT 1')
            def factory(cursor,row):probe();return row
            cursor.row_factory=factory
            cursor.execute('SELECT 1')
        with NativeWriteGuard(db) as guard:
            with guard.publisher():rows=cursor.fetchall() if kind in ('cursor','execute-cursor','script-cursor') else db.execute(sql).fetchall()
            assert rows==([('a',),('b',)] if kind=='collation' else [(1,)])
            assert seen==['entered','blocked']
            with pytest.raises(StoreError):guard.check()
        assert db.execute('SELECT count(*) FROM protected').fetchone()==(0,)
    finally:db.close()


def test_benign_sqlite_factories_preserve_native_save_and_cursor_shapes(tmp_path):
    path,pair=fixture(tmp_path)
    with opened(path,pair) as session:
        store=session.store;store.db.row_factory=lambda cursor,row:row;store.db.text_factory=lambda raw:raw.decode()
        session.world.year=1
        assert session.save()==1
        assert store.read_record('world.year',0)==(0,1)
        assert list(store.iter_keys(session.pin,NS))==[(1,'craft'),(2,'craft')]
        cursor=store.db.cursor();cursor.row_factory=lambda c,r:r
        assert cursor.execute('SELECT 1').fetchone()==(1,)


@pytest.mark.parametrize('kind',['foreign','unregistered','released'])
@pytest.mark.parametrize('namespace',[NS,'world.not-present'])
def test_native_iterator_requires_callers_registered_pin_before_decode(tmp_path,monkeypatch,kind,namespace):
    from dataclasses import replace
    from ate_sim.incremental_store import StoreError
    path,pair=fixture(tmp_path)
    with opened(path,pair) as session:
        store=session.store
        pin=replace(session.pin,store_identity='foreign') if kind=='foreign' else replace(session.pin,token='not-registered')
        if kind=='released':
            pin=store.capture_pin();store.release_pin(pin);reset_epoch(store)
        decode=store.codec.decode;seen=[]
        def observed(raw):
            if raw==store.codec.encode((1,'craft')):seen.append(True)
            return decode(raw)
        monkeypatch.setattr(store.codec,'decode',observed)
        with pytest.raises(StoreError):list(store.iter_keys(pin,namespace))
        assert not seen and not store.db.in_transaction


def test_native_iterator_accepts_a_compatible_registered_pin(tmp_path):
    path,pair=fixture(tmp_path)
    with opened(path,pair) as session:
        store=session.store;pin=store.capture_pin();reset_epoch(store)
        try:
            assert list(store.iter_keys(pin,NS))==[(1,'craft'),(2,'craft')]
            assert list(store.iter_keys(pin,'world.not-present'))==[]
        finally:store.release_pin(pin);reset_epoch(store)


@pytest.mark.parametrize('kind',['point','page','namespace'])
def test_native_current_head_rejects_future_starting_open_surplus(tmp_path,kind):
    path,pair=fixture(tmp_path);session=opened(path,pair);store=session.store
    try:
        if kind=='namespace':
            ns='world.not-present'
            store.db.execute('INSERT INTO lazy_namespace_state VALUES(?,?,?,?,?,?)',(ns,1,None,0,0,_namespace_checksum(ns,0,0,1,None)))
            read=lambda:store.namespace_size(session.pin,ns)
        else:
            key=store.codec.encode((99,'craft'))
            store.db.execute('INSERT INTO lazy_order_versions VALUES(?,?,?,?,?,?)',(NS,key,99,1,None,_order_checksum(NS,key,99,1,None)))
            read=(lambda:store._visible_order(NS,key,0)) if kind=='point' else lambda:list(store.iter_keys(session.pin,NS))
        store.db.commit();reset_epoch(store)
        with pytest.raises(StoreIntegrityError):read()
        assert not store.db.in_transaction
    finally:store.close()


def test_native_invalid_metadata_never_reaches_sqlite_materialization(tmp_path):
    path,pair=fixture(tmp_path);session=opened(path,pair);store=session.store
    try:
        store.db.execute('UPDATE lazy_order_versions SET row_checksum=? WHERE namespace=?',('x'*4194304,NS));store.db.commit();reset_epoch(store)
        statements=[];store.db.set_trace_callback(statements.append)
        with pytest.raises(StoreIntegrityError):list(store.iter_keys(session.pin,NS))
        store.db.set_trace_callback(None)
        assert not any(sql.startswith('WITH physical AS MATERIALIZED') for sql in statements)
    finally:store.db.set_trace_callback(None);store.close()


def test_paused_native_iterator_retains_no_selected_source_row(tmp_path):
    path,pair=fixture(tmp_path)
    with opened(path,pair) as session:
        it=session.store.iter_keys(session.pin,NS);assert next(it)==(1,'craft')
        assert 'record' not in it.gi_frame.f_locals
        assert not session.store.db.in_transaction
        it.close()


def test_native_cold_and_scoped_reads_select_physical_state_once(tmp_path,monkeypatch):
    from ate_sim.persistence_validation_scope import checked_read_operation
    path,pair=fixture(tmp_path)
    with opened(path,pair) as session:
        store=session.store;statements=[];store.db.set_trace_callback(statements.append)
        def selections():return sum('FROM lazy_namespace_state' in sql and 'row_checksum' in sql for sql in statements)
        try:
            assert store.namespace_size(session.pin,NS)==2
            cold=selections();assert cold==1
            with checked_read_operation(store,session.pin):
                for _ in range(2):
                    statements.clear();assert store.namespace_size(session.pin,NS)==2
                    assert selections()==1
        finally:store.db.set_trace_callback(None)


@pytest.mark.parametrize('size',[1000,10000])
def test_native_count_point_and_key_page_fetch_no_unrelated_bodies(tmp_path,monkeypatch,record_property,size):
    import sqlite3,time
    from ate_sim import persistence_proof_publication as content
    path,pair=fixture(tmp_path,size=size)
    with opened(path,pair) as session:
        store=session.store;original=content._source_version;calls=[];unexpected=[]
        def source(s,g,ns,key,**kw):
            calls.append((ns,key));assert ns==NS
            return original(s,g,ns,key,**kw)
        def trace(sql):
            lower=sql.lower()
            if 'select' in lower and 'payload' in lower and 'from lazy_record_versions' in lower and "namespace='"+NS+"'" not in lower:unexpected.append(sql)
        def authorize(action,table,column,database,source):
            if action==sqlite3.SQLITE_READ and table in ('records','segments') and column=='payload':unexpected.append((table,column))
            return sqlite3.SQLITE_OK
        store.db.set_trace_callback(trace);store.db.set_authorizer(authorize)
        try:
            with monkeypatch.context() as patch:
                patch.setattr(content,'_source_version',source);start=time.perf_counter()
                for _ in range(10):
                    assert store.namespace_size(session.pin,NS)==2
                    assert store._visible_order(NS,store.codec.encode((1,'craft')),0)[0]==0
                    assert store._visible_order(NS,store.codec.encode((99,'craft')),0) is None
                assert calls==[]
                assert list(store.iter_keys(session.pin,NS,page_size=1))==[(1,'craft'),(2,'craft')]
                elapsed=time.perf_counter()-start
        finally:store.db.set_trace_callback(None);store.db.set_authorizer(None)
        assert not unexpected and calls==[(NS,store.codec.encode((i,'craft'))) for i in (1,2)]
        record_property('history_values',size);record_property('selected_source_bodies',len(calls))
        record_property('count_and_order_repetitions',10);record_property('seconds',elapsed)
        record_property('unexpected_physical_body_selects',len(unexpected))
