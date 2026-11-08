"""Public metadata and warm prefix reads retain the admitted World authority."""
import shutil
import sqlite3
import pytest

from ate_sim.incremental_store import StoreError,StoreIntegrityError,_head_checksum
from simulation.tests.test_stage_0_5_proof_world_session import fixture,opened
from simulation.tests.test_stage_0_6_proof_native_sources import sealed_fixture


def head_read(store,api):
    return store.generation if api=='generation' else getattr(store,api)()


@pytest.mark.parametrize('api',['generation','checked_head','head_metadata'])
@pytest.mark.parametrize('field',['seed','position','counts'])
def test_all_public_head_reads_bind_before_forged_bytes_are_decoded(tmp_path,monkeypatch,api,field):
    path,pair=fixture(tmp_path,size=4);session=opened(path,pair);store=session.store
    original=tuple(store.db.execute('SELECT generation,parent_generation,simulation_position,seed,next_ids,namespace_inventory,namespace_counts,head_checksum FROM save_head').fetchone())
    try:
        row=list(original);slot={'seed':3,'position':2,'counts':6}[field]
        changed=original[3]+1 if field=='seed' else store.codec.encode(999 if field=='position' else ())
        row[slot]=changed;row[7]=_head_checksum(*row[:7])
        store.db.execute('UPDATE save_head SET simulation_position=?,seed=?,namespace_counts=?,head_checksum=?',(row[2],row[3],row[6],row[7]));store.db.commit()
        authority=store._world_proof_authority;authority.epoch=authority._epoch()
        decode=store.codec.decode;seen=[]
        def observe(raw):
            if raw==changed:seen.append(True)
            return decode(raw)
        monkeypatch.setattr(store.codec,'decode',observe)
        with pytest.raises(StoreIntegrityError):head_read(store,api)
        assert not seen and not store.db.in_transaction
    finally:store.close()


@pytest.mark.parametrize('api',['generation','checked_head','head_metadata'])
@pytest.mark.parametrize('damage',['end-transaction','change-epoch'])
def test_public_head_decoder_cannot_end_or_rebind_the_snapshot(tmp_path,monkeypatch,api,damage):
    path,pair=fixture(tmp_path,size=4);session=opened(path,pair);store=session.store
    try:
        store._validated_head_row_cache=None;decode=store.codec.decode;fired=[]
        def hook(raw):
            if not fired:
                fired.append(True)
                if damage=='end-transaction':store.db.rollback()
                else:
                    authority=store._world_proof_authority;authority.epoch=(*authority.epoch[:-1],-1)
            return decode(raw)
        monkeypatch.setattr(store.codec,'decode',hook)
        with pytest.raises(StoreError):head_read(store,api)
        assert fired
    finally:store.close()


@pytest.mark.parametrize('api',['generation','checked_head','head_metadata'])
def test_public_head_reads_nest_and_follow_legitimate_save(tmp_path,api):
    path,pair=fixture(tmp_path,size=4)
    with opened(path,pair) as session:
        store=session.store
        with store.read_snapshot(session.pin):head_read(store,api)
        assert not store.db.in_transaction
        session.world.year=1;assert session.save()==1
        found=head_read(store,api)
        assert (found if api=='generation' else found.generation if api=='checked_head' else found['simulation_position'])==1


@pytest.mark.parametrize('api',['event','count','year'])
@pytest.mark.parametrize('external',[False,True])
def test_warmed_native_prefix_rejects_untracked_sql_before_cached_output(tmp_path,sealed_fixture,api,external):
    source,pair=sealed_fixture;path=tmp_path/'copy.sqlite';shutil.copyfile(source,path)
    session=opened(path,pair);store=session.store
    try:
        prefix=session.world.events._disk_prefix
        assert prefix[0].id==1 and prefix.resident_segments==1
        db=sqlite3.connect(path) if external else store.db
        try:db.execute("UPDATE segments SET payload_checksum='corrupt'");db.commit()
        finally:
            if external:db.close()
        with pytest.raises(StoreError):
            if api=='event':prefix[0]
            elif api=='count':len(prefix)
            else:prefix.last_year
    finally:store.close()


def test_warmed_native_prefix_keeps_same_cache_across_legitimate_save(tmp_path,sealed_fixture,monkeypatch):
    source,pair=sealed_fixture;path=tmp_path/'copy.sqlite';shutil.copyfile(source,path)
    with opened(path,pair) as session:
        prefix=session.world.events._disk_prefix;first=prefix[0];reads=prefix.diagnostics().segment_reads
        session.world.year+=1;session.save()
        with pytest.raises(StoreError):prefix[0]
        prefix=session.world.events._disk_prefix;first=prefix[0];reads=prefix.diagnostics().segment_reads
        def body(*args,**kwargs):pytest.fail('a warm prefix cache hit fetched a segment body')
        monkeypatch.setattr(session.store,'read_segment_checked',body)
        assert prefix[0] is first and prefix.diagnostics().segment_reads==reads


def test_paused_native_prefix_iterator_rechecks_before_each_cached_event(tmp_path,sealed_fixture):
    source,pair=sealed_fixture;path=tmp_path/'copy.sqlite';shutil.copyfile(source,path)
    session=opened(path,pair);store=session.store
    try:
        iterator=iter(session.world.events._disk_prefix)
        assert next(iterator).id==1 and not store.db.in_transaction
        store.db.execute("UPDATE segments SET payload_checksum='changed'");store.db.commit()
        with pytest.raises(StoreError):next(iterator)
    finally:store.close()


@pytest.mark.parametrize('operation',['point','verify'])
@pytest.mark.parametrize('rebind',[False,True])
def test_native_prefix_rechecks_after_segment_codec_before_caching(tmp_path,sealed_fixture,monkeypatch,operation,rebind):
    source,pair=sealed_fixture;path=tmp_path/'copy.sqlite';shutil.copyfile(source,path)
    session=opened(path,pair);store=session.store
    try:
        payload=store.db.execute('SELECT payload FROM segments LIMIT 1').fetchone()[0]
        prefix=session.world.events._disk_prefix;decode=store.codec.decode;called=[]
        def hook(raw):
            if raw==payload and not called:
                called.append(True)
                store.db.execute("UPDATE segments SET payload_checksum='changed'");store.db.commit()
                if rebind:
                    authority=store._world_proof_authority;authority.epoch=authority._epoch()
            return decode(raw)
        monkeypatch.setattr(store.codec,'decode',hook)
        with pytest.raises(StoreError):
            if operation=='point':prefix[0]
            else:prefix.verify_full()
        assert called and not prefix._cache
    finally:store.close()


@pytest.mark.parametrize('api',['generation','checked_head','head_metadata'])
def test_public_native_head_rejects_arbitrary_borrowed_transaction(tmp_path,api):
    path,pair=fixture(tmp_path,size=4)
    with opened(path,pair) as session:
        store=session.store;store.db.execute('BEGIN')
        try:
            with pytest.raises(StoreError):head_read(store,api)
        finally:store.db.rollback()


@pytest.mark.parametrize('damage',['rebegin','pin'])
@pytest.mark.parametrize('phase',['opener','result'])
def test_native_head_retains_original_transaction_and_pin(tmp_path,monkeypatch,damage,phase):
    from dataclasses import replace
    path,pair=fixture(tmp_path,size=4);session=opened(path,pair);store=session.store
    try:
        if phase=='opener':store._validated_head_row_cache=None
        decode=store.codec.decode;called=[]
        def hook(raw):
            if not called:
                called.append(True)
                if damage=='rebegin':store.db.rollback();store.db.execute('BEGIN')
                else:
                    authority=store._world_proof_authority
                    authority.read_pin=replace(authority.read_pin,token='not-registered')
            return decode(raw)
        monkeypatch.setattr(store.codec,'decode',hook)
        with pytest.raises(StoreError):store.checked_head()
        assert called and not store.db.in_transaction
    finally:store.close()


def test_native_head_checks_epoch_after_owned_snapshot_cleanup(tmp_path):
    path,pair=fixture(tmp_path,size=4);session=opened(path,pair);store=session.store
    called=[]
    def trace(sql):
        if sql=='ROLLBACK' and not called:
            called.append(True)
            store.db.execute("UPDATE records SET payload_checksum=payload_checksum WHERE namespace='world.year'")
    try:
        store.db.set_trace_callback(trace)
        with pytest.raises(StoreError):store.checked_head()
        assert called and not store.db.in_transaction
    finally:store.db.set_trace_callback(None);store.close()


def test_warm_prefix_has_one_bounded_context_check_and_rejects_arbitrary_transaction(tmp_path,sealed_fixture):
    source,pair=sealed_fixture;path=tmp_path/'copy.sqlite';shutil.copyfile(source,path)
    with opened(path,pair) as session:
        store=session.store;prefix=session.world.events._disk_prefix;first=prefix[0];sql=[]
        store.db.set_trace_callback(sql.append)
        try:assert prefix[0] is first
        finally:store.db.set_trace_callback(None)
        assert len(sql)<=25
        assert not any('FROM segments' in x for x in sql)
        store.db.execute('BEGIN')
        try:
            with pytest.raises(StoreError):len(prefix)
            assert store.db.in_transaction
        finally:store.db.rollback()
