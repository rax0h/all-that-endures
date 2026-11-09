"""Closure checks for review findings, using the qualified local runtime."""
from pathlib import Path
import gc
import hashlib
import json
import subprocess
import sys
import tempfile
import tracemalloc
from unittest.mock import patch

from ate_sim import persistence_lazy_store as lazy
from ate_sim.persistence_conversion_workspace import ConversionWorkspace

OUT=Path(__file__).parent


def sources():
    files={str(p) for p in Path('simulation/ate_sim').glob('*.py')}
    files.update(('simulation/tests/test_stage_0_6_bounded_genesis.py',
        'simulation/stage_0_6_proof_mature_genesis.py','.github/tests/test_stage_0_6_proof_mature_genesis.py'))
    return {name:hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in sorted(files)}


def sequence_inventory():
    from ate_sim.persistence_catalog_copy import _verify_sequences
    from ate_sim.incremental_store import TypedCodec
    from simulation.tests.catalog_sequence_scrub_probe import populate_sequences
    for count in (1000,10000):
        with tempfile.TemporaryDirectory(prefix='ate-review-sequence-closure-') as directory:
            with lazy.LazyRecordStore.create(Path(directory)/'sequence.sqlite',codec=TypedCodec(),
                    simulation_schema='8',rules_id='scrub-probe') as store:
                pin=populate_sequences(store,1,length=count)
                captured={}
                def observe(frame,event,arg):
                    if event=='return' and frame.f_code.co_name=='scrub' and frame.f_code.co_filename.endswith('persistence_conversion_sequence_audit.py'):
                        state=frame.f_locals
                        captured.update(occurrence_map_type=type(state['occurrences']).__name__,
                            occurrence_entries=state['occurrences'].count,
                            expected_set_types=sorted({type(s).__name__ for s in state['expected'].values()}),
                            expected_physical_entries=sum(s.count for s in state['expected'].values()),
                            wanted_relation_type=type(state['wanted_members']).__name__,
                            found_relation_type=type(state['found_members']).__name__)
                gc.collect();tracemalloc.start();sys.setprofile(observe)
                try:
                    with lazy._bounded_conversion_audits(),ConversionWorkspace(store.codec,directory=directory) as workspace:
                        _verify_sequences(store,pin,workspace)
                finally:
                    sys.setprofile(None)
                    live,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
                assert captured['occurrence_map_type']=='DiskLookup'
                assert captured['expected_set_types']==['DiskSet']
                assert captured['wanted_relation_type']==captured['found_relation_type']=='DiskSet'
                print(json.dumps(dict(probe='sequence_inventory_closure',length=count,
                    python_traced_peak_bytes=peak,python_traced_live_bytes=live,inventories=captured)),flush=True)


def frozen_and_shared_spool():
    from ate_sim import persistence_lazy_nested_history as nested
    from ate_sim.persistence_adapters import WorldCodec,SCHEMA
    from ate_sim.persistence_conversion_audit import construction_spills
    from ate_sim.persistence_history_types import initial_type_change,verify_type_witnesses
    with tempfile.TemporaryDirectory(prefix='ate-review-frozen-closure-') as directory:
        with lazy.LazyRecordStore.create(Path(directory)/'frozen.sqlite',codec=WorldCodec(identity_links_recorded=True),
                simulation_schema=SCHEMA,rules_id='review-frozen') as store:
            pin=store.capture_pin()
            pin=store.commit(pin,commit_token='empty-map',changes=(),new_segments=(),
                version_changes=(lazy.VersionChange(nested.DESCRIPTOR_NAMESPACE,1,('frozen-map',0,0,True)),
                    initial_type_change(1,'map',())),next_incarnation_id=2,required_format_version=5,
                metadata=dict(simulation_position=1,seed=7,next_ids={},namespaces=())).pin
            def reject(*a,**kw):raise AssertionError('bulk frozen certification')
            with (lazy._bounded_conversion_audits(),ConversionWorkspace(store.codec,directory=directory) as workspace,
                    construction_spills(workspace),patch.object(nested._ScalarHistory,'_ordered_entries',reject)):
                assert verify_type_witnesses(store,pin,workspace=workspace)==1
                proxy=nested.LazyFrozenHistoryMap(store,pin,1,checked_types=True,recursive=True)
                with patch.object(ConversionWorkspace,'__init__',side_effect=AssertionError('new scalar spill file')):
                    for _ in range(1000):assert tuple(proxy)==()
            print(json.dumps(dict(probe='frozen_certification_and_shared_spool',status='passed',iterations=1000)),flush=True)


before=sources()
(OUT/'closure-source-hashes.json').write_text(json.dumps(before,indent=2)+'\n')
from review_probes import multi_ordinal_query
multi_ordinal_query()
sequence_inventory()
frozen_and_shared_spool()
assert sources()==before,'product sources changed during closure checks'
print(json.dumps(dict(probe='exact_source_stability',status='passed',source_files=len(before))),flush=True)
