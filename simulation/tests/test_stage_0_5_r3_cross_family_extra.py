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
