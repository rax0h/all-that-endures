"""Exceptional IDs must not expand a large consecutive prefix."""
import pytest
import random

from ate_sim.core import World, Layer
from ate_sim.persistence_lazy import convert_cold_to_lazy, open_lazy_world_session
from ate_sim.persistence_session import write_cold_snapshot

RULES = 'final-event-id-exceptions'


def converted(tmp_path, size):
    world = World(843000)
    world.event_ids = set(range(1, size + 1))
    world.currency.wallets[1] = {'ids': world.event_ids}
    source, target = tmp_path / 'source.sqlite', tmp_path / 'target.sqlite'
    write_cold_snapshot(world, source, rules_id=RULES)
    convert_cold_to_lazy(source, target, rules_id=RULES, native_graph_buckets=True)
    return target


@pytest.mark.parametrize('size', [1000, 10000])
def test_middle_removal_outlier_and_native_representative_stay_paged(tmp_path, size):
    path = converted(tmp_path, size)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        ids = session.world.event_ids
        ids.remove(1)
        ids.add(True)
        ids.remove(size // 2)
        ids.add(size + 20)
        assert ids.diagnostics()['member_visits'] == 0
        assert len(ids) == size
        assert session.wallets[1]['ids'] is ids
        plan = session._prepare_hybrid_save()
        assert len(plan.nested_history_version_changes) <= 64
        session.save()
        assert ids.diagnostics()['member_visits'] == 0
    with open_lazy_world_session(path, rules_id=RULES) as session:
        ids = session.world.event_ids
        assert len(ids) == size
        assert size // 2 not in ids and size + 20 in ids
        assert type(next(value for value in ids if value == 1)) is bool
        assert session.wallets[1]['ids'] is ids
        session.world.year += 1
        session.save()
        world = session.detach(materialize_history=True)
    assert world.currency.wallets[1]['ids'] is world.event_ids


@pytest.mark.parametrize('phase', ['during_version_writes', 'during_ordinary_writes', 'before_commit', 'after_commit'])
def test_exception_descriptor_and_events_publish_atomically(tmp_path, phase):
    world = World(843000)
    for _ in range(4):
        world.emit('probe', Layer.REALITY)
    source, path = tmp_path / 'source.sqlite', tmp_path / 'target.sqlite'
    write_cold_snapshot(world, source, rules_id=RULES)
    convert_cold_to_lazy(source, path, rules_id=RULES, native_graph_buckets=True)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        ids = session.world.event_ids
        ids.remove(2)
        session.world.emit('probe', Layer.REALITY, causes=(1,))
        generation = session.pin.captured_head
        def fail(at):
            if at == phase:
                raise OSError(phase)
        session.store._phase_hook = fail
        with pytest.raises(OSError, match=phase):
            session.save()
        session.store._phase_hook = lambda _at: None
        assert session.resolve_save() == generation + (phase == 'after_commit')
        if phase != 'after_commit':
            session.save()
        assert ids is session.world.event_ids
        assert ids.diagnostics()['member_visits'] == 0
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert set(session.world.event_ids) == {1, 3, 4, 5}
        assert len(session.world.events) == 5


@pytest.mark.parametrize('size', [1000, 10000])
def test_explicit_conversion_of_nonconsecutive_source_is_paged(tmp_path, size):
    world = World(843000)
    values = {True, *range(3, size + 2)}
    world.event_ids = values
    world.currency.wallets[1] = {'ids': values}
    source, path = tmp_path / 'source.sqlite', tmp_path / 'target.sqlite'
    write_cold_snapshot(world, source, rules_id=RULES)
    original = source.read_bytes()
    convert_cold_to_lazy(source, path, rules_id=RULES, native_graph_buckets=True)
    assert source.read_bytes() == original
    with open_lazy_world_session(path, rules_id=RULES) as session:
        ids = session.world.event_ids
        assert ids.diagnostics()['resident_members'] == 0
        assert ids.diagnostics()['member_visits'] == 0
        ids.discard(size)
        ids.add(size + 20)
        assert ids.diagnostics()['member_visits'] == 0
        assert len(session._prepare_hybrid_save().nested_history_version_changes) <= 3
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert set(session.world.event_ids) == values - {size} | {size + 20}


def representatives(values):
    return {(type(value).__name__, repr(value)) for value in values}


def test_random_native_representatives_and_whole_operations_across_reopen(tmp_path):
    path = converted(tmp_path, 32)
    expected = set(range(1, 33))
    rng = random.Random(843000)
    values = (-1, 0, -0.0, 1, True, 1.0, 2, 2.0, 5, 9, 20, 34, 99, 'extra', frozenset({1}))
    operations = ('add', 'discard', 'update', 'difference_update', 'intersection_update', 'symmetric_difference_update')
    for _ in range(4):
        with open_lazy_world_session(path, rules_id=RULES) as session:
            ids = session.world.event_ids
            for _ in range(40):
                name = rng.choice(operations)
                operand = rng.choice(values) if name in ('add', 'discard') else [rng.choice(values) for _ in range(rng.randrange(5))]
                getattr(expected, name)(operand)
                getattr(ids, name)(operand)
                assert representatives(ids) == representatives(expected)
            session.save()
        with open_lazy_world_session(path, rules_id=RULES) as session:
            assert representatives(session.world.event_ids) == representatives(expected)


def test_pop_skips_large_removed_suffix_and_clear_replaces_authority(tmp_path):
    path = converted(tmp_path, 1000)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        ids = session.world.event_ids
        ids.remove(10)  # Enter the exceptional form without visiting the prefix.
        for value in range(11, 1001):
            ids.remove(value)
        session.save()
        before = session.store.diagnostics().payload_reads
        assert ids.pop() == 9
        assert session.store.diagnostics().payload_reads - before < 100
        assert ids.diagnostics()['member_visits'] == 0
        ids.clear()
        ids.add(-0.0)
        ids.add(0)
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert representatives(session.world.event_ids) == {('float', '-0.0')}


def test_root_replacement_guard_and_wallet_retirement_keep_current_authority(tmp_path):
    from ate_sim.incremental_store import StoreError
    path = converted(tmp_path, 32)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        old = session.world.event_ids
        old.remove(2)
        session.save()
        with pytest.raises(StoreError, match='root collection replacement'):
            session.world.event_ids = {101, 102}
        assert session.world.event_ids is old
        del session.wallets[1]
        session.save()
        old.add(200)
        session.world.year += 1
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert set(session.world.event_ids) == set(range(1, 33)) - {2} | {200}
        assert 1 not in session.wallets


def test_exotic_probes_and_nonreflexive_compatibility_preserve_native_behavior(tmp_path):
    path = converted(tmp_path, 32)
    class Probe:
        def __init__(self, hashed, equal):
            self.hashed, self.equal = hashed, equal
        def __hash__(self):
            return self.hashed
        def __eq__(self, other):
            return other == self.equal
    with open_lazy_world_session(path, rules_id=RULES) as session:
        ids = session.world.event_ids
        ids.remove(2)
        ids.add(99)
        expected = set(range(1, 33)) - {2} | {99}
        for probe in (Probe(2, 2), Probe(99, 99), Probe(1, 2), set(), []):
            try:
                result = probe in expected
            except TypeError:
                with pytest.raises(TypeError):
                    probe in ids
            else:
                assert (probe in ids) == result
        ids.discard(Probe(99, 99))
        assert 99 not in ids
        first, second = float('nan'), float('nan')
        ids.add(first)
        ids.add(second)
        assert first in ids and second in ids
        assert float('nan') not in ids
        assert sum(type(value) is float and value != value for value in ids) == 2
        session.save()
        assert first in ids and second in ids
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert sum(type(value) is float and value != value for value in session.world.event_ids) == 2


@pytest.mark.parametrize('damage', ['missing_child', 'contradictory_counts'])
def test_exception_open_checks_internal_authorities_and_counts(tmp_path, damage):
    from ate_sim.incremental_store import StoreIntegrityError, _framed_sha
    from ate_sim.persistence_lazy_nested_history import DESCRIPTOR_NAMESPACE
    path = converted(tmp_path, 32)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        session.world.event_ids.remove(2)
        session.world.event_ids.add(99)
        session.save()
        descriptor = session.world.event_ids.descriptor()
        store = session.store
        if damage == 'missing_child':
            store.db.execute('DELETE FROM lazy_record_versions WHERE namespace=? AND typed_key=?',
                (DESCRIPTOR_NAMESPACE, store.codec.encode(descriptor[3].incarnation)))
        else:
            value = ('set', 2, 2)  # A checked row contradicting the parent count.
            key = store.codec.encode(descriptor[3].incarnation)
            row = store.db.execute('SELECT valid_from,memberships FROM lazy_record_versions WHERE namespace=? AND typed_key=? AND valid_to IS NULL',
                (DESCRIPTOR_NAMESPACE, key)).fetchone()
            from ate_sim.persistence_lazy_store import _version_checksum
            payload = store.codec.encode(value)
            checksum = _version_checksum(DESCRIPTOR_NAMESPACE, key, 1, store.codec.version, row[0], None, row[1], payload)
            store.db.execute('UPDATE lazy_record_versions SET payload=?,payload_checksum=?,row_checksum=? WHERE namespace=? AND typed_key=? AND valid_to IS NULL',
                (payload, _framed_sha(b'lazy-payload-v1', payload), checksum, DESCRIPTOR_NAMESPACE, key))
        store.db.commit()
    with pytest.raises(StoreIntegrityError):
        open_lazy_world_session(path, rules_id=RULES)
