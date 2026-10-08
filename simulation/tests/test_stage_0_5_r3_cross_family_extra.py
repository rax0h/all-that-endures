"""R3 P2C identity regression across a paged household and lazy wallet owner."""
from ate_sim.core import Household
from ate_sim.persistence_lazy import convert_cold_to_lazy, open_lazy_world_session
from ate_sim.persistence_session import write_cold_snapshot
from simulation.tests.test_persistence_lazy_people import people_world, RULES


def test_paged_household_members_shared_with_wallet_roundtrips_identity(tmp_path):
    from ate_sim import checkpoint
    world = people_world(250, active=8)
    shared = [1, 2, 2, 4]
    world.households[1] = Household(1, 1, shared)
    world.currency.wallets[99] = {"members": shared}
    world.next_household = 2
    source = tmp_path / "source.sqlite"
    destination = tmp_path / "paged.sqlite"
    write_cold_snapshot(world, source, rules_id=RULES)
    convert_cold_to_lazy(
        source, destination, rules_id=RULES, paged_household_members=True
    )
    with open_lazy_world_session(
        destination, rules_id=RULES, paged_household_members=True
    ) as session:
        primary = session.world.households[1].members
        print("PRIMARY INC", session._registry.incarnation_for_object(primary))
        print("INC KEYS", sorted((x.value for x in session._registry._by_incarnation)))
        from ate_sim.persistence_lazy import WALLET_NAMESPACE
        from ate_sim.persistence_lazy_identity import IncarnationId
        for ident_path in ((("key", "members"),), ()):
            try:
                row = session.store.read_identity_occurrence(
                    session.pin, WALLET_NAMESPACE, 99, ident_path
                )
                print("CROSS LABEL", ident_path, row.incarnation_id)
                print("LIVE", session._registry.object_for_incarnation(
                    IncarnationId(session.store.store_identity, row.incarnation_id)
                ))
            except KeyError:
                print("CROSS LABEL ABSENT", ident_path)
        print("DEFERRED", session._deferred_household_cross_links)
        related = session.world.currency.wallets[99]["members"]
        assert primary is related
        assert session.world.digest() == world.digest()
        related.append(500)
        shared.append(500)
        assert session.world.digest() == world.digest()
        assert session.save() > 0
    with open_lazy_world_session(
        destination, rules_id=RULES, paged_household_members=True
    ) as reopened:
        assert reopened.world.households[1].members is reopened.world.currency.wallets[99]["members"]
        assert reopened.world.digest() == world.digest()
        detached = reopened.detach(materialize_history=True)
    assert type(detached.households[1].members) is list
    assert detached.households[1].members is detached.currency.wallets[99]["members"]
    portable = checkpoint.loads(checkpoint.dumps(detached))
    assert portable.households[1].members is portable.currency.wallets[99]["members"]
    assert portable.digest() == world.digest()


import pytest


@pytest.mark.parametrize("count", [1000, 10000])
def test_three_owner_shared_members_are_bounded_and_portable(tmp_path, count):
    from ate_sim import checkpoint
    world = people_world(count, active=8)
    shared = list(range(1, count + 1))
    world.households[1] = Household(1, 1, shared)
    world.households[2] = Household(2, 1, shared)
    world.currency.wallets[99] = {"members": shared}
    world.next_household = 3
    cold = tmp_path / "cold.sqlite"
    path = tmp_path / "paged.sqlite"
    write_cold_snapshot(world, cold, rules_id=RULES)
    convert_cold_to_lazy(cold, path, rules_id=RULES, paged_household_members=True)

    with open_lazy_world_session(path, rules_id=RULES, paged_household_members=True) as session:
        left = session.world.households[1].members
        assert left is session.world.households[2].members
        assert left is session.world.currency.wallets[99]["members"]
        assert session.world.digest() == world.digest()
        session.store.reset_diagnostics()
        left.append(count + 1)
        shared.append(count + 1)
        assert session.save() > 0
        d = session.store.diagnostics()
        print("CROSS-OWNER WRITES", count, d.payload_writes, d.payload_write_bytes)
        assert d.payload_writes < 20
        assert d.payload_write_bytes < 8000
        assert session.store.verify_all()
        assert session.world.digest() == world.digest()

    with open_lazy_world_session(path, rules_id=RULES, paged_household_members=True) as reopened:
        shared_alias = reopened.world.currency.wallets[99]["members"]
        assert shared_alias is reopened.world.households[1].members
        assert shared_alias is reopened.world.households[2].members
        shared_alias.append(count + 2)
        shared.append(count + 2)
        reopened.save()
        assert reopened.world.digest() == world.digest()
        detached = reopened.detach(materialize_history=True)

    assert type(detached.households[1].members) is list
    assert detached.households[1].members is detached.households[2].members
    assert detached.households[1].members is detached.currency.wallets[99]["members"]
    portable = checkpoint.loads(checkpoint.dumps(detached))
    assert portable.households[1].members is portable.currency.wallets[99]["members"]
    assert portable.digest() == world.digest()
