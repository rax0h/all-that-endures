"""Shared catalog scrub must visit a physical namespace only once."""
import pytest

from ate_sim import persistence_catalog_copy as copy
from ate_sim import persistence_lazy_sequence as sequence
from ate_sim.persistence_conversion_workspace import ConversionWorkspace
from ate_sim.incremental_store import StoreIntegrityError, StoreConflictError
from ate_sim.persistence_lazy_store import LazyRecordStore, VersionChange
from ate_sim.incremental_store import TypedCodec
from simulation.tests.catalog_sequence_scrub_probe import InventoryConnection, populate_sequences
from simulation.tests.test_stage_0_5_final_catalog_copy import legacy_lazy, RULES, sha


def verify_sequences(store, pin, workspace):
    assert hasattr(copy, '_verify_sequences'), 'shared sequence catalog verifier is missing'
    return copy._verify_sequences(store, pin, workspace)


def make_store(path):
    return LazyRecordStore.create(path, codec=TypedCodec(), simulation_schema='8', rules_id='scrub-probe')


def test_catalog_scans_each_sequence_namespace_at_most_once(tmp_path, monkeypatch):
    from ate_sim.core import Household
    def configure(world):
        for ident in range(1, 9):
            world.households[ident] = Household(ident, 1, members=[1, 2, 1, 3])
    source = legacy_lazy(tmp_path, configure=configure)
    before = sha(source)
    counters = []
    original = copy._verify_catalog
    def measured(store, pin, *args, **kwargs):
        connection = store.db
        counter = InventoryConnection(connection, sequence.NAMESPACES)
        counters.append(counter)
        store.db = counter
        try:
            return original(store, pin, *args, **kwargs)
        finally:
            store.db = connection
    monkeypatch.setattr(copy, '_verify_catalog', measured)
    copy._copy_with_checked_catalog(source, tmp_path / 'copy.sqlite', rules_id=RULES)
    assert sha(source) == before
    assert counters
    for counter in counters:
        assert max(counter.calls.values()) <= 1, dict(counter.calls)
        assert counter.largest_fetchall == 0, 'shared inventories must stream rather than fetchall'


def test_shared_inventory_respects_old_generation_after_another_commit(tmp_path):
    with make_store(tmp_path / 'pins.sqlite') as store:
        old = populate_sequences(store, 4)
        writer = store.capture_pin()
        changed = sequence.LazyOrderedSequence(store, writer, 1)
        changed.append(2)
        delta = changed.prepare_delta()
        current = store.commit(writer, commit_token='later', changes=(), new_segments=(),
            version_changes=delta.decode(store.codec)[0], metadata=store.head_metadata()).pin
        for pin in (old, current):
            with ConversionWorkspace(store.codec, directory=tmp_path) as workspace:
                verify_sequences(store, pin, workspace)
            for incarnation in range(1, 5):
                sequence.LazyOrderedSequence(store, pin, incarnation).scrub()


@pytest.mark.parametrize('namespace', sequence.NAMESPACES[1:])
def test_shared_inventory_rejects_extra_physical_projection(tmp_path, namespace):
    with make_store(tmp_path / 'extra.sqlite') as store:
        pin = populate_sequences(store, 3)
        key = (1, b'extra') if namespace == sequence.DIRECTORY_NAMESPACE else (1, 999999)
        pin = store.commit(pin, commit_token='extra', changes=(), new_segments=(),
            version_changes=(VersionChange(namespace, key, ('extra',)),), metadata=store.head_metadata()).pin
        with ConversionWorkspace(store.codec, directory=tmp_path) as workspace:
            with pytest.raises(StoreIntegrityError, match='extra/missing'):
                verify_sequences(store, pin, workspace)


def test_shared_inventory_rejects_overlapping_visible_versions(tmp_path):
    with make_store(tmp_path / 'overlap.sqlite') as store:
        pin = populate_sequences(store, 3)
        store.db.execute('INSERT INTO lazy_record_versions SELECT namespace,typed_key,0,valid_to,payload,'
            'payload_checksum,codec_version,record_schema,memberships,row_checksum FROM lazy_record_versions '
            'WHERE namespace=? AND typed_key=?', (sequence.LOCATOR_NAMESPACE, store.codec.encode((1, 1))))
        store.db.commit()
        with ConversionWorkspace(store.codec, directory=tmp_path) as workspace:
            with pytest.raises(StoreIntegrityError, match='overlapping'):
                verify_sequences(store, pin, workspace)


@pytest.mark.parametrize('namespace', sequence.NAMESPACES[1:])
def test_shared_inventory_rejects_missing_projection(tmp_path, namespace):
    with make_store(tmp_path / 'missing.sqlite') as store:
        pin = populate_sequences(store, 3)
        key = next(store.iter_keys(pin, namespace))
        pin = store.commit(pin, commit_token='missing', changes=(), new_segments=(),
            version_changes=(VersionChange(namespace, key, delete=True),), metadata=store.head_metadata()).pin
        with ConversionWorkspace(store.codec, directory=tmp_path) as workspace:
            with pytest.raises(StoreIntegrityError):
                verify_sequences(store, pin, workspace)


@pytest.mark.parametrize('started', [False, True])
def test_partial_retirement_is_exempt_only_after_reclamation_started(tmp_path, started):
    from dataclasses import replace
    from ate_sim.persistence_history_retirement import initial_retirement_change
    with make_store(tmp_path / 'retirement.sqlite') as store:
        pin = populate_sequences(store, 3)
        job = initial_retirement_change('sequence', 1, generation=pin.captured_head + 1)
        job = replace(job, value=(*job.value[:-1], started))
        pin = store.commit(pin, commit_token='partial', changes=(), new_segments=(),
            version_changes=(job, VersionChange(sequence.NODE_NAMESPACE, (1, 1), delete=True)),
            metadata=store.head_metadata()).pin
        with ConversionWorkspace(store.codec, directory=tmp_path) as workspace:
            if started:
                verify_sequences(store, pin, workspace)
            else:
                with pytest.raises(StoreIntegrityError):
                    verify_sequences(store, pin, workspace)


def test_standalone_scrub_preserves_dirty_and_new_sequence_support(tmp_path):
    with make_store(tmp_path / 'dirty.sqlite') as store:
        pin = populate_sequences(store, 2)
        dirty = sequence.LazyOrderedSequence(store, pin, 1)
        dirty.append(7)
        new = sequence.LazyOrderedSequence(store, pin, 3, initial_values=[4], checked_types=True)
        for value in (dirty, new):
            value.scrub()
            with pytest.raises(StoreConflictError, match='clean persisted'):
                value.scrub(_inventory=lambda *args: pytest.fail('collected a dirty inventory'))


@pytest.mark.parametrize('which', [1, 2, 3])
@pytest.mark.parametrize('corruption', ['delete', 'key', 'checksum'])
def test_shared_scrub_authenticates_disposable_inventories(tmp_path, monkeypatch, which, corruption):
    """Tamper after the final SQL inventory scan, before any set is validated."""
    with make_store(tmp_path / 'scratch.sqlite') as store:
        pin = populate_sequences(store, 3)
        with ConversionWorkspace(store.codec, directory=tmp_path) as workspace:
            connection = store.db
            injected = False

            class LastCursor:
                def __init__(self, cursor):
                    self.cursor = cursor
                def __iter__(self):
                    return iter(self.cursor)
                def close(self):
                    nonlocal injected
                    self.cursor.close()
                    row = workspace.db.execute('SELECT key FROM conversion_sets WHERE stream=? LIMIT 1', (which,)).fetchone()
                    assert row is not None
                    if corruption == 'delete':
                        workspace.db.execute('DELETE FROM conversion_sets WHERE stream=? AND key=?', (which, row[0]))
                    elif corruption == 'key':
                        workspace.db.execute('UPDATE conversion_sets SET key=? WHERE stream=? AND key=?', (b'changed-key', which, row[0]))
                    else:
                        workspace.db.execute('UPDATE conversion_sets SET checksum=? WHERE stream=? AND key=?', ('0' * 64, which, row[0]))
                    injected = True

            class TamperedConnection(InventoryConnection):
                def execute(self, sql, parameters=()):
                    cursor = super().execute(sql, parameters)
                    if ('SELECT typed_key FROM lazy_record_versions WHERE namespace=?' in sql
                            and parameters[0] == sequence.DIRECTORY_NAMESPACE):
                        return LastCursor(cursor)
                    return cursor

            monkeypatch.setattr(store, 'db', TamperedConnection(connection, sequence.NAMESPACES))
            try:
                with pytest.raises(StoreIntegrityError, match='scrub inventory'):
                    verify_sequences(store, pin, workspace)
                assert injected
            finally:
                monkeypatch.setattr(store, 'db', connection)


def test_catalog_inventory_corruption_never_publishes_destination(tmp_path, monkeypatch):
    from ate_sim.core import Household
    from ate_sim.persistence_conversion_workspace import DiskSet
    def configure(world):
        world.households[1] = Household(1, 1, members=[1, 2, 3])
    source = legacy_lazy(tmp_path, configure=configure)
    before = sha(source)
    destination = tmp_path / 'unpublished.sqlite'
    original = DiskSet.validate
    original_sequences = copy._verify_sequences
    in_sequences = False
    def sequences(*args, **kwargs):
        nonlocal in_sequences
        in_sequences = True
        try:
            return original_sequences(*args, **kwargs)
        finally:
            in_sequences = False
    def corrupt(inventory):
        if in_sequences:
            inventory.workspace.db.execute('UPDATE conversion_sets SET checksum=? WHERE stream=?', ('0' * 64, inventory.stream))
        return original(inventory)
    monkeypatch.setattr(DiskSet, 'validate', corrupt)
    monkeypatch.setattr(copy, '_verify_sequences', sequences)
    with pytest.raises(StoreIntegrityError, match='scrub inventory'):
        copy._copy_with_checked_catalog(source, destination, rules_id=RULES)
    assert not destination.exists() and sha(source) == before
    assert not tuple(tmp_path.glob('.ate-catalog-copy-*'))


def test_verification_probe_records_counts_and_durations_without_changing_results(tmp_path, capsys):
    import json
    from ate_sim.core import Household
    from simulation.tests import catalog_sequence_scrub_probe as probe
    assert hasattr(probe, 'verification_probe'), 'large-fixture verification diagnostics are missing'
    def configure(world):
        world.households[1] = Household(1, 1, members=[1, 2, 1, 3])
    source = legacy_lazy(tmp_path, configure=configure)
    before = sha(source)
    original_scrub, original_verify = sequence.LazyOrderedSequence.scrub, copy._verify_catalog
    records = tmp_path / 'sequences.jsonl'
    with probe.verification_probe(records):
        copy._copy_with_checked_catalog(source, tmp_path / 'copy.sqlite', rules_id=RULES)
    assert sequence.LazyOrderedSequence.scrub is original_scrub and copy._verify_catalog is original_verify
    assert sha(source) == before
    lines = [json.loads(line) for line in records.read_text().splitlines()]
    timings = [line for line in lines if line.get('probe') == 'sequence_scrub']
    assert timings and all(line['seconds'] >= 0 and line['length'] == 4 for line in timings)
    finished = [line for line in lines if line.get('probe') == 'catalog_inventory' and line.get('phase') == 'finished']
    assert finished
    assert finished[-1]['rows_fetched'] == finished[-1]['visible_rows']
    assert max(finished[-1]['inventory_calls'].values()) == 1
    assert 'catalog_inventory' in capsys.readouterr().out
