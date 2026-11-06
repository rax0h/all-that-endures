"""Ordinary enumeration is complete against accepted head counts and bodies."""
import pytest
from ate_sim.incremental_store import StoreIntegrityError,_record_checksum,_head_checksum
from simulation.tests.test_stage_0_5_proof_world_session import fixture,opened
from simulation.tests.test_stage_0_6_proof_native_sources import sealed_fixture

NS='world.year'

def reset_epoch(store):store._world_proof_authority.epoch=store._world_proof_authority._epoch()


@pytest.mark.parametrize('damage',['missing','extra','compensated','head-count'])
def test_native_ordinary_roster_rejects_coherent_missing_extra_and_head_forgery(tmp_path,monkeypatch,damage):
    path,pair=fixture(tmp_path);s=opened(path,pair);st=s.store
    try:
        if damage in ('missing','compensated','head-count'):st.db.execute('DELETE FROM records WHERE namespace=?',(NS,))
        payload=st.codec.encode((0,999));key=st.codec.encode(99)
        if damage in ('extra','compensated'):
            st.db.execute('INSERT INTO records VALUES(?,?,?,?,?,?,?)',(NS,key,payload,_record_checksum(NS,key,1,st.codec.version,0,payload),st.codec.version,1,0))
        if damage=='head-count':
            row=list(st._checked_head_row());counts=st.codec.decode(row[6]);counts.pop(NS);row[6]=st.codec.encode(counts)
            st.db.execute('UPDATE save_head SET namespace_counts=?,head_checksum=?',(row[6],_head_checksum(*row[:7])))
        st.db.commit();reset_epoch(st);decode=st.codec.decode;seen=[]
        def observed(raw):
            if raw==payload:seen.append(True)
            return decode(raw)
        monkeypatch.setattr(st.codec,'decode',observed)
        with pytest.raises(StoreIntegrityError):st.read_records(NS)
        assert not seen and not st.db.in_transaction
    finally:st.close()


@pytest.mark.parametrize('damage',['missing','extra'])
def test_native_roster_count_precedes_any_payload_selection(tmp_path,damage):
    import sqlite3
    path,pair=fixture(tmp_path);s=opened(path,pair);st=s.store
    try:
        if damage=='missing':st.db.execute('DELETE FROM records WHERE namespace=?',(NS,))
        else:
            key=st.codec.encode(99);payload=st.codec.encode((0,0))
            st.db.execute('INSERT INTO records VALUES(?,?,?,?,?,?,?)',(NS,key,payload,_record_checksum(NS,key,1,st.codec.version,0,payload),st.codec.version,1,0))
        st.db.commit();reset_epoch(st);reads=[]
        def authorize(action,table,column,database,source):
            if action==sqlite3.SQLITE_READ and table=='records' and column=='payload':reads.append(True)
            return sqlite3.SQLITE_OK
        st.db.set_authorizer(authorize)
        with pytest.raises(StoreIntegrityError):st.read_records(NS)
        assert not reads and not st.db.in_transaction
    finally:st.db.set_authorizer(None);st.close()


def test_native_roster_shapes_lazy_namespace_rejection_and_save_refresh(tmp_path):
    from ate_sim.incremental_store import StoreError
    path,pair=fixture(tmp_path)
    with opened(path,pair) as s:
        assert s.store.read_records(NS)==((0,(0,0),1),)
        assert s.store.read_records('world.not-present')==()
        with pytest.raises(StoreError):s.store.read_records('world.skills.skills')
        s.world.year=1;assert s.save()==1
        assert s.store.read_records(NS)==((0,(0,1),1),)


def test_native_roster_scope_cache_never_hides_physical_deletion(tmp_path):
    from ate_sim.persistence_validation_scope import checked_read_operation
    path,pair=fixture(tmp_path);s=opened(path,pair);st=s.store
    try:
        with checked_read_operation(st,s.pin) as cache:
            assert st.read_records(NS)==((0,(0,0),1),)
            st.db.execute('DELETE FROM records WHERE namespace=?',(NS,));reset_epoch(st)
            with pytest.raises(StoreIntegrityError):st.read_records(NS)
            assert cache.entries==0
        assert not st.db.in_transaction
    finally:st.close()


def test_native_roster_accepted_counts_use_closed_metadata_decoder(tmp_path,monkeypatch):
    path,pair=fixture(tmp_path)
    with opened(path,pair) as s:
        st=s.store;decode=st.codec.decode;counts=s.proof_manifest[0].head.namespace_counts
        def observed(raw):
            if raw==counts:pytest.fail('caller decoder used for accepted count metadata')
            return decode(raw)
        monkeypatch.setattr(st.codec,'decode',observed)
        assert st.read_records(NS)==((0,(0,0),1),)


@pytest.mark.parametrize('kind',['descriptor','retired','owner','tree','group','link','placement','membership'])
def test_public_catalog_entrypoints_compose_accepted_native_authorities(tmp_path,monkeypatch,kind):
    from ate_sim import persistence_lazy_identity_catalog as catalog
    from ate_sim.persistence_lazy_store import _version_checksum
    from ate_sim.incremental_store import _framed_sha
    path,pair=fixture(tmp_path);s=opened(path,pair);st=s.store
    try:
        owner=('world.skills.skills',(1,'craft'));where=(('field','provenance'),)
        inc=st.read_identity_occurrence(s.pin,*owner,where).incarnation_id
        cat=catalog.IdentityCatalog(st);cat.read_owner_identity(s.pin,owner)
        namespace,key={'descriptor':(catalog.CATALOG_NAMESPACE,0),'retired':(catalog.RETIRED_NAMESPACE,0),'owner':(catalog.OWNER_NAMESPACE,owner),
            'group':(catalog.GROUP_NAMESPACE,inc),'tree':(catalog.OWNER_TREE_NAMESPACE,(*owner,cat._owner(s.pin,owner)[6])),
            'link':(catalog.LINK_NAMESPACE,st.query_keys(s.pin,catalog.LINK_NAMESPACE,'incarnation',inc)[0]),
            'placement':(None,None),'membership':(None,None)}[kind]
        payload=st.codec.encode(('forged-catalog-body',))
        if kind in ('placement','membership'):
            st.db.execute('DELETE FROM lazy_identity_occurrence_versions WHERE owner_namespace=? AND owner_key=? AND occurrence_path=?',(owner[0],st.codec.encode(owner[1]),st.codec.encode(where)))
        else:
            typed=st.codec.encode(key)
            start,end,codec,schema,members=st.db.execute('SELECT valid_from,valid_to,codec_version,record_schema,memberships FROM lazy_record_versions WHERE namespace=? AND typed_key=? AND valid_to IS NULL',(namespace,typed)).fetchone()
            st.db.execute('UPDATE lazy_record_versions SET payload=?,payload_checksum=?,row_checksum=? WHERE namespace=? AND typed_key=? AND valid_to IS NULL',
                (payload,_framed_sha(b'lazy-payload-v1',payload),_version_checksum(namespace,typed,schema,codec,start,end,members,payload),namespace,typed))
        st.db.commit();reset_epoch(st);decode=st.codec.decode;seen=[]
        def observed(raw):
            if raw==payload:seen.append(True)
            return decode(raw)
        monkeypatch.setattr(st.codec,'decode',observed)
        with pytest.raises(StoreIntegrityError):
            if kind=='membership':cat.read_identity_membership(s.pin,owner,where)
            elif kind in ('owner','tree','placement'):cat.read_owner_identity(s.pin,owner)
            elif kind=='link':cat.read_identity_links(s.pin,inc)
            else:cat.read_identity_group(s.pin,inc)
        assert not seen and not st.db.in_transaction
    finally:st.close()


def test_native_catalog_missing_header_and_source_cannot_become_new_owner(tmp_path):
    from ate_sim.persistence_lazy_identity_catalog import IdentityCatalog,OWNER_NAMESPACE
    path,pair=fixture(tmp_path);s=opened(path,pair);st=s.store
    try:
        owner=('world.skills.skills',(1,'craft'));cat=IdentityCatalog(st)
        assert cat.read_owner_identity(s.pin,owner).exists
        st.db.execute('DELETE FROM lazy_record_versions WHERE namespace=? AND typed_key=? AND valid_to IS NULL',
            (owner[0],st.codec.encode(owner[1])))
        st.db.execute('DELETE FROM lazy_identity_occurrence_versions WHERE owner_namespace=? AND owner_key=?',
            (owner[0],st.codec.encode(owner[1])))
        st.db.execute('DELETE FROM lazy_record_versions WHERE namespace=? AND typed_key=? AND valid_to IS NULL',
            (OWNER_NAMESPACE,st.codec.encode(owner)))
        st.db.commit();reset_epoch(st)
        with pytest.raises(StoreIntegrityError):cat.read_identity_membership(s.pin,owner,())
        assert not st.db.in_transaction
    finally:st.close()


def test_catalog_owner_metadata_witness_requires_separate_body_proof(tmp_path):
    from ate_sim.persistence_lazy_identity_catalog import IdentityCatalog
    path,pair=fixture(tmp_path);s=opened(path,pair);st=s.store
    try:
        owner=('world.skills.skills',(1,'craft'));cat=IdentityCatalog(st)
        before=cat.read_owner_identity(s.pin,owner)
        st.db.execute('UPDATE lazy_record_versions SET payload=? WHERE namespace=? AND typed_key=? AND valid_to IS NULL',(st.codec.encode(('bad-body',)),owner[0],st.codec.encode(owner[1])))
        st.db.commit();reset_epoch(st)
        after=cat.read_owner_identity(s.pin,owner)
        assert after.payload_commitment==before.payload_commitment and after.exists
        with pytest.raises(StoreIntegrityError):st.read_version(s.pin,*owner,expected_record_schema=1)
        assert not st.db.in_transaction
    finally:st.close()


@pytest.mark.parametrize('size',[1000,10000])
def test_native_roster_reads_only_selected_ordinary_namespace_bodies(tmp_path,record_property,size):
    import sqlite3,time
    path,pair=fixture(tmp_path,size=size)
    with opened(path,pair) as s:
        st=s.store;unexpected=[];selected=[];empty_queries=[]
        def trace(sql):
            lower=sql.lower()
            if 'select' in lower and 'payload' in lower:
                if 'from records' in lower:
                    (selected if "namespace='world.year'" in lower else empty_queries if "namespace='world.not-present'" in lower else unexpected).append(sql)
                elif 'from lazy_record_versions' in lower or 'from segments' in lower:unexpected.append(sql)
        def authorize(action,table,column,database,source):
            if action==sqlite3.SQLITE_READ and table in ('segments','lazy_record_versions') and column=='payload':unexpected.append((table,column))
            return sqlite3.SQLITE_OK
        st.db.set_trace_callback(trace);st.db.set_authorizer(authorize)
        try:
            start=time.perf_counter()
            for _ in range(10):
                assert st.read_records(NS)==((0,(0,0),1),)
                assert st.read_records('world.not-present')==()
            elapsed=time.perf_counter()-start
        finally:st.db.set_trace_callback(None);st.db.set_authorizer(None)
        # Empty namespace cursor may be prepared, but selects no actual body.
        assert len(selected)==10
        assert not unexpected
        record_property('history_values',size);record_property('selected_namespace_queries',len(selected))
        record_property('empty_namespace_payload_queries',len(empty_queries))
        record_property('unexpected_other_body_reads',len(unexpected));record_property('seconds',elapsed)


def test_native_roster_schema_and_decoder_failures_close_snapshot(tmp_path,monkeypatch):
    from ate_sim.incremental_store import StoreFormatError
    path,pair=fixture(tmp_path)
    with opened(path,pair) as s:
        st=s.store
        with pytest.raises(StoreFormatError):st.read_records(NS,expected_record_schema=999)
        assert not st.db.in_transaction
        decode=st.codec.decode;payload=st.codec.encode((0,0))
        def failed(raw):
            if raw==payload:raise ValueError('roster decoder failure')
            return decode(raw)
        with monkeypatch.context() as patch:
            patch.setattr(st.codec,'decode',failed)
            with pytest.raises(ValueError,match='roster decoder failure'):st.read_records(NS)
        assert not st.db.in_transaction and s.save()==0


@pytest.mark.parametrize('phase',['before_commit','after_commit'])
def test_native_roster_recovery_uses_resolved_accepted_counts(tmp_path,phase):
    path,pair=fixture(tmp_path)
    with opened(path,pair) as s:
        s.world.year=1
        def fault(at):
            if at==phase:raise RuntimeError('roster lost acknowledgement')
        s.store._phase_hook=fault
        with pytest.raises(RuntimeError):s.save()
        s.store._phase_hook=lambda _:None
        assert s.resolve_save()==(1 if phase=='after_commit' else 0)
        assert s.store.read_records(NS)==((0,(0,1 if phase=='after_commit' else 0),1),)
        assert s.save()==1


def test_native_roster_staging_callback_has_no_authority(tmp_path):
    from ate_sim.incremental_store import StoreError
    path,pair=fixture(tmp_path)
    with opened(path,pair) as s:
        s.world.year=1;seen=[]
        def callback(at):
            if at=='before_commit':
                with pytest.raises(StoreError):s.store.read_records(NS)
                seen.append(True);raise RuntimeError('roster callback rollback')
        s.store._phase_hook=callback
        with pytest.raises(RuntimeError):s.save()
        s.store._phase_hook=lambda _:None
        assert seen and s.resolve_save()==0


def test_native_roster_separates_record_and_segment_counts(tmp_path,sealed_fixture):
    import shutil,sqlite3
    from ate_sim.incremental_store import _namespace_counts
    from ate_sim.persistence_proof_projection import _ProjectionCodec
    source,pair=sealed_fixture;path=tmp_path/'proof.sqlite';shutil.copyfile(source,path)
    with opened(path,pair) as s:
        st=s.store;namespace=st.db.execute('SELECT namespace FROM segments LIMIT 1').fetchone()[0]
        counts=_namespace_counts(_ProjectionCodec(metadata=True),s.proof_manifest[0].head.namespace_counts)
        records,segments=counts[namespace];assert segments>0
        seen=[]
        def authorize(action,table,column,database,source):
            if action==sqlite3.SQLITE_READ and table=='segments' and column=='payload':seen.append(True)
            return sqlite3.SQLITE_OK
        st.db.set_authorizer(authorize)
        try:assert len(st.read_records(namespace))==records
        finally:st.db.set_authorizer(None)
        assert not seen and not st.db.in_transaction
