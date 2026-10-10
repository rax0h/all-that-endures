"""Fixed-work H1k/H10k counted household measurements, no endurance run."""
import argparse
from dataclasses import asdict
import gc
import hashlib
import json
from pathlib import Path
import tempfile
import time

from ate_sim.core import World, Household, Person, Settlement
from ate_sim.persistence_lazy import convert_cold_to_lazy, open_lazy_world_session
from ate_sim.persistence_pressure import household_preparedness_mean
from ate_sim.persistence_session import write_cold_snapshot
from ate_sim.persistence_lazy_sequence import NODE_NAMESPACE, LOCATOR_NAMESPACE

RULES = 'final-counted-household-measurement'


def fixture(directory, size, topology):
    world = World(843000)
    for pid in range(1, 10):
        world.people[pid] = Person(pid, 0, 1, 1, alive=pid < 9)
    if topology == 'long_history':
        members = [9] * (size - 8) + list(range(1, 9))
        world.households[1] = Household(1, 1, members=members)
        world.households[2] = Household(2, 1, members=members, alive=False)
        households = [1, 2] * (size // 2)
    else:
        for hid in range(1, size + 1):
            world.households[hid] = Household(hid, 1, members=[hid % 8 + 1], alive=hid <= 8)
        # Exactly two placements share a single historical child.
        world.households[2].members = world.households[1].members
        households = list(range(1, size + 1))
    world.settlements[1] = Settlement(1, 0, 0, households=households)
    source, target = directory / 'cold.sqlite', directory / 'lazy.sqlite'
    write_cold_snapshot(world, source, rules_id=RULES)
    convert_cold_to_lazy(source, target, rules_id=RULES, counted_households=True)
    return target


def io_delta(before, after):
    return {key: value - before[key] for key, value in asdict(after).items()
            if type(value) is int and key in before}


def run(size, topology):
    with tempfile.TemporaryDirectory(prefix='ate-counted-households-') as temp:
        started = time.perf_counter()
        path = fixture(Path(temp), size, topology)
        construction = time.perf_counter() - started
        rows = []
        with open_lazy_world_session(path, rules_id=RULES) as session:
            table = session.world.households
            rows.append({'operation': 'open', 'io': asdict(session.store.diagnostics()),
                         'resident_household_headers': dict.__len__(table),
                         'history_cache': session._history_cache_budget.diagnostics()})
            for operation in ('no_op_save', 'scalar_edit', 'middle_insert', 'pressure_cold', 'pressure_hit'):
                before = asdict(session.store.diagnostics())
                started = time.perf_counter()
                writes = {}
                if operation == 'no_op_save':
                    session.save()
                elif operation == 'scalar_edit':
                    table[1].food += 1.
                    session.save()
                elif operation == 'middle_insert':
                    sequence = table[1].members
                    sequence.insert(len(sequence) // 2, 1)
                    plan = session._prepare_hybrid_save()
                    changes = plan.nested_history_version_changes
                    writes = {'sequence_node_writes': sum(c.namespace == NODE_NAMESPACE for c in changes),
                              'sequence_locator_writes': sum(c.namespace == LOCATOR_NAMESPACE for c in changes),
                              'history_version_writes': len(changes),
                              'history_encoded_write_bytes': sum(len(session.store.codec.encode(c.value)) for c in changes)}
                    session.save()
                else:
                    value = household_preparedness_mean(session.world, session.world.settlements[1])
                    writes = {'result_hex': value.hex()}
                elapsed = time.perf_counter() - started
                gc.collect()
                rows.append({'operation': operation, 'seconds': elapsed,
                             'io': io_delta(before, session.store.diagnostics()), **writes,
                             'resident_household_headers': dict.__len__(table),
                             'record_cache': session._record_cache_budget.diagnostics(),
                             'history_cache': session._history_cache_budget.diagnostics(),
                             'identity_residency': session._registry.diagnostics(),
                             'pressure_cache': session._pressure_cache.diagnostics()})
        return {'H': size, 'topology': topology, 'fixture_seconds': construction,
                'fixture_cost': 'explicit O(H) construction and verification excluded from ordinary operations',
                'sharing_placements': 2, 'live_people': 8, 'rows': rows}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    root = Path(__file__).parent
    files = ['ate_sim/persistence_lazy.py', 'ate_sim/persistence_lazy_sequence.py',
             'ate_sim/persistence_lazy_store.py', 'ate_sim/persistence_tracking.py',
             'ate_sim/persistence_pressure.py', 'ate_sim/engine.py', 'ate_sim/household_queries.py']
    report = {'source_sha256': {path: hashlib.sha256((root / path).read_bytes()).hexdigest() for path in files},
              'scope': 'counted household integration; legacy global current links remain; not capability-6 closeout',
              'release_exception': 'Exact pressure cache misses visit all household occurrences, O(H); owner latency decision remains open.',
              'measurements': [run(size, topology) for topology in ('long_history', 'many_owners') for size in (1000, 10000)]}
    Path(args.output).write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps([{'H': row['H'], 'topology': row['topology'],
                       'ordinary': [{'operation': op['operation'], 'io': op['io'],
                                     'seconds': op.get('seconds'), 'resident_headers': op['resident_household_headers']}
                                    for op in row['rows']]} for row in report['measurements']], indent=2))


if __name__ == '__main__':
    main()
