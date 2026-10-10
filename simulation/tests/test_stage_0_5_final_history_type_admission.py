"""Checked type witnesses close admission of previously paged shared aliases."""
import json
import pytest

from ate_sim.core import World, Household
from ate_sim.metaphysics import SoulState
from ate_sim.skills import SkillHistory
from ate_sim.incremental_store import StoreIntegrityError
from ate_sim.persistence_lazy import convert_cold_to_lazy, open_lazy_world_session
from ate_sim.persistence_session import write_cold_snapshot

RULES = 'final-history-type-admission'


def converted(tmp_path, kind, values):
    world = World(843000)
    if kind == 'set':
        world.metaphysics.souls[1] = SoulState(1, authorities=values)
        world.magic_resources.owner_index['person', 1] = {7}
    elif kind == 'list':
        world.skills.skills[1, 'craft'] = SkillHistory(1, 'craft', provenance=values)
        world.genealogy.children[1] = [7]
    else:
        world.households[1] = Household(1, 1, members=values)
        world.genealogy.children[1] = [7]
    source, target = tmp_path / 'source.sqlite', tmp_path / 'target.sqlite'
    write_cold_snapshot(world, source, rules_id=RULES)
    convert_cold_to_lazy(source, target, rules_id=RULES, native_graph_buckets=True)
    return target


def donor(session, kind):
    if kind == 'set':
        return session.souls[1].authorities
    if kind == 'list':
        return session.skills[1, 'craft'].provenance
    return session.world.households[1].members


@pytest.mark.parametrize('kind', ['list', 'set', 'sequence'])
def test_invalid_paged_alias_rejected_before_replacing_current_owner(tmp_path, kind):
    path = converted(tmp_path, kind, {'bad'} if kind == 'set' else ['bad'])
    with open_lazy_world_session(path, rules_id=RULES) as session:
        incoming = donor(session, kind)
        table, key = (session.owner_index, ('person', 1)) if kind == 'set' else (session.genealogy_children, 1)
        old = table[key]
        registry = session._registry
        inc = registry.incarnation_for_object(old)
        routes = registry.occurrences_for_incarnation(inc)
        with pytest.raises(TypeError, match='member'):
            table[key] = incoming
        assert table[key] is old
        assert registry.occurrences_for_incarnation(inc) == routes
        old.add(8) if kind == 'set' else old.append(8)
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        table = session.owner_index if kind == 'set' else session.genealogy_children
        assert 8 in table[key] and 'bad' not in table[key]


@pytest.mark.parametrize('kind', ['list', 'set', 'sequence'])
@pytest.mark.parametrize('size', [1000, 10000])
def test_valid_paged_admission_reads_no_member_payload(tmp_path, kind, size, record_property):
    path = converted(tmp_path, kind, set(range(size)) if kind == 'set' else list(range(size)))
    with open_lazy_world_session(path, rules_id=RULES) as session:
        incoming = donor(session, kind)
        table, key = (session.owner_index, ('person', 2)) if kind == 'set' else (session.genealogy_children, 2)
        before = incoming.diagnostics().copy()
        session.store.reset_diagnostics()
        table[key] = incoming
        after = incoming.diagnostics()
        assert table[key] is incoming
        for metric in ('entry_loads', 'page_loads', 'node_reads'):
            if metric in before:
                assert after[metric] == before[metric]
        assert session.store.diagnostics().payload_reads < 12
        assert session.store.diagnostics().payload_read_bytes < 8192
        metrics = session.store.diagnostics()
        record_property('admission_metrics', json.dumps({'kind': kind, 'H': size,
            'payload_reads': metrics.payload_reads, 'payload_bytes': metrics.payload_read_bytes,
            'metadata_rows': metrics.metadata_rows}))
        with pytest.raises(TypeError):
            (incoming.add if kind == 'set' else incoming.append)('bad')
        session.save()


def test_cached_scalar_entry_obeys_new_owner_validator(tmp_path):
    path = converted(tmp_path, 'set', {'bad'})
    with open_lazy_world_session(path, rules_id=RULES) as session:
        values = donor(session, 'set')
        assert 'bad' in values  # Populate the ordinary clean entry cache.
        def integers(value):
            if type(value) is not int:
                raise TypeError('member must be int')
        values._key_validator = integers
        with pytest.raises(StoreIntegrityError, match='owner type'):
            assert 'bad' in values


@pytest.mark.parametrize('kind', ['list', 'sequence'])
def test_cached_list_entry_obeys_new_owner_validator(tmp_path, kind):
    path = converted(tmp_path, kind, ['bad'])
    with open_lazy_world_session(path, rules_id=RULES) as session:
        values = donor(session, kind)
        assert values[0] == 'bad'
        def integers(value):
            if type(value) is not int:
                raise TypeError('member must be int')
        values._value_validator = integers
        with pytest.raises(StoreIntegrityError, match='owner type'):
            values[0]
        with pytest.raises(StoreIntegrityError, match='owner type'):
            list(values)


def test_record_field_assignment_rejects_bad_alias_before_attribute_changes(tmp_path):
    from ate_sim.magic_resources import MagicResource
    path = converted(tmp_path, 'list', ['bad'])
    with open_lazy_world_session(path, rules_id=RULES) as session:
        session.resources[1] = MagicResource(1, 'essence', 'fire', 'common', 1, transfers=[7])
        record, incoming = session.resources[1], donor(session, 'list')
        old = record.transfers
        inc = session._registry.incarnation_for_object(old)
        routes = session._registry.occurrences_for_incarnation(inc)
        with pytest.raises(TypeError, match='member'):
            record.transfers = incoming
        assert record.transfers is old
        assert session._registry.occurrences_for_incarnation(inc) == routes


@pytest.mark.parametrize('kind', ['list', 'set', 'sequence'])
def test_private_overlay_type_changes_are_used_for_admission(tmp_path, kind):
    path = converted(tmp_path, kind, {'bad'} if kind == 'set' else ['bad'])
    with open_lazy_world_session(path, rules_id=RULES) as session:
        values = donor(session, kind)
        if kind == 'set':
            values.remove('bad')
            values.add(8)
        else:
            values[0] = 8
        table, key = (session.owner_index, ('person', 2)) if kind == 'set' else (session.genealogy_children, 2)
        table[key] = values
        assert table[key] is values
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        values = donor(session, kind)
        table = session.owner_index if kind == 'set' else session.genealogy_children
        assert table[key] is values and 8 in values
        assert values._member_types.counts == (1, 0, 0)


@pytest.mark.parametrize('phase', ['before_commit', 'after_commit'])
def test_type_witness_and_history_share_exact_failed_save_recovery(tmp_path, phase):
    path = converted(tmp_path, 'list', ['bad'])
    with open_lazy_world_session(path, rules_id=RULES) as session:
        values = donor(session, 'list')
        values[0] = 8
        session.genealogy_children[2] = values
        parent = session.pin.captured_head
        def fail(at):
            if at == phase:
                raise OSError('type witness publication failed')
        session.store._phase_hook = fail
        with pytest.raises(OSError, match='publication failed'):
            session.save()
        session.store._phase_hook = lambda _at: None
        assert session.resolve_save() == parent + (phase == 'after_commit')
        assert session.genealogy_children[2] is values
        assert values._member_types.counts == (1, 0, 0)
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        values = donor(session, 'list')
        assert session.genealogy_children[2] is values and list(values) == [8]
        assert values._member_types.counts == values._member_types._base == (1, 0, 0)
