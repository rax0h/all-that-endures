"""Pressure uses the same one native ordered sum on every cache miss."""
from ate_sim.core import Household
from ate_sim.persistence_lazy import open_lazy_world_session
from ate_sim.persistence_pressure import household_preparedness_mean
from simulation.tests.test_stage_0_5_final_household_sequences import converted, RULES


def native(world, settlement):
    return sum(world.households[hid].preparedness for hid in settlement.households) / max(1, len(settlement.households))


def test_pressure_exact_float_hex_duplicate_extinct_order_and_cache_writers(tmp_path):
    path = converted(tmp_path, size=16)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        world, settlement = session.world, session.world.settlements[1]
        world.households[1].preparedness = 1e16
        world.households[2].preparedness = -1e16
        world.households[3] = Household(3, 1, preparedness=1.)
        settlement.households = [1, 3, 2, 3, 2, 1]
        assert household_preparedness_mean(world, settlement).hex() == native(world, settlement).hex()
        before = session.store.diagnostics().payload_reads
        assert household_preparedness_mean(world, settlement).hex() == native(world, settlement).hex()
        assert session._pressure_cache.diagnostics()['hits'] == 1
        assert session.store.diagnostics().payload_reads == before
        world.households[2].preparedness = -.25
        assert household_preparedness_mean(world, settlement).hex() == native(world, settlement).hex()
        settlement.households.remove(1.)
        assert household_preparedness_mean(world, settlement).hex() == native(world, settlement).hex()
        world.households[3] = Household(3, 1, preparedness=.125)
        assert household_preparedness_mean(world, settlement).hex() == native(world, settlement).hex()
        settlement.households = [3, 2, 3]
        assert household_preparedness_mean(world, settlement).hex() == native(world, settlement).hex()
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert household_preparedness_mean(session.world, session.world.settlements[1]).hex() == native(session.world, session.world.settlements[1]).hex()


def test_pressure_missing_household_is_not_filtered_out(tmp_path):
    import pytest
    path = converted(tmp_path, size=16)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        household_preparedness_mean(session.world, session.world.settlements[1])
        del session.world.households[2]
        with pytest.raises(KeyError):
            household_preparedness_mean(session.world, session.world.settlements[1])


def test_pressure_stream_reads_headers_without_household_member_backing(tmp_path, monkeypatch):
    from ate_sim.persistence_lazy_sequence import DESCRIPTOR_NAMESPACE
    path = converted(tmp_path, size=1000)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        original = session.store.read_version
        reads = []
        def read(pin, namespace, key, **kwargs):
            reads.append(namespace)
            return original(pin, namespace, key, **kwargs)
        monkeypatch.setattr(session.store, 'read_version', read)
        assert household_preparedness_mean(session.world, session.world.settlements[1]) == (.2 + .9 + .2) / 3
        assert reads.count('world.households') == 3
        assert DESCRIPTOR_NAMESPACE not in reads
        assert dict.__len__(session.world.households) == 0
