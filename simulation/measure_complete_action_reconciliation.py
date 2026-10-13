"""Small component diagnostic; timings exclude explicit fixture conversion.

This measures accepted packed-current-body work, not a fixed-history bound.
It does not claim full-year or long-horizon performance.
"""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import time
from unittest.mock import patch

from ate_sim.agency import ActionRecord
from ate_sim.core import World
from ate_sim.persistence_complete_format import upgrade_lazy_snapshot
from ate_sim.persistence_lazy import convert_cold_to_lazy, open_lazy_world_session
from ate_sim.persistence_session import write_cold_snapshot


def run(folder, sizes):
    folder.mkdir(parents=True, exist_ok=False)
    results = []
    for size in sizes:
        path = folder / str(size)
        path.mkdir()
        world = World(843000)
        world.agency.actions.extend(ActionRecord(0, i, 'work', 'wealth', .5) for i in range(size))
        rules = 'complete-action-profile'
        write_cold_snapshot(world, path / 'cold.sqlite', rules_id=rules)
        convert_cold_to_lazy(path / 'cold.sqlite', path / 'legacy.sqlite', rules_id=rules,
                             native_graph_buckets=True)
        upgrade_lazy_snapshot(path / 'legacy.sqlite', path / 'complete.sqlite', rules_id=rules)
        with open_lazy_world_session(path / 'complete.sqlite', rules_id=rules) as session:
            cat = session._identity_coordinator.catalog
            for label, operation in (
                ('append_and_reconcile', lambda: session.world.agency.actions.append(
                    ActionRecord(1, size, 'work', 'wealth', .75))),
                ('scalar_and_reconcile', lambda: setattr(session.world.agency.actions[-1], 'strength', .8)),
                ('unchanged_reconcile', lambda: None),
            ):
                session.store.reset_diagnostics()
                with patch.object(cat, 'read_identity_group', wraps=cat.read_identity_group) as groups, \
                     patch.object(cat, 'read_owner_identity', wraps=cat.read_owner_identity) as owners:
                    start = time.perf_counter()
                    operation()
                    session._identity_bridge.synchronize_lazy_placements()
                    elapsed = time.perf_counter() - start
                    row = dict(size=size, operation=label, seconds=elapsed,
                               group_reads=groups.call_count, owner_reads=owners.call_count,
                               io=asdict(session.store.diagnostics()))
                results.append(row)
                print(json.dumps(row), flush=True)
            assert len(session.world.agency.actions) == size + 1
            assert session.world.agency.actions[-1].strength == .8
        (folder / 'result.json').write_text(json.dumps(results, indent=2))
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--sizes', type=int, nargs='+', default=[16, 128])
    args = parser.parse_args()
    run(args.output, args.sizes)
