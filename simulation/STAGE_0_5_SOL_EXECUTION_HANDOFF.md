# Stage 0.5 — final Astra review and autonomous Sol execution handoff

**Date:** 2026-10-05. **Reviewed head:**
`006e2bb88216e207b5867a7f92ded8841538821a`.
**Repo/branch:** rax0h/all-that-endures, PR #14,
sim/stage-0-5-stabilization.

## 1. Authority and current disposition

The owner requests that Sol carry the remaining work forward without mandatory
Astra visits after every tranche. This handoff supersedes earlier mandatory
return-to-Astra stop points **within the scope below**. It does not remove tests,
independent controls, evidence requirements or prohibited-work boundaries.

P1/P2/P3A/P3B remain accepted. P4 preparation remains accepted.
**P4.1 is not accepted yet:** the reproduced blockers below must be fixed first.
A passing suite is evidence, not permission to ignore those failures.
No product code was changed in this architect review.

Sol is authorized to repair P4.1, implement P4 in the sequence below, and prepare/
execute the short integrated P5 validation. Continue automatically between
internal gates when their objective requirements pass. Commit focused steps
and evidence; do not request permission for routine reversible work.

Do not describe Sol's own completion as “Astra accepted.” Use “implementation
gate passed,” retain the evidence, and assemble a final release-review package.
If a fundamental invariant cannot be met, record a precise blocker; do not
silently weaken it to reach a completion label.

Still prohibited: millennium/endurance, balance/magic-progression changes,
Stage 1, normal checkpoint-default replacement, unrelated simulation work,
main writes, PR merge. These require explicit owner instruction. No quota or
model-usage pressure overrides correctness or those restrictions.

## 2. Verified P4.1 evidence and blockers

Completed full suite: run 37307789377, job 111755564165,
**674 passed in 1737.93 seconds**.
Actual workflow head: `bc6f76dc3a0fadf5748a10b3c960c800754ed5d7`.
Its difference from the stable code commit
`c3f3525d7ddf3b2afdf39946a6fa9add9dd98225` is workflow/staging scaffolding;
no simulation Python source difference. Subsequent live commits are evidence.
Independent focused rerun during review:
`PYTHONPATH=/tmp/ate-final-deps:simulation:. python -m pytest -q simulation/tests/test_persistence_lazy_store.py simulation/tests/test_persistence_lazy_store_failures.py simulation/tests/test_incremental_store.py`:
**56 passed in 2.49 seconds**.

The following probes expose missing coverage. They use the existing make_store/
commit helpers, TypedCodec, and VersionChange; reproduce them as regressions.

### R1 — iter_keys materializes the complete key collection

`iter_keys` appends every decoded key to result and returns a tuple.
Requesting only the first item with `islice(..., 1)` consumed 100/1,000 query rows
at respective archive sizes. SQL LIMIT 128 does not bound Python retention.

Make the API a genuinely lazy iterator/page iterator. Check and buffer at most
one 128-key page; close the read transaction before yielding to caller code.
Abandonment/exception/close must release temporary resources. Keep the durable
pin rules. Never retain earlier pages internally. Callers that intentionally
need all keys must explicitly use tuple/list outside this primitive.
Test first-item work, complete order, page boundaries, pin movement/release and
mutation/close between pages. Count temporary keys and record-body bytes too.

### R2 — visible-result counters conceal a historical SQL scan

Fixture: N people initially have membership bucket=hot. Pin that generation.
Change people 1..N-1 to bucket=cold and keep person 0 hot.
Query current hot: result is always (0,), but sqlite progress-handler instruction
counts rose **891 -> 7,191** for N=100 -> 1,000. query_rows reports only the one
returned row. Existing tests vary a different index value and miss this case.

Separate/index current and previous visibility so old same-value memberships
cannot force a scan of unrelated history. Preserve checked generation semantics.
Possible implementation: disjoint open-interval / exact closing-generation
queries with suitable partial/composite indexes, rather than one broad
valid_from range followed by valid_to filtering. Prove the actual selected
query plans/work; merely adding an index name is insufficient.

Also fix order paging access paths: keyset LIMIT must not repeatedly scan/sort
all historical order rows for each page. Measure cumulative SQLite work over
full traversal, not just returned rows. Permit indexed logarithmic navigation
and work proportional to actual returned rows, not H for a fixed result.
Include old same-value memberships, newer-only memberships, zero results,
insert/delete/reinsert and both visible generations at 1k/10k.

`_check_record_row(decode=False)` still fetches/checks whole record payloads:
zero “decoded payload” counters do not mean zero payload bytes. Report actual
bytes fetched/hashed, or use checked compact owner-projection metadata for key
queries. Do not hide large body reads in metadata counters.

### R3 — healthy pin release breaks full verification and recovery copy

With an old pin retained, publish a newer version; release the old pin;
immediately call verify_all. Reproduced:
`StoreIntegrityError: expired lazy versions remain below the retention floor`.

release_pin moves the derived floor but does not clean obsolete rows;
verify_all rejects those legitimate leftovers. copy_current_head calls the same
scrub, so the defect also blocks healthy recovery/copy.

Choose and document a consistent cleanup contract: bounded explicit obsolete
state that scrub validates and maintenance later reclaims, or transactional
release-time cleanup with its cost accounted for. A valid API sequence must
never manufacture “corruption.” Keep no-op saves free of archive maintenance.
Cover verify/copy/backup/reopen directly after release and injected release/
cleanup faults, plus release of the last pin. No test may insert an extra save
merely to mask the broken state.

### R4 — failed later attempt cannot be resolved with an older receipt present

Commit token old at G=1. Attempt token new from its updated pin, inject failure
before_commit, then resolve_commit(pin_at_1, new).
Reproduced: `StoreConflictError: commit token does not match the pin's latest receipt`
although the head remains 1 and the attempt rolled back.

Distinguish a previous successful receipt from the newer failed attempt.
Resolution needs the attempt's expected parent generation and token, not only
“does this equal latest successful token?” Preserve rejection of unrelated/
obsolete tokens. If that proof needs durable bookkeeping, use at most one
checked most-recent attempt slot per pin alongside its bounded successful
receipt; do not create a lifetime token log or second World publication head.
Specify operational attempt registration/recovery before implementing it.
No-op must remain payload/receipt-write-free.

Test after an earlier success: pre-transaction, during writes, before commit,
after commit, process death/reopen, competing winner, repeat resolve and a later
successful attempt. Each valid attempt resolves to complete old/new/conflict
without duplicated writes/events or guessing. Unknown tokens fail explicitly.

### Additional foundation audit before progression

- verify_all must acquire one consistent read snapshot when called standalone,
  and reuse an already-owned snapshot safely when called by copy. It currently
  performs many selects without establishing its own read transaction.
- Validate checked pin/receipt metadata before it determines reclamation.
  There are at most 64 pins; a corrupt aggregate MIN input cannot silently
  control data deletion.
- Audit real SQLite commit errors/ambiguous acknowledgement, not only a hook
  that runs after a successful commit.
- Align counters with bytes/rows actually touched, including projection checks.
- Preserve format isolation, full checksum/completeness checks, combined
  old-or-new publication, stale rejection and the 100-save retention proof.

P4.1 gate: all regressions above + existing focused storage tests + measured
scaling + one full suite on corrected stable bytes. Record exact source SHA and
completed evidence. Then proceed to section 3; no Astra round trip is required.

## 3. P4 identity architecture: binding decisions and proof-first integration

Use PERSISTENCE_P4.md, PERSISTENCE_P4_REVIEW.md and the P4.2 addendum as context;
these decisions resolve the remaining direction.

### Object identity and placement

Use explicit incarnation identity for persistable mutable objects, scoped to
the store/world. Allocate independently of simulation RNG. Incarnation metadata
is storage/runtime state, never new canonical gameplay data or digest content.
P2C current links remain sharing authority. A versioned occurrence-to-incarnation
map labels the objects that authority describes; validate agreement, do not
create a second incompatible alias graph. Group IDs are derived lookup aids.

Correct the earlier addendum's blanket delete/reinsert rule: **a new Python
object creates a new incarnation; moving or removing/reinserting the same object
preserves its incarnation.** Owner placement/ordinal changes separately.
Replacing an object with an equal-but-distinct object is still replacement.
A retained obsolete object must never be rebound to a new occupant of its key.

Define the encoded incarnation/occurrence schema and pin it with tests before
World integration. Current links, occurrences, ownership, membership, counters
and record values must publish at the same generation. All lookups use its pin.

### Registry, owners and pins

One live mutable instance per incarnation within a session.
Weak registries cannot alone prove correct retention: enumerate every strong
reference from roots, wrappers, global bindings, occurrence indexes, memo maps,
query caches and external aliases. Remove archive-sized eager retention for
migrated families. Remove dead weak entries without global sweeps or id-reuse
races. Account for object/group counts and bytes.

A retained child needs enough live/current ownership information to dirty and
persist its real owner after parent eviction. It must not resurrect obsolete
ownership after replacement/deletion. For the first implementation, it is
permissible to pin that child's complete sharing group while an external child
alias survives; make those pins observable. Correctness precedes finer eviction.
Do not implement refcount thresholds or guess whether an external alias exists.

Implement small standalone identity fixtures first: retained top-level alias;
retained child after parent pressure; parent/child cross-owner sharing; moved
same object; replaced equal object; delete/reinsert same/different object;
group merge/split; failed save; weak cleanup; close/detach. If an old alias has
no remaining canonical owner, preserve accepted detached-alias semantics and
never write it into a replacement owner's slot.

Use B=256 clean groups initially, with dirty/current/external pins separate.
A group may be large; report its size/bytes. Derived caches may hold IDs/weak
handles; supported externally held mutable objects stay valid. No “dead means
immutable” or serialization-copy workaround.

## 4. People pilot, then measured family expansion

Before each implementation slice, write its exact file/API/invariant/test plan
in PERSISTENCE_P4.md (or a narrowly named linked subplan), self-review against
this contract, then implement. This planning does not require another architect
permission request. A genuinely unresolved authority change is a blocker.

1. Add explicit P3B-to-P4 conversion into a new destination and
   open_lazy_world_session. Keep original source, legacy APIs and defaults.
   Declare lazy namespaces; preserve exact non-lazy graph capture.
   Conversion is explicit O(total), checked and atomically no-overwrite.
   Stream cold segments/records; do not fetch all EventLog segments into memory.
2. Make world.people lazy with exact supported mapping behavior, stable
   dictionary order, alive memberships and unsaved overlays. Ensure serializer/
   digest/query helpers recognize the facade without an eager dict(...) fallback.
3. Extend accepted save/lifecycle guards to the new session composition.
   A detected-stale session rejects further mutation/step/save; preserve existing
   edits for explicit detach. Resolve publishes exactly the committed local state.
4. Prove separately generated unbound control vs lazy session through short
   simulation, save, close/reopen, failures and further continuation. Compare
   full digests, IDs/order/years/causes/values/frozen flags, sharing and RNG outcome.
5. Warm current queries and apply cache pressure; test resurrection/reactivation,
   retained aliases, nested direct mutation, owner transfer, old provenance,
   index invalidation and source-preserving conversion.
6. Remeasure fixed A/R/K while H grows 10x. Open loads zero unrequested Person
   payloads; current query decodes only eligible/requested groups; no-op writes
   zero payloads; one local edit has no unrelated-history scan. Measure actual
   SQL work/bytes, registry/pins/caches and peak/retained memory.

After the people gate passes, proceed to high-impact residual families using
the same proven primitives: resources/aspirations and owner queries, materials
and active indexes, wallets/paths/souls, relationships/genealogy and memberships,
then any measured remaining archive-sized metadata. Keep canonical redundant
indexes exact until a tested reconstruction/storage adapter replaces them.

For each family, enumerate all read/write/alias paths, define memberships and
ordering, implement differential/lifecycle/failure tests, measure 10x cold growth,
then proceed. Do not stop for Astra between families. Do not perform unrelated
optimizations or introduce a universal proxy framework without demonstrated need.

Growing mutable lists/sets need explicit adapters. Preserve arbitrary supported
edits, order and duplicates; segment only genuinely append-only data. A lazy
owner whose payload grows without bound remains a reported unresolved cost.
Do not hide it in metadata or call it an active pin merely because the current
implementation retains it.

event_ids may become an exact compact representation only after compatibility
proof for imported/nonconsecutive/directly edited cases, equality/membership/
iteration and canonical encoding. Retain an exact fallback for shapes that do
not satisfy a range invariant; no silent history normalization.

P4 gate: full inventory updated; ordinary open/read/save/resident costs measured
by family including indexes/identity; independent continuation and failure/
lifetime matrix pass; all residual growth explained as genuine active/external
working state or an explicit unresolved blocker. A passing people pilot alone
does not close P4. Run one full suite at the integrated stable-code gate.

## 5. Lifecycle and short integrated release validation

Preserve P3B D/F/N authority: disk [0,D), pending sealed [D,F), live tail [F,N).
Only successful combined publication transfers authority; no duplicate/gap.
New current links/queries/incarnations are in the same transaction as owners,
mutable tail, sealed segments/descriptors, counters and head. Failed save retains
local dirtiness; ambiguous acknowledgement resolves without repeating actions.

Prove old/new subprocess recovery, stale writer, disk/encoding failure,
corruption/missing rows and memberships, backup/relocation, current-head recovery
copy, close/direct store close, failed detach and explicit materializing detach.
Digest/archive/scrub are explicit full operations and stream cold history.
No ordinary open/save/gameplay may trigger a full digest, archive or scrub.

Complete the existing STAGE_0_5_COMPLETION_PLAN.md sections 5–7 within their
authorization. Use short independent controls, affected regressions and one
final full suite on stable product bytes. Separate gameplay timing from digest,
save/open, export and verification. No golden-digest refresh to conceal drift.

Prepare STAGE_0_5_RELEASE_VALIDATION.md with exact final SHA/source equality,
commands, completed job links, evidence matrix, memory/read/write tables,
compatibility, failure outcomes, residual limits and run/artifact requirements.
Do not manufacture late-world evidence from synthetic fixtures.
The old year-2000/year-3010 replay fixtures were lost; logs/digests are not Worlds.

## 6. Execution discipline and stopping conditions

- Preserve existing user work; verify live head at start and before publishing.
- Focused [skip ci] commits on PR #14; no force push or merge.
- Self-review diffs and invariant/test matrix after each slice. Separate
  implementation and review passes; seek an available Sol review pass if useful,
  without consuming Astra by default.
- Fix concrete in-scope failures and continue. Do not weaken tests, skip failing
  integrity paths, change rules or relabel unmet goals.
- Run short tests locally/once. For a long unit-only gate, start once, return
  run ID/next resume step, and let the owner re-prompt. Do not poll repeatedly.
  Re-prompt resumes this assignment, not a new permission cycle.
- Do not run full suites for each tiny fix: batch stable changes and use targeted
  regressions, then one relevant final full suite. No test-only evidence applies
  to later modified product bytes without an appropriate new check.

Stop only for: a reproduced unresolved fundamental correctness/authority
conflict; unavailable capability/access; a running long job awaiting completion;
or the explicit remaining long-horizon/merge authorization boundary.
Give exact evidence and the smallest needed decision. An Astra quota ending
is not itself a reason to stop routine work.

## 7. Final authorization boundary and final report

The owner has NOT lifted the millennium/endurance ban. After architecture and
short validation pass, prepare the precise canonical/late-fixture run plan and
artifact retention instructions, then stop before launching it. Keep 120 seconds
as the existing optimization goal and all correctness/audit failures fatal.
Do not change participation/rank targets or magic balance.

Required final report:
- repaired P4.1 status and all four regressions;
- completed P4 families, true resident/I/O bounds and residual blockers;
- independent continuation, legacy/converted/detached compatibility;
- final source SHA and actual completed tests;
- exact remaining P5 long-horizon evidence and requested run authorization;
- no merge/Stage 1 claim.

If final long-horizon evidence is absent, say **“architecture and short validation
complete; final Stage 0.5 release validation pending.”** Do not label Stage 0.5
fully complete. This handoff authorizes getting all the way to that boundary
without further routine Astra sign-offs.
