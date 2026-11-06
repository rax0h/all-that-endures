"""Native identity reads join allocator and placements to accepted roots."""
import pytest
from ate_sim.incremental_store import StoreIntegrityError,StoreConflictError
from ate_sim.persistence_lazy_store import _identity_state_checksum,_identity_occurrence_checksum
from simulation.tests.test_stage_0_5_proof_world_session import fixture,opened

NS='world.skills.skills'
PATH=(('field','provenance'),)

def reset_epoch(store):store._world_proof_authority.epoch=store._world_proof_authority._epoch()


@pytest.mark.parametrize('api',['point','owner','group'])
@pytest.mark.parametrize('damage',['missing','moved','extra','future'])
def test_native_identity_rejects_coherent_placement_forgeries(tmp_path,monkeypatch,api,damage):
    path,pair=fixture(tmp_path);session=opened(path,pair);store=session.store
    try:
        key=store.codec.encode((1,'craft'));encoded=store.codec.encode(PATH)
        inc,start,end,_=store._visible_identity_occurrence(0,NS,key,encoded)
        original_inc=inc
        if damage=='missing':store.db.execute('DELETE FROM lazy_identity_occurrence_versions WHERE owner_namespace=? AND owner_key=? AND occurrence_path=?',(NS,key,encoded))
        elif damage in ('moved','future'):
            if damage=='moved':inc=inc+1 if inc+1<store.read_identity_state(session.pin) else 1
            else:end=1
            store.db.execute('UPDATE lazy_identity_occurrence_versions SET incarnation_id=?,valid_to=?,row_checksum=? WHERE owner_namespace=? AND owner_key=? AND occurrence_path=?',
                (inc,end,_identity_occurrence_checksum(NS,key,encoded,inc,start,end),NS,key,encoded))
        else:
            encoded=store.codec.encode((('field','forged'),))
            store.db.execute('INSERT INTO lazy_identity_occurrence_versions VALUES(?,?,?,?,?,?,?)',
                (NS,key,encoded,inc,0,None,_identity_occurrence_checksum(NS,key,encoded,inc,0,None)))
        store.db.commit();reset_epoch(store)
        if api=='point':read=lambda:store._visible_identity_occurrence(0,NS,key,encoded)
        elif api=='owner':read=lambda:store.identity_occurrences_for_owner(session.pin,NS,(1,'craft'))
        else:read=lambda:store.identity_occurrences_for_incarnation(session.pin,original_inc)
        with pytest.raises(StoreIntegrityError):read()
        assert not store.db.in_transaction
    finally:store.close()


def test_native_allocator_rejects_checksum_consistent_number_change(tmp_path):
    path,pair=fixture(tmp_path);session=opened(path,pair);store=session.store
    try:
        n,start,end=store._identity_state_at(0)
        store.db.execute('UPDATE lazy_identity_state SET next_incarnation_id=?,row_checksum=?',(n+1,_identity_state_checksum(n+1,start,end)));store.db.commit();reset_epoch(store)
        with pytest.raises(StoreIntegrityError):store.read_identity_state(session.pin)
    finally:store.close()


def test_native_identity_shapes_aliases_absence_and_snapshot_release(tmp_path):
    path,pair=fixture(tmp_path)
    with opened(path,pair) as s:
        st=s.store;row=st.read_identity_occurrence(s.pin,NS,(1,'craft'),PATH);inc=row.incarnation_id
        assert s.skills[1,'craft'].provenance is s.skills[2,'craft'].provenance
        assert (PATH,inc) in st.identity_occurrences_for_owner(s.pin,NS,(1,'craft'))
        assert (NS,(1,'craft'),PATH) in st.identity_occurrences_for_incarnation(s.pin,inc)
        assert st.identity_occurrences_for_owner(s.pin,NS,(99,'craft'))==()
        assert st.identity_occurrences_for_incarnation(s.pin,st.read_identity_state(s.pin)+99)==()
        it=st.iter_identity_occurrences_for_incarnation(s.pin,inc);next(it)
        assert not st.db.in_transaction
        s.world.year=1;assert s.save()==1
        with pytest.raises(StoreConflictError):next(it)


@pytest.mark.parametrize('kind',['foreign','unknown','released'])
@pytest.mark.parametrize('api',['state','point','owner','group','empty'])
def test_native_identity_checks_actual_caller_pin(tmp_path,kind,api):
    from dataclasses import replace
    from ate_sim.incremental_store import StoreError
    path,pair=fixture(tmp_path)
    with opened(path,pair) as s:
        st=s.store;pin=replace(s.pin,store_identity='foreign') if kind=='foreign' else replace(s.pin,token='unknown')
        if kind=='released':pin=st.capture_pin();st.release_pin(pin);reset_epoch(st)
        with pytest.raises(StoreError):
            if api=='state':st.read_identity_state(pin)
            elif api=='point':st.read_identity_occurrence(pin,NS,(1,'craft'),PATH)
            elif api=='owner':st.identity_occurrences_for_owner(pin,NS,(1,'craft'))
            else:st.identity_occurrences_for_incarnation(pin,999 if api=='empty' else 1)
        assert not st.db.in_transaction


@pytest.mark.parametrize('change',['local','external','recovery'])
def test_native_identity_paused_page_binds_original_epoch(tmp_path,change):
    import sqlite3
    path,pair=fixture(tmp_path);s=opened(path,pair);st=s.store
    try:
        inc=st.read_identity_occurrence(s.pin,NS,(1,'craft'),PATH).incarnation_id
        it=st.iter_identity_occurrences_for_incarnation(s.pin,inc);next(it)
        assert not st.db.in_transaction
        if change=='recovery':
            s.world.year=1
            def fault(phase):
                if phase=='before_commit':raise RuntimeError('identity rollback')
            st._phase_hook=fault
            with pytest.raises(RuntimeError):s.save()
            st._phase_hook=lambda _:None;assert s.resolve_save()==0
        else:
            db=sqlite3.connect(path) if change=='external' else st.db
            db.execute("UPDATE records SET payload_checksum='identity-drift' WHERE namespace='world.seed'");db.commit()
            if db is not st.db:db.close()
        with pytest.raises(StoreConflictError):next(it)
        assert not st.db.in_transaction
    finally:st.close()


@pytest.mark.parametrize('damage',['overlap','future-start','huge-path','huge-checksum','descriptor','owner-node','group-node','future-allocator'])
def test_native_identity_invalid_metadata_and_proofs_reject_before_decode(tmp_path,monkeypatch,damage):
    from ate_sim import persistence_proof_scope as scopes
    from ate_sim.persistence_proof_occurrence import OwnerScope,GroupScope
    path,pair=fixture(tmp_path);s=opened(path,pair);st=s.store
    try:
        if damage=='overlap':s.world.year=1;assert s.save()==1
        key,path=st.codec.encode((1,'craft')),st.codec.encode(PATH)
        inc,start,end,_=st._visible_identity_occurrence(s.pin.captured_head,NS,key,path)
        if damage=='overlap':
            st.db.execute('INSERT INTO lazy_identity_occurrence_versions VALUES(?,?,?,?,?,?,?)',(NS,key,path,inc,1,None,_identity_occurrence_checksum(NS,key,path,inc,1,None)))
        elif damage=='future-start':
            st.db.execute('UPDATE lazy_identity_occurrence_versions SET valid_from=1,row_checksum=? WHERE owner_namespace=? AND owner_key=? AND occurrence_path=?',(_identity_occurrence_checksum(NS,key,path,inc,1,None),NS,key,path))
        elif damage=='huge-path':
            huge=b'x'*4194304
            st.db.execute('INSERT INTO lazy_identity_occurrence_versions VALUES(?,?,?,?,?,?,?)',(NS,key,huge,inc,0,None,_identity_occurrence_checksum(NS,key,huge,inc,0,None)))
        elif damage=='huge-checksum':st.db.execute('UPDATE lazy_identity_occurrence_versions SET row_checksum=?',('x'*4194304,))
        elif damage=='descriptor':st.db.execute('UPDATE ate_scope_descriptors SET root_count=root_count+1')
        elif damage=='future-allocator':
            n,start,_=st._identity_state_at(0)
            st.db.execute('UPDATE lazy_identity_state SET valid_from=1,row_checksum=?',(_identity_state_checksum(n,1,None),))
        else:
            scope=OwnerScope(NS,key) if damage=='owner-node' else GroupScope(inc)
            st.db.execute('UPDATE ate_ordered_seek_nodes SET raw=? WHERE domain=?',(b'bad',scopes._seek_domain(st,scope)))
        st.db.commit();reset_epoch(st);decode=st.codec.decode;seen=[]
        def observed(raw):
            if raw==path:seen.append(True)
            return decode(raw)
        def rows(cursor,row):
            assert not any(isinstance(v,(str,bytes)) and len(v)>=4194304 for v in row),'oversized physical identity metadata transferred'
            return row
        st.db.row_factory=rows;monkeypatch.setattr(st.codec,'decode',observed)
        with pytest.raises(StoreIntegrityError):st.identity_occurrences_for_owner(s.pin,NS,(1,'craft'))
        assert not seen and not st.db.in_transaction
    finally:st.close()


def test_native_identity_scope_cache_cannot_hide_omission(tmp_path):
    from ate_sim.persistence_validation_scope import checked_read_operation
    path,pair=fixture(tmp_path);s=opened(path,pair);st=s.store
    try:
        with checked_read_operation(st,s.pin) as cache:
            assert st.identity_occurrences_for_owner(s.pin,NS,(1,'craft')) and cache.entries>0
            st.db.execute('DELETE FROM lazy_identity_occurrence_versions WHERE owner_namespace=? AND owner_key=?',(NS,st.codec.encode((1,'craft'))));reset_epoch(st)
            with pytest.raises(StoreIntegrityError):st.identity_occurrences_for_owner(s.pin,NS,(1,'craft'))
            assert cache.entries==0
        assert not st.db.in_transaction
    finally:st.close()


@pytest.mark.parametrize('size',[1000,10000])
def test_native_identity_reads_fetch_no_owner_or_archive_bodies(tmp_path,monkeypatch,record_property,size):
    import sqlite3,time
    from ate_sim import persistence_proof_publication as content
    path,pair=fixture(tmp_path,size=size)
    with opened(path,pair) as s:
        st=s.store;unexpected=[]
        def authorize(action,table,column,database,source):
            if action==sqlite3.SQLITE_READ and table in ('records','segments','lazy_record_versions') and column in ('payload','memberships'):unexpected.append((table,column))
            return sqlite3.SQLITE_OK
        st.db.set_authorizer(authorize)
        try:
            with monkeypatch.context() as patch:
                patch.setattr(content,'_source_version',lambda *a,**k:pytest.fail('identity read fetched owner body'))
                start=time.perf_counter()
                for _ in range(10):
                    inc=st.read_identity_occurrence(s.pin,NS,(1,'craft'),PATH).incarnation_id
                    assert st.read_identity_state(s.pin)>inc
                    assert (PATH,inc) in st.identity_occurrences_for_owner(s.pin,NS,(1,'craft'))
                    assert (NS,(1,'craft'),PATH) in st.identity_occurrences_for_incarnation(s.pin,inc)
                elapsed=time.perf_counter()-start
        finally:st.db.set_authorizer(None)
        assert not unexpected
        record_property('history_values',size);record_property('repetitions',10);record_property('unexpected_physical_body_reads',len(unexpected));record_property('seconds',elapsed)


def test_native_identity_group_pagination_and_shared_save_restore_aliases(tmp_path):
    from ate_sim.skills import SkillHistory
    def configure(w):
        shared=list(range(8));w.skills.skills.clear()
        for i in range(132):w.skills.skills[i,'craft']=SkillHistory(i,'craft',provenance=shared)
    path,pair=fixture(tmp_path,configure=configure)
    with opened(path,pair) as s:
        st=s.store;inc=st.read_identity_occurrence(s.pin,NS,(0,'craft'),PATH).incarnation_id
        owners=st.identity_occurrences_for_incarnation(s.pin,inc)
        assert len(owners)==132 and len(set(owners))==132 and not st.db.in_transaction
        s.skills[0,'craft'].provenance.append(99);assert s.save()==1
        assert len(st.identity_occurrences_for_incarnation(s.pin,inc))==132
        assert s.skills[1,'craft'].provenance is s.skills[131,'craft'].provenance
        child=s.proof_manifest
    with opened(path,child) as s:assert s.skills[1,'craft'].provenance is s.skills[131,'craft'].provenance


def test_native_identity_publisher_callback_cannot_read_staging(tmp_path):
    from ate_sim.incremental_store import StoreError
    path,pair=fixture(tmp_path)
    with opened(path,pair) as s:
        s.world.year=1;seen=[]
        def fault(phase):
            if phase=='before_commit':
                with pytest.raises(StoreError):s.store.read_identity_state(s.pin)
                with pytest.raises(StoreError):s.store.identity_occurrences_for_owner(s.pin,NS,(1,'craft'))
                seen.append(True);raise RuntimeError('identity callback rollback')
        s.store._phase_hook=fault
        with pytest.raises(RuntimeError):s.save()
        s.store._phase_hook=lambda _:None
        assert seen and s.resolve_save()==0


def test_native_long_identity_group_shrinks_pages_and_counts_only_current_scope(tmp_path,monkeypatch,record_property):
    from ate_sim.skills import SkillHistory
    from ate_sim import persistence_proof_native_identity as native
    def configure(w):
        shared=list(range(8));w.skills.skills.clear()
        for i in range(132):w.skills.skills[i,'x'*3850]=SkillHistory(i,'x'*3850,provenance=shared)
    path,pair=fixture(tmp_path,configure=configure)
    with opened(path,pair) as s:
        st=s.store;inc=st.read_identity_occurrence(s.pin,NS,(0,'x'*3850),PATH).incarnation_id
        windows=[];original=native._positions;counts=[]
        def positions(*args,**kwargs):
            result=original(*args,**kwargs);windows.append(len(result[0]));return result
        def trace(sql):
            if sql.startswith('SELECT count(*) FROM lazy_identity_occurrence_versions INDEXED BY lazy_identity_incarnation_interval'):counts.append(sql)
        st.db.set_trace_callback(trace)
        try:
            with monkeypatch.context() as patch:
                patch.setattr(native,'_positions',positions)
                result=st.identity_occurrences_for_incarnation(s.pin,inc)
        finally:st.db.set_trace_callback(None)
        assert len(result)==132 and len(set(result))==132
        assert len(windows)>=2 and windows[0]<129 and len(counts)==1
        assert not st.db.in_transaction
        record_property('physical_window_positions',windows);record_property('current_group_count_queries',len(counts))
