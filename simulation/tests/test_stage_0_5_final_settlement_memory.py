"""Imported settlement memory uses existing checked recursive map authority."""
import pytest
from ate_sim.core import Settlement
from ate_sim.persistence_lazy_nested_history import LazyHistoryMap
from simulation.tests.test_stage_0_5_final_catalog_copy import legacy_lazy, module, RULES, sha
from simulation.tests.test_stage_0_5_final_world_catalog_bridge import open_bridge, activate


def converted(tmp_path,size=32,alias=True):
    def configure(world):
        memory={str(n):float(n) for n in range(size)}
        world.settlements[1]=Settlement(1,0,0,memory=memory)
        if alias:world.currency.wallets[1]={'memory':memory}
    source=legacy_lazy(tmp_path,configure=configure);before=sha(source)
    target=tmp_path/'normalized.sqlite'
    module()._copy_with_checked_catalog(source,target,rules_id=RULES,normalize_events=True)
    assert sha(source)==before
    return target


def test_imported_memory_is_one_compact_map_across_eager_and_lazy_roots(tmp_path):
    target=converted(tmp_path)
    with open_bridge(target,rules_id=RULES) as s:
        activate(s)
        memory=s.world.settlements[1].memory
        assert isinstance(memory,LazyHistoryMap)
        assert s.wallets[1]['memory'] is memory and len(memory)==32
        memory['monster_surge']=.25;s.save()
    with open_bridge(target,rules_id=RULES) as s:
        activate(s)
        memory=s.world.settlements[1].memory
        assert memory['monster_surge']==.25 and s.wallets[1]['memory'] is memory
        world=s.detach(materialize_history=True)
    assert world.settlements[1].memory is world.currency.wallets[1]['memory']


def test_imported_memory_is_compact_without_an_incidental_currency_alias(tmp_path):
    target=converted(tmp_path,alias=False)
    with open_bridge(target,rules_id=RULES) as s:
        activate(s)
        assert isinstance(s.world.settlements[1].memory,LazyHistoryMap)
        assert len(s.world.settlements[1].memory)==32


@pytest.mark.parametrize('phase',['before_commit','after_commit'])
def test_memory_replacement_and_shared_child_recover_atomically(tmp_path,phase):
    target=converted(tmp_path)
    with open_bridge(target,rules_id=RULES) as s:
        activate(s)
        settlement=s.world.settlements[1];old=settlement.memory
        settlement.memory={'nested':[1,2]}
        assert isinstance(settlement.memory,LazyHistoryMap) and s.wallets[1]['memory'] is old
        replacement=settlement.memory
        s.wallets[2]={'memory':replacement}
        replacement['nested'].append(3)
        generation=s.pin.captured_head
        def fail(at):
            if at==phase:raise OSError(phase)
        s.store._phase_hook=fail
        with pytest.raises(OSError,match=phase):s.save()
        s.store._phase_hook=lambda _at:None
        assert s.resolve_save()==generation+(phase=='after_commit')
        if phase!='after_commit':s.save()
    with open_bridge(target,rules_id=RULES) as s:
        activate(s)
        memory=s.world.settlements[1].memory
        assert memory is s.wallets[2]['memory'] and memory is not s.wallets[1]['memory']
        assert list(memory['nested'])==[1,2,3]


def test_invalid_or_foreign_replacement_preserves_memory_before_change(tmp_path):
    from ate_sim.incremental_store import StoreError
    a=tmp_path/'a';b=tmp_path/'b';a.mkdir();b.mkdir()
    first,second=converted(a),converted(b)
    with open_bridge(first,rules_id=RULES) as s,open_bridge(second,rules_id=RULES) as other:
        activate(s);activate(other)
        settlement=s.world.settlements[1];old=settlement.memory
        with pytest.raises((StoreError,TypeError)):settlement.memory=other.world.settlements[1].memory
        assert settlement.memory is old
        with pytest.raises((StoreError,TypeError)):settlement.memory={'bad':object()}
        assert settlement.memory is old and s.wallets[1]['memory'] is old
        s.save()


def test_scalar_settlement_edit_has_fixed_imported_memory_work(tmp_path,record_property):
    from dataclasses import asdict
    from ate_sim.persistence_lazy_nested_history import ENTRY_NAMESPACE
    measured=[]
    for size in (1000,10000):
        folder=tmp_path/str(size);folder.mkdir();target=converted(folder,size,alias=False)
        with open_bridge(target,rules_id=RULES) as s:
            activate(s)
            settlement=s.world.settlements[1];memory=settlement.memory
            assert isinstance(memory,LazyHistoryMap) and len(memory)==size
            read=s.store.read_version
            def no_memory(pin,namespace,key,**kwargs):
                if namespace==ENTRY_NAMESPACE and key[0]==memory._incarnation:
                    pytest.fail('scalar edit traversed imported memory entries')
                return read(pin,namespace,key,**kwargs)
            s.store.read_version=no_memory
            s.store.reset_diagnostics()
            settlement.defense=.75;s.save()
            measured.append(asdict(s.store.diagnostics()))
            s.store.reset_diagnostics();s.save()
            assert s.store.diagnostics().payload_writes==0
        with open_bridge(target,rules_id=RULES) as s:
            activate(s)
            assert s.world.settlements[1].defense==.75
            assert s.world.settlements[1].memory[str(size-1)]==float(size-1)
    record_property('h1k_h10k_settlement_memory_io',measured)
    for name in ('payload_reads','payload_writes','metadata_rows'):
        assert measured[0][name]==measured[1][name]
    for name in ('payload_read_bytes','payload_write_bytes'):
        assert abs(measured[0][name]-measured[1][name])<=512


def test_imported_cultural_institution_practices_use_compact_eager_child(tmp_path):
    from ate_sim.culture import Institution
    from ate_sim.persistence_lazy_nested_history import LazyHistorySet
    def configure(world):world.culture.institutions[1]=Institution(1,1,'guild',0,practices=set(range(1000)))
    source=legacy_lazy(tmp_path,configure=configure);target=tmp_path/'normalized.sqlite'
    module()._copy_with_checked_catalog(source,target,rules_id=RULES,normalize_events=True)
    with open_bridge(target,rules_id=RULES) as s:
        activate(s)
        record=s.world.culture.institutions[1]
        assert isinstance(record.practices,LazyHistorySet) and len(record.practices)==1000
        record.practices.add(1001);s.save()
    with open_bridge(target,rules_id=RULES) as s:
        activate(s)
        record=s.world.culture.institutions[1]
        assert 1001 in record.practices and len(record.practices)==1001
        record.practices={3,7}
        assert isinstance(record.practices,LazyHistorySet)
        s.save()
