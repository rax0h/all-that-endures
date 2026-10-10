"""Reproduce paired history measurements with exactly two sharing placements."""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import tempfile
import time

from ate_sim.core import World
from ate_sim.magic_resources import MagicResource
from ate_sim.materials import MaterialLot
from ate_sim.social import Relationship
from ate_sim.metaphysics import SoulState
from ate_sim.persistence_lazy import convert_cold_to_lazy, open_lazy_world_session
from ate_sim.persistence_lazy_nested_history import PAGE_NAMESPACE, ENTRY_NAMESPACE
from ate_sim.persistence_session import write_cold_snapshot

RULES = 'final-native-history-measurement'


def fixture(kind, size):
    world = World(843000)
    if kind == 'soul_set':
        history = {f'mark-{i}' for i in range(size)}
        world.metaphysics.souls[1] = SoulState(1, marks=history)
        attribute, key, field, scalar, value = 'souls', 1, 'marks', 'death_count', 1
    elif kind == 'soul_map':
        history = {f'link-{i}': float(i) for i in range(size)}
        world.metaphysics.souls[1] = SoulState(1, cosmic_links=history)
        attribute, key, field, scalar, value = 'souls', 1, 'cosmic_links', 'death_count', 1
    else:
        history = list(range(size))
        if kind == 'resource':
            world.magic_resources.resources[1] = MagicResource(1, 'essence', 'fire', 'common', 1, transfers=history)
            attribute, key, field, scalar, value = 'resources', 1, 'transfers', 'location', 2
        elif kind == 'lot':
            world.materials.lots[1] = MaterialLot(1, 'ore', 10., .5, 1, 1, 0, 1, 'person', 1, transfers=history)
            attribute, key, field, scalar, value = 'material_lots', 1, 'transfers', 'quantity', 12.
        else:
            world.social.edges[1, 2] = Relationship(1, 2, shared_history=history)
            attribute, key, field, scalar, value = 'social_edges', (1, 2), 'shared_history', 'trust', .75
    world.currency.wallets[1] = {'history': history}
    return world, attribute, key, field, scalar, value


def measure(root, kind, size):
    world, attribute, key, field, scalar, value = fixture(kind, size)
    source, target = root / 'cold.sqlite', root / 'lazy.sqlite'
    started = time.perf_counter()
    write_cold_snapshot(world, source, rules_id=RULES)
    convert_cold_to_lazy(source, target, rules_id=RULES)
    construction_seconds = time.perf_counter() - started
    rows = []
    with open_lazy_world_session(target, rules_id=RULES) as session:
        table = getattr(session, attribute)
        record = table[key]
        history = getattr(record, field)
        assert history is session.wallets[1]['history']
        for operation in ('scalar', 'point'):
            session.store.reset_diagnostics()
            before = history.diagnostics()
            started = time.perf_counter()
            if operation == 'scalar':
                setattr(record, scalar, value)
            elif kind == 'soul_set':
                history.add('new-mark')
            elif kind == 'soul_map':
                history['new-link'] = 2.5
            else:
                history.append(size)
            plan = session._prepare_hybrid_save()
            history_changes = [change for change in plan.nested_history_version_changes
                               if change.namespace in (PAGE_NAMESPACE, ENTRY_NAMESPACE)]
            session.save()
            after = history.diagnostics()
            loads = 'entry_loads' if kind.startswith('soul_') else 'page_loads'
            rows.append({
                'H': size, 'family': kind, 'operation': operation,
                'sharing_placements': 2, 'edited_owners': 1,
                'history_payload_loads': after[loads] - before[loads],
                'history_payload_writes': len(history_changes),
                'history_write_bytes': sum(len(session.store.codec.encode(change.value)) for change in history_changes),
                'header_bytes': len(table._baseline_payload[key]),
                'store_counters': asdict(session.store.diagnostics()),
                'history_cache': session._history_cache_budget.diagnostics(),
                'history_residency': after,
                'elapsed_seconds': time.perf_counter() - started,
                'explicit_fixture_construction_seconds': construction_seconds,
            })
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    rows = []
    with tempfile.TemporaryDirectory(prefix='ate-native-histories-') as directory:
        root = Path(directory)
        for size in (1000, 10000):
            for kind in ('resource', 'lot', 'social', 'soul_set', 'soul_map'):
                place = root / f'{kind}-{size}'
                place.mkdir()
                rows.extend(measure(place, kind, size))
    report = {
        'scope': 'Native scalar histories, two placements in two owners, one edit. Construction and explicit materialization are O(H). Not whole-World catalog, household, pressure or recursive-history certification.',
        'source_sha256': {name: hashlib.sha256((Path(__file__).parent / 'ate_sim' / name).read_bytes()).hexdigest()
                          for name in ('persistence_lazy.py', 'persistence_lazy_nested_history.py', 'persistence_lazy_families.py')},
        'rows': rows,
    }
    args.output.write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
