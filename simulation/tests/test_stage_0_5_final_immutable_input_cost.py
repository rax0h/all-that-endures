"""Native immutable input bytes are preserved and charged as current value work."""
import pytest
from dataclasses import asdict
from ate_sim.core import Person
from ate_sim.persistence_complete_format import upgrade_lazy_snapshot
from ate_sim.persistence_lazy import open_lazy_world_session
from ate_sim.persistence_lazy_budget import SharedCacheBudget
from simulation.tests.test_stage_0_5_final_catalog_copy import legacy_lazy,RULES


@pytest.mark.parametrize('field',['parents','species'])
def test_imported_native_tuple_and_scalar_have_explicit_byte_cost(tmp_path,record_property,field):
    measured=[]
    for size in (1000,10000):
        folder=tmp_path/str(size);folder.mkdir()
        expected=tuple(range(size)) if field=='parents' else 'x'*size
        def configure(world):
            person=Person(1,0,1,1);setattr(person,field,expected)
            world.people[1]=person;world.next_person=2
        source=legacy_lazy(folder,configure=configure);target=folder/'complete.sqlite'
        upgrade_lazy_snapshot(source,target,rules_id=RULES)
        with open_lazy_world_session(target,rules_id=RULES) as s:
            budget=SharedCacheBudget(entry_limit=4096,byte_limit=128)
            s._record_cache_budget=budget
            s.store.reset_diagnostics()
            held=s.people[1]
            assert type(getattr(held,field)) is type(expected) and getattr(held,field)==expected
            assert budget.diagnostics()['bytes']==budget.diagnostics()['entries']==0
            held.wealth=17.;s.save()
            measured.append(asdict(s.store.diagnostics()))
        with open_lazy_world_session(target,rules_id=RULES) as s:
            assert getattr(s.people[1],field)==expected and s.people[1].wealth==17.
            world=s.detach(materialize_history=True)
        assert type(getattr(world.people[1],field)) is type(expected) and getattr(world.people[1],field)==expected
    record_property(field+'_h1k_h10k_current_immutable_io',measured)
    # A native tuple/string is one current value; its input bytes are not a
    # fixed historical page. Record that cost rather than inventing a bound.
    assert measured[1]['payload_read_bytes']>measured[0]['payload_read_bytes']
    assert measured[1]['payload_write_bytes']>measured[0]['payload_write_bytes']
