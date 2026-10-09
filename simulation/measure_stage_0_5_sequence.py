"""Reproducible standalone sequence measurements; not an integrated World gate.

PYTHONPATH=.:simulation python simulation/measure_stage_0_5_sequence.py --output result.json
Conversion cost is excluded explicitly. Actual store counters include payload
and metadata work; EXPLAIN is recorded separately from rows returned. Estimated
cache residency and tracemalloc observations are distinct from process RSS.
"""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import tempfile
import tracemalloc

from ate_sim.incremental_store import TypedCodec
from ate_sim.persistence_lazy_store import LazyRecordStore
from ate_sim.persistence_lazy_sequence import LazyOrderedSequence, NODE_NAMESPACE, LOCATOR_NAMESPACE, MEMBER_NAMESPACE


def counters(store):
    return asdict(store.diagnostics())


def difference(after, before):
    return {key: after[key] - before[key] for key in after}


def publish(seq, token):
    delta = seq.prepare_delta()
    result = seq._store.commit(seq._pin, commit_token=token,
        version_changes=delta.decode(seq._store.codec)[0], changes=(), new_segments=(),
        metadata={'simulation_position': seq._pin.captured_head + 1, 'seed': 843000,
                  'next_ids': {}, 'namespaces': ()})
    seq.accept_delta(delta, result.pin)
    return delta


def measure(size, duplicate_history, operation, directory):
    with LazyRecordStore.create(directory / 'measure.sqlite', codec=TypedCodec(),
            simulation_schema='8', rules_id='stage-0.5') as store:
        values = [1] * size if duplicate_history else list(range(1, 9)) + list(range(1000, 1000 + size - 8))
        seq = LazyOrderedSequence(store, store.capture_pin(), 1, initial_values=values)
        publish(seq, 'conversion')
        before = counters(store)
        seq = LazyOrderedSequence(store, seq._pin, 1)
        opened = counters(store)
        tracemalloc.start()
        if operation == 'insert':
            seq.insert(size // 2, 1)
        elif operation == 'delete':
            del seq[size // 2]
        elif operation == 'first_remove':
            seq.remove(1)
        elif operation == 'candidates':
            assert seq.candidate_positions(range(1, 9)) == tuple(range(8))
        elif operation == 'stream':
            assert sum(seq) == sum(values)
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        operated = counters(store)
        diagnostics = seq.diagnostics()
        output = {'H': size, 'fixture': 'duplicates' if duplicate_history else 'eight_candidates',
            'operation': operation, 'open': difference(opened, before),
            'operation_io': difference(operated, opened), 'cache': diagnostics,
            'tracemalloc_current_bytes': current, 'tracemalloc_peak_bytes': peak,
            'sql_rows_examined': None}
        if operation in ('insert', 'delete', 'first_remove'):
            delta = seq.prepare_delta()
            prepared = counters(store)
            changes = delta.decode(store.codec)[0]
            output['prepare_io'] = difference(prepared, operated)
            output['main_node_writes'] = sum(c.namespace == NODE_NAMESPACE for c in changes)
            output['locator_changes'] = sum(c.namespace == LOCATOR_NAMESPACE for c in changes)
            output['member_node_changes'] = sum(c.namespace == MEMBER_NAMESPACE for c in changes)
            output['total_version_changes'] = len(changes)
            publish(seq, 'edit')
            output['commit_io'] = difference(counters(store), prepared)
        output['point_query_plan'] = [row[3] for row in store.db.execute(
            'EXPLAIN QUERY PLAN SELECT payload FROM lazy_record_versions WHERE namespace=? AND typed_key=? '
            'AND valid_from<=? AND (valid_to IS NULL OR ?<valid_to)',
            (NODE_NAMESPACE, store.codec.encode((1, 1)), seq._pin.captured_head, seq._pin.captured_head))]
        return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    results = []
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        for size in (1000, 10000):
            for duplicates, operations in ((False, ('insert', 'delete', 'candidates', 'stream')),
                                            (True, ('first_remove',))):
                for operation in operations:
                    directory = root / f'{size}-{duplicates}-{operation}'
                    directory.mkdir()
                    results.append(measure(size, duplicates, operation, directory))
    args.output.write_text(json.dumps({'scope': 'standalone primitive, excludes explicit conversion; no World/identity/event gate',
        'python_residency': 'estimated recursive cache sizes and actual tracemalloc; process RSS not measured',
        'results': results}, indent=2) + '\n')


if __name__ == '__main__':
    main()
