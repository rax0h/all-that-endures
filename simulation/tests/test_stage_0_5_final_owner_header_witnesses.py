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


@pytest.mark.parametrize('size', [1000, 10000])
def test_actual_eager_header_capture_does_not_materialize_counted_history(tmp_path, size, monkeypatch):
    from ate_sim.core import Settlement
    from ate_sim.incremental_store import RecordChange
    world = World(843000)
    world.settlements[1] = Settlement(1, 0, 0, households=[1] * size)
    source, target = tmp_path / 'source.sqlite', tmp_path / 'target.sqlite'
    write_cold_snapshot(world, source, rules_id=RULES)
    convert_cold_to_lazy(source, target, rules_id=RULES, counted_households=True)
    with open_lazy_world_session(target, rules_id=RULES) as session:
        record = session.world.settlements[1]
        record.households.append(2)
        record.households._clear_cache()
        monkeypatch.setattr(type(record.households), '__iter__', lambda *_args: pytest.fail('eager header read member history'))
        session.store.reset_diagnostics()
        change = session._family_bindings.unchanged_owner_header(('world.settlements', 1))
        assert type(change) is RecordChange
        assert change.value[1].households == record.households.storage_reference()
        assert change.memberships == ()
        assert session.store.diagnostics().payload_reads == 1
        assert session.store.diagnostics().payload_read_bytes < 4096
        assert not record.households._cache


def test_changed_eager_header_cannot_be_substituted_from_old_ordinary_body(tmp_path):
    from ate_sim.core import Settlement
    from ate_sim.incremental_store import StoreIntegrityError
    world = World(843000)
    world.settlements[1] = Settlement(1, 0, 0)
    source, target = tmp_path / 'source.sqlite', tmp_path / 'target.sqlite'
    write_cold_snapshot(world, source, rules_id=RULES)
    convert_cold_to_lazy(source, target, rules_id=RULES, counted_households=True)
    with open_lazy_world_session(target, rules_id=RULES) as session:
        session.world.settlements[1].food_stock = 12.
        with pytest.raises(StoreIntegrityError, match='changed owner header'):
            session._family_bindings.unchanged_owner_header(('world.settlements', 1))


@pytest.mark.parametrize('fault', ['extra_query', 'missing_index', 'missing_body'])
def test_eager_header_capture_checks_required_source_and_empty_query_projection(tmp_path, fault):
    from ate_sim.core import Settlement
    from ate_sim.incremental_store import StoreIntegrityError, StoreFormatError
    world = World(843000)
    world.settlements[1] = Settlement(1, 0, 0)
    source, target = tmp_path / 'source.sqlite', tmp_path / 'target.sqlite'
    write_cold_snapshot(world, source, rules_id=RULES)
    convert_cold_to_lazy(source, target, rules_id=RULES, counted_households=True)
    with open_lazy_world_session(target, rules_id=RULES) as session:
        if fault == 'extra_query':
            session.store.db.execute('INSERT INTO query_membership VALUES (?,?,?,?,?,?)',
                ('world.settlements', 'extra', session.store.codec.encode(1), session.store.codec.encode(1), 0, session.pin.captured_head))
        elif fault == 'missing_index':
            session.store.db.execute('DROP INDEX ordinary_query_owner')
        else:
            session.store.db.execute('DELETE FROM records WHERE namespace=? AND typed_key=?',
                ('world.settlements', session.store.codec.encode(1)))
        session.store.db.commit()
        error = StoreFormatError if fault == 'missing_index' else StoreIntegrityError
        with pytest.raises(error):
            session._family_bindings.unchanged_owner_header(('world.settlements', 1))


@pytest.mark.parametrize('kind', ['dict', 'list', 'set'])
def test_compact_eager_wrapper_requires_its_current_live_tracker_lease(tmp_path, kind):
    from ate_sim.core import Settlement
    from ate_sim.incremental_store import StoreConflictError
    from ate_sim.persistence_lazy_families import FAMILIES
    world = World(843000)
    value = {'seen': 1.} if kind == 'dict' else [True, 1., 2] if kind == 'list' else {True, 2.}
    world.settlements[1] = Settlement(1, 0, 0, memory={'nested': value})
    source, target = tmp_path / 'source.sqlite', tmp_path / 'target.sqlite'
    write_cold_snapshot(world, source, rules_id=RULES)
    convert_cold_to_lazy(source, target, rules_id=RULES, counted_households=True)
    first = open_lazy_world_session(target, rules_id=RULES)
    second = open_lazy_world_session(target, rules_id=RULES)
    wrapper = first.world.settlements[1].memory['nested']
    try:
        assert FAMILIES['world.settlements'].identity_payload_bytes(first.store, first.pin, wrapper) == first.store.codec.encode(value)
        with pytest.raises(StoreConflictError, match='tracked.*lease'):
            FAMILIES['world.settlements'].identity_payload_bytes(second.store, second.pin, wrapper)
        first.close()
        with pytest.raises(StoreConflictError, match='tracked.*lease'):
            FAMILIES['world.settlements'].identity_payload_bytes(second.store, second.pin, wrapper)
    finally:
        first.close()
        second.close()


def test_eager_header_capture_rejects_old_pin_before_reading_current_ordinary_body(tmp_path):
    from ate_sim.core import Settlement
    from ate_sim.incremental_store import StoreConflictError
    world = World(843000)
    world.settlements[1] = Settlement(1, 0, 0)
    source, target = tmp_path / 'source.sqlite', tmp_path / 'target.sqlite'
    write_cold_snapshot(world, source, rules_id=RULES)
    convert_cold_to_lazy(source, target, rules_id=RULES, counted_households=True)
    with open_lazy_world_session(target, rules_id=RULES) as older, open_lazy_world_session(target, rules_id=RULES) as writer:
        writer.world.settlements[1].defense = .7
        writer.save()
        older.store.reset_diagnostics()
        with pytest.raises(StoreConflictError, match='current head'):
            older._family_bindings.unchanged_owner_header(('world.settlements', 1))
        assert older.store.diagnostics().payload_reads == 0
