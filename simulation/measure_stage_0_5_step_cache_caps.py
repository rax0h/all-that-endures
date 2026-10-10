"""Paired record-cap stress with fixed current work, then retained-alias edit."""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import tempfile
import time

from ate_sim.core import World, Person
from ate_sim.persistence_lazy import convert_cold_to_lazy, open_lazy_world_session
from ate_sim.persistence_lazy_budget import resident_bytes
from ate_sim.persistence_session import write_cold_snapshot

RULES = 'final-step-cache-measurement'


def measure(size):
    with tempfile.TemporaryDirectory(prefix='ate-step-cache-metrics-') as temp:
        world = World(843000)
        for pid in range(1, size + 1):
            world.people[pid] = Person(pid, 0, 1, 1, alive=pid <= 8)
        source, target = Path(temp) / 'source.sqlite', Path(temp) / 'target.sqlite'
        started = time.perf_counter()
        write_cold_snapshot(world, source, rules_id=RULES)
        convert_cold_to_lazy(source, target, rules_id=RULES, native_graph_buckets=True)
        creation_seconds = time.perf_counter() - started
        with open_lazy_world_session(target, rules_id=RULES) as session:
            people = session.people
            retained = people[1]
            lifetime = session.world.__dict__['_ate_persistence_lifetime']
            peak = 0
            started = time.perf_counter()
            lifetime.begin_run()
            lifetime.begin_step()
            try:
                # Deliberate archive sweep stresses eviction; this O(H) request
                # is separate from the fixed-current-work point operation.
                for pid in range(2, size + 1):
                    people[pid]
                    peak = max(peak, len(people._lru))
                sidecars = {name: getattr(people, name) for name in (
                    '_baseline_payload', '_baseline_presence', '_baseline_incarnation',
                    '_baseline_ordinal', '_baseline_identity_labels') if hasattr(people, name)}
                snapshot = {'clean_entries': len(people._lru), 'step_touched': len(people._lru._step_touched),
                    'peak_clean_entries': peak, 'sidecar_entries': {name: len(value) for name, value in sidecars.items()},
                    'sidecar_python_bytes': resident_bytes(sidecars), 'record_budget': session._record_cache_budget.diagnostics()}
            finally:
                lifetime.end_step()
                lifetime.end_run()
            sweep_seconds = time.perf_counter() - started
            before = asdict(session.store.diagnostics())
            started = time.perf_counter()
            retained.wealth = 99.
            assert people[1] is retained
            session.save()
            after = asdict(session.store.diagnostics())
            point = {'seconds': time.perf_counter() - started,
                     'io': {name: after[name] - value for name, value in before.items()}}
        return {'H': size, 'live_people': 8, 'external_aliases': 1, 'point_edits': 1,
                'construction_seconds': creation_seconds, 'explicit_sweep_seconds': sweep_seconds,
                'construction_and_sweep_cost': 'explicit O(H), excluded from point timing',
                'inside_step': snapshot, 'retained_alias_scalar_edit': point}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    root = Path(__file__).parent
    files = ['ate_sim/persistence_lazy.py', 'ate_sim/persistence_lazy_budget.py', 'ate_sim/persistence_lazy_families.py']
    result = {'source_sha256': {path: hashlib.sha256((root / path).read_bytes()).hexdigest() for path in files},
              'scope': 'record/sidecar cache cap; not global catalog/external lease/eager topology acceptance',
              'measurements': [measure(size) for size in (1000, 10000)]}
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps([{'H': item['H'], 'peak_clean': item['inside_step']['peak_clean_entries'],
        'sidecars': item['inside_step']['sidecar_entries'], 'point_io': item['retained_alias_scalar_edit']['io']} for item in result['measurements']]))


if __name__ == '__main__':
    main()
