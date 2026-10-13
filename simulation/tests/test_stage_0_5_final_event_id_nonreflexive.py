"""Checked Event-ID exceptions reuse the runtime's exact native key projection."""
import pytest
from ate_sim.core import Ref
from ate_sim.persistence_event_ids import EventIdSet, EXCEPTION_TAG
from simulation.tests.test_stage_0_5_final_catalog_copy import legacy_lazy, module, RULES
from simulation.tests.test_stage_0_5_final_world_catalog_bridge import open_bridge, activate


def converted(tmp_path, end=1000):
    def configure(world):world.event_ids=EventIdSet.from_range_descriptor(end)
    source=legacy_lazy(tmp_path,configure=configure);target=tmp_path/'checked.sqlite'
    module()._copy_with_checked_catalog(source,target,rules_id=RULES,normalize_events=True)
    return target


@pytest.mark.parametrize('shape', [lambda n:n,lambda n:('key',n),lambda n:frozenset((n,)),lambda n:Ref('key',n)],ids=['float','tuple','frozenset','ref'])
def test_nan_addition_uses_paged_exceptions_without_expanding_range(tmp_path,monkeypatch,shape):
    target=converted(tmp_path,1000)
    with open_bridge(target,rules_id=RULES) as s:
        activate(s)
        ids=s.world.event_ids;first,second=shape(float('nan')),shape(float('nan'))
        def no_scan(_self):pytest.fail('NaN addition expanded the captured event-ID prefix')
        with monkeypatch.context() as m:
            m.setattr(EventIdSet,'__iter__',no_scan)
            ids.add(first);ids.add(second)
            assert first in ids and second in ids
            assert shape(float('nan')) not in ids
            ids.remove(first)
            s.save()
        assert ids.descriptor()[0]==EXCEPTION_TAG and len(ids)==1001
        assert ids.diagnostics()['member_visits']==0
    with open_bridge(target,rules_id=RULES) as s:
        activate(s)
        ids=s.world.event_ids
        held=next(iter(ids._exact.added))
        ids._exact.added._clear_cache()
        assert held in ids and len(ids)==1001
        s.save()


@pytest.mark.parametrize('phase', ['during_version_writes', 'during_ordinary_writes', 'before_commit', 'after_commit'])
def test_checked_nan_event_ids_resolve_atomic_save_faults(tmp_path,phase):
    target=converted(tmp_path)
    with open_bridge(target,rules_id=RULES) as s:
        activate(s)
        ids=s.world.event_ids;nan=float('nan')
        ids.add(nan)
        s.wallets[1]={'ids':ids,'exceptions':ids._exact.added,'key':nan}
        generation=s.pin.captured_head
        def fail(at):
            if at==phase:raise OSError(phase)
        s.store._phase_hook=fail
        with pytest.raises(OSError,match=phase):s.save()
        s.store._phase_hook=lambda _at:None
        assert s.resolve_save()==generation+(phase=='after_commit')
        if phase!='after_commit':s.save()
        assert ids is s.world.event_ids and nan in ids
    with open_bridge(target,rules_id=RULES) as s:
        activate(s)
        ids=s.world.event_ids;wallet=s.wallets[1]
        assert wallet['ids'] is ids and wallet['exceptions'] is ids._exact.added
        assert wallet['key'] in ids
        added=float('nan');wallet['exceptions'].add(added)
        s.save()
    with open_bridge(target,rules_id=RULES) as s:
        activate(s)
        ids=s.world.event_ids
        assert len(ids)==1002 and s.wallets[1]['key'] in ids
        detached=s.detach(materialize_history=True)
    assert detached.currency.wallets[1]['ids'] is detached.event_ids
    assert detached.currency.wallets[1]['key'] in detached.event_ids


def test_genuine_legacy_nan_keys_keep_native_compatibility(tmp_path):
    from ate_sim.persistence_lazy import open_lazy_world_session
    target=legacy_lazy(tmp_path)
    with open_lazy_world_session(target,rules_id=RULES) as s:
        assert s._identity_coordinator is None
        nan=float('nan');s.world.event_ids.add(nan)
        assert nan in s.world.event_ids and isinstance(s.world.event_ids._exact,set)
        s.save()


def test_explicit_copy_upgrades_legacy_nan_event_id_authority(tmp_path):
    from ate_sim.core import Event, Layer
    from simulation.tests.test_stage_0_5_final_catalog_copy import sha
    def configure(world):
        world.event_ids={1,float('nan'),('key',float('nan'))}
        world.events.append(Event(1,0,'legacy',Layer.SOCIETY,data={'ids':world.event_ids}))
        world.next_event=2
    source=legacy_lazy(tmp_path,configure=configure);before=sha(source)
    target=tmp_path/'normalized.sqlite'
    module()._copy_with_checked_catalog(source,target,rules_id=RULES,normalize_events=True)
    assert sha(source)==before
    with open_bridge(target,rules_id=RULES) as s:
        activate(s)
        ids=s.world.event_ids
        assert ids.descriptor()[0]==EXCEPTION_TAG and len(ids)==3
        assert s.world.events[0].data['ids'] is ids
        held=tuple(ids._exact.added)
        ids._exact.added._clear_cache()
        assert all(key in ids for key in held)
        ids.add(float('nan'));s.save()
    with open_bridge(target,rules_id=RULES) as s:
        activate(s)
        assert len(s.world.event_ids)==4


def test_nan_point_edit_has_fixed_work_at_h1k_h10k(tmp_path,record_property):
    from dataclasses import asdict
    measured=[]
    for size in (1000,10000):
        folder=tmp_path/str(size);folder.mkdir()
        target=converted(folder,size)
        with open_bridge(target,rules_id=RULES) as s:
            activate(s)
            ids=s.world.event_ids
            s.store.reset_diagnostics()
            nan=float('nan');ids.add(nan);s.save()
            row=asdict(s.store.diagnostics())
            assert ids.diagnostics()['member_visits']==0
            measured.append(row)
            s.store.reset_diagnostics()
            original=s.store.read_version
            def no_archive(*_args,**_kwargs):pytest.fail('no-op save read versioned archive payload')
            s.store.read_version=no_archive
            try:s.save()
            finally:s.store.read_version=original
            no_op=s.store.diagnostics()
            assert no_op.payload_writes==0
            row['no_op_metadata_reads']=no_op.payload_reads
    record_property('h1k_h10k_nan_event_id_io',measured)
    for name in ('payload_reads','payload_writes','metadata_rows'):
        assert measured[0][name]==measured[1][name]
    for name in ('payload_read_bytes','payload_write_bytes'):
        assert abs(measured[0][name]-measured[1][name])<=512
