"""Checked touched-owner placement journals include concrete eager dictionaries."""
import pytest

from ate_sim.core import Settlement
from simulation.tests.test_stage_0_5_final_world_catalog_bridge import converted_catalog, open_bridge, activate, RULES


def catalog_with_settlement(tmp_path):
    def configure(world, history):
        world.settlements[1] = Settlement(1, 0, 0, households=history)
    return converted_catalog(tmp_path, owners=1, configure_world=configure, counted_households=True)


def test_deleted_eager_owner_cannot_be_resurrected_by_shared_lazy_child(tmp_path):
    target = catalog_with_settlement(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        coord = activate(session)
        child = session.world.settlements[1].households
        del session.world.settlements[1]
        child.append(99)
        assert session.skills[1, 'craft'].provenance is child
        assert coord.dirty_owners == {('world.settlements', 1), ('world.skills.skills', (1, 'craft'))}
        assert ('world.settlements', 1) in session._eager_tracker._deleted
        session.save()
        assert 1 not in session.world.settlements
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        assert 1 not in session.world.settlements
        assert session.skills[1, 'craft'].provenance[-1] == 99


def test_replaced_eager_child_routes_old_alias_only_to_its_remaining_owner(tmp_path):
    target = catalog_with_settlement(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        coord = activate(session)
        child = session.world.settlements[1].households
        session.world.settlements[1].households = [777]
        child.append(99)
        assert session.skills[1, 'craft'].provenance is child
        assert list(session.world.settlements[1].households) == [777]
        assert ('world.settlements', 1) in coord.dirty_owners
        session.save()
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        assert list(session.world.settlements[1].households) == [777]
        assert session.skills[1, 'craft'].provenance[-1] == 99


def test_eager_scalar_save_keeps_complete_catalog_owner_projection(tmp_path):
    target = catalog_with_settlement(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        coord = activate(session)
        record = session.world.settlements[1]
        child = record.households
        before = dict(coord.catalog.read_owner_identity(session.pin, ('world.settlements', 1)).occurrences)
        record.food_stock = 12.5
        session._registry.live_bindings = lambda: pytest.fail('eager save inventoried all live bindings')
        session._eager_tracker._contains_identity = lambda *_: pytest.fail('eager save scanned an owner graph')
        session.save()
        assert session.world.settlements[1].food_stock == 12.5
        assert session.world.settlements[1].households is child
        assert dict(coord.catalog.read_owner_identity(session.pin, ('world.settlements', 1)).occurrences) == before
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        assert session.world.settlements[1].food_stock == 12.5


def test_new_eager_owner_attaches_existing_canonical_history(tmp_path):
    target = catalog_with_settlement(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        coord = activate(session)
        child = session.world.settlements[1].households
        session.world.settlements[2] = Settlement(2, 0, 0, households=child)
        child.append(99)
        assert ('world.settlements', 2) in coord.dirty_owners
        session.save()
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        assert session.world.settlements[1].households is session.world.settlements[2].households
        assert session.skills[1, 'craft'].provenance is session.world.settlements[2].households
        assert session.world.settlements[2].households[-1] == 99
