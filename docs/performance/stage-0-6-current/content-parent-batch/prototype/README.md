# Archived, unpromoted experiment

The active engine remains hosted-green runtime95c61911. These files preserve the
content-parent batch experiments. The TEMP-only variant is publication.py from
local1d7ac562/runtimeaae639ba; the buffered variant is runtimec8dd4bf6. Full exact
source/input/runtime fences live in each raw trial receipt.

To reproduce, use a separate checkout of local7c8d493 (published0759128), copy
persistence_proof_verify_batch.py and persistence_proof_publication.py into
simulation/ate_sim, plus persistence_proof_parent_inputs.py for the buffered
variant; copy regressions.py into simulation/tests/test_stage_0_6_content_parent_batch.py.
For TEMP-only, substitute temp-only-publication.py and omit parent_inputs.py.
Use the qualified313 runtime and disposable authenticated small input; do not
open the original native file. Check reproduced engine tree against the relevant
trial manifest before comparing. Do not treat archived tests as active tests or
candidate timing as accepted performance. No new hosted suite was requested.
