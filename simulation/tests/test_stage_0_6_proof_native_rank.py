"""Native rank seeks must prove no better accepted candidate was omitted."""
import hashlib
import pytest

from ate_sim.metaphysics import ResurrectionToken
from ate_sim.incremental_store import StoreError,StoreIntegrityError,StoreConflictError
from ate_sim.persistence_lazy_minimum import numeric_rank,rank_neighbor,scope_name
from ate_sim.persistence_lazy_store import _query_checksum
from ate_sim.persistence_proof_world_copy import copy_world_with_proofs
from simulation.tests.test_stage_0_5_final_catalog_copy import legacy_lazy
from simulation.tests.test_stage_0_5_proof_world_session import opened

NS='world.metaphysics.resurrection_tokens'


def rank_fixture(tmp_path,*,size=4,ranked=True):
    def configure(w):
        for key,ident in ((11,-2),(12,-2),(13,4)):
            w.metaphysics.resurrection_tokens[key]=ResurrectionToken(ident,1,'god',str(key),0,1)
    source=legacy_lazy(tmp_path,size=size,configure=configure)
    before=hashlib.sha256(source.read_bytes()).digest()
    path=tmp_path/'ranked.sqlite'
    value=copy_world_with_proofs(source,path,rules_id='private-catalog-copy',rank_proofs=ranked)
    assert hashlib.sha256(source.read_bytes()).digest()==before
    return path,(value.manifest,value.commitment)


def bucket(store):return scope_name('person_consumed',(1,None),store.codec)


@pytest.mark.parametrize('before,rank,ordinal,exclude,want',[
    (False,None,None,(),(0,11)),(True,None,None,(),(2,13)),
    (False,-2,0,(),(1,12)),(True,-2,1,(),(0,11)),
    (False,-2,1,(),(2,13)),(True,-2,0,(),None),
    (False,None,None,(11,),(1,12)),(True,None,None,(13,),(1,12)),
    (False,None,None,(11,12,13),None)])
def test_native_rank_preserves_strict_bounds_equal_ties_and_exclusions(tmp_path,before,rank,ordinal,exclude,want):
    path,pair=rank_fixture(tmp_path)
    with opened(path,pair) as session:
        store=session.store
        assert len(store._world_proof_authority.read_components[1][0].roots)==7
        found=rank_neighbor(store,session.pin,NS,bucket(store),rank=None if rank is None else numeric_rank(rank),
            ordinal=ordinal,before=before,exclude=exclude)
        assert (None if found is None else found[1:])==want
        assert rank_neighbor(store,session.pin,NS,scope_name('person_consumed',(99,None),store.codec)) is None
        assert not store.db.in_transaction


@pytest.mark.parametrize('damage',['extra-earlier','extra-later','empty-extra','missing','missing-second','ordinal','future-start','future-close','overlap','oversized-rank'])
def test_native_rank_rejects_coherent_physical_window_damage_before_decoding(tmp_path,monkeypatch,damage):
    path,pair=rank_fixture(tmp_path);session=opened(path,pair);store=session.store
    try:
        scope=bucket(store);key=store.codec.encode(11);rank=store.codec.encode(numeric_rank(-2));ordinal=0;start,end=0,None
        if damage=='empty-extra':scope=scope_name('person_consumed',(99,None),store.codec)
        if damage in ('missing','missing-second','ordinal','future-start','future-close','oversized-rank'):
            deleted=store.codec.encode(12) if damage=='missing-second' else key
            store.db.execute('DELETE FROM lazy_query_versions WHERE namespace=? AND index_name=? AND record_key=?',(NS,scope,deleted))
        if damage not in ('missing','missing-second'):
            if damage in ('extra-earlier','extra-later'):key=store.codec.encode(99);rank=store.codec.encode(numeric_rank(-3 if damage=='extra-earlier' else 10));ordinal=9
            if damage=='ordinal':ordinal=99
            if damage in ('future-start','overlap'):start=1
            if damage=='future-close':end=1
            if damage=='oversized-rank':rank=b'0'*4097
            store.db.execute('INSERT INTO lazy_query_versions VALUES(?,?,?,?,?,?,?,?)',
                (NS,scope,rank,key,ordinal,start,end,_query_checksum(NS,scope,rank,key,ordinal,start,end)))
        store.db.commit();store._world_proof_authority.epoch=store._world_proof_authority._epoch()
        seen=[];decode=store.codec.decode;selected=tuple(store.codec.encode(k) for k in (11,12,13,99))
        def watched(raw):
            if raw in selected:seen.append(raw)
            return decode(raw)
        monkeypatch.setattr(store.codec,'decode',watched)
        with pytest.raises(StoreError):rank_neighbor(store,session.pin,NS,scope,before=damage=='extra-later')
        assert not seen and not store.db.in_transaction
    finally:store.close()


def test_native_rank_uses_original_caller_pin_and_callback_guard(tmp_path):
    from dataclasses import replace
    path,pair=rank_fixture(tmp_path)
    with opened(path,pair) as session:
        store=session.store;scope=bucket(store)
        with pytest.raises(StoreError):rank_neighbor(store,replace(session.pin,token='released-pin'),NS,scope)
        with pytest.raises(StoreConflictError):rank_neighbor(store,replace(session.pin,captured_head=1),NS,scope)
        original=session.pin;session.world.year=1;session.save()
        with pytest.raises(StoreConflictError):rank_neighbor(store,original,NS,scope)
        caught=[]
        def callback():
            try:rank_neighbor(store,session.pin,NS,scope)
            except StoreError as exc:caught.append(exc)
            return 1
        store.db.create_function('rank_callback',0,callback)
        from ate_sim.persistence_proof_native_guard import NativeWriteGuard
        with NativeWriteGuard(store.db):
            assert store.db.execute('SELECT rank_callback()').fetchone()==(1,)
        assert len(caught)==1 and isinstance(caught[0],StoreConflictError)


def test_native_rank_copy_is_explicit_and_old_format_seven_still_reads(tmp_path):
    path,pair=rank_fixture(tmp_path,ranked=False)
    with opened(path,pair) as session:
        assert len(session.store._world_proof_authority.read_components[1][0].roots)==6
        assert rank_neighbor(session.store,session.pin,NS,bucket(session.store))[2]==11


def test_native_rank_public_minimum_move_save_and_fresh_open(tmp_path):
    path,pair=rank_fixture(tmp_path)
    with opened(path,pair) as session:
        assert session.world.metaphysics.available_token(1).patron_id=='11'
        session.world.metaphysics.resurrection_tokens[11].consumed_year=2
        assert session.save()==1
        assert session.world.metaphysics.available_token(1).patron_id=='12'
        child=session.proof_manifest;digest=session.world.digest()
    with opened(path,child) as session:
        assert session.world.metaphysics.available_token(1).patron_id=='12'
        assert session.world.digest()==digest


@pytest.mark.parametrize('history',[1000,10000])
def test_native_rank_skips_expired_bucket_backlog_and_unrelated_owner_bodies(tmp_path,monkeypatch,history):
    path,pair=rank_fixture(tmp_path)
    with opened(path,pair) as session:
        store=session.store
        for year in (1,2):session.world.year=year;assert session.save()==year
        name=bucket(store);rank=store.codec.encode(numeric_rank(-2))
        rows=[]
        for i in range(history):
            key=store.codec.encode(100000+i)
            rows.append((NS,name,rank,key,i,0,1,_query_checksum(NS,name,rank,key,i,0,1)))
        store.db.executemany('INSERT INTO lazy_query_versions VALUES(?,?,?,?,?,?,?,?)',rows);store.db.commit()
        store._world_proof_authority.epoch=store._world_proof_authority._epoch()
        original=store._visible_record_row;selected=[]
        def checked(generation,namespace,typed):
            assert (namespace,typed)==(NS,store.codec.encode(11))
            selected.append(typed)
            return original(generation,namespace,typed)
        monkeypatch.setattr(store,'_visible_record_row',checked)
        ticks=[];store.db.set_progress_handler(lambda:ticks.append(1) or 0,100)
        try:assert rank_neighbor(store,session.pin,NS,name)==(numeric_rank(-2),0,11)
        finally:store.db.set_progress_handler(None,0)
        assert selected==[store.codec.encode(11)] and len(ticks)*100<15000
        assert not store.db.in_transaction


@pytest.mark.parametrize('field',['rank','exclude','composite-exclude'])
def test_rank_rejects_large_input_before_codec_serialization(tmp_path,monkeypatch,field):
    path,pair=rank_fixture(tmp_path)
    with opened(path,pair) as session:
        store=session.store;scope=bucket(store);huge='X'*(8*1024*1024)
        value=huge if field=='rank' else huge.encode() if field=='exclude' else ('ok',huge.encode())
        kwargs=dict(rank=value,ordinal=0) if field=='rank' else dict(exclude=(value,))
        encode=store.codec.encode;seen=[]
        def observed(v):
            if v is value:seen.append(True)
            return encode(v)
        monkeypatch.setattr(store.codec,'encode',observed)
        with pytest.raises(StoreError):rank_neighbor(store,session.pin,NS,scope,**kwargs)
        assert not seen


def test_rank_rejects_bad_pin_before_serializing_supplied_fields(tmp_path,monkeypatch):
    from dataclasses import replace
    path,pair=rank_fixture(tmp_path)
    with opened(path,pair) as session:
        store=session.store;scope=bucket(store);seen=[];encode=store.codec.encode
        def observed(v):
            if v in ('RANK','KEY'):seen.append(v)
            return encode(v)
        monkeypatch.setattr(store.codec,'encode',observed)
        with pytest.raises(StoreConflictError):
            rank_neighbor(store,replace(session.pin,token='released'),NS,scope,rank='RANK',ordinal=1,exclude=('KEY',))
        assert not seen


def test_rank_rejects_temporary_physical_source_during_guarded_preparation(tmp_path):
    path,pair=rank_fixture(tmp_path)
    with opened(path,pair) as session:
        store=session.store;scope=bucket(store)
        def shadow():
            store.db.execute('CREATE TEMP TABLE lazy_query_versions AS SELECT * FROM main.lazy_query_versions')
            store.db.execute('CREATE INDEX temp.lazy_query_current ON lazy_query_versions(namespace,index_name,index_value,ordinal,record_key) WHERE valid_to IS NULL')
            store.db.execute('CREATE INDEX temp.ate_rank_query_closed ON lazy_query_versions(namespace,index_name,valid_to,index_value,ordinal,record_key) WHERE valid_to IS NOT NULL')
            try:
                with pytest.raises(StoreError):rank_neighbor(store,session.pin,NS,scope)
            finally:store.db.execute('DROP TABLE temp.lazy_query_versions')
        store._world_proof_authority.execute(session,shadow)


@pytest.mark.parametrize('damage',['commit','epoch','end-snapshot'])
@pytest.mark.parametrize('excluded',[False,True])
def test_rank_rejects_snapshot_or_epoch_drift_from_selected_decoder(tmp_path,monkeypatch,damage,excluded):
    path,pair=rank_fixture(tmp_path);session=opened(path,pair);store=session.store
    try:
        scope=bucket(store);expected=store.codec.encode(numeric_rank(-2));decode=store.codec.decode;called=[]
        def changed(raw):
            if not called and raw==expected:
                called.append(True)
                if damage=='commit':
                    store.db.execute('DELETE FROM lazy_query_versions WHERE namespace=? AND index_name=? AND ordinal=0',(NS,scope))
                    store.db.commit()
                elif damage=='end-snapshot':store.db.rollback()
                else:store._world_proof_authority.epoch=(*store._world_proof_authority.epoch[:-1],-1)
            return decode(raw)
        monkeypatch.setattr(store.codec,'decode',changed)
        with pytest.raises(StoreError):rank_neighbor(store,session.pin,NS,scope,exclude=(11,) if excluded else ())
        assert called
    finally:store.close()


def test_rank_missing_active_components_cannot_fall_back_to_legacy(tmp_path):
    path,pair=rank_fixture(tmp_path);session=opened(path,pair);store=session.store
    try:
        scope=bucket(store)
        store.db.execute('DELETE FROM lazy_query_versions WHERE namespace=? AND index_name=? AND ordinal=0',(NS,scope))
        store.db.commit();authority=store._world_proof_authority;authority.epoch=authority._epoch()
        authority.read_components=None
        with pytest.raises(StoreError):rank_neighbor(store,session.pin,NS,scope)
    finally:store.close()


def test_rank_bounded_preflight_preserves_scalar_and_composite_key_encodings(tmp_path):
    from ate_sim.core import Ref,Layer
    from ate_sim.persistence_record_headers import RecordReference
    path,pair=rank_fixture(tmp_path)
    excluded=(None,False,1,1.5,'ok',b'k',(1,'x'),frozenset((1,'x')),Ref('person',1),Layer.REALITY,RecordReference(1))
    with opened(path,pair) as session:
        assert rank_neighbor(session.store,session.pin,NS,bucket(session.store),exclude=excluded)==(numeric_rank(-2),0,11)


def test_rank_rechecks_durable_sources_after_exclusion_codec_hook(tmp_path,monkeypatch):
    path,pair=rank_fixture(tmp_path)
    with opened(path,pair) as session:
        store=session.store;scope=bucket(store);encode=store.codec.encode;created=[]
        def changed(value):
            if value=='hook-key' and not created:
                created.append(True)
                store.db.execute('CREATE TEMP TABLE lazy_query_versions AS SELECT * FROM main.lazy_query_versions')
                store.db.execute('CREATE INDEX temp.lazy_query_current ON lazy_query_versions(namespace,index_name,index_value,ordinal,record_key) WHERE valid_to IS NULL')
                store.db.execute('CREATE INDEX temp.ate_rank_query_closed ON lazy_query_versions(namespace,index_name,valid_to,index_value,ordinal,record_key) WHERE valid_to IS NOT NULL')
            return encode(value)
        def operation():
            with monkeypatch.context() as patch:
                patch.setattr(store.codec,'encode',changed)
                try:
                    with pytest.raises(StoreError):rank_neighbor(store,session.pin,NS,scope,exclude=('hook-key',))
                finally:
                    if created:store.db.execute('DROP TABLE IF EXISTS temp.lazy_query_versions')
        store._world_proof_authority.execute(session,operation)
        assert created
