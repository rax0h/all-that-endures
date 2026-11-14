import runpy
from unittest.mock import patch
import ate_sim.persistence_proof_parent_inputs as module
for limit in (0,1024*1024):
 print('AMENDED PERSISTED BUFFER LIMIT',limit,flush=True)
 with patch.object(module,'BUFFER_BYTES',limit):
  runpy.run_path('/workspace/scratch/72797495b7a4/content-parent-review/persisted-probe.py')
