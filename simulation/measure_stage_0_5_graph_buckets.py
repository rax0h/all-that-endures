"""Paired nested graph history measurements; explicit construction excluded."""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import tempfile
import time

from ate_sim.core import World
from ate_sim.persistence_lazy import convert_cold_to_lazy, open_lazy_world_session
from ate_sim.persistence_lazy_graph_buckets import BUCKET_SPECS
from ate_sim.persistence_lazy_nested_history import PAGE_NAMESPACE, ENTRY_NAMESPACE, LazyHistoryList
from ate_sim.persistence_session import write_cold_snapshot

RULES = 'final-native-graph-measurement'


def measure(namespace, spec, size):
    with tempfile.TemporaryDirectory(prefix='ate-graph-buckets-') as temp:
        world = World(843000)
        kind, attribute, _touched = spec
        owner = world
        for field in namespace.split('.')[1:-1]:
            owner = getattr(owner, field)
        root = getattr(owner, namespace.split('.')[-1])
        key = ('person', 1) if attribute in ('lineage_children', 'owner_index') else 1
        values = ({('person', n) for n in range(size)} if attribute == 'lineage_children'
                  else list(range(size)) if kind == 'list' else set(range(size)))
        root[key] = values
        world.currency.wallets[1] = {'history': values}
        source, target = Path(temp) / 'source.sqlite', Path(temp) / 'target.sqlite'
        started = time.perf_counter()
        write_cold_snapshot(world, source, rules_id=RULES)
        convert_cold_to_lazy(source, target, rules_id=RULES, native_graph_buckets=True)
        creation = time.perf_counter() - started
        rows = []
        with open_lazy_world_session(target, rules_id=RULES) as session:
            table = getattr(session, attribute)
            bucket = table[key]
            for operation in ('scalar_wallet', 'one_addition'):
                before = asdict(session.store.diagnostics())
                started = time.perf_counter()
                if operation == 'scalar_wallet':
                    session.wallets[1]['amount'] = 1
                else:
                    value = ('person', size) if attribute == 'lineage_children' else size
                    (bucket.append if isinstance(bucket, LazyHistoryList) else bucket.add)(value)
                plan = session._prepare_hybrid_save()
                edits = () if plan is None else plan.nested_history_version_changes
                page_writes = [change for change in edits if change.namespace in (PAGE_NAMESPACE, ENTRY_NAMESPACE)]
                session.save()
                after = asdict(session.store.diagnostics())
                rows.append({'operation': operation, 'seconds': time.perf_counter() - started,
                             'io': {name: after[name] - value for name, value in before.items()},
                             'history_payload_writes': len(page_writes),
                             'history_encoded_write_bytes': sum(len(session.store.codec.encode(c.value)) for c in page_writes),
                             'header_bytes': len(table._baseline_payload[key]),
                             'history_cache': session._history_cache_budget.diagnostics(),
                             'record_cache': session._record_cache_budget.diagnostics(),
                             'proxy': bucket.diagnostics()})
        return {'H': size, 'family': namespace, 'sharing_placements': 2,
                'fixture_seconds': creation, 'fixture_cost': 'explicit O(H) conversion and verification', 'rows': rows}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    root = Path(__file__).parent
    files = ['ate_sim/persistence_lazy.py', 'ate_sim/persistence_lazy_nested_history.py',
             'ate_sim/persistence_lazy_graph_buckets.py', 'ate_sim/persistence_tracking.py']
    result = {'source_sha256': {path: hashlib.sha256((root / path).read_bytes()).hexdigest() for path in files},
              'scope': 'native graph candidate lane; not complete capability-6/catalog/lifetime acceptance',
              'measurements': [measure(namespace, spec, size) for namespace, spec in BUCKET_SPECS.items() for size in (1000, 10000)]}
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps([{'family': item['family'], 'H': item['H'],
                      'writes': [row['history_payload_writes'] for row in item['rows']],
                      'header_bytes': item['rows'][-1]['header_bytes']} for item in result['measurements']], indent=2))


if __name__ == '__main__':
    main()
