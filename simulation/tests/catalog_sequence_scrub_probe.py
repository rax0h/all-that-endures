"""Explicit verification diagnostics; does not change persistence behavior."""
from collections import Counter
from contextlib import contextmanager
import functools
from itertools import chain
import json
from pathlib import Path
import statistics
import tempfile
import time


class InventoryConnection:
    """Count only full sequence-key inventory queries and their returned rows."""
    def __init__(self, connection, namespaces):
        self.connection = connection
        self.namespaces = namespaces
        self.calls, self.rows = Counter(), Counter()
        self.largest_fetchall = 0

    def __getattr__(self, name):
        return getattr(self.connection, name)

    def execute(self, sql, parameters=()):
        cursor = self.connection.execute(sql, parameters)
        normalized = ' '.join(sql.lower().split())
        if (normalized.startswith('select typed_key from lazy_record_versions where namespace=?')
                and parameters and parameters[0] in self.namespaces):
            namespace = parameters[0]
            self.calls[namespace] += 1
            return InventoryCursor(cursor, self, namespace)
        return cursor


class InventoryCursor:
    def __init__(self, cursor, counter, namespace):
        self.cursor, self.counter, self.namespace = cursor, counter, namespace

    def __getattr__(self, name):
        return getattr(self.cursor, name)

    def __iter__(self):
        for row in self.cursor:
            self.counter.rows[self.namespace] += 1
            yield row

    def fetchall(self):
        rows = self.cursor.fetchall()
        self.counter.rows[self.namespace] += len(rows)
        self.counter.largest_fetchall = max(self.counter.largest_fetchall, len(rows))
        return rows

    def fetchmany(self, size=None):
        rows = self.cursor.fetchmany() if size is None else self.cursor.fetchmany(size)
        self.counter.rows[self.namespace] += len(rows)
        return rows


def populate_sequences(store, count, length=16):
    from ate_sim.persistence_lazy_sequence import LazyOrderedSequence
    pin = store.capture_pin()
    sequences = [LazyOrderedSequence(store, pin, incarnation, initial_values=[1] * length,
                 value_mode='native', checked_types=True)
                 for incarnation in range(1, count + 1)]
    deltas = [sequence.prepare_delta() for sequence in sequences]
    result = store.commit(pin, commit_token='sequences', changes=(), new_segments=(),
        version_changes=chain.from_iterable(delta.decode(store.codec)[0] for delta in deltas),
        metadata={'simulation_position': 1, 'seed': 7, 'next_ids': {}, 'namespaces': ()})
    for sequence, delta in zip(sequences, deltas):
        sequence.accept_delta(delta, result.pin)
    return result.pin


def measure(store, pin, *, shared=False):
    from ate_sim.persistence_lazy_sequence import LazyOrderedSequence, NAMESPACES, DESCRIPTOR_NAMESPACE
    counts = {ns: store.db.execute('SELECT count(*) FROM lazy_record_versions WHERE namespace=? '
        'AND valid_from<=? AND (valid_to IS NULL OR ?<valid_to)',
        (ns, pin.captured_head, pin.captured_head)).fetchone()[0] for ns in NAMESPACES}
    connection = store.db
    counter = InventoryConnection(connection, NAMESPACES)
    store.db = counter
    durations = []
    original = LazyOrderedSequence.scrub

    def timed(sequence, *args, **kwargs):
        before = store.diagnostics()
        started = time.perf_counter()
        try:
            return original(sequence, *args, **kwargs)
        finally:
            durations.append({'incarnation': sequence._incarnation, 'length': len(sequence),
                'seconds': time.perf_counter() - started,
                'metadata_rows': store.diagnostics().metadata_rows - before.metadata_rows})

    started = time.perf_counter()
    LazyOrderedSequence.scrub = timed
    try:
        if shared:
            from ate_sim.persistence_catalog_copy import _verify_sequences
            from ate_sim.persistence_conversion_workspace import ConversionWorkspace
            with ConversionWorkspace(store.codec, directory=store.path.parent) as workspace:
                _verify_sequences(store, pin, workspace)
        else:
            for incarnation in store.iter_keys(pin, DESCRIPTOR_NAMESPACE):
                LazyOrderedSequence(store, pin, incarnation, value_mode='native', checked_types=True).scrub()
    finally:
        LazyOrderedSequence.scrub = original
        store.db = connection
    return {'mode': 'shared' if shared else 'original', 'descriptors': len(durations),
        'visible_rows': counts, 'inventory_calls': dict(counter.calls),
        'rows_fetched': dict(counter.rows), 'largest_fetchall': counter.largest_fetchall,
        'seconds': time.perf_counter() - started,
        'median_sequence_seconds': statistics.median(d['seconds'] for d in durations),
        'sequences': durations}


@contextmanager
def verification_probe(output):
    """Record real-upgrade phase timings and every sequence; restore on exit."""
    from ate_sim import persistence_catalog_copy as copy
    from ate_sim.persistence_lazy_sequence import LazyOrderedSequence, NAMESPACES
    from ate_sim.persistence_lazy_store import LazyRecordStore
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    patches = []
    state = {'depth': 0, 'sequences': 0}
    with output.open('a', buffering=1) as records:
        def emit(value, *, console=True):
            line = json.dumps(value, sort_keys=True)
            records.write(line + '\n')
            if console:
                print(line, flush=True)

        def replace(target, name, value):
            patches.append((target, name, getattr(target, name)))
            setattr(target, name, value)

        def observe(target, name):
            original = getattr(target, name)
            @functools.wraps(original)
            def wrapped(*args, **kwargs):
                started = time.perf_counter()
                emit({'probe': name, 'phase': 'started'})
                try:
                    result = original(*args, **kwargs)
                except BaseException as error:
                    emit({'probe': name, 'phase': 'failed', 'seconds': time.perf_counter() - started,
                          'exception': type(error).__name__})
                    raise
                emit({'probe': name, 'phase': 'finished', 'seconds': time.perf_counter() - started})
                return result
            replace(target, name, wrapped)

        original_scrub = LazyOrderedSequence.scrub
        @functools.wraps(original_scrub)
        def scrub(value, *args, **kwargs):
            started = time.perf_counter()
            before = value._store.diagnostics()
            outcome = 'finished'
            try:
                return original_scrub(value, *args, **kwargs)
            except BaseException:
                outcome = 'failed'
                raise
            finally:
                after = value._store.diagnostics()
                state['sequences'] += 1
                emit({'probe': 'sequence_scrub', 'phase': outcome, 'incarnation': value._incarnation,
                    'length': value._length, 'seconds': time.perf_counter() - started,
                    'payload_reads': after.payload_reads - before.payload_reads,
                    'metadata_rows': after.metadata_rows - before.metadata_rows,
                    'sequence_number': state['sequences']},
                    console=state['sequences'] == 1 or state['sequences'] % 128 == 0 or outcome == 'failed')

        original_catalog = copy._verify_catalog
        @functools.wraps(original_catalog)
        def catalog(store, pin, *args, **kwargs):
            if state['depth']:
                return original_catalog(store, pin, *args, **kwargs)
            state['depth'] += 1
            connection = store.db
            counter = InventoryConnection(connection, NAMESPACES)
            started = time.perf_counter()
            first_sequence = state['sequences']
            counts = {}
            phase = 'failed'
            emit({'probe': 'catalog_inventory', 'phase': 'started', 'generation': pin.captured_head})
            try:
                counts = {ns: connection.execute('SELECT count(*) FROM lazy_record_versions WHERE namespace=? '
                    'AND valid_from<=? AND (valid_to IS NULL OR ?<valid_to)',
                    (ns, pin.captured_head, pin.captured_head)).fetchone()[0] for ns in NAMESPACES}
                emit({'probe': 'catalog_inventory', 'phase': 'counted', 'visible_rows': counts,
                      'descriptors': counts[NAMESPACES[0]]})
                store.db = counter
                result = original_catalog(store, pin, *args, **kwargs)
                phase = 'finished'
                return result
            finally:
                store.db = connection
                state['depth'] -= 1
                emit({'probe': 'catalog_inventory', 'phase': phase, 'seconds': time.perf_counter() - started,
                    'sequences': state['sequences'] - first_sequence, 'visible_rows': counts,
                    'inventory_calls': dict(counter.calls), 'rows_fetched': dict(counter.rows),
                    'largest_fetchall': counter.largest_fetchall})

        try:
            replace(LazyOrderedSequence, 'scrub', scrub)
            replace(copy, '_verify_catalog', catalog)
            observe(copy, '_verify_sequences')
            observe(copy, 'verify_type_witnesses')
            observe(LazyRecordStore, 'verify_all')
            yield
        finally:
            for target, name, original in reversed(patches):
                setattr(target, name, original)


if __name__ == '__main__':
    import argparse
    from ate_sim.incremental_store import TypedCodec
    from ate_sim.persistence_lazy_store import LazyRecordStore
    parser = argparse.ArgumentParser()
    parser.add_argument('--shared', action='store_true')
    parser.add_argument('--counts', nargs='+', type=int, default=[8, 32, 128])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    results = []
    with tempfile.TemporaryDirectory() as directory:
        for count in args.counts:
            with LazyRecordStore.create(Path(directory) / f'{count}.sqlite', codec=TypedCodec(),
                    simulation_schema='8', rules_id='scrub-probe') as store:
                pin = populate_sequences(store, count)
                result = measure(store, pin, shared=args.shared)
                results.append(result)
                print(json.dumps({k: v for k, v in result.items() if k != 'sequences'}), flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2) + '\n')
