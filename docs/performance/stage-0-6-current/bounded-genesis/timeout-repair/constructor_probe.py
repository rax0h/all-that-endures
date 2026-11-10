"""Paired small complete-format construction probe; never mature acceptance."""
import argparse,hashlib,json,subprocess,time
from collections import Counter
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--destination',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--instrumented',action='store_true');p.add_argument('--expected-digest');args=p.parse_args()
from ate_sim.persistence_proof_world_copy import copy_world_with_proofs
from ate_sim.persistence_lazy_store import LazyRecordStore
from ate_sim.persistence_sqlite_guard import _NativeGuardCursor
from ate_sim.persistence_lazy import open_lazy_world_session
from ate_sim.persistence_proof_world_session import open_proof_world_session
h=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
source_hash=h(args.source)
if args.expected_digest:expected=args.expected_digest
else:
 with open_lazy_world_session(args.source,rules_id='stage-0-6-real-year-probe') as s:expected=s.world.digest()
# Opening a canonical session changes operational lease rows. Seal the actual
# input after that closed control; construction must preserve those bytes.
source_hash=h(args.source)
counts=Counter()
execute,audit=_NativeGuardCursor.execute,LazyRecordStore._verify_all_in_snapshot
if args.instrumented:
 def traced(self,sql,*a,**k):
  counts['sql_calls']+=1
  if 'from save_head' in sql.lower():counts['head_queries']+=1
  if 'integrity_check' in sql.lower():counts['physical_checks']+=1
  return execute(self,sql,*a,**k)
 def scrub(self):counts['full_source_audits']+=1;return audit(self)
 _NativeGuardCursor.execute=traced;LazyRecordStore._verify_all_in_snapshot=scrub
start=time.monotonic()
try:result=copy_world_with_proofs(args.source,args.destination,rules_id='stage-0-6-real-year-probe',rank_proofs=True)
finally:
 elapsed=time.monotonic()-start
 _NativeGuardCursor.execute=execute;LazyRecordStore._verify_all_in_snapshot=audit
unchanged=h(args.source)==source_hash
if not unchanged:
 args.output.write_text(json.dumps(dict(status='invalid_source_hash',source_before=source_hash,source_after=h(args.source),wall_seconds=elapsed,counts=dict(counts)),indent=2)+'\n')
 raise AssertionError('construction source bytes changed')
with open_proof_world_session(args.destination,rules_id='stage-0-6-real-year-probe',expected_commitment=result.commitment) as s:
 actual=s.world.digest();assert actual==expected
row=dict(status='complete',instrumented=args.instrumented,wall_seconds=elapsed,counts=dict(counts),source_bytes=args.source.stat().st_size,source_sha256=source_hash,source_unchanged=True,canonical_digest=actual,code={str(p):h(p) for p in sorted(Path('simulation/ate_sim').glob('*.py'))},head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),limitation='Small real generated year2 complete format6 input; instrumented timings separate from raw; no mature or interactive-latency guarantee')
args.output.write_text(json.dumps(row,indent=2)+'\n');print(json.dumps({k:v for k,v in row.items() if k!='code'}),flush=True)
