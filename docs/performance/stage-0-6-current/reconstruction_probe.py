"""Time paired constructors on a disposable, authenticated after-digest input."""

import argparse
import os
from contextlib import ExitStack, closing
from pathlib import Path
import re
import shutil
import sys
import tempfile


BUDGETS = {
    'smoke': dict(admission=120, restore=120, copy=45, setup=60,
                  first=90, repeat=90, verify_parent=45),
    'mature': dict(admission=300, restore=1800, copy=420, setup=1200,
                   first=2700, repeat=2700, verify_parent=300),
}
SMOKE_RUN = 44028694698
REQUEST = Path(__file__).with_name('reconstruction-probe-request.json')


class ProbeInterrupted(Exception):
    """The smoke drill deliberately unwinds after the first pass."""


class _Discard(Exception):
    """Force the owned transaction to roll back on successful diagnostics."""


def _scopes(store, generation):
    from ate_sim import persistence_proof_scope as scope

    allocator = store._identity_state_at(generation)[0]
    return scope._construct_roots(
        store, generation, allocator, include_children=True,
        include_sequence=True, include_rank=True,
    )


def _collections(store, generation):
    from ate_sim import persistence_proof_collection_directory as directory

    domain = directory.domain(store.store_identity, store.codec.version)
    seek = directory.OrderedSeekMap(store.db, domain)
    with closing(store.db.execute(
        'SELECT namespace FROM lazy_namespace_state WHERE valid_from<=? '
        'AND (valid_to IS NULL OR ?<valid_to) ORDER BY CAST(namespace AS BLOB)',
        (generation, generation),
    )) as rows:
        def certificates():
            for (namespace,) in rows:
                certificate, _ = directory.collection._construct_collection(
                    store, generation, namespace
                )
                key = directory._key(namespace)
                yield key, directory._persist(store, domain, key, certificate)

        return (seek.build(certificates()),)


CONSTRUCTORS = {'scope': _scopes, 'collection': _collections}


def sample(store, pin, component, recorder, write, *, interrupt=False):
    construct = CONSTRUCTORS[component]

    def build(phase):
        print(f'{component} {phase} reconstruction', flush=True)
        roots = recorder.measure(phase, lambda: construct(store, pin.captured_head))
        summary = [{'digest': root.digest.hex(), 'count': root.count} for root in roots]
        write(phase, summary)
        return summary

    first = build('first')
    if interrupt:
        raise ProbeInterrupted()
    repeat = build('repeat')
    if first != repeat:
        raise ValueError('reconstruction roots differ')
    return first, repeat


def exercise(database, descriptor, rules, component, recorder, write, *, interrupt=False):
    from ate_sim import persistence_proof_collection_directory as directory
    from ate_sim import persistence_proof_scope as scope
    from ate_sim.persistence_adapters import SCHEMA, WorldCodec
    from ate_sim.persistence_genesis_transaction import ProofGenesisTransaction
    from ate_sim.persistence_lazy_store import LazyRecordStore, _bounded_conversion_audits

    def schema(store):
        with closing(store.db.execute(
            'SELECT type, name, tbl_name, sql FROM main.sqlite_schema ORDER BY type, name'
        )) as cursor:
            return tuple(cursor)

    with ExitStack() as lifetime:
        lifetime.enter_context(_bounded_conversion_audits())
        store = lifetime.enter_context(LazyRecordStore.open(
            database, codec=WorldCodec(identity_links_recorded=True),
            expected_simulation_schema=SCHEMA, expected_rules_id=rules,
        ))
        original_schema = schema(store)
        if (store.generation != 0 or store.store_identity != descriptor['store_identity']
                or any(row[1] in ('ate_proof_nodes', 'ate_ordered_seek_nodes') for row in original_schema)
                or store.db.execute(
                    "SELECT value FROM store_metadata WHERE key='format_version'"
                ).fetchone() != ('6',)):
            raise ValueError('probe requires the original generation-zero format-6 copy')
        store.db.execute("UPDATE store_metadata SET value='7' WHERE key='format_version'")
        store.db.commit()
        pin = store.capture_pin()
        lifetime.callback(store.release_pin, pin)

        def prepare(snapshot):
            snapshot.enter_context(ProofGenesisTransaction(store, pin, rank=True))
            directory._source_schemas(store.db)
            if component == 'scope':
                scope._guard_construction(store.db)
                scope._guard_child_keys(store)
                scope._guard_sequence_keys(store)
            else:
                directory.collection._indexes(store)
                directory._source_indexes(store.db)

        recorder.store = store
        try:
            with ExitStack() as snapshot:
                recorder.measure('setup', lambda: prepare(snapshot))
                roots, _ = sample(store, pin, component, recorder, write, interrupt=interrupt)
                raise _Discard()
        except (_Discard, ProbeInterrupted) as outcome:
            if (store.db.in_transaction or store._active_read_transaction
                    or store._genesis_transaction is not None
                    or schema(store) != original_schema or getattr(outcome, '__notes__', ())):
                raise RuntimeError('probe rollback did not restore disposable source custody') from outcome
            if isinstance(outcome, ProbeInterrupted):
                raise
            return roots
        finally:
            recorder.store = None


def run(root, output, mode, component, *, interrupt=False):
    import ate_sim
    from simulation import continuation_receipts
    from simulation import stage_0_6_after_digest_admission as admission
    from simulation import stage_0_6_genesis_checkpoint as checkpoint
    from simulation import stage_0_6_genesis_resume as resume
    from simulation import stage_0_6_genesis_transport as transport
    from simulation.stage_0_6_genesis_stages import Recorder
    from simulation.stage_0_6_mature_benchmark import machine

    if interrupt and mode != 'smoke':
        raise ValueError('interruption drill requires the small input')
    if (Path(ate_sim.__file__).resolve().parent != root / 'simulation/ate_sim'
            or resume.git(root, 'rev-parse', 'HEAD') != os.environ['GITHUB_SHA']):
        raise ValueError('probe imported a different source checkout')
    request = continuation_receipts.load_receipt(REQUEST)
    checkpoint.exact(request, {'request_id'}, 'reconstruction request')
    request_id = request['request_id']
    if type(request_id) is not str or re.fullmatch(r'[a-zA-Z0-9_-]{1,96}', request_id) is None:
        raise ValueError('invalid reconstruction request ID')
    output.mkdir(parents=True, exist_ok=False)
    recorder = Recorder(output, BUDGETS[mode])

    def write(name, value):
        continuation_receipts.publish_receipt(output / (name + '.json'), value)

    with tempfile.TemporaryDirectory(prefix='ate-reconstruction-', dir=root) as directory:
        private = Path(directory)
        pair = admission.contract(root)['after_digests'][mode]

        def admit():
            green = resume.inspect_green(root)
            software, details = resume.runtime_description()
            note = pair['metadata']
            ref, parent = admission.restore_prior(
                root, mode, note['run_id'], note['artifact_id'], private / 'receipt'
            )
            if mode == 'mature':
                resume.require_smoke(root, SMOKE_RUN, private / 'accepted-smoke')
            context = dict(parent['context'], runtime_tree=green['runtime_tree'],
                           critical_blobs=resume.fence(root)[1], execution_runtime=software)
            stamp = admission.attest(root, parent, context)
            write('input', {
                'metadata_ref': ref, 'data_ref': parent['data_ref'],
                'database': parent['database'], 'admission': stamp, 'green': green,
                'head': os.environ['GITHUB_SHA'], 'component': component, 'mode': mode,
                'request_id': request_id, 'runtime': details, 'machine': machine(),
            })
            return parent

        parent = recorder.measure('admission', admit)
        descriptor = parent['database']
        source = private / 'input-data' / 'candidate.sqlite'
        working = private / 'working.sqlite'

        def restore():
            transport.restore(
                parent['data_ref'], source.parent, member=source.name,
                member_bytes=descriptor['bytes'],
                compatible=lambda head: admission.verify_old_head(root, mode, head),
            )
            checkpoint.verify_database(source, descriptor)

        def copy_source():
            if shutil.disk_usage(private).free < 2 * descriptor['bytes'] + 64 * 1024**2:
                raise ValueError('insufficient disposable copy and journal headroom')
            shutil.copyfile(source, working)
            checkpoint.verify_database(working, descriptor)

        recorder.measure('restore', restore)
        status = 'complete'
        try:
            recorder.measure('copy', copy_source)
            roots = exercise(
                working, descriptor, parent['context']['rules_id'],
                component, recorder, write, interrupt=interrupt,
            )
        except ProbeInterrupted:
            status, roots = 'interrupted', None
        finally:
            primary = sys.exception()
            try:
                recorder.measure('verify_parent', lambda: checkpoint.verify_database(source, descriptor))
            except Exception as error:
                if primary is None:
                    raise
                primary.add_note('retained input verification failed: ' + str(error))
    write('result', {
        'status': status, 'component': component, 'mode': mode, 'roots': roots,
        'database_sha256': descriptor['sha256'], 'parent_verified': True,
    })
    return 77 if status == 'interrupted' else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=BUDGETS, required=True)
    parser.add_argument('--component', choices=CONSTRUCTORS, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--interrupt-after-first', action='store_true')
    args = parser.parse_args()
    return run(Path.cwd().resolve(), args.output, args.mode, args.component,
               interrupt=args.interrupt_after_first)


if __name__ == '__main__':
    raise SystemExit(main())
