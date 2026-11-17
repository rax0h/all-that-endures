import cProfile
import io
import json
from pathlib import Path
import pstats
import sys
import time

from simulation.tests.proof_publication_fixtures import make_publication_store
from ate_sim import persistence_proof_publication as content
from ate_sim.persistence_proof_content import version_key
from ate_sim.persistence_proof_store import ProofNodeStore
from ate_sim.persistence_proof_world import _check_source_map

base=Path(sys.argv[1]);base.mkdir(parents=True,exist_ok=True)
result=[]
for n in (512,1024,2048,8192):
    start=time.monotonic()
    s,p,a=make_publication_store(base/f'{n}.sqlite',n)
    setup=time.monotonic()-start
    s.db.execute('BEGIN')
    calls=[0];reads=[0];sql=[0]
    original=ProofNodeStore._read_bound_bytes
    def counted(self,*args):
        reads[0]+=1
        return original(self,*args)
    ProofNodeStore._read_bound_bytes=counted
    s.db.set_trace_callback(lambda stmt:sql.__setitem__(0,sql[0]+1))
    def audit():
        for ns,key in s.db.execute('SELECT namespace,typed_key FROM lazy_record_versions WHERE valid_from<=? AND (valid_to IS NULL OR ?<valid_to)',(p.captured_head,p.captured_head)):
            row=content._source_version(s,p.captured_head,ns,key)
            assert content._map(s).get(a.content[0].versions,version_key(ns,key))==content._version_value(ns,key,row,s.codec.version)
            calls[0]+=1
    profiler=cProfile.Profile();start=time.monotonic();profiler.runcall(audit);wall=time.monotonic()-start
    s.db.set_trace_callback(None)
    profiler.dump_stats(base/f'{n}.prof')
    stream=io.StringIO();pstats.Stats(profiler,stream=stream).sort_stats('cumtime').print_stats(22)
    item=dict(versions=calls[0],proof_node_reads=reads[0],sql_statements=sql[0],setup_wall_seconds=setup,audit_wall_seconds=wall,profile=stream.getvalue())
    reads[0]=0;sql[0]=0
    def values():
        for ns,key in s.db.execute('SELECT namespace,typed_key FROM lazy_record_versions WHERE valid_from<=? AND (valid_to IS NULL OR ?<valid_to)',(p.captured_head,p.captured_head)):
            row=content._source_version(s,p.captured_head,ns,key)
            yield version_key(ns,key),content._version_value(ns,key,row,s.codec.version)
    s.db.set_trace_callback(lambda stmt:sql.__setitem__(0,sql[0]+1))
    profiler=cProfile.Profile();start=time.monotonic()
    profiler.runcall(_check_source_map,s,content._map(s),a.content[0].versions,values(),'source mismatch')
    item['candidate_audit_wall_seconds']=time.monotonic()-start
    item['candidate_proof_node_reads']=reads[0];item['candidate_sql_statements']=sql[0]
    s.db.set_trace_callback(None);ProofNodeStore._read_bound_bytes=original
    s.db.rollback()
    profiler.dump_stats(base/f'{n}-candidate.prof')
    stream=io.StringIO();pstats.Stats(profiler,stream=stream).sort_stats('cumtime').print_stats(22)
    item['candidate_profile']=stream.getvalue()
    result.append(item);print(json.dumps({k:v for k,v in item.items() if 'profile' not in k}),flush=True)
    (base/'baseline.json').write_text(json.dumps(result,indent=2))
    s.release_pin(p);s.close()
print(result[-1]['profile'])
