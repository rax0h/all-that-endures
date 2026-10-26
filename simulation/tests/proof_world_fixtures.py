"""Real normalized complete World files, not synthetic manifest root slots."""
from simulation.tests.test_stage_0_5_final_complete_format import upgraded
from simulation.tests.test_stage_0_5_final_catalog_copy import opened
from simulation.tests.proof_sequence_event_fixtures import authorities
from ate_sim.persistence_proof_directory_publish import _load

def make_world(path,*,size=32,configure=None):
 path.mkdir(parents=True,exist_ok=True)
 if size==32 and configure is None:file=upgraded(path)
 else:
  from simulation.tests.test_stage_0_5_final_catalog_copy import legacy_lazy,RULES
  from ate_sim.persistence_complete_format import upgrade_lazy_snapshot
  from ate_sim.core import Settlement
  def config(w):
   w.settlements[1]=Settlement(1,0,0,memory={'war':.25})
   if configure is not None:configure(w)
  source=legacy_lazy(path,size=size,configure=config);file=path/'complete.sqlite';upgrade_lazy_snapshot(source,file,rules_id=RULES)
 s=opened(file);p=s.capture_pin();a,ra=authorities(s,p);d=_load(s,p.captured_head)[0]
 return s,p,a,ra,d
