# Stage 0.5 pending workspace recovery — October 10 UTC

Stage0.5 is not complete. Capability6 is not emitted. PR14 remains unchanged at
c29e3d06a0c9d219235e2b3f0390271bd1245aea. Continue the authorized complete closeout;
do not stop after a package or promote production.

Latest durable implementation is compact checked EventIdSet identity headers:
public source 0b3bd9f1123aca32f6f0e4df952fc805ab75eef4,
local source b8c7621a11576d07c40b64fa2f4fa35ee64b6441,
matching tree 50565c4101f4caf460c7094763f2ba257c02c909.
Public docs parent of this note: 8b491a15ec7385aaa2bc082b4a04b2c110d4c6d9;
local docs ee05948dbaa1c9a05206213469d4f809efb002a0.
This recovery note was published directly because workspace execution disconnected.
It has not yet been added to the local branch.

## Uncommitted tested batch to recover

Worktree /workspace/scratch/c3a830e86cea/stage-0-5-closeout,
branch sol/stage-0-5-complete-closeout.
Python /workspace/scratch/c3a830e86cea/ownership-gate-venv/bin/python.
Use PYTHONPATH=.:simulation and shell pipefail.

New files:
- simulation/ate_sim/persistence_history_dependencies.py
- simulation/ate_sim/persistence_history_retirement.py
- simulation/tests/test_stage_0_5_final_backing_dependencies.py
- simulation/tests/test_stage_0_5_final_history_retirement.py

Modified:
- simulation/ate_sim/persistence_lazy_store.py:
  partial lazy_record_current_key index on(namespace,typed_key) WHERE valid_to IS NULL.
- simulation/ate_sim/persistence_lazy_identity_catalog.py:
  metadata retirement defers groups with a checked pending backing-retirement job.

These files were written and tested locally, but NOT committed or published before
the execution transport failed. Recover them from this worktree first. The full
apply_patch operations are also in the originating conversation. Do not claim a
published source SHA or matching tree for this pending batch.

BackingDependencyPool borrows the existing publisher token without cloning an old
snapshot pin. A mandatory checked roster per backing contains at most MAX_PINS
tokens, prunes released tokens on updates, and retains an empty row until backing
reclamation. There is no per-visit immortal lease row. Weak GC only changes bounded
memory; a frozen immutable SaveParticipant publishes dependency changes in the
central commit. Exact publication validation and acknowledgement preserve recovery.
Final publisher-pin release expires dependencies without advancing the World.
Failed release preserves pool state. Fresh complete-format conversion must create
empty dependency authorities for all existing backings; missing authority is
corruption. The pool is deliberately NOT activated in World yet.

Retirement queues one compact MVCC job without enumerating backing pages. A plan
checks complete-group emptiness, retirement floor, mandatory dependencies, backing
kind, and current writer pin. Indexed first-incarnation tuple ranges select only
current rows, with at most256 total VersionChanges per plan. Lists, maps, sets and
counted sequences have explicit child scopes and retire their descriptor/dependency/
job together last. Rotating checked-at membership order lets held jobs yield to
others. A started job cannot silently cancel into a partly deleted revived backing.
Normal store cleanup still removes at most256 eligible physical rows per operation.
The new scope index is created with new stores; existing stores need explicit copy
upgrade before this retirement API, with no ordinary-open index migration.

## Verified local evidence

Final combined affected gate:
78 passed in6.88s, pipefail exit0,
stage_0_5_final_backing_retirement_gate.txt under
/workspace/scratch/c3a830e86cea.

Selection: new retirement/dependency tests, snapshot leases, store and store failures.
Tests cover H1k/H10k private overlays surviving12 unrelated saves with one pin and
no World publication, GC/abort metadata reclamation, exact retry, failed pin release,
bounded roster reuse through12 publisher close/reopen cycles, existing two-publisher
generation pressure, required authority corruption, old-pin and live-alias protection,
bounded cleanup progress, all four backend scopes, catalog deferral/final compaction,
before/after-commit recovery, and indexed incarnation1 selection excluding11.

Earlier gate76pass/onefailure only required a less-specific corruption-error regex;
the final78 gate includes its correction and a new frozen-GC abort case.
An earlier dependency/store selection66passed in6.26s precedes the last queue/abort
changes and is supporting only. Counts overlap. There is no P5 or full-suite claim
for this new batch; preceding P5 remains evidence at its own integrated source.

The next planned catalog selection never returned a process after the transport
failed. Run:
simulation/tests/test_stage_0_5_final_retired_identity.py with
-k 'retired_header or retirement_respects or catalog_churn or allocator_only or retirement_subprocess or legacy_catalog'
and retain its result. Inspect diff/check whitespace, finish targeted repair if
needed, commit and publish with live GitHub ref lease and exact matching tree.
Then document the actual source boundaries and remove/update this pending note.
Do not broadly repeat unchanged tests solely because execution disconnected.

## Work still required

Activate backing dependencies and queued retirement only with complete checked
World identity authority; integrate pending acquisitions/GC/revival into the same
frozen publication and exact close/detach lifecycle. Preserve ordinary generation
pressure: this is backing protection, not a historical whole-store snapshot.
Finish touched owner/header witnesses, remove new-format global link/bootstrap
scans, complete recursive mutable descendants and bounded type admission, and
close equality semantics beyond candidate finite event keys. Preserve real runtime
append-list/counting aliases without O(H) ordinary promotion or rejecting legal
sharing. Build the complete source-preserving capability6 copy upgrade and all
mandatory feature authorities together; do not partially activate catalog at5.
Finish integrated scale/fault/P5 evidence, one final full applicable suite on stable
source, and the final independent architectural review/release package. Exact native
pressure O(H) release decision remains open; keep coding before asking that decision.
No production promotion or new endurance run is authorized.
