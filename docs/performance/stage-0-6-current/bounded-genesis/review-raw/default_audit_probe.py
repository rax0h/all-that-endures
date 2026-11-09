"""Observe construction-algorithm selection in the ordinary audited opener."""
from pathlib import Path
import json
import tempfile
from unittest.mock import patch
from ate_sim import persistence_catalog_copy as catalog
from ate_sim import persistence_lazy_store as lazy
from ate_sim.persistence_proof_world_copy import copy_world_with_proofs
from ate_sim.persistence_proof_world_session import open_audited_proof_world_session
from simulation.tests.test_stage_0_5_final_complete_format import upgraded
from simulation.tests.test_stage_0_5_final_catalog_copy import RULES

with tempfile.TemporaryDirectory(prefix='ate-review-default-') as directory:
    root=Path(directory)
    source=upgraded(root)
    destination=root/'proof.sqlite'
    copied=copy_world_with_proofs(source,destination,rules_id=RULES,rank_proofs=True)
    original=catalog.verify_type_witnesses
    observed=[]
    def track(*args,**kwargs):
        observed.append(dict(conversion_scope=lazy._CONVERSION_AUDITS.get(),
            bounded_workspace=kwargs.get('workspace') is not None))
        return original(*args,**kwargs)
    with patch.object(catalog,'verify_type_witnesses',track):
        with open_audited_proof_world_session(destination,rules_id=RULES,expected_commitment=copied.commitment):
            pass
    print(json.dumps(dict(probe='default_audited_opener',observed=observed)),flush=True)
