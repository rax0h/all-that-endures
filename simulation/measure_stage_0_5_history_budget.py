"""Component cache residency evidence: long histories and many visited owners.

Explicit fixture construction/traversal is O(H). This does not certify World
identity/open/pressure bounds. Keep eight external proxies; dirty state and
traced Python memory are separate from bounded clean payload weights.
"""
import argparse
from collections import deque
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import tempfile
import tracemalloc

from ate_sim.incremental_store import TypedCodec
from ate_sim.persistence_lazy_store import LazyRecordStore
from ate_sim.persistence_lazy_budget import SharedCacheBudget, resident_bytes
from ate_sim.persistence_lazy_nested_history import LazyHistoryList, initial_list_changes


def measure(root, history, mode):
    codec = TypedCodec()
    budget = SharedCacheBudget()
    with LazyRecordStore.create(root / f'{mode}-{history}.sqlite', codec=codec,
                               simulation_schema='8', rules_id='shared-history-budget') as store:
        pin = store.capture_pin()
        owner_count = 2 if mode == 'long' else history
        values = range(history) if mode == 'long' else range(8)
        changes = tuple(change for owner in range(1, owner_count + 1)
                        for change in initial_list_changes(owner, values, codec))
        pin = store.commit(pin, commit_token='initial', changes=(), new_segments=(),
                           version_changes=changes,
                           metadata={'simulation_position': 0, 'seed': 843000, 'next_ids': {}, 'namespaces': ()}).pin
        del changes
        store.reset_diagnostics()
        aliases = deque(maxlen=8)
        peak_entries = peak_bytes = peak_owners = 0
        tracemalloc.start()
        for owner in range(1, owner_count + 1):
            proxy = LazyHistoryList(store, pin, owner, cache_budget=budget)
            aliases.append(proxy)
            for index in range(len(proxy)):
                assert proxy[index] == index
                # Constant-size counters; avoid tracing a diagnostics traversal
                # at every occurrence and mistaking it for production work.
                peak_entries = max(peak_entries, len(budget._entries))
                peak_bytes = max(peak_bytes, budget._bytes)
                peak_owners = max(peak_owners, len(budget._owners))
        traced_current, traced_peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        scan_reads = asdict(store.diagnostics())
        cache_python = resident_bytes(tuple((h._cache, h._cache_weights) for h in aliases))
        store.reset_diagnostics()
        proxy[len(proxy) // 2] = -1
        edit = proxy.pending_changes()
        edit_reads = asdict(store.diagnostics())
        dirty = proxy.diagnostics()
        assert len(edit) == 1
        old_pin = store.capture_pin()
        store.reset_diagnostics()
        next_pin = store.commit(pin, commit_token='edit', changes=(), new_segments=(), version_changes=edit,
            metadata={'simulation_position': 1, 'seed': 843000, 'next_ids': {}, 'namespaces': ()}).pin
        commit_counters = asdict(store.diagnostics())
        old = LazyHistoryList(store, old_pin, proxy._incarnation)
        assert old[len(old) // 2] == len(old) // 2
        store.release_pin(old_pin)
        del old
        for retained in aliases:
            retained.accept_save(next_pin)
        budget.clear()
        assert not budget._entries and not budget._owners and all(not h._cache for h in aliases)
        return {'H': history, 'mode': mode, 'owners_visited': owner_count,
                'externally_retained_proxy_count': len(aliases),
                'peak_clean_entries': peak_entries, 'peak_clean_weight_bytes': peak_bytes,
                'peak_weak_cache_owners': peak_owners, 'retained_cache_python_bytes': cache_python,
                'tracemalloc_current_bytes': traced_current, 'tracemalloc_peak_bytes': traced_peak,
                'traversal_store_counters': scan_reads, 'one_edit_store_counters': edit_reads,
                'one_edit_version_changes': len(edit),
                'one_edit_payload_bytes': sum(len(codec.encode(v.value)) for v in edit),
                'one_edit_commit_counters': commit_counters,
                'dirty': dirty, 'after_release': budget.diagnostics(),
                'sql_rows_examined': None}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    source = Path(__file__).parent
    paths = ('ate_sim/persistence_lazy_budget.py', 'ate_sim/persistence_lazy_nested_history.py',
             'ate_sim/persistence_lazy_sequence.py', 'ate_sim/persistence_lazy_household_members.py',
             'ate_sim/persistence_lazy.py', 'ate_sim/persistence_lazy_store.py', Path(__file__).name)
    with tempfile.TemporaryDirectory(prefix='stage05-cache-') as directory:
        results = [measure(Path(directory), size, mode)
                   for mode in ('long', 'many') for size in (1000, 10000)]
    report = {'scope': 'component clean history budget, explicit traversal, eight retained aliases maximum',
              'limits': {'entries': 64, 'payload_weight_bytes': 8 * 1024 * 1024},
              'source_sha256': {str(p): hashlib.sha256((source / p).read_bytes()).hexdigest() for p in paths},
              'results': results}
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps([{'H': r['H'], 'mode': r['mode'], 'clean_entries': r['peak_clean_entries'],
                      'clean_bytes': r['peak_clean_weight_bytes'],
                      'traced_peak': r['tracemalloc_peak_bytes'], 'edit_bytes': r['one_edit_payload_bytes']}
                     for r in results]))


if __name__ == '__main__':
    main()
