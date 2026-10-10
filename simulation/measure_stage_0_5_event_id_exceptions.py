"""Paired range-plus-exception point measurements, excluding construction."""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import tempfile
import time

from ate_sim.core import World
from ate_sim.persistence_lazy import convert_cold_to_lazy, open_lazy_world_session
from ate_sim.persistence_session import write_cold_snapshot

RULES = 'final-event-id-measurement'


def measure(size):
    with tempfile.TemporaryDirectory(prefix='ate-event-id-metrics-') as temp:
        world = World(843000)
        world.event_ids = set(range(1, size + 1))
        world.currency.wallets[1] = {'ids': world.event_ids}
        source, target = Path(temp) / 'source.sqlite', Path(temp) / 'target.sqlite'
        started = time.perf_counter()
        write_cold_snapshot(world, source, rules_id=RULES)
        convert_cold_to_lazy(source, target, rules_id=RULES, native_graph_buckets=True)
        construction_seconds = time.perf_counter() - started
        rows = []
        with open_lazy_world_session(target, rules_id=RULES) as session:
            ids = session.world.event_ids
            for operation in ('middle_remove', 'outlier_add', 'replace_representative'):
                before = asdict(session.store.diagnostics())
                started = time.perf_counter()
                if operation == 'middle_remove':
                    ids.remove(size // 2)
                elif operation == 'outlier_add':
                    ids.add(size + 20)
                else:
                    ids.remove(1)
                    ids.add(1.0)
                plan = session._prepare_hybrid_save()
                changes = plan.nested_history_version_changes
                session.save()
                after = asdict(session.store.diagnostics())
                rows.append({'operation': operation, 'seconds': time.perf_counter() - started,
                    'io': {name: after[name] - value for name, value in before.items()},
                    'nested_writes': len(changes),
                    'nested_encoded_write_bytes': sum(len(session.store.codec.encode(c.value)) for c in changes),
                    'descriptor_bytes': len(session.store.codec.encode(ids.descriptor())),
                    'facade': ids.diagnostics(), 'history_cache': session._history_cache_budget.diagnostics()})
        return {'H': size, 'sharing_placements': 2, 'construction_seconds': construction_seconds,
                'construction_scope': 'explicit O(H) conversion and verification; excluded from point metrics', 'rows': rows}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    root = Path(__file__).parent
    paths = ['ate_sim/persistence_event_id_exceptions.py', 'ate_sim/persistence_event_ids.py',
             'ate_sim/persistence_lazy.py', 'ate_sim/persistence_tracking.py',
             'ate_sim/persistence_adapters.py', 'ate_sim/persistence_session.py',
             'ate_sim/persistence_cold_save.py', 'ate_sim/persistence_lazy_participants.py']
    result = {'source_sha256': {path: hashlib.sha256((root / path).read_bytes()).hexdigest() for path in paths},
              'scope': 'candidate exceptional point authority; full catalog/lifetime/recursive acceptance remains open',
              'measurements': [measure(size) for size in (1000, 10000)]}
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps([{'H': row['H'], 'operations': [
        {'operation': item['operation'], 'reads': item['io']['payload_reads'],
         'writes': item['io']['payload_writes'], 'nested_writes': item['nested_writes'],
         'member_visits': item['facade']['member_visits']} for item in row['rows']]} for row in result['measurements']]))


if __name__ == '__main__':
    main()
