"""Session history budgets are shared across independent family owners."""
from ate_sim.core import World, Household
from ate_sim.economy import Property
from ate_sim.infrastructure import Infrastructure
from ate_sim.persistence_session import write_cold_snapshot
from ate_sim.persistence_lazy import convert_cold_to_lazy, open_lazy_world_session


def test_world_shares_history_budget_and_close_releases_clean_sidecars(tmp_path):
    rules = 'shared-history-budget'
    world = World(843000)
    for key in range(1, 38):
        world.economy.property[key] = Property(key, 'farm', 1, 'household', key, 10., 3,
                                             list(range(256)), [])
    world.infrastructure.assets[1] = Infrastructure(1, 'farm', (1,), .8, 1., 0,
                                                   provenance=list(range(256)))
    world.households[1] = Household(1, 1, list(range(1, 257)))
    source, path = tmp_path / 'source.sqlite', tmp_path / 'lazy.sqlite'
    write_cold_snapshot(world, source, rules_id=rules)
    convert_cold_to_lazy(source, path, rules_id=rules, paged_household_members=True)
    session = open_lazy_world_session(path, rules_id=rules)
    try:
        budget = session._history_cache_budget
        histories = [session.world.economy.property[key].provenance for key in range(1, 38)]
        histories.append(session.world.infrastructure.assets[1].provenance)
        histories.append(session.world.households[1].members)
        for history in histories:
            first = 1 if history is session.world.households[1].members else 0
            assert history[0] == first and history[128] == first + 128
            assert history._cache_budget is budget
        assert sum(len(h._cache) for h in histories) == budget.diagnostics()['entries'] == 64
        assert budget.diagnostics()['bytes'] <= 8 * 1024 * 1024
        assert session.diagnostics()['history_cache'] == budget.diagnostics()
        session.close()
        assert budget.diagnostics()['entries'] == budget.diagnostics()['owners'] == 0
        assert all(not h._cache and not h._cache_weights for h in histories)
    finally:
        session.close()
