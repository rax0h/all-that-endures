"""Native child writes require physical owner headers in the same frozen plan."""
import pytest

from ate_sim.core import World
from ate_sim.skills import SkillHistory
from ate_sim.persistence_session import write_cold_snapshot
from ate_sim.persistence_lazy import convert_cold_to_lazy, open_lazy_world_session

RULES = 'final-owner-header-witnesses'


@pytest.mark.parametrize('size', [1000, 10000])
def test_actual_family_forces_compact_unchanged_header_without_history_reads(tmp_path, size):
    world = World(843000)
    world.skills.skills[1, 'craft'] = SkillHistory(1, 'craft', provenance=list(range(size)))
    source, target = tmp_path / 'source.sqlite', tmp_path / 'target.sqlite'
    write_cold_snapshot(world, source, rules_id=RULES)
    convert_cold_to_lazy(source, target, rules_id=RULES)
    with open_lazy_world_session(target, rules_id=RULES) as session:
        record = session.skills[1, 'craft']
        child = record.provenance
        child.append(size)
        assert session.skills.prepare_save_changes()[0] == ()
        child._read_page = lambda *_args: pytest.fail('header witness read member history')
        session.store.reset_diagnostics()
        change = session._family_bindings.unchanged_owner_header(('world.skills.skills', (1, 'craft')))
        assert change.namespace == 'world.skills.skills' and change.key == (1, 'craft')
        assert change.value.provenance == child.storage_reference()
        assert change.record_schema == 1
        assert session.store.diagnostics().payload_reads == 1
        assert session.store.diagnostics().payload_read_bytes < 4096


def test_changed_header_cannot_be_replaced_by_a_baseline_witness(tmp_path):
    world = World(843000)
    world.skills.skills[1, 'craft'] = SkillHistory(1, 'craft', level=.25)
    source, target = tmp_path / 'source.sqlite', tmp_path / 'target.sqlite'
    write_cold_snapshot(world, source, rules_id=RULES)
    convert_cold_to_lazy(source, target, rules_id=RULES)
    from ate_sim.incremental_store import StoreIntegrityError
    with open_lazy_world_session(target, rules_id=RULES) as session:
        session.skills[1, 'craft'].level = .75
        with pytest.raises(StoreIntegrityError, match='changed owner header'):
            session._family_bindings.unchanged_owner_header(('world.skills.skills', (1, 'craft')))


def test_header_witness_checks_and_preserves_scalar_query_memberships(tmp_path):
    from ate_sim.core import Household
    from ate_sim.incremental_store import StoreIntegrityError
    world = World(843000)
    world.households[1] = Household(1, 2, members=[1, 2, 3])
    source, target = tmp_path / 'source.sqlite', tmp_path / 'target.sqlite'
    write_cold_snapshot(world, source, rules_id=RULES)
    convert_cold_to_lazy(source, target, rules_id=RULES, counted_households=True)
    with open_lazy_world_session(target, rules_id=RULES) as session:
        record = session.world.households[1]
        record.members.append(4)
        owner = ('world.households', 1)
        change = session._family_bindings.unchanged_owner_header(owner)
        assert change.memberships and change.value.members == record.members.storage_reference()
        key = session.store.codec.encode(1)
        session.store.db.execute('DELETE FROM lazy_query_versions WHERE namespace=? AND record_key=?', (owner[0], key))
        session.store.db.commit()
        with pytest.raises(StoreIntegrityError, match='query membership'):
            session._family_bindings.unchanged_owner_header(owner)
