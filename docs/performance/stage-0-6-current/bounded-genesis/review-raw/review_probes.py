"""Independent review probes; not product tests or mature acceptance."""
from pathlib import Path
import gc
import hashlib
import json
import platform
import sqlite3
import sys
import tempfile
import tracemalloc

from ate_sim import persistence_lazy_store as lazy
from ate_sim.persistence_proof_world_copy import _rebase_private_snapshot
from ate_sim.incremental_store import TypedCodec, Membership

OUT = Path(__file__).parent


def fingerprint():
    expected = json.loads(Path('docs/performance/stage-0-6-current/fixture-construction/qualified-local-runtime.json').read_text())
    def sha(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    import _sqlite3
    db = sqlite3.connect(':memory:')
    libraries = sorted({line.split()[-1] for line in Path('/proc/self/maps').read_text().splitlines()
                        if '/libsqlite3.so.' in line})
    actual = dict(resolved_executable=str(Path(sys.executable).resolve()),
        executable_sha256=sha(Path(sys.executable).resolve()), python=sys.version,
        compiler=platform.python_compiler(), sqlite=sqlite3.sqlite_version,
        sqlite_source_id=db.execute('select sqlite_source_id()').fetchone()[0],
        sqlite_compile_options=[row[0] for row in db.execute('pragma compile_options')],
        sqlite_extension_path=_sqlite3.__file__,sqlite_extension_sha256=sha(_sqlite3.__file__),
        loaded_sqlite_libraries=[dict(path=p,sha256=sha(p)) for p in libraries])
    db.close()
    differences = {k:dict(expected=expected[k],actual=v) for k,v in actual.items() if expected[k]!=v}
    result = dict(qualified=not differences,actual=actual,differences=differences)
    (OUT/'fingerprint.json').write_text(json.dumps(result,indent=2)+'\n')
    assert not differences, differences
    print(json.dumps(dict(probe='fingerprint',qualified=True)),flush=True)


def multi_ordinal_query():
    with tempfile.TemporaryDirectory(prefix='ate-review-query-') as directory:
        path=Path(directory)/'query.sqlite'
        with lazy.LazyRecordStore.create(path,codec=TypedCodec(),simulation_schema='test',rules_id='test') as store:
            pin=store.capture_pin()
            pin=store.commit(pin,commit_token='seed',changes=(),new_segments=(),
                version_changes=(lazy.VersionChange('people',0,'valid',memberships=(
                    Membership('same','same',1),Membership('same','same',2))),),
                metadata=dict(simulation_position=1,seed=7,next_ids={},namespaces=('people',))).pin
            store.release_pin(pin)
            before=store.verify_all()
            row=dict(probe='multi_ordinal_query',before=before,
                memberships=[(key,ordinal) for key,ordinal in store.iter_query_memberships(
                    store.capture_pin(),'people','same','same')])
            for (token,) in store.db.execute('SELECT token FROM generation_pins').fetchall():
                store.db.execute('DELETE FROM generation_pins WHERE token=?',(token,))
            store.db.commit()
            try:
                with lazy._bounded_conversion_audits():
                    _rebase_private_snapshot(store)
                row['outcome']='success'
            except BaseException as exc:
                row.update(outcome='error',error_type=type(exc).__name__,error=str(exc))
            row['after']=store.verify_all()
            print(json.dumps(row),flush=True)


def sequence_inventory():
    from ate_sim.persistence_catalog_copy import _verify_sequences
    from ate_sim.persistence_conversion_workspace import ConversionWorkspace
    from simulation.tests.catalog_sequence_scrub_probe import populate_sequences
    for count in (1000,10000):
        with tempfile.TemporaryDirectory(prefix='ate-review-sequence-') as directory:
            with lazy.LazyRecordStore.create(Path(directory)/'sequence.sqlite',codec=TypedCodec(),
                    simulation_schema='8',rules_id='scrub-probe') as store:
                pin=populate_sequences(store,1,length=count)
                captured={}
                def observe(frame,event,arg):
                    if event=='return' and frame.f_code.co_name=='scrub' and frame.f_code.co_filename.endswith('persistence_lazy_sequence.py'):
                        state=frame.f_locals
                        captured.update(occurrence_entries=len(state['occurrences']),
                            expected_physical_entries=sum(len(s) for s in state['expected'].values()),
                            expected_member_occurrences=sum(len(s) for s in state['members'].values()),
                            actual_member_occurrences=sum(len(s) for s in state['found_members'].values()))
                gc.collect();tracemalloc.start();sys.setprofile(observe)
                try:
                    with lazy._bounded_conversion_audits(),ConversionWorkspace(store.codec,directory=directory) as workspace:
                        _verify_sequences(store,pin,workspace)
                finally:
                    sys.setprofile(None)
                    live,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
                print(json.dumps(dict(probe='sequence_inventory',length=count,python_traced_peak_bytes=peak,
                    python_traced_live_bytes=live,retained_physical_inventories=captured)),flush=True)


if __name__=='__main__':
    fingerprint()
    multi_ordinal_query()
    sequence_inventory()
