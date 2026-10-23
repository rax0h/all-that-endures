"""Real retained-version point reads, not World/save latency acceptance."""
import argparse
from pathlib import Path
import platform
import resource
import sqlite3
import subprocess
import sys
import time
import tracemalloc

from ate_sim.incremental_store import TypedCodec
from ate_sim.persistence_lazy_store import LazyRecordStore, VersionChange
from ate_sim.persistence_proof_version import read_version_bytes
from simulation import continuation_receipts as receipts
from simulation.tests.proof_version_fixtures import construct_version_certificate

SIZES = (1000, 10000, 100000)


def git(*args):
    return subprocess.check_output(['git', *args], text=True).strip()


def measure(store, operation):
    store.reset_diagnostics()
    selects = dict(version=0, proof=0, unrelated=0, metadata=0)
    def trace(statement):
        if not statement.lstrip().upper().startswith('SELECT'):
            return
        source = ('version' if 'FROM lazy_record_versions' in statement else
                  'proof' if 'FROM ate_proof_nodes' in statement else
                  'unrelated' if any('FROM '+t in statement for t in
                      ('records', 'segments', 'lazy_order_versions', 'lazy_query_versions')) else 'metadata')
        selects[source] += 1
    store.db.set_trace_callback(trace)
    tracemalloc.start()
    try:
        started = time.perf_counter()
        result = operation()
        elapsed = time.perf_counter()-started
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
        store.db.set_trace_callback(None)
    return result, dict(wall_seconds=elapsed, python_peak_bytes=peak, sql_selects=selects,
        payload_checks=store._payload_check_reads, payload_check_bytes=store._payload_check_bytes,
        payload_decodes=store._payload_reads)


def run(output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    git('ls-files', '--error-unmatch', str(Path(__file__).resolve().relative_to(Path(git('rev-parse', '--show-toplevel')))))
    if git('status', '--porcelain', '--untracked-files=no'):
        raise ValueError('tracked source is dirty')
    source = dict(head=git('rev-parse', 'HEAD'), runtime_tree=git('rev-parse', 'HEAD:simulation/ate_sim'),
        driver_sha256=receipts.file_hash(__file__), fixture_sha256=receipts.file_hash('simulation/tests/proof_version_fixtures.py'),
        python=platform.python_version(), sqlite=sqlite3.sqlite_version, platform=platform.platform())
    receipts.publish_receipt(output/'source.json', dict(schema='ate-proof-version-source/1', source=source,
        archive_sizes=SIZES, active_records=1, requested_records=1, absent_key=999,
        sqlite_main_cache_kib=2048, sqlite_temp_cache_kib=2048, temp_store='FILE', clean_node_cache_bytes=0,
        scope='Raw retained-version point presence/absence, not World/save/open/step or a save history-read gate'))
    results = []
    for size in SIZES:
        started = time.perf_counter()
        store = LazyRecordStore.create(output/f'source-{size}.sqlite', codec=TypedCodec(),
                                       simulation_schema='8', rules_id='proof-version-scaling')
        try:
            store.db.execute('PRAGMA cache_size=-2048')
            store.db.execute('PRAGMA temp_store=FILE')
            store.db.execute('PRAGMA temp.cache_size=-2048')
            pin = store.capture_pin()
            def changes():
                yield VersionChange('people', 0, {'wealth': 17})
                for i in range(size):
                    yield VersionChange('archive', i, b'retained-history-'+b'x'*111)
            result = store.commit(pin, commit_token='seed', version_changes=changes(), changes=(), new_segments=(),
                metadata=dict(simulation_position=1, seed=7, next_ids={}, namespaces=('people', 'archive')))
            pin = result.pin
            fixture_seconds = time.perf_counter()-started
            started = time.perf_counter()
            cert, expected = construct_version_certificate(store, pin)
            construction_seconds = time.perf_counter()-started
            receipts.publish_receipt(output/f'constructed-{size}.json', dict(source=source, archive_records=size,
                fixture_seconds=fixture_seconds, verified_construction_seconds=construction_seconds,
                committed_content_leaves=cert.content.count, certificate_commitment=expected.hex()))
            baseline, checked = measure(store, lambda: store.read_version(pin, 'people', 0, expected_record_schema=1))
            present, presence = measure(store, lambda: read_version_bytes(store, pin, cert, expected,
                'people', store.codec.encode(0), expected_record_schema=1))
            absent, absence = measure(store, lambda: read_version_bytes(store, pin, cert, expected,
                'people', store.codec.encode(999), expected_record_schema=1))
            if (baseline.value != {'wealth': 17} or present.payload != store.codec.encode({'wealth': 17})
                    or present.memberships != store.codec.encode(())
                    or (present.record_schema, present.valid_from, present.valid_to) != (1, 1, None)
                    or absent is not None or cert.content.count != size+1):
                raise ValueError('raw content/presence/absence result disagreement')
            for observation, count in ((presence, 1), (absence, 0)):
                if (observation['sql_selects']['unrelated'] or observation['sql_selects']['version'] != 1
                        or observation['payload_checks'] != count or observation['payload_decodes']
                        or observation['sql_selects']['proof'] > 256 or observation['python_peak_bytes'] >= 2*1024*1024):
                    raise ValueError('fixed read work/memory gate failed')
            row = dict(schema='ate-proof-version-scaling/1', status='complete', source=source, archive_records=size,
                fixture_seconds=fixture_seconds, verified_construction_seconds=construction_seconds,
                exact=True, baseline=checked, presence=presence, absence=absence,
                process_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=='darwin' else 1024),
                limitations=['Synthetic contents in real versioned store schema; no mature World or point-edit save.',
                    'One explicit full verify/construction outside point timers; zero clean-node Python cache.',
                    'Sequential warm/uncontrolled filesystem caches; no latency distribution or speedup claim.',
                    'A fetched record must be checked; one check here is not a zero-history-read save result.',
                    'SELECT counts are application work, not physical disk traffic; RSS includes setup and prior cases.'])
            receipts.publish_receipt(output/f'size-{size}.json', row)
            results.append(row)
            print(f'{size}: exact; presence/absence node SELECTs={presence["sql_selects"]["proof"]}/{absence["sql_selects"]["proof"]}; '
                  f'payload checks={presence["payload_checks"]}/{absence["payload_checks"]}', flush=True)
        finally:
            store.close()
    receipts.publish_receipt(output/'summary.json', dict(schema='ate-proof-version-summary/1', status='complete',
        source=source, results=[dict(archive_records=x['archive_records'], exact=x['exact'],
            baseline=x['baseline'], presence=x['presence'], absence=x['absence']) for x in results]))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)
