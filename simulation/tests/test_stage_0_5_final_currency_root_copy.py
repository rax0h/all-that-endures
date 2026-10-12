"""Currency root maps may share the existing backing with copied Event data."""
import pytest
from ate_sim.core import Event, Layer
from ate_sim.persistence_lazy_nested_history import LazyHistoryMap
from simulation.tests.test_stage_0_5_final_catalog_copy import legacy_lazy, sha, module, RULES
from simulation.tests.test_stage_0_5_final_world_catalog_bridge import open_bridge, activate


def source_with_currency(tmp_path, name):
    def configure(world):
        bucket = {'copper': 1, 'detail': [7]}
        getattr(world.currency, name)[1] = bucket
        world.events.append(Event(1, 0, 'legacy', Layer.SOCIETY, data={'bucket': bucket}))
        world.event_ids.add(1); world.next_event = 2
    return legacy_lazy(tmp_path, configure=configure)


@pytest.mark.parametrize('name', ['wallets', 'treasuries'])
@pytest.mark.parametrize('first', ['root', 'event'])
def test_currency_root_copy_preserves_shared_map_and_descendants(tmp_path, name, first):
    source = source_with_currency(tmp_path, name)
    before = sha(source)
    target = tmp_path / 'normalized.sqlite'
    module()._copy_with_checked_catalog(source, target, rules_id=RULES, normalize_events=True)
    assert sha(source) == before
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        table = getattr(session.world.currency, name)
        bucket = table[1] if first == 'root' else session.world.events[0].data['bucket']
        assert type(bucket) is LazyHistoryMap
        assert bucket is table[1] is session.world.events[0].data['bucket']
        bucket['copper'] = 2
        bucket['detail'].append(8)
        session.save()
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        bucket = getattr(session.world.currency, name)[1]
        assert bucket is session.world.events[0].data['bucket']
        assert bucket['copper'] == 2 and list(bucket['detail']) == [7, 8]


@pytest.mark.parametrize('operation', ['replace', 'delete'])
def test_currency_root_removal_keeps_shared_alias_without_resurrecting_root(tmp_path, operation):
    source = source_with_currency(tmp_path, 'wallets')
    target = tmp_path / 'normalized.sqlite'
    module()._copy_with_checked_catalog(source, target, rules_id=RULES, normalize_events=True)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        old = session.world.currency.wallets[1]
        if operation == 'replace': session.world.currency.wallets[1] = {'copper': 99}
        else: del session.world.currency.wallets[1]
        old['copper'] = 2
        session.save()
        assert session.world.events[0].data['bucket'] is old
        if operation == 'replace': assert session.world.currency.wallets[1]['copper'] == 99
        else: assert 1 not in session.world.currency.wallets
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        assert session.world.events[0].data['bucket']['copper'] == 2
        if operation == 'replace': assert session.world.currency.wallets[1]['copper'] == 99
        else: assert 1 not in session.world.currency.wallets


def test_currency_backed_root_assigns_to_second_family_and_detaches_portably(tmp_path):
    source = source_with_currency(tmp_path, 'wallets')
    target = tmp_path / 'normalized.sqlite'
    module()._copy_with_checked_catalog(source, target, rules_id=RULES, normalize_events=True)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        bucket = session.world.currency.wallets[1]
        session.world.currency.treasuries[2] = bucket
        bucket['copper'] = 3
        session.save()
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        assert session.world.currency.wallets[1] is session.world.currency.treasuries[2]
        plain = session.detach(materialize_history=True)
    assert type(plain.currency.wallets[1]) is dict
    assert plain.currency.wallets[1] is plain.currency.treasuries[2] is plain.events[0].data['bucket']
    assert plain.currency.wallets[1]['copper'] == 3


@pytest.mark.parametrize('phase', ['before_commit', 'after_commit'])
def test_currency_root_backing_and_event_alias_resolve_one_save(tmp_path, phase):
    source = source_with_currency(tmp_path, 'wallets')
    target = tmp_path / 'normalized.sqlite'
    module()._copy_with_checked_catalog(source, target, rules_id=RULES, normalize_events=True)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        bucket = session.world.currency.wallets[1]
        bucket['copper'] = 4
        def fail(at):
            if at == phase: raise OSError('currency root save fault')
        session.store._phase_hook = fail
        with pytest.raises(OSError, match='currency root save fault'): session.save()
        session.store._phase_hook = lambda _: None
        session.resolve_save(); session.save()
        assert session.world.currency.wallets[1] is bucket is session.world.events[0].data['bucket']
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        assert session.world.currency.wallets[1]['copper'] == 4
        assert session.world.currency.wallets[1] is session.world.events[0].data['bucket']


def test_currency_root_point_save_does_not_walk_map_history(tmp_path, record_property):
    metrics = []
    for size in (1000, 10000):
        directory = tmp_path / str(size); directory.mkdir()
        def configure(world):
            bucket = {f'mark-{n}': n for n in range(size)}
            world.currency.wallets[1] = bucket
            world.events.append(Event(1, 0, 'legacy', Layer.SOCIETY, data={'bucket': bucket}))
            world.event_ids.add(1); world.next_event = 2
        source = legacy_lazy(directory, configure=configure)
        target = directory / 'normalized.sqlite'
        module()._copy_with_checked_catalog(source, target, rules_id=RULES, normalize_events=True)
        with open_bridge(target, rules_id=RULES) as session:
            activate(session)
            bucket = session.world.currency.wallets[1]
            bucket.items = lambda: pytest.fail('currency save walked map archive')
            session._registry.live_bindings = lambda: pytest.fail('currency save inventoried registry')
            session.store.reset_diagnostics()
            bucket['mark-0'] = -1
            session.save()
            now = session.store.diagnostics()
            metric = now.payload_reads, now.payload_writes, now.metadata_rows
            metrics.append(metric)
            for label, count in zip(('payload_reads', 'payload_writes', 'metadata_rows'), metric):
                record_property(f'H{size}_{label}', count)
            session.store.reset_diagnostics()
            generation = session.pin.captured_head
            reads = []
            original_read = session.store.read_version
            def trace(pin, namespace, key, **kwargs):
                reads.append((namespace, key))
                return original_read(pin, namespace, key, **kwargs)
            session.store.read_version = trace
            original_record, original_records = session.store.read_record, session.store.read_records
            def trace_record(namespace, key, **kwargs):
                reads.append((namespace, key))
                return original_record(namespace, key, **kwargs)
            def trace_records(namespace, **kwargs):
                reads.append((namespace, 'ALL'))
                return original_records(namespace, **kwargs)
            session.store.read_record, session.store.read_records = trace_record, trace_records
            assert session.save() == generation
            idle = session.store.diagnostics()
            # Existing no-op publication checks three fixed Event-storage rows;
            # they are descriptor authority, not map/event archive payloads.
            assert reads == [('world_event_storage', 'ALL')]
            assert idle.payload_reads == 3 and idle.payload_writes == 0
            record_property(f'H{size}_noop_descriptor_reads', idle.payload_reads)
            record_property(f'H{size}_noop_metadata_rows', idle.metadata_rows)
    assert metrics[0] == metrics[1]


@pytest.mark.parametrize('bad', ['foreign', 'undeclared'])
def test_rejected_currency_root_assignment_preserves_old_occurrence(tmp_path, bad):
    from ate_sim.incremental_store import StoreError
    from ate_sim.persistence_lazy_identity import Occurrence
    paths = []
    for name in ('left', 'right'):
        directory = tmp_path / name; directory.mkdir()
        source = source_with_currency(directory, 'wallets')
        target = directory / 'normalized.sqlite'
        module()._copy_with_checked_catalog(source, target, rules_id=RULES, normalize_events=True)
        paths.append(target)
    with open_bridge(paths[0], rules_id=RULES) as left, open_bridge(paths[1], rules_id=RULES) as right:
        activate(left); activate(right)
        table = left.world.currency.wallets
        original = table[1]
        occurrence = Occurrence('world.currency.wallets', 1, ())
        before = left._registry.incarnation_for_occurrence(occurrence)
        dirty = set(table._dirty)
        replacement = right.world.currency.wallets[1] if bad == 'foreign' else {'bad': object()}
        with pytest.raises(StoreError if bad == 'foreign' else TypeError): table[1] = replacement
        assert table[1] is original and table._dirty == dirty
        assert left._registry.incarnation_for_occurrence(occurrence) == before
        original['copper'] = 5
        left.save()
        assert left.world.events[0].data['bucket'] is original


def test_explicit_graph_copy_normalizes_currency_roots_without_event_aliases(tmp_path):
    def configure(world):
        shared = {'copper': 1, 'detail': [7]}
        world.currency.wallets[1] = shared
        world.currency.treasuries[2] = shared
    source = legacy_lazy(tmp_path, configure=configure)
    target = tmp_path / 'normalized.sqlite'
    module()._copy_with_checked_catalog(source, target, rules_id=RULES, normalize_events=True)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        bucket = session.world.currency.wallets[1]
        assert type(bucket) is LazyHistoryMap
        assert bucket is session.world.currency.treasuries[2]
        bucket['copper'] = 2
        session.save()
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        assert session.world.currency.wallets[1] is session.world.currency.treasuries[2]
        assert session.world.currency.wallets[1]['copper'] == 2


def test_checked_current_copy_preserves_currency_root_id_and_source_overlay(tmp_path):
    source = source_with_currency(tmp_path, 'wallets')
    normalized = tmp_path / 'normalized.sqlite'
    module()._copy_with_checked_catalog(source, normalized, rules_id=RULES, normalize_events=True)
    copied = tmp_path / 'copied.sqlite'
    with open_bridge(normalized, rules_id=RULES) as original:
        activate(original)
        bucket, pin = original.world.currency.wallets[1], original.pin
        inc = bucket._incarnation
        bucket['copper'] = 99
        before = sha(normalized)
        module()._copy_current_checked_catalog(normalized, copied, rules_id=RULES)
        assert sha(normalized) == before and original.pin == pin
        assert original.world.currency.wallets[1] is bucket and bucket['copper'] == 99
        with open_bridge(copied, rules_id=RULES) as destination:
            activate(destination)
            replica = destination.world.currency.wallets[1]
            assert replica._incarnation == inc and replica['copper'] == 1
            assert replica is destination.world.events[0].data['bucket']
            replica['copper'] = 2
            destination.save()
        original.save()
    with open_bridge(copied, rules_id=RULES) as destination:
        activate(destination)
        assert destination.world.currency.wallets[1]['copper'] == 2
