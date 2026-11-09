"""Independent frozen-map certification guard and small-map spill probe."""
from pathlib import Path
import json
import tempfile
import time
from unittest.mock import patch

from ate_sim import persistence_lazy_store as lazy
from ate_sim import persistence_lazy_nested_history as nested
from ate_sim.persistence_history_types import initial_type_change, verify_type_witnesses
from ate_sim.persistence_conversion_workspace import ConversionWorkspace
from ate_sim.persistence_adapters import WorldCodec, SCHEMA

with tempfile.TemporaryDirectory(prefix='ate-review-frozen-') as directory:
    with lazy.LazyRecordStore.create(Path(directory)/'frozen.sqlite',codec=WorldCodec(identity_links_recorded=True),
            simulation_schema=SCHEMA,rules_id='review-frozen') as store:
        pin=store.capture_pin()
        pin=store.commit(pin,commit_token='empty-map',changes=(),new_segments=(),
            version_changes=(lazy.VersionChange(nested.DESCRIPTOR_NAMESPACE,1,('frozen-map',0,0,True)),
                             initial_type_change(1,'map',())),next_incarnation_id=2,required_format_version=5,
            metadata=dict(simulation_position=1,seed=7,next_ids={},namespaces=())).pin
        store.verify_all()
        class BulkCertification(Exception): pass
        def reject(*_args,**_kwargs):
            raise BulkCertification('conversion frozen-map certification called _ordered_entries')
        try:
            with (lazy._bounded_conversion_audits(),ConversionWorkspace(store.codec,directory=directory) as workspace,
                    patch.object(nested._ScalarHistory,'_ordered_entries',reject)):
                verify_type_witnesses(store,pin,workspace=workspace)
            guard=dict(outcome='streamed')
        except BulkCertification as exc:
            guard=dict(outcome='bulk-path',error=str(exc))
        print(json.dumps(dict(probe='frozen_map_certification',**guard)),flush=True)
        proxy=nested.LazyFrozenHistoryMap(store,pin,1,checked_types=True,recursive=True)
        calls=0
        original=ConversionWorkspace.__init__
        def counted(self,*args,**kwargs):
            global calls
            calls+=1
            return original(self,*args,**kwargs)
        start=time.perf_counter()
        with lazy._bounded_conversion_audits(),patch.object(ConversionWorkspace,'__init__',counted):
            for _ in range(1000):
                assert tuple(proxy)==()
        elapsed=time.perf_counter()-start
        print(json.dumps(dict(probe='empty_scalar_spill',iterations=1000,scratch_databases=calls,
            wall_seconds=elapsed,estimated_million_spill_seconds=elapsed*1000,
            limitation='single empty proxy microbenchmark; excludes descriptor reads and all mature acceptance work')),flush=True)
