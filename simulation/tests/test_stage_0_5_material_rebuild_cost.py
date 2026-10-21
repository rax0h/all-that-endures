"""Cold derived indexes must not reload every active lot for each projection."""
import pytest

from ate_sim.persistence_lazy import open_lazy_world_session
from simulation.tests.test_persistence_lazy_materials import converted, material_world, RULES


def loads(session):
    return session.material_lots.diagnostics()['material_lot_payload_loads']


def test_selection_does_not_build_unused_rank_or_capacity_indexes():
    state = material_world(20, active=20).materials
    assert state.best_available(1) is not None
    assert not hasattr(state, '_rank_heaps')
    assert not hasattr(state, '_whole_units')


def test_consumed_history_does_not_accumulate_in_unused_projections():
    from ate_sim.materials import MaterialEconomy
    state = MaterialEconomy()
    for n in range(1000):
        lot = state.create_lot('ore', 1., .5, 1, 1, 0, n)
        assert state.best_available(1) is lot
        state.consume(lot, 1.)
        assert state.best_available(1) is None
    assert len(state.lots) == 1000
    assert state._derived_lots == {}
    assert not hasattr(state, '_rank_heaps')


def test_rank_rebuild_preserves_original_ordered_push_for_nan():
    from heapq import heappush, heappop
    from ate_sim.materials import MaterialEconomy
    state = MaterialEconomy()
    expected = []
    for quality in (.1, float('nan'), .5, .7, .3):
        state.create_lot('ore', 1., quality, 1, 1, 0, 1, material_rank=2)
    for identity in state.active_lot_index[1]:
        heappush(expected, state._selection_key(state.lots[identity]))
    order = []
    while expected:
        order.append(heappop(expected)[1])
    actual = []
    while state.has_available(1):
        lot = state.best_at_rank(1, 2)
        actual.append(lot.id)
        state.consume(lot, 1.)
    assert actual == order


def test_selection_does_not_evaluate_infinite_capacity():
    from ate_sim.materials import MaterialEconomy
    state = MaterialEconomy()
    lot = state.create_lot('ore', float('inf'), .5, 1, 1, 0, 1)
    assert state.best_available(1) is lot
    with pytest.raises(OverflowError):
        state.crafting_capacity(1, 10)


def test_failed_rank_build_does_not_publish_a_partial_index():
    from ate_sim.materials import MaterialEconomy
    state = MaterialEconomy()
    state.create_lot('ore', 1., 'invalid quality', 1, 1, 0, 1)
    for _ in range(2):
        with pytest.raises(TypeError): state.best_at_rank(1, 0)


@pytest.mark.parametrize('order', [('selection', 'rank', 'capacity'), ('capacity', 'rank', 'selection')])
def test_cold_combined_queries_load_each_active_lot_once(tmp_path, order, record_property):
    count = 400
    path = converted(tmp_path, count, active=count)
    expected = material_world(count, active=count).materials
    with open_lazy_world_session(path, rules_id=RULES) as session:
        state = session.world.materials
        before = loads(session)
        for query in order:
            if query == 'selection':
                assert state.best_available(1).id == expected.best_available(1).id
                assert state.magical_available_count(1) == 57
            elif query == 'rank':
                assert state.best_at_rank(1, 2).id == expected.best_at_rank(1, 2).id
            else: assert state.crafting_capacity(1, 10) == 10
        actual = loads(session)-before
        record_property('cold_material_lot_loads', actual)
        assert actual <= count+2, actual


def test_selection_only_reads_once_and_mutations_rebuild_exactly(tmp_path):
    path = converted(tmp_path, 400, active=400)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        state = session.world.materials
        before = loads(session)
        selected = state.best_available(1)
        assert loads(session)-before <= 401
        state.consume(selected, selected.quantity)
        assert state.best_available(1).id != selected.id
        new = state.create_lot('ore', 100., 5., 1, 1, 0, 900, ('earth',), 2)
        assert state.best_available(1) is new and state.best_at_rank(1, 2) is new
        new.owner_kind, new.owner_id = 'household', 5
        assert state.best_available(1) is new
        new.quality, new.material_rank = .01, 0
        state.rebuild_active_index()  # Explicit data repair invalidates derived indexes.
        assert state.best_available(1).id != new.id
        assert state.best_at_rank(1, 2).id != new.id
        del state.lots[new.id]
        state.rebuild_active_index()
        assert new.id not in state.active_lot_index[1]
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        state = session.world.materials
        assert state.best_available(1) is not None
        assert state.crafting_capacity(1, 10) == 10
