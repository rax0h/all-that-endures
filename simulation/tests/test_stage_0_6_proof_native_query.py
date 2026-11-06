"""Native query selection uses accepted scope roots, before key decoding."""
import pytest
from ate_sim.core import Person
from ate_sim.incremental_store import StoreIntegrityError,StoreConflictError
from ate_sim.persistence_lazy_store import _query_checksum
from simulation.tests.test_stage_0_5_proof_world_session import fixture,opened

NS='world.people'


def query_fixture(tmp_path,*,count=2,size=32):
    def configure(w):
        for i in range(1,count+1):w.people[i]=Person(i,0,1,1)
        w.next_person=count+1
    return fixture(tmp_path,configure=configure,size=size)


def reset_epoch(store):
    store._world_proof_authority.epoch=store._world_proof_authority._epoch()


@pytest.mark.parametrize('api',['tuple','stream'])
@pytest.mark.parametrize('damage',['missing','extra','empty-extra','ordinal','future-start','future-close'])
def test_native_query_rejects_coherent_scope_disagreement_before_key_decode(tmp_path,monkeypatch,api,damage):
    path,pair=query_fixture(tmp_path);session=opened(path,pair);store=session.store
    try:
        key=store.codec.encode(1);value=store.codec.encode(True);name='alive'
        if damage=='missing':
            store.db.execute('DELETE FROM lazy_query_versions WHERE namespace=? AND index_name=? AND index_value=? AND record_key=?',(NS,name,value,key))
        else:
            if damage=='extra':key=store.codec.encode(99)
            if damage=='empty-extra':name='absent'
            ordinal=99 if damage in ('extra','ordinal') else 0
            start,end=(1,None) if damage=='future-start' else (0,1) if damage=='future-close' else (0,None)
            if damage in ('ordinal','future-start','future-close'):
                store.db.execute('DELETE FROM lazy_query_versions WHERE namespace=? AND index_name=? AND index_value=? AND record_key=?',(NS,name,value,key))
            store.db.execute('INSERT INTO lazy_query_versions VALUES(?,?,?,?,?,?,?,?)',
                (NS,name,value,key,ordinal,start,end,_query_checksum(NS,name,value,key,ordinal,start,end)))
        store.db.commit();reset_epoch(store)
        decode=store.codec.decode;seen=[]
        def observed(raw):
            if raw in (store.codec.encode(1),store.codec.encode(2)):seen.append(raw)
            return decode(raw)
        monkeypatch.setattr(store.codec,'decode',observed)
        read=lambda:store.query_memberships(session.pin,NS,name,True) if api=='tuple' else list(store.iter_query_memberships(session.pin,NS,name,True))
        with pytest.raises(StoreIntegrityError):read()
        assert not seen and not store.db.in_transaction
    finally:store.close()


@pytest.mark.parametrize('limit,excluded,expected',[(None,(),((1,0),(2,1))),(1,(),((1,0),)),(1,(1,),((2,1),)),(0,(),()),(None,(1,2),())])
def test_native_query_preserves_order_limit_exclusions_and_absence(tmp_path,limit,excluded,expected):
    path,pair=query_fixture(tmp_path)
    with opened(path,pair) as session:
        store=session.store
        assert store.query_memberships(session.pin,NS,'alive',True,limit=limit,exclude_keys=excluded)==expected
        assert store.query_keys(session.pin,NS,'alive',True)==(1,2)
        assert store.query_memberships(session.pin,NS,'absent',True)==()
        assert list(store.iter_query_memberships(session.pin,NS,'absent',True))==[]


def test_native_query_stream_releases_snapshot_and_rejects_paused_generation(tmp_path):
    path,pair=query_fixture(tmp_path)
    with opened(path,pair) as session:
        store=session.store;it=store.iter_query_memberships(session.pin,NS,'alive',True)
        assert next(it)==(1,0)
        assert not store.db.in_transaction
        session.world.year=1;assert session.save()==1
        with pytest.raises(StoreConflictError):next(it)
        assert not store.db.in_transaction


@pytest.mark.parametrize('api',['tuple','stream','zero','absent'])
@pytest.mark.parametrize('bad',['foreign','unknown','released'])
def test_native_query_checks_actual_pin_even_for_empty_output(tmp_path,api,bad):
    from dataclasses import replace
    from ate_sim.incremental_store import StoreError
    path,pair=query_fixture(tmp_path)
    with opened(path,pair) as session:
        store=session.store
        pin=replace(session.pin,store_identity='foreign') if bad=='foreign' else replace(session.pin,token='unknown')
        if bad=='released':pin=store.capture_pin();store.release_pin(pin);reset_epoch(store)
        with pytest.raises(StoreError):
            if api=='stream':list(store.iter_query_memberships(pin,NS,'alive',True))
            else:store.query_memberships(pin,NS,'absent' if api=='absent' else 'alive',True,limit=0 if api=='zero' else None)
        assert not store.db.in_transaction


def test_native_query_compatible_pin_and_scope_refresh_after_save(tmp_path):
    path,pair=query_fixture(tmp_path)
    with opened(path,pair) as session:
        store=session.store;pin=store.capture_pin();reset_epoch(store)
        assert store.query_memberships(pin,NS,'alive',True)==((1,0),(2,1))
        store.release_pin(pin);reset_epoch(store)
        session.world.people[1].alive=False
        assert session.save()==1
        assert store.query_memberships(session.pin,NS,'alive',True)==((2,1),)
        assert store.query_memberships(session.pin,NS,'alive',False)==((1,0),)
        child=session.proof_manifest
    with opened(path,child) as restored:
        assert restored.store.query_memberships(restored.pin,NS,'alive',True)==((2,1),)


@pytest.mark.parametrize('change',['local','external','recovery'])
def test_native_query_paused_page_binds_original_accepted_epoch(tmp_path,change):
    import sqlite3
    path,pair=query_fixture(tmp_path);session=opened(path,pair);store=session.store
    try:
        it=store.iter_query_memberships(session.pin,NS,'alive',True);assert next(it)==(1,0)
        assert not store.db.in_transaction
        if change=='recovery':
            session.world.year=1
            def fault(phase):
                if phase=='before_commit':raise RuntimeError('query rollback')
            store._phase_hook=fault
            with pytest.raises(RuntimeError):session.save()
            store._phase_hook=lambda _:None;assert session.resolve_save()==0
        else:
            db=sqlite3.connect(path) if change=='external' else store.db
            db.execute("UPDATE records SET payload_checksum='query-drift' WHERE namespace='world.seed'");db.commit()
            if db is not store.db:db.close()
        with pytest.raises(StoreConflictError):next(it)
        assert not store.db.in_transaction
    finally:store.close()


@pytest.mark.parametrize('damage',['checksum','ordinal','start','key','owner','descriptor','directory','seek'])
def test_native_query_bad_metadata_proofs_and_sources_fail_before_materialization_or_decode(tmp_path,monkeypatch,damage):
    from ate_sim import persistence_proof_scope as scopes
    from ate_sim.persistence_proof_query import QueryScope
    path,pair=query_fixture(tmp_path);session=opened(path,pair);store=session.store
    try:
        value=store.codec.encode(True);key=store.codec.encode(1)
        if damage in ('checksum','ordinal','start'):
            column={'checksum':'row_checksum','ordinal':'ordinal','start':'valid_from'}[damage]
            store.db.execute('UPDATE lazy_query_versions SET '+column+'=? WHERE namespace=? AND index_name=?',('x'*1048576,NS,'alive'))
        elif damage=='key':
            huge=b'x'*1048576
            store.db.execute('INSERT INTO lazy_query_versions VALUES(?,?,?,?,?,?,?,?)',(NS,'alive',value,huge,99,0,None,_query_checksum(NS,'alive',value,huge,99,0,None)))
        elif damage=='owner':store.db.execute('DELETE FROM lazy_record_versions WHERE namespace=? AND typed_key=?',(NS,key))
        elif damage=='descriptor':store.db.execute('UPDATE ate_scope_descriptors SET root_count=root_count+1')
        elif damage=='directory':
            cert=store._world_proof_authority.read_components[1][0]
            domain=scopes.directory_domain(store.store_identity,store.codec.version,2)
            store.db.execute('UPDATE ate_proof_nodes SET node_bytes=? WHERE map_domain=? AND digest=?',(b'broken',domain,cert.roots[2].digest))
        else:
            domain=scopes._seek_domain(store,QueryScope(NS,'alive',value))
            store.db.execute('UPDATE ate_ordered_seek_nodes SET raw=? WHERE domain=?',(b'broken',domain))
        store.db.commit();reset_epoch(store);statements=[];seen=[];decode=store.codec.decode
        def observed(raw):
            if raw in (store.codec.encode(1),store.codec.encode(2)):seen.append(True)
            return decode(raw)
        def row(cursor,values):
            assert not any(isinstance(v,(str,bytes)) and len(v)>=1048576 for v in values),'oversized query metadata transferred'
            return values
        store.db.row_factory=row;store.db.set_trace_callback(statements.append)
        monkeypatch.setattr(store.codec,'decode',observed)
        with pytest.raises(StoreIntegrityError):store.query_memberships(session.pin,NS,'alive',True)
        assert not seen and not store.db.in_transaction
        if damage in ('checksum','ordinal','start','key'):
            assert not any(sql.startswith('WITH physical AS MATERIALIZED') for sql in statements)
    finally:store.db.set_trace_callback(None);store.close()


def test_native_query_scope_cache_does_not_hide_physical_omission(tmp_path):
    from ate_sim.persistence_validation_scope import checked_read_operation
    path,pair=query_fixture(tmp_path);session=opened(path,pair);store=session.store
    try:
        with checked_read_operation(store,session.pin) as cache:
            assert store.query_keys(session.pin,NS,'alive',True)==(1,2) and cache.entries>0
            store.db.execute('DELETE FROM lazy_query_versions WHERE namespace=? AND index_name=? AND record_key=?',(NS,'alive',store.codec.encode(1)))
            reset_epoch(store)
            with pytest.raises(StoreIntegrityError):store.query_keys(session.pin,NS,'alive',True)
            assert cache.entries==0
        assert not store.db.in_transaction
    finally:store.close()


@pytest.mark.parametrize('size',[1000,10000])
def test_native_limited_excluded_queries_fetch_only_selected_owner_bodies(tmp_path,monkeypatch,record_property,size):
    import sqlite3,time
    from ate_sim import persistence_proof_publication as content
    path,pair=query_fixture(tmp_path,count=3,size=size)
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
                assert store.query_memberships(session.pin,NS,'alive',True,limit=1,exclude_keys=(1,1))==((2,1),)
                assert store.query_memberships(session.pin,NS,'alive',True,limit=0)==()
                assert store.query_memberships(session.pin,NS,'alive',True,exclude_keys=(1,2,3))==()
                assert store.query_memberships(session.pin,NS,'absent',True)==()
                elapsed=time.perf_counter()-start
        finally:store.db.set_trace_callback(None);store.db.set_authorizer(None)
        assert calls==[(NS,store.codec.encode(2))] and not unexpected
        record_property('history_values',size);record_property('selected_source_bodies',len(calls))
        record_property('unexpected_physical_body_selects',len(unexpected));record_property('seconds',elapsed)


def test_native_query_windows_paginate_release_bodies_and_preserve_prefix_contract(tmp_path,monkeypatch,record_property):
    from ate_sim import persistence_proof_native_query as native
    path,pair=query_fixture(tmp_path,count=132)
    with opened(path,pair) as session:
        store=session.store;windows=[];original=native._window
        def window(s,g,scope,after,positions,exhausted):
            windows.append(len(positions));return original(s,g,scope,after,positions,exhausted)
        with monkeypatch.context() as patch:
            patch.setattr(native,'_window',window)
            it=store.iter_query_memberships(session.pin,NS,'alive',True)
            assert next(it)==(1,0) and not store.db.in_transaction
            assert 'row' not in it.gi_yieldfrom.gi_frame.f_locals
            assert list(it)==[(i,i-1) for i in range(2,133)]
        assert windows==[129,4]
        value=store.codec.encode(True);key=store.codec.encode(999)
        store.db.execute('INSERT INTO lazy_query_versions VALUES(?,?,?,?,?,?,?,?)',(NS,'alive',value,key,999,0,None,_query_checksum(NS,'alive',value,key,999,0,None)))
        store.db.commit();reset_epoch(store)
        # A checked requested prefix does not certify unvisited suffix bytes.
        assert store.query_memberships(session.pin,NS,'alive',True,limit=1)==((1,0),)
        with pytest.raises(StoreIntegrityError):store.query_memberships(session.pin,NS,'alive',True)
        record_property('physical_window_positions',windows)


def test_native_query_locator_and_exclusion_budgets_precede_owner_reads(tmp_path,monkeypatch):
    from ate_sim.incremental_store import StoreError
    from ate_sim import persistence_proof_publication as content
    path,pair=query_fixture(tmp_path)
    with opened(path,pair) as session:
        monkeypatch.setattr(content,'_source_version',lambda *a,**k:pytest.fail('budget failure fetched owner body'))
        with pytest.raises(StoreError):session.store.query_memberships(session.pin,NS,'alive','x'*4097)
        with pytest.raises(StoreError):session.store.query_memberships(session.pin,NS,'alive',True,exclude_keys=(1 for _ in range(10000)))
        assert not session.store.db.in_transaction


def test_native_query_is_unavailable_inside_staged_publisher_callbacks(tmp_path):
    from ate_sim.incremental_store import StoreError
    path,pair=query_fixture(tmp_path)
    with opened(path,pair) as session:
        session.world.year=1;seen=[]
        def callback(phase):
            if phase=='before_commit':
                with pytest.raises(StoreError):session.store.query_memberships(session.pin,NS,'alive',True)
                with pytest.raises(StoreError):next(session.store.iter_query_memberships(session.pin,NS,'alive',True))
                seen.append(True);raise RuntimeError('query callback rollback')
        session.store._phase_hook=callback
        with pytest.raises(RuntimeError):session.save()
        session.store._phase_hook=lambda _:None
        assert seen and session.resolve_save()==0
        assert session.store.query_keys(session.pin,NS,'alive',True)==(1,2)


def test_native_query_duplicate_current_intervals_reject_with_limits_and_exclusions(tmp_path):
    path,pair=query_fixture(tmp_path)
    with opened(path,pair) as session:
        session.world.year=1;assert session.save()==1
        store=session.store;key=store.codec.encode(1);value=store.codec.encode(True)
        store.db.execute('INSERT INTO lazy_query_versions VALUES(?,?,?,?,?,?,?,?)',
            (NS,'alive',value,key,0,1,None,_query_checksum(NS,'alive',value,key,0,1,None)))
        store.db.commit();reset_epoch(store)
        for kwargs in ({},{'limit':1},{'limit':1,'exclude_keys':(1,)}):
            with pytest.raises(StoreIntegrityError):store.query_memberships(session.pin,NS,'alive',True,**kwargs)
        with pytest.raises(StoreIntegrityError):next(store.iter_query_memberships(session.pin,NS,'alive',True))
        assert not store.db.in_transaction


def test_native_long_query_keys_shrink_windows_without_skips(tmp_path,monkeypatch,record_property):
    from ate_sim import persistence_proof_native_query as native
    keys=[(1,10**3950+i) for i in range(132)]
    def configure(w):
        for key in keys:w.communities.memberships[key]=.5
    path,pair=fixture(tmp_path,configure=configure)
    with opened(path,pair) as session:
        store=session.store;original=native._window;windows=[]
        def window(s,g,scope,after,positions,exhausted):
            windows.append(len(positions));return original(s,g,scope,after,positions,exhausted)
        with monkeypatch.context() as patch:
            patch.setattr(native,'_window',window)
            actual=store.query_memberships(session.pin,'world.communities.memberships','person',1)
        assert actual==tuple((key,i) for i,key in enumerate(keys))
        assert len(windows)>=2 and windows[0]<129 and not store.db.in_transaction
        record_property('physical_window_positions',windows)
