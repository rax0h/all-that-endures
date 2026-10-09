"""Standalone retirement measurements; explicit bootstrap excluded.

PYTHONPATH=.:simulation python simulation/measure_stage_0_5_retired_identity.py --output result.json
Counters are actual store I/O, not a claim about SQL rows examined. Residency
estimates, tracemalloc and on-disk logical rows are reported separately.
"""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import tempfile
import tracemalloc

from ate_sim.incremental_store import TypedCodec
from ate_sim.persistence_lazy_store import LazyRecordStore
from ate_sim.persistence_lazy_identity_retired import RetiredIdentityRanges, NODE_NAMESPACE
from ate_sim.persistence_lazy_identity_catalog import IdentityCatalog, GROUP_NAMESPACE, initial_catalog_delta


def counters(store): return asdict(store.diagnostics())


def difference(after, before): return {key: after[key] - before[key] for key in after}


def publish(store, pin, changes, token, *, allocator=None, namespaces=()):
    return store.commit(pin, commit_token=token, version_changes=changes,
        next_incarnation_id=allocator, changes=(), new_segments=(),
        metadata={'simulation_position': pin.captured_head + 1, 'seed': 843000,
                  'next_ids': {}, 'namespaces': namespaces}).pin


def point(size, path):
    with LazyRecordStore.create(path, codec=TypedCodec(), simulation_schema='8', rules_id='stage-0.5') as store:
        tree = RetiredIdentityRanges(store, store.capture_pin(), initial=True)
        for inc in range(1, size * 3, 3): tree.add(inc)
        pin = publish(store, tree.pin, tree.pending_changes(), 'initial')
        before = counters(store)
        tree = RetiredIdentityRanges(store, pin)
        opened = counters(store)
        target = size * 3 // 2 + 2
        tracemalloc.start()
        tree.add(target)
        changes = tree.pending_changes()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        edited = counters(store)
        resident = tree.diagnostics()
        pin = publish(store, pin, changes, 'edit')
        committed = counters(store)
        assert RetiredIdentityRanges(store, pin).contains(target)
        return {'intervals': size, 'target': target, 'open_io': difference(opened, before),
            'edit_io': difference(edited, opened), 'commit_io': difference(committed, edited),
            'version_changes': len(changes), 'node_changes': sum(v.namespace == NODE_NAMESPACE for v in changes),
            'cache': resident, 'tracemalloc_current_bytes': current, 'tracemalloc_peak_bytes': peak,
            'sql_rows_examined': None,
            'point_query_plan': [row[3] for row in store.db.execute(
                'EXPLAIN QUERY PLAN SELECT payload FROM lazy_record_versions WHERE namespace=? AND typed_key=? '
                'AND valid_from<=? AND (valid_to IS NULL OR ?<valid_to)',
                (NODE_NAMESPACE, store.codec.encode(target), pin.captured_head, pin.captured_head))]}


def churn(path):
    with LazyRecordStore.create(path, codec=TypedCodec(), simulation_schema='8', rules_id='stage-0.5') as store:
        pin = store.capture_pin()
        initial = initial_catalog_delta(store.codec, (), (), next_incarnation_id=601, generation=1)
        pin = publish(store, pin, initial.decode(store.codec)[0], 'initial', allocator=601,
                      namespaces=('world_identity_links',))
        operations = []
        for step in range(3):
            before = counters(store)
            delta = IdentityCatalog(store).prepare_retirement_delta(pin)
            changes = delta.decode(store.codec)[0]
            prepared = counters(store)
            pin = publish(store, pin, changes, f'churn-{step}', namespaces=('world_identity_links',))
            committed = counters(store)
            operations.append({'step': step, 'version_changes': len(changes),
                'retired_headers': sum(v.namespace == GROUP_NAMESPACE and v.delete for v in changes),
                'prepare_io': difference(prepared, before), 'commit_io': difference(committed, prepared),
                'remaining_headers': store.namespace_size(pin, GROUP_NAMESPACE)})
        store.verify_all()
        tree = RetiredIdentityRanges(store, pin)
        tree.scrub()
        return {'fixture': '600_reserved_unplaced_ids', 'operations': operations,
            'final_ranges': tree.intervals(), 'retired_node_count': store.namespace_size(pin, NODE_NAMESPACE),
            'sql_rows_examined': None, 'selection_query_plan': store.query_plan(pin, GROUP_NAMESPACE, 'retired', True),
            'logical_backing_rows': store.db.execute('SELECT count(*) FROM lazy_record_versions').fetchone()[0]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).parent
    paths = ('persistence_lazy_identity_retired.py', 'persistence_lazy_identity_catalog.py',
             'persistence_lazy_identity_coordinator.py', 'persistence_lazy_store.py')
    hashes = {name: hashlib.sha256((root / 'ate_sim' / name).read_bytes()).hexdigest() for name in paths}
    with tempfile.TemporaryDirectory() as directory:
        work = Path(directory)
        result = {'scope': 'standalone retired metadata; not World integration or global maintenance',
            'source_sha256': hashes, 'point_edits': [point(size, work / f'{size}.sqlite') for size in (1000, 10000)],
            'churn': churn(work / 'churn.sqlite')}
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'point_edits': [{k: r[k] for k in ('intervals','version_changes','node_changes','edit_io')}
                                    for r in result['point_edits']], 'churn': result['churn']}, indent=2))


if __name__ == '__main__': main()
