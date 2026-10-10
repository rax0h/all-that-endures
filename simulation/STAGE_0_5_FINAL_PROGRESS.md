# Stage 0.5 complete closeout ledger

## Latest checkpoint: checked snapshot-lease primitives; World lease constraint found (October 10 UTC)

Public source `cebc98ca8693fce72dd5d00aed7c73450704b719`, local source
`95e0a261ed5ba65cd2ab4baf5f40ea070074761b`, matching tree
`8cafa4427f2347bf226dff1ef725032da04928b1`. Parent public
`f46b60d61a537a229e9ff21adf83cfdb8e325120`, local
`2978fca9c054592cd5fd749cff992dae79d272d7`, matching tree
`7f7c938bed05750c8557f848dcb2305a675eb257`.
Production remains `c29e3d06a0c9d219235e2b3f0390271bd1245aea`.

Store capture can now clone an existing checked generation pin, including an old
pinned generation, without substituting today's head. A bounded release group
validates every pin/receipt before atomically releasing all tokens and uses one
<=256-row maintenance budget for the entire group. Existing single-pin callers
use the same implementation. Explicit zero-cleanup release lets deferred alias
GC avoid multiplying the next ordinary operation's maintenance work.

HistoryLeasePool is a tested snapshot-lease primitive: weak alias bookkeeping,
one independent token per referenced generation, no SQL in weak callbacks,
deferred checked release, shared-token revival, and atomic close together with
the publisher pin. A hundred aliases share one token. Failed group release
rolls back all tokens so old and current checked reads both remain valid.

**It is deliberately not activated in World.** An integration experiment found
that leaving an unowned child at one old ordinary snapshot correctly triggers
the existing generation-pressure guard on the next publisher advance: an
external pin older than the current head blocks another ordinary commit. A
broad reattachment matrix caught this immediately. The entire experimental
World integration was removed; persistence_lazy.py is identical to the preceding
published checkpoint. Generation-pressure behavior was not weakened to hide the
failure. An explicit regression preserves it and proves release allows progress.

The operational World alias lease must retain only that backing/incarnation,
with durable checked dependencies understood by retirement and row cleanup,
rather than pin every unrelated record at an old whole-store generation. This
is still within the approved backing-lifetime scope, but is a concrete integration
constraint. Blindly advancing an old pin or bypassing the guard does not prove
old private views or safe retirement. Do not claim external alias lease or
retired backing cleanup complete. Current compatibility backing is not reclaimed
on owner retirement; retained overlays still work through the accepted path.

Final store/World affected gate: **83 passed in47.08s**, exit0, with pipefail,
`stage_0_5_final_history_lease_affected_gate.txt`: snapshot/atomic release cases,
store, store failures, counted households and exceptional event IDs. Supporting
retention/reattachment/native graph selection: **56 passed,69 deselected in10.78s**,
`stage_0_5_final_history_lease_store_gate.txt`. Five final primitive cases passed
in0.21s, `stage_0_5_final_history_lease_primitive_gate.txt`. Counts overlap.
Fixture API mistakes were corrected before the valid RED (missing source-pin
clone argument). No full applicable suite or new P5/endurance run; the preceding
strict-cache integrated P5 remains evidence at its own source boundary.

Continue backing-specific operational leases/retirement, compact identity header
coverage, complete checked World catalog/touched journals, recursive/type/equality
closure, explicit capability-6 copy upgrade and final integrated acceptance.
Exotic event-key and exact pressure costs remain disclosed/open as above.
Stage0.5 is not complete; do not emit capability6 or promote PR14.

## Latest checkpoint: clean caps throughout run/step lifetimes (October 10 UTC)

Public source `e92d107b8d5227ee9b9e2eeefc1196cd179a9229`, local source
`4b1b68d8ec1839578016505c24c7c166481d15e8`, matching tree
`0f786f6aff6cd163261479c256b87337516bf7e9`. Parent public
`92c20279987f3d3e05b685f880a85234140692af`, local
`f95b11eb0e5c76542f9d148542f94b2505162f2f`, matching tree
`6acc05e0f3516735b5b35f4f0bfac685c6f7d245`.
Production remains `c29e3d06a0c9d219235e2b3f0390271bd1245aea`.

The common record-table clean eviction path now enforces256 headers per family
inside simulation steps and between years in a run, alongside the shared32MiB
byte cap. It no longer treats the complete step working set as exempt clean
residency. Dirty owners and externally held aliases remain actual working state,
separate from clean cache accounting. Eviction drops payload/presence/incarnation/
ordinal/label sidecars while preserving live registry identity. A retained alias
rehydrates the same object, routes the edit and saves successfully. Query-cache
admission also caps entries before returning, with bounded step-touched metadata;
query bytes remain charged to the shared record budget.

RED: all four people, skill, lineage-node and native graph cases exceeded the
clean cap at257 inside a step. An older regression intentionally expected400
clean headers retained across years and zero misses on a400-owner sweep. That
expectation conflicts with the approved final architecture; it now verifies256
resident headers remain warm and other requested current owners rehydrate under
the same cap. A new query stress test initially selected an unsupported people
index and was corrected to the accepted alive-query API. No gameplay or schema
semantics changed; a current working set larger than256 may incur more reads.

Final affected gate: **79 passed in50.25s**, exit0, with shell pipefail,
`stage_0_5_final_step_cache_caps_gate.txt`. Includes new cap cases, shared byte
budgets, tiny-cache retained aliases/recovery, people, scalar families, concrete
bindings and pressure. The added1000-query admission case passed in0.21s,
`stage_0_5_final_step_cache_caps_query_gate.txt`; the revised run regression also
passed independently in0.71s, `stage_0_5_final_step_cache_caps_run_gate.txt`.
Counts overlap. Earlier gate78passed/1failed was the superseded400-header test,
not a passing final certificate. No full applicable suite or endurance run.

Fresh final-runtime P5 `--native-graph-buckets` passed seed843000,3+4+3,
year10,439 events and expected digest
`3301d4e4a6a2f415679cabe62754813440034cf4c190035c79ba82cc7b8e378e`;
`stage_0_5_final_step_cache_caps_p5.json` includes independent eager control,
relocation, reopen and portable sharing-preserving detach.
Paired H1k/H10k metrics in `stage_0_5_final_step_cache_caps_metrics.json` have
verified runtime hashes. Eight live people, one retained alias, one scalar edit
are fixed; explicit construction and deliberate archive sweep are excluded from
point timing. During both sweeps: maximum256 clean headers and step-touched keys,
256 payload/presence/incarnation sidecars and zero ordinal sidecars.
Sidecar Python bytes238322/238578, shared charged bytes600065/600321; accounting
metadata121676 bytes at both sizes. Retained-alias point edit:8 payload reads,
3 writes,220 metadata rows and3 maintenance removals at both sizes. This is
record-cache closure evidence, not certification of all global identity/eager
metadata or independent external history leases.

Continue checked World catalog/touched journals, complete recursive/type/equality
history closure, external alias leases and retired backing cleanup, explicit
capability-6 copy upgrade, then stable integrated bounds, one full applicable
suite and final independent architectural review. Exotic event keys still retain
the disclosed legacy O(H) compatibility path. Exact O(H) pressure cold-miss owner
release decision remains open. Stage0.5 is not complete.

## Latest checkpoint: candidate exceptional event-ID paging (October 10 UTC)

Public source `12034323043bf3b36ea897d4941a372e8f3ba89a`, local source
`4e7c5b1d573b696bb0e39fbbc5add2078c620d65`, matching tree
`d04c0d667db88800fab49821d99bd976874a68ae`. Parent public
`f27c0903cae5e938ed0b25ef6dc541ccd6c3727f`, local
`3e6dfc2` (full ID in local history), matching tree
`2a7f61f8454afdc07664a058cd270d5ed8ee0f0d`.
Production remains `c29e3d06a0c9d219235e2b3f0390271bd1245aea`.

The explicit native-graph candidate lane now enters range-plus-paged-exceptions
without materializing the positive-integer prefix. Sorted removed integer IDs
use the existing counted sequence; exact additional representatives use the
existing typed set. The descriptor, internal backing, EventLog and aliases
publish in the sole hybrid transaction. Internal children use the sole registry
allocator and existing frozen-plan acknowledgement/abort path, not another
current-link relation or publisher. Reopen checks child descriptor presence and
parent/child counts. Popping past a long removed suffix uses binary value-rank
search in the counted tree, rather than walking all holes.

Removing integer1 then adding True or1.0 retains that native representative.
Signed zero, set comparisons, failed-input behavior and explicit whole-set
operations retain the facade contract. Wallet and scalar-record set aliases,
including Institution.members, retain the same EventIdSet facade across save,
reopen and portable detach. Root collection replacement remains the accepted
P2B guarded operation; tests were corrected to preserve this contract rather
than introducing unsupported root replacement. Retiring a wallet does not
resurrect it through a later event-ID edit. Ordinary participant evidence errors
now identify their namespace, making corrupt successor failures actionable.

**Equality closure still has a disclosed compatibility exception.** NaNs (also
inside tuples/frozensets) and opaque unsupported Python keys retain native exact
resident authority, including distinct NaN representatives and partial mutation
semantics. The existing typed equality-key primitive cannot encode these as a
unique exact paged set. Point entry into this compatibility path can still cost
O(H); it is not a capability-6 acceptance claim. Unsupported hash/equality probes
retain native results via explicit comparison of additional exceptions. Explicit
whole-set operations/materializing export remain O(H). Legacy opens do not
silently convert member rows. Complete equality-directory admission and history
lease/backing reclamation remain part of closeout, not silently waived.

RED evidence: middle deletion visited1000/10000 prefix members; exceptional
reopen initially used logical size as ordinary row count; pop traversed removed
suffix; affected compatibility checks found a set-field routing type error and
an uninformative earlier participant failure. These are corrected. Corruption
regressions remove a child descriptor and install a checksum-valid contradictory
child count; both fail open before adopting incomplete state.

Affected graph/household/identity/event gate before the final exotic-key
compatibility extension: **156 passed in72.63s**, exit0,
`stage_0_5_final_event_id_exceptions_gate.txt`. Final runtime focused/affected
facade, compact IDs, new exceptions, World participants and abort gate:
**111 passed in39.78s**, exit0,
`stage_0_5_final_event_id_exceptions_compat_gate.txt`. Two added integrity cases
passed in0.31s on the same runtime;
`stage_0_5_final_event_id_exceptions_integrity_gate.txt`. Counts overlap.
A first gate invocation named a nonexistent test file, collected no tests, and
was corrected; it is not evidence of a passing gate. No full suite/endurance.

Fresh final-runtime P5 `--native-graph-buckets` passed seed843000,3+4+3,
year10,439 events and expected digest
`3301d4e4a6a2f415679cabe62754813440034cf4c190035c79ba82cc7b8e378e`;
`stage_0_5_final_event_id_exceptions_p5.json`. Eager control, relocation, reopen
and one-memo detach are included. Paired H1k/H10k metrics in
`stage_0_5_final_event_id_exceptions_metrics.json` have verified source hashes:
fixed two aliases and one edit; explicit O(H) construction excluded.
Middle deletion20 payload reads/11 total writes/7 nested writes;
outlier addition15/6/2; representative replacement(two point edits)29/13/9.
All counts identical at both sizes; zero facade member visits, maximum combined
nested payload1288 bytes. These bounds apply to the paged admissible lane only.

Continue global clean-cache caps and metadata closure, checked World catalog and
touched journals, recursive/type/equality closure, external leases/retired backing
and explicit capability-6 copy upgrade, then stable integrated H gates, one full
applicable suite and final independent architecture review. Exact O(H) pressure
cold-miss owner release decision remains open. Stage0.5 is not complete.

## Latest checkpoint: native graph bucket histories (October 10 UTC)

Public source `d09aa2a71f66436d3e5aaa63869c8633680cf50a`, local source
`009a3af1ae765b6eebcb0612f198889bd9a2c643`, matching tree
`bde43af3471d5ed80500c6c007dc0580cf6bb380`. Parent public
`a51ecf8622423f3f721b68b25877bb6ea253c795`, local
`6ed11256cb2bca675bd7b8b2a37837b7e2b6dbf7`, tree
`5cf92346292fbd47c1a09c64923bc3f8b2a64df6`.
Production remains `c29e3d06a0c9d219235e2b3f0390271bd1245aea`.

Explicit `native_graph_buckets=True` conversion integrates genealogy children,
lineage children, social adjacency, resource owner buckets, material lot buckets
and active-lot buckets with typed history references. It implies counted
households. It is still a capability-5 candidate, not the full capability-6
upgrade. Defaults and genuine legacy authorities remain separate/readable.
Community membership already has scalar `(person, community)` rows and a person
index, rather than a resident historical set bucket.

One scalar wallet edit reads/writes no history pages. One bucket append or set
addition writes exactly one bounded page or entry. Alias mutation uses current
owner type guards, including complete prevalidation of constrained batches.
Retiring the typed owner releases its constraint on a remaining wallet alias.
Unowned overlays survive unrelated saves and later reattachment without restoring
deleted owners. Rollback uses explicit resolve before retry. Counted histories
selected during conversion can also be shared with resource/skill fields,
genealogy and eager Settlement memory; detach retains one shared native object.
The social-adjacency route type accepts typed sets, and P5 mode selection now
normalizes the mutually exclusive household readers.

Affected gate: **174 passed in67.94s**, exit0,
`stage_0_5_final_graph_buckets_gate.txt`. After the final route-type fix and six
additional eager-memory alias cases: **35 passed in27.02s**, exit0,
`stage_0_5_final_graph_buckets_alias_gate.txt`. Counts overlap.
P5 `--native-graph-buckets` passed seed843000,3+4+3, year10,439 events and
`3301d4e4a6a2f415679cabe62754813440034cf4c190035c79ba82cc7b8e378e`.
`stage_0_5_final_graph_buckets_p5.json` predates only the final route-type
allowance/CLI household-mode normalization, which the focused alias gate covers;
it is supporting evidence, not a full final-source certification.

Paired H1k/H10k metrics in `stage_0_5_final_graph_buckets_metrics.json` have
verified current runtime hashes. Each fixture holds one historical bucket, two
sharing placements and one edit; explicit construction/verification is excluded.
All six families: scalar11 payload reads/3 writes, addition11 reads/4 writes,
exactly one history payload write. Header sizes28/29 bytes. Largest page write
1482 bytes, largest set-entry write81 bytes. Ordinary maintenance removals<=4.
These local bounds do not establish checked catalog open/global coordination or
all Python metadata bounds. No full suite, Actions/endurance run or promotion.

Remaining alias closure includes bounded type-admission proofs for already paged
histories and live attachment between append-page/count-tree list backings; the
cold conversion sharing test is not proof of all live transitions. Continue with
exceptional IDs, complete checked World routing/touched journals, recursive
mutable closure, external leases/retired backing, global caps and explicit
capability-6 copy upgrade, then integrated gates and final independent review.
The exact O(H) pressure cold-miss release decision remains open.

## Latest checkpoint: counted World household histories and exact pressure (October 10 UTC)

Public implementation `57e2625a79d26c770142d94ebe93261c1f97043a`;
local implementation `6e025cdd257cc9c0bf73cd4553993adaae5fd197`;
matching tree `8155c2dd94c85f8d192228ef8adce7a817de26e5`.
Parent public `70738836b7cf53ab7367867c3f65477b621a840d` / local
`e0b63eb8ea910246e3472d1dfb1da5e018fb2a5d`, matching tree
`fc33d19121c5b8484946add3b48103d7e937209e`.
Production remains `c29e3d06a0c9d219235e2b3f0390271bd1245aea`.

The explicit counted conversion lane (`counted_households=True`) now creates
lazy Household headers with checked alive/settlement projections and counted
members references. Settlement.households uses the same counted tree while
Settlement headers remain in the accepted eager tracker. Existing paged/eager
legacy modes remain readable and the converter default is unchanged. This is
an integrated candidate lane, not a complete capability-6 copy upgrade; no
capability-6 feature marker is emitted while the mandatory catalog, exceptional
IDs, recursive history and lease authorities remain unfinished.

Scalar household edits load no member nodes. Ordered edits use local tree paths,
stable occurrences and checked membership projections. Living selection queries
only current candidates and returns their original occurrence order, including
duplicates. Settlement lists retain extinct households, duplicate occurrences,
native first-equal removal and replacement order. New household/settlement fields
normalize before exposure; shared new lists, wallet aliases, retained unowned
sequences and portable detach reuse the sole registry and sharing memo.
Deletion of an unloaded household reads identity placements, not member pages.
Retired backing reclamation and external leases are still outstanding.

World open now composes counted sequence reads with its already checked snapshot;
it neither starts a second SQLite transaction nor rolls back the caller's outer
read. Sequence rollback follows the existing explicit resolve protocol and only
thaws a frozen child after checked proof that the central token did not publish.
A central preparation failure before commit gets the same unpublished-token
proof, retaining all dirty tree edits. Lost acknowledgement blocks further reads
and edits until resolve_save publishes the exact frozen plan once.

Pressure keeps one native ordered sum over all household occurrences. On a cold
miss it reads checked preparedness headers directly, consulting dirty/canonical
objects first, without loading those households' members descriptors or nodes.
Cache witnesses include the membership incarnation/revision, a conservative
household writer revision, length and generation. Scalar assignment, household
replacement/deletion, membership edits/replacement and save/recovery invalidate
the result. The scalar cache has both entry and byte caps. Household clean caches
keep their 256-header cap inside simulation steps; historical pressure reads do
not become an H-sized retained hot set. Other-family hot-cache closure remains
part of the remaining global budget work.

REDs retained: missing counted converter argument; nested snapshot failure on
open; central preparation left sequences permanently frozen. The first scalar
test was corrected to distinguish the necessary descriptor read from forbidden
member-node reads. Rollback tests use the established required resolve_save
before editing, rather than bypassing recovery.

Final focused/affected gate on this runtime: `pytest -q --tb=short` on
final_household_sequences, final_pressure, final_pressure_arithmetic,
final_event_histories, final_history_reattachment, final_owner_binders,
final_runtime_families, final_sequence_compat, final_sequence_errors and
final_sequence_numeric_index: **112 passed in33.40s**, exit0.
Retained `stage_0_5_final_counted_households_gate.txt`. A prior affected legacy
household/store/lifecycle/scalar gate passed136 in108.82s before the final
checked-pressure reader/preparation-release extension; this is supporting
compatibility evidence, not another final-source certificate. Counts overlap.
No full suite, Actions/endurance run, production promotion or Stage1 work.

Fresh final-runtime independent P5 using
`python simulation/persistence_p5_validation.py --counted-households --output <report>`
passed seed843000,3+4+3, year10,439 events and digest
`3301d4e4a6a2f415679cabe62754813440034cf4c190035c79ba82cc7b8e378e`.
Retained `stage_0_5_final_counted_households_p5.json`; includes eager control,
save/reopen, relocation and one-memo materializing detach. Forced hazard tests
compare exact float.hex preparedness/severity and unchanged RNG calls in both
the accepted legacy and counted lanes, through edits/replacement/reopen.

Reproducible paired metrics:
`python simulation/measure_stage_0_5_counted_households.py --output <report>`;
retained `stage_0_5_final_counted_households_metrics.json`, verified source hashes.
H1k/H10k separate long-history and many-owner fixtures hold eight live people,
two sharing placements and one edit. Explicit O(H) construction is excluded.
Open:38 payload reads in all four fixtures, zero resident household headers.
No-op:3 descriptor/control reads, zero writes (not zero global-link work).
Scalar:9 reads and3 writes in every fixture; zero member-node reads.
Long-history insert:135/91 total writes, at most256 moved locators; many-owner
insert:9 writes at both sizes. All ordinary maintenance removed <=256 rows.
Pressure cold visits every occurrence: many-owner reads1016/10164 and measured
0.1773/1.8270 seconds; pressure hits read0 payloads. Only the two already loaded
headers remain resident after the stream. Timings are observations, not SLAs.
This does not certify ordinary checked-catalog open or all Python metadata costs.

**Continue the whole assignment:** integrate the remaining nested graph buckets
and exceptional event-ID authorities; activate complete checked-catalog World
routing and touched journals; finish recursive closure, leases/retired backing,
global budgets and explicit capability-6 upgrade; then stable integrated H gates,
one final applicable suite and final independent architectural review. The exact
O(H) pressure cold-miss owner release decision remains open while coding proceeds.

## Latest checkpoint: retain unpublished history overlays and publish on reattachment (October 10 UTC)

Public implementation `3ee303f90ad5cf2bc72b0fd749f2f2555a47a1a2`;
local implementation `85a29d44bb46566460e826136b6ddf5ee092e4c4`;
matching tree `676d838c2117d53ee0afce8db124824bf0c41ea6`.
Continues the native-history implementation below, from public
`007052d404ad7c2a4a06c5f5af1f2968f80ca74b` / local `6f50d8144b022e14dc9d5e1c4f8dc1820eccf0eb`,
matching tree `3748a67f9c2ea3bf64c15bea5795b3ba95abd8a6`.
Live production branch remained `c29e3d06a0c9d219235e2b3f0390271bd1245aea`.

The native-field lifetime check found a real data-loss bug. After deleting every
owner, a retained typed list/set/map could hold private edits. A later unrelated
save acknowledged every live proxy, clearing those unpublished edits or making
its cached baseline claim nonexistent pages. Reattaching without the unrelated
save also omitted its private overlay from the central publication. New histories
assigned and removed before their first publication could lose their entire
initial value. These were not successful acknowledgements of history data.

A constant-state has_pending_overlay helper now inspects dirty state/counters
without reading pages or freezing a sequence. Native binding, currency placement
reconciliation and eager identity reconciliation journal a canonical same-session
history's retained overlay. Unknown/cross-session histories reject instead of
receiving a new identity for an old backing incarnation. History byte capture now
runs after all family placement reconciliation: an edit inside an existing wallet
can attach a private history during that family's preparation, and its pages must
join that same frozen hybrid plan. No additional publisher or identity registry.

Acknowledgement derives the published history incarnations from the exact frozen
version changes. Published histories and clean proxies accept the new pin normally.
Unpublished dirty proxies advance their existing lease and clear clean cache entries,
retaining their original backing baseline, new-state flag and private dirty values.
Reattachment publishes those values and the owner placement together. Removed
placements stay removed; the retained history keeps its original incarnation.
This closes the tested active-session private-overlay cases, not the remaining
independent external-lease/retired-tree reclamation requirement.

RED:9 initial list/set/map cases failed (missing reattachment writes, discarded
private values and absent pages for new unpublished histories). Extending destinations
to eager and wallet owners exposed12 more failures; placing the alias inside an
existing wallet exposed6 additional capture-order failures. All remain regressions.
The lost-ack fixture's function boundary was corrected before final validation;
no production validation was changed for a fixture error.

Final focused new regression command: `pytest -q --tb=short
simulation/tests/test_stage_0_5_final_history_reattachment.py`:
**36 passed in8.03s**, exit0,
`stage_0_5_final_history_reattachment_focused_gate.txt`. Matrix covers list/set/map;
private edits with/without an unrelated save; native, new/replaced eager and wallet
owners, edits inside existing eager/wallet owners; new never-published histories;
lost acknowledgement, mutation/read guards and repeated resolve_save.

Final runtime affected command (PYTHONPATH=.:simulation,
ownership-gate-venv/bin/python): `pytest -q --tb=short` on
final_history_reattachment, final_event_histories, final_soul_collections,
final_skill_histories, final_soul_transformations, persistence_lazy_nested_history,
persistence_lazy_nested_maps_sets, persistence_lazy_currency, persistence_lifecycle,
final_owner_binders, final_runtime_families and stage_0_5_unloaded_alias_routing:
**167 passed in35.47s**, exit0,
`stage_0_5_final_history_reattachment_gate.txt`. A preliminary affected run including
the counted-sequence primitive passed128 in111.05s before the final destination
queue/capture-order extension; it is not final-source counted World integration
evidence and is not retained as a final gate. Counts overlap; do not sum. No full
suite or endurance launch. `git diff --check` passed.

Fresh final-runtime independent P5 passed seed843000,3+4+3 years, final year10,
439 exact events and expected digest
`3301d4e4a6a2f415679cabe62754813440034cf4c190035c79ba82cc7b8e378e`.
Command: `python simulation/persistence_p5_validation.py --output <report>`;
retained `stage_0_5_final_history_reattachment_p5.json` includes independent eager
control, save/reopen, relocation and portable detach. It does not certify ordinary
checked-catalog open or final release/endurance acceptance.

Repeated paired measurements on this exact runtime source using
`python simulation/measure_stage_0_5_native_histories.py --output <report>`;
retained `stage_0_5_final_history_reattachment_metrics.json`. Source SHA-256s were
verified against the files. All20 rows retain the preceding field-level bounds:
H1k/H10k, two placements/two owners, one edit; scalar history loads/writes0/0;
list addition1 page read/write, soul set/map addition0 payload reads/1 entry write;
headers394/489/394/430/430 bytes respectively. Construction, timings, real store
counters and cache/residency weights are explicit. This does not measure all
external-alias/private-overlay residency, global catalog discovery or pressure.

Bounded self-review checked ownership admission, descriptor-only dirty counters,
byte capture after placement reconciliation, acknowledgement of actually published
incarnations, lease advancement, retained baseline/new flags, no resurrection,
same-incarnation reattachment and receipt replay. Independent final architectural
review remains outstanding.

Ruling: preserve unpublished overlays through unrelated acknowledgement and collect
them after concrete owner reconciliation — prevents a valid commit from erasing
data that it never wrote — cost if wrong: untested lifecycle/retirement cases must
remain rejected or receive a valid separate backing lease before reclamation ships.

The fast native-history batch and this discovered data-loss repair are saved.
Stage0.5 remains in progress; capability6 is not emitted. The remaining work list
in the preceding checkpoint still controls: checked ordinary World catalog/routing
and journals; lazy Household/counting sequences and Settlement.households;
remaining bucket/recursive closure; exceptional EventIdSet; exact pressure,
external leases and retired backing cleanup; complete source-copy upgrade;
final integrated tests/metrics/full suite, independent review and release artifacts.
No production promotion, checkpoint-default change or new endurance run.

## Latest checkpoint: native event histories, soul collections and concrete owner callbacks (October 10 UTC)

Public implementation `e28a5c5273116a9215e2321e30ec6ab6f9a013dd`;
local implementation `1500b112555cd83a1826cdb4d6c453a98e2f789b`;
matching tree `b01e7f8d0098ab5f3171d08838dece002eadb3ac`.
Recovered clean public `4979b34b663be7487163fbc218d286fc96f0402b` /
local `13febff99da82e2a577b5b88e870fe9053dedd31`, matching tree
`328321b182917711df23f37caa46de8a2c30a495`. Live production PR14 branch
was still `c29e3d06a0c9d219235e2b3f0390271bd1245aea`; no production change,
Actions launch, whole-suite claim, capability6 emission or endurance run.

Six additional fields now preserve compact typed backing in ordinary adapters:
Relationship.shared_history, MagicResource.transfers, MaterialLot.transfers,
SoulState.authorities, SoulState.marks and SoulState.cosmic_links. Reused the
existing typed primitives, sole registry, shared cache and frozen hybrid
publisher. Scalar serialization/acknowledgement retains references, avoiding
list/set/map materialization. Portable detach uses the existing shared memo;
resource, lot and relationship detach now explicitly replaces typed lists.
New Soul assignment preserves a supplied shared authorities/marks set using
one local replacement memo. Genuine resident legacy representations do not
migrate on open or no-op save. Soul mutable map values reject during the
existing cold-conversion preflight before destination staging; the previously
conservative skill/soul recursive-import boundary remains in force.

Integer event-ID mutation validation now follows the current typed-list owners,
including unloaded resource/lot/social peers reached through wallet/skill
aliases. Bool, float and other non-int additions reject. Extend/iadd validates
the entire incoming batch before changing these histories, retaining the
legacy adapter's atomic invalid-input behavior. A retired integer owner removes
its constraint from a surviving native skill alias. Generic unqualified typed
lists retain native partial-extend behavior. Invalid slice input validates
before reading the existing history. No values are dropped or coerced.

A genuine legacy shared event-list fixture exposed a pre-existing notification
bug: only its last attached owner became dirty. Legacy LazyTrackedList guards
and notifications now route through the sole registry, marking every current
resource/lot/social owner and any supported eager placements. This uses a weak
session reference so replacing one placement cannot disable remaining routes;
retained old placements are not resurrected. The fixture intentionally tests
the legacy resource/lot/social adapter intersection, not the separately
unfinished arbitrary legacy skill/currency compound-alias closure.

RuntimeFamilyBindings now supplies concrete load_owner, resolve_path,
install_path, mark_dirty and compact encode_placement callbacks. Existing
ordinary live routing uses its loading/path callbacks; the retained indexed
record shortcut remains. Installation bypasses user notifications, preserves
lazy IndexedRecord callbacks, restricts events to the mutable tail, and restores
eager bindings without expanding typed history children. Tuple paths rebuild
their immutable parent while preserving siblings and native index errors.
The catalog/coordinator can consume these callbacks, but ordinary checked
catalog activation and complete owner journals remain **unfinished**. No claim
that global identity-link discovery has been removed follows from this work.

RED evidence:13 event-history tests failed at compact-reference/adapter and
cross-family validation boundaries;4 soul collection tests failed at resident
types/shared assignment;4 initial concrete callback tests failed because the
callbacks were absent. Later legacy append/reopen failed and remains a
regression. A soul metrics fixture was corrected to read entry_loads for the
set/map primitives, not list page_loads. Existing adapter type assertions now
name the compact proxies. Soul point-read bound is max5 payloads (one header
plus four checked child descriptors), additionally asserting zero history
payload loads in all four fields; its scalar write budget remains max3.

Final runtime focused/affected command (PYTHONPATH=.:simulation,
ownership-gate-venv/bin/python): `pytest -q --tb=short` on final_contracts,
final_owner_binders, final_runtime_families, final_event_histories,
final_soul_collections, final_skill_histories, final_soul_transformations,
persistence_lazy_resources, persistence_lazy_materials, persistence_lazy_social,
persistence_lazy_souls, persistence_lazy_nested_history and
persistence_lazy_nested_maps_sets, `-k 'not scale_metrics'`:
**131 passed in66.90s**, exit0, `stage_0_5_final_native_history_gate.txt`.
The filter did not deselect tests in this set. Unused legacy-type imports were
subsequently removed from one test module; runtime source was stable.
Additional routing/alias gate: owner_binders, runtime_families,
stage_0_5_unloaded_alias_routing, final_skill_histories,
final_soul_collections and final_event_histories: **74 passed in15.14s**, exit0,
`stage_0_5_final_owner_binder_gate.txt` (before the final tuple index-error
cleanup, which the131 gate covers). Focused new histories: **23 passed in9.13s**,
`stage_0_5_final_native_history_focused_gate.txt`. Counts overlap; do not sum.
`git diff --check` passed. This is not the final full simulation suite.

Reproducible paired measurements: `python
simulation/measure_stage_0_5_native_histories.py --output <report>`;
exact report `stage_0_5_final_native_history_metrics.json` contains source
SHA-256s verified against this runtime source, actual store counters/cache
weights/residency, bytes and timings. H1k/H10k hold one edit and exactly two
sharing placements in two concrete owners fixed. Explicit fixture construction
is reported separately as O(H).

| Field | Scalar history reads/writes, H1k and H10k | One addition reads/writes, both H | Header bytes, both H |
|---|---|---|---|
| Resource transfers | 0/0 | 1 page /1 page | 394 |
| Material lot transfers | 0/0 | 1 page /1 page | 489 |
| Relationship shared history | 0/0 | 1 page /1 page | 394 |
| Soul marks | 0/0 | 0 payload /1 indexed entry | 430 |
| Soul cosmic links | 0/0 | 0 payload /1 indexed entry | 430 |

Tail bytes differ with tail-page occupancy, not full history length. Maintenance
removed2–4 rows in these operations. These measurements do not certify ordinary
checked-catalog open, many historical owners, exceptional EventIdSet, household
sequences, pressure, recursive imports or all external-alias/lifetime bounds.

Fresh final-runtime independent P5: `python
simulation/persistence_p5_validation.py --output <report>` passed seed843000,
3+4+3 years, final year10,439 exact events, expected digest
`3301d4e4a6a2f415679cabe62754813440034cf4c190035c79ba82cc7b8e378e`.
Retained `stage_0_5_final_native_history_p5.json`, including checked save/reopen,
relocation and portable detach against independent eager authority. Its normal
open still reads resident World/identity state; it is not an ordinary-open
archive-bound certificate. No long restore fixture or final endurance evidence
is implied. Bounded task self-review covered validation/retirement, compact
references, sharing, descriptor reads, legacy notifications, detach memo and
failure/recovery; final independent architecture review remains outstanding.

Ruling: reuse existing typed backing for these six native fields and the existing
registry for legacy notification repair; supply concrete owner callbacks without
claiming checked World activation — preserves values, identity and event-ID
validation while isolating the remaining catalog transition — cost if wrong:
callback/install cases outside the tested native closure must reject or be
extended before capability6 migration/release.

Implementation remains in progress. Next: wire these concrete callbacks to
ordinary checked-catalog routing and complete replacement/deletion journals;
integrate lazy Household headers and counted members/Settlement.households;
close residual buckets and recursive histories; page exceptional EventIdSet;
implement exact pressure/revisions and lifetime/retired-tree reclamation;
complete capability6 source-copy upgrade; final integrated H/fault/P5/full-suite,
independent review and release artifacts. Pressure release decision, final
endurance/restore policy and production promotion keep their explicit gates.

## Latest checkpoint: scalar skill and soul transformation pages (October 10 UTC / October 9 Chicago)

Public implementation `7d964c0fcd6440840e205ec4c75bda404d5a2385`;
local implementation `67d1f0d3dc784b9a3e56c3da7c19084086bd8dc8`;
matching tree `dfc1195a3a7d70b338d073c6c3cc71ce80aae550`.
Recovered the clean isolated worktree from local `dc879862` / public
`17108e09`, matching baseline tree `93fd95b39f8f17964efdc8f7182a453ee0154598`.
No production PR14 change, Actions run, full suite or endurance launch.

The ordinary skill adapter now preserves compact teachers/provenance references
instead of materializing their pages during scalar save or acknowledgement.
The soul adapter does the same for transformations. Explicit cold conversion
constructs existing typed list authority and propagates each reference to all
persisted sharing placements. Load/mutation uses the existing sole registry,
typed-list callbacks, shared history cache and central hybrid publisher.
New skill assignment uses one local replacement memo, preserving shared
teachers/provenance instead of splitting a single supplied list. Whole-list
replacement retires the old placement; surviving skill/soul/eager/wallet aliases
remain the same object. Materializing detach uses the existing sharing memo.
No new backend, identity relation, receipt or event authority was introduced.

RED evidence: eight initial paging/alias/detach tests failed; four soul/skill
cross-family cases rejected a compact history as the wrong live list type;
new assignment split a shared list into distinct wrappers. All retained as
regressions. Failed-publication fixtures were corrected to call resolve_save
before reading/retrying an uncertain attempted commit, preserving the existing
receipt protocol; the corruption fixture now commits its direct SQL tamper
before requesting a checked read. Production integrity checks were not weakened.

An unrestricted compound cold import exposed a pre-existing incomplete binding
boundary: a legacy skill with a mutable descendant has extra identity labels
that its closed adapter cannot bind. The attempted legacy conversion fallback
was rejected. Conversion now raises StoreFormatError before destination staging
for mutable descendants in these newly paged fields; the source SHA-256 stays
identical and no destination is published. New compound assignments retain the
existing resident compatibility path and preserve their values across reopen.
This is not recursive mutable-history closure or a guarantee about arbitrary
nested mutable aliases. Existing genuine legacy scalar lists remain readable,
open performs no migration and a no-op save does not upgrade their representation.

Ruling: compact the supported immutable schema-value histories using the existing
primitive; reject unsupported compound cold conversion before publication,
retain genuine legacy reading/assignment behavior and leave recursive closure
explicitly unfinished — prevents publishing an unbindable destination without
broadening the closed serializer — cost if wrong: a future recursive adapter
must extend this conservative conversion boundary before release.

Fresh final focused command (PYTHONPATH=.:simulation, ownership-gate-venv/bin/python):
`pytest -q --tb=short` on final_contracts, final_skill_histories,
final_soul_transformations, persistence_lazy_skills and final_runtime_families:
**40 passed in 3.08s**, exit0, `stage_0_5_final_skill_soul_gate.txt`.
Existing soul command on persistence_lazy_souls: **14 passed in 14.86s**, exit0.
Its point-read budget now names both the compact header and checked descriptor
(max2 payloads), additionally requiring zero transformation page loads; scalar
save write budget remains max3. The previous one-whole-record assertion is
incompatible with splitting the child authority, not an H-dependent regression.

Final-source affected command on persistence_lazy_nested_history,
persistence_lazy_nested_maps_sets, persistence_lazy_currency,
persistence_lifecycle, stage_0_5_unloaded_alias_routing,
final_identity_headers and final_world_budget, with
`-k 'not identity_header_comparison_never_reads_sequence_history'`:
**78 passed,2 deselected in23.61s**, exit0,
`stage_0_5_final_skill_soul_affected_short_gate.txt`.
An earlier broader run before the final unsupported-import rejection passed
**80 in83.65s**; its log is retained separately and is not final-source
certification of those two larger header-history cases. Counts overlap; do not
sum them. `git diff --check` passed. No full-suite acceptance claim.

Paired H1k/H10k measurements in `stage_0_5_final_skill_soul_metrics.json` hold
one edit and the same three placements in two concrete owners fixed:

| Operation | H1k page loads / writes | H10k page loads / writes | Header bytes, both scales |
|---|---|---|---|
| Skill scalar | 0 / 0 | 0 / 0 | skill260, soul377 |
| Soul scalar | 0 / 0 | 0 / 0 | skill260, soul377 |
| Shared append | 1 / 1 | 1 / 1 | skill260, soul377 |

Append page bytes are1482/267 because the last page occupies different offsets,
not proportional to full history. Report includes actual store counters and
shared-cache weights, separately from these field-level page bounds. These
fixtures do not certify ordinary checked-catalog World open, households,
recursive imports, pressure or global alias-discovery bounds.

Fresh independent P5 on this runtime source passed: seed843000,3+4+3 years,
year10,439 exact events, expected final digest
`3301d4e4a6a2f415679cabe62754813440034cf4c190035c79ba82cc7b8e378e`.
Command: `python simulation/persistence_p5_validation.py --output <scratch-report>`;
retained exact report `stage_0_5_final_skill_soul_p5.json`. It also checks
save/reopen, relocation and portable detach against independent eager authority.
No long restore fixture retention or final endurance acceptance is implied.
A previous P5 before the final invalid-input guard also passed; only the final
report is used for this checkpoint. Metadata-only field-policy inventory edits
were subsequently covered by the focused contract gate.

Bounded task self-review checked reference/label agreement, typed versus legacy
binding, preflight/acknowledgement guards, sharing, cache ownership, source-copy
failure and portable detach. This is not independent final architectural review.
Implementation remains in progress; capability6 is still not emitted. Remaining:
ordinary checked owner binders/coordinator activation and touched journals;
lazy Household headers/counting sequences; resource/lot/relationship histories,
soul maps/sets and recursive mutable closure; exceptional EventIdSet paging;
exact pressure/cache/lifetime/retired-tree closure; complete capability6 source-copy
upgrade; final-source integrated H/fault/P5/full-suite/review and release artifacts.
Next fast boundaries are concrete checked owner binders and residual typed-history
adapters, preserving validation of integer event-ID lists where currently enforced.
Pressure exception, independent acceptance, endurance and production promotion
retain their existing explicit release gates.


Spec: STAGE_0_5_FINAL_ARCHITECTURE.md. Execution: STAGE_0_5_SOL_61_EXECUTION.md.

## Latest checkpoint: central checked-catalog composition (October 10 UTC / October 9 Chicago)

Local source `20ce624750755193495ffea5b869b6770859f7ff`; public
`db3cb7fbc62a6451b38bba34cc8794f28ddf0f51`; matching tree
`95939ec6018fd5c63f7c2c10d7e19b4e9df69921`.
Isolated branch; no production promotion or Actions run.

The existing frozen hybrid publisher optionally composes an explicit checked
IdentityCoordinator. It captures owner payloads from detached family bytes,
requires exactly the coordinator placement overlay (no missing/extra/duplicate
rows), requires every touched owner header, and appends catalog version writes
to the same central commit. It never duplicates family placement writes or
publishes legacy ordinary P2C links alongside checked catalog authority.
The coordinator participant validates the relational catalog and joins the
central successor proof before exact, idempotent live acknowledgement.
Unrelated auxiliary writes freeze even an empty coordinator delta, perform no
owner/group discovery and advance its lease only after acknowledgement.

Frozen replay now captures the commit token and target generation as well as
payload/control bytes; replacing a private replay frame cannot change them.
World failed-plan reset checks the existing pin/attempt/receipt protocol before
discarding its pending plan. Corrupt failure evidence keeps recovery-required
state and dirty owners. No new journal or publication authority was added.

RED:8 missing-composition cases; actual World token/generation replay mismatch;
then empty-delta mutation was not blocked and missing touched-owner payload was
accepted. Retained as regressions. A corruption fixture initially left the
attempt pending (correctly already retained) and used the wrong checksum helper
signature; corrected to a resolved-not-committed attempt then checksum damage.
An auxiliary fixture initially omitted its new namespace from head inventory;
corrected the fixture without relaxing production validation.

Affected gate (PYTHONPATH=.:simulation, ownership-gate-venv/bin/python):
`pytest -q --tb=short` on final_catalog_publication, final_world_participants,
final_identity_coordinator, final_participant_abort, final_owner_replacement,
and persistence_lazy_store_failures, `-k 'not process_death'`:
**70 passed,3 deselected in12.22s**, exit0.
Compatibility gate on persistence_lazy_people, persistence_lifecycle,
persistence_cold_save_failures: **74 passed in31.98s**, exit0, including its
three subprocess writer-death cases. A second concurrently started gate with
`-k 'not subprocess_writer_death'` passed71,deselected3 in27.71s; counts overlap
and it adds no separate acceptance claim. These durable gate logs are committed.
Earlier direct-store process-death run without a final summary remains
uncertified; the complete cold-session crash gate does not silently certify it.
`git diff --check` passed. No final full suite or fresh integrated P5 launched.

This closes central composition, not ordinary checked World activation.
Capability6 is still not emitted; default World sessions retain genuine legacy
compatibility. Remaining work: concrete checked owner binders and touched
journals/open integration; lazy Household headers and counted settlement/member
sequences; residual nested-history and exceptional EventIdSet closure; exact
pressure streaming/cache/measurement, strict shared lifetime budgets and retired
tree cleanup; complete source-copy upgrade/feature markers; final-source fault,
H1k/H10k,P5/full-suite/review and retrievable restore artifacts. Pressure cold
latency exception still needs owner resolution for release. Implementation is
in progress; candidate validation and production acceptance remain outstanding.

## Verified starting boundary

Live repair ref a6f1b55a30b259c03e9e895a1df18ca0caf8b9b9, tree 5db9482a5685d6342691e1bcde123057a2212c04.
Planning ref 2d8072e462697a4486c1cf260af10bc26c7cd82a, tree 3ba6debbfc795b0cdb9a20a6f82faa66e4082c13, direct parent a6f1b55.
Implementation branch sol/stage-0-5-complete-closeout; isolated worktree /workspace/scratch/c3a830e86cea/stage-0-5-closeout.
PR14 verified open/draft/unmerged, head c29e3d06a0c9d219235e2b3f0390271bd1245aea. No modifications authorized or made.

Local earlier checkout bf5261b is behind the live baseline. Inspected delta: 19 files / 1044 additions / 23 deletions; preserves four household gates and checked owner-scoped index, living consumers and tail deletion. Source begins from the complete planning commit. Earlier uncommitted identity proposal/regression remain untouched in ownership-repair, outside this implementation tree; they are superseded by the approved counted-tree/catalog design, not silently integrated.

Capability 6 is unallocated at baseline (supported floors 3/4/5). Do not advertise 6 until all mandatory new authorities are complete.

## Preflight shared interfaces

| Producer → consumer | Contract and ruling |
|---|---|
| 1 → 2,4,5,6 | Static concrete adapters classify all root collections, including eager owners. Immutable participant deltas encode inputs before commit. Existing central commit remains the only publisher. |
| 2 → 3,4,5 | One registry; catalog proves complete pinned groups and exact owner membership. Coordinator overlays replacement/deletion before routing. History references preserve incarnations. |
| 3 → 4 | Stable occurrence IDs separate from rank and physical slot. Counted tree supersedes older sparse-vacancy proposal; duplicates/order remain exact. |
| 4,5 → 6 | Compact children expose shared cache accounting and retirement leases. Header/projection revisions govern pressure invalidation; native sum preserved. |
| 1–6 → 7 | Final full suite is deferred until stable integrated source. One final fresh architectural review; ordinary failures repaired inline. |

## Package 1: contracts and baseline inventory

RED: four new contract tests failed because the family/participant module did not exist. Fixture corrections during GREEN: use module-qualified names for the two Institution classes; supply required expected_record_schema to read_version. These were test-fixture mistakes, not production defects.
GREEN: PYTHONPATH=.:simulation /workspace/scratch/c3a830e86cea/ownership-gate-venv/bin/python -m pytest -q --tb=short simulation/tests/test_stage_0_5_final_contracts.py simulation/tests/test_persistence_lazy_identity_reverse.py simulation/tests/test_persistence_lazy_store.py simulation/tests/test_persistence_lazy_store_failures.py — 68 passed in 5.51s.

Added static family declarations and exhaustive field classification (future fields fail coverage), immutable byte-backed ParticipantDelta / SaveParticipant interface, and actual store-I/O measurement deltas. SQL rows examined are explicitly unknown; query plans/scale measurements remain separate evidence. No storage format change or claim of participant integration yet. Inventory lists pending compact representations and unrestricted import costs honestly; exact writer/bound evidence is refined with each integration package.

Next: permanent missing reverse-occurrence regression and checked catalog, then affected-group coordinator. Packages 2–7 remain incomplete. No final suite, final review or endurance launched.

## Identity foundation checkpoint (October 9, 2026)

Contracts published as bc14d8011a58cd4e02c8c0313441ac149bc1c237, exact tree c0293da984147a2f80cee09ddbe145b68d5d3631; matches local f7bae3265dd94e2b4ddc74568c24357e7bd537ab. Isolated closeout branch, no repair/planning/production ref overwrite.

Added checked MVCC catalog APIs, mandatory descriptor/group/owner/retirement witnesses, canonical versioned P2C projections, and a compressed authenticated owner radix directory. The directory proves exact requested paths without enumerating the other identities in a large owner. Preparation updates affected directory paths/groups and freezes bytes using ParticipantDelta. Added composable checked read snapshots so catalog reads share one head/pin-consistent transaction.

Added coordinator callbacks using the existing sole LazyIdentityRegistry. Complete persisted group discovery precedes mutation; explicit replacement/deletion overlays override persisted placements. No live_bindings inventory. Clean discovery is bounded by 4096 occurrences, 2 MiB estimated Python metadata, and 256 entries; dirty group costs are reported separately. These are independent primitives, NOT yet ordinary World open/save integration.

Observed RED: nine catalog tests before catalog APIs; three affected-path/no-op/large-owner tests before preparation; five coordinator tests before coordinator implementation. Meaningful subsequent REDs: stale intermediate routes after repeated replacement/cancellation; a deleted forward placement incorrectly treated as a new path; a later incompatible peer allowed an earlier copy to be installed before rejection. All repaired and retained as regressions. Fixture corrections: use a explicitly registered dataclass instead of an unsupported arbitrary dict subclass; use matching payload values for genuinely shared roots; use the registry's actual object_for_incarnation API. No broad serializer allowance was added.

Final foundation gate: PYTHONPATH=.:simulation /workspace/scratch/c3a830e86cea/ownership-gate-venv/bin/python -m pytest -q --tb=short simulation/tests/test_stage_0_5_final_identity_coordinator.py simulation/tests/test_stage_0_5_final_identity_catalog.py simulation/tests/test_stage_0_5_final_contracts.py simulation/tests/test_persistence_lazy_identity_reverse.py simulation/tests/test_persistence_lazy_store.py simulation/tests/test_persistence_lazy_store_failures.py — **92 passed in 23.75s**.

Existing-runtime compatibility gate: same interpreter/environment, test_persistence_lazy_identity.py, test_persistence_lazy_currency.py, test_stage_0_5_unloaded_alias_routing.py, test_persistence_lifecycle.py, test_stage_0_5_paged_household_world.py, test_stage_0_5_household_scoped_index.py — **73 passed in 48.54s**. These gates have different scopes; neither certifies complete Stage 0.5.

Measured standalone group routing at H1k/H10k: constructor 2 compact payloads / 309–311 bytes; route 9 compact/peer payload reads / 1562–1564 bytes, 48 metadata rows, one indexed query row; two owners loaded and dirtied; preparation 4 compact payload reads / 931–933 bytes; two owner-witness changes, zero unchanged P2C writes, 704 projected payload bytes including both owner copies. Estimated retained requested-group metadata 1019 bytes / 2 occurrences. SQL examined rows remain unknown; reverse EXPLAIN coverage is a separate permanent assertion. Machine-readable measurements distinguish preparation from actual commit counters. This synthetic primitive gate includes no EventLog session markers and is not an integrated World measurement.

Still required before Package 2 completion: full World converter/open/binders/save/ack/detach routing integration; eager owner/version commitments; safe checked retired-ID directory and reclaiming zero-placement headers after retention permits; large-group spill/stream handling; complete cross-family fault/recovery matrix and catalog full scrub. Current primitive keeps explicit zero-placement headers and a checked empty retirement-directory marker; no bounded churn reclamation claim. Capability 6 is NOT emitted, and no ordinary open builds missing authority. Counted sequence work may proceed behind its interface, then integration closes these gaps.

Next action: counted order-tree primitive and checked occurrence projections, with local edit/split/merge differential regressions; then household/settlement and catalog/coordinator runtime integration. Existing source/checkpoints and old compatibility mode remain intact. Final suite/review/endurance have not started.

## Counted sequence checkpoint (October 9, 2026)

Added `persistence_lazy_sequence.py`: counted B+ main tree (leaf128/fanout32),
stable MVCC node/occurrence IDs, checked reciprocal parents and occurrence
locators, per-value relative-order AVL trees and an authenticated compressed
membership-root directory. Ordinary rank edits rebalance local paths. Explicit
conversion and bulk edits may visit affected history. Streaming holds a bounded
leaf and depth stack and follows native list iterator ranks after a mutation.
The central store commit remains the sole publisher; immutable prepared bytes
and dirty state survive failed/lost acknowledgements and clear only on exact
checked acknowledgement. Clean payloads and sidecars share a 64-entry/8MiB
budget; dirty journal costs and tracemalloc observations are separate.

RED: 18 initial tests failed with the missing module. Two later permanent REDs
exposed silent repair of corrupted moved locators and child-parent projections.
Both now validate affected projections before overwriting them. Fixture
corrections: a no-op still performs its required pin check (archive counters
remain unchanged); the store requires a new attempt token after a resolved
non-commit, even when retrying identical frozen participant bytes.

Checked primitive gate: same interpreter/environment as earlier gates,
`pytest -q --tb=short simulation/tests/test_stage_0_5_final_sequence.py` —
**31 passed in 86.44s**. Combined affected gate: that file plus final identity
coordinator/catalog/contracts, lazy identity reverse, store and store failures
— **123 passed in 115.40s**. Subsequently added separate SIGKILL tests during
version writes, before commit and after commit — **3 passed in 1.08s**; old or
fully new authority was recovered and fully scrubbed. These scopes overlap;
this is not the final integrated simulation suite.

Implementation blob: `775c61b58bb75bac1d508509adb46a3aef71c487`.
Expanded test blob: `9e79cbef3ec84204ef90799734de7aee891b1ad8`.
Harness blob: `5ce6fa8ba3a354e0af8fd8e1a18a76c61938c016`.
Measurement blob: `e0e375f1c1030ca1340f5686b97749f3d5e80a03`.
The code blob is identical across the combined gate, death tests and final
measurement run. Later changes to these primitives require new evidence.

Reproducible command:
`PYTHONPATH=.:simulation /workspace/scratch/c3a830e86cea/ownership-gate-venv/bin/python simulation/measure_stage_0_5_sequence.py --output simulation/stage_0_5_final_sequence_metrics.json`.
Explicit conversion is excluded; eight candidate values and one edit are fixed.
The long duplicate history is a separate fixture. These are sequence-only
measurements, not an integrated World/identity/event bound.

| Ordinary operation | H1k payload reads / bytes | H10k payload reads / bytes | H1k / H10k main-node writes | H1k / H10k total version changes |
| --- | ---: | ---: | ---: | ---: |
| Midpoint insert | 152 / 92,001 | 180 / 110,606 | 2 / 3 | 134 / 90 |
| Midpoint delete | 148 / 86,882 | 177 / 104,074 | 2 / 3 | 132 / 89 |
| First-equal remove, duplicate history | 169 / 36,591 | 213 / 64,181 | 2 / 3 | 139 / 146 |
| Eight candidate lookups | 36 / 47,670 | 41 / 92,655 | 0 / 0 | 0 / 0 |

Insert commit payload writes/bytes: 134/46,105 at H1k and 90/51,602 at H10k.
Delete commit payload writes/bytes: 129/45,365 and 85/51,706 (retirements account
for the difference from total version changes). First removal: 137/13,250 and
144/17,306. Midpoint physical slots differ; bounded locator movement is 126/81
for insertion, 125/80 for deletion, not a suffix rewrite. Formula gate checks
main writes <=3L+3, locators <=256 and total changes <400.

Cold full streaming is explicitly O(H): 18 payloads/42,525 bytes at H1k and
166/436,383 at H10k. Its measured tracemalloc peak is 147,228/505,616 bytes.
Insert dirty estimated bytes are 217,695/210,173; tracemalloc peak
417,066/437,284. Recursive residency estimates are conservative and are not
process RSS. The JSON contains all preparation/commit/query/metadata/cache
counters. EXPLAIN reports indexed namespace/key/version lookup; actual SQL
rows examined remain unknown. Churn with future bounded cleanup still needs a
separate query-plan/scan gate; returned rows do not prove that bound.

Still pending: typed references and numeric/import compatibility for settlement
lists, household headers/selectors, catalog/coordinator integration, retirement
leases/reclamation, shared cross-family budgets and the full integration matrix.
The primitive currently preserves the existing positive-integer household
element guard; it is not yet a replacement for unrestricted settlement lists.
Capability6 is still not emitted. No production ref changed, final review or
endurance started. Continue through the integration packages, not a green-test
stop or routine Astra implementation request.

## Eager-owner commitment checkpoint (October 9, 2026)

Sequence checkpoint published as `479bd4f467312f03353083bf8f278feca51df116`,
tree `e8640726601e9e043ea52e9dbe9d949c638ad337`; matches local implementation
commit `41b0490c4ac61d4a309808d479e5919424e725cb`. Production PR14 still has
`c29e3d06a0c9d219235e2b3f0390271bd1245aea`.

Catalog preparation now accepts concrete ordinary family writes alongside MVCC
owner writes. Current ordinary source checksum/schema/revision must match its
versioned witness; old-pin ordinary identity metadata comes only from that
witness. This does not recover overwritten ordinary payloads. World adapters
must use their captured eager objects, not today's rows, for historical data.
No shadow ordinary payload authority or second registry was added.

Permanent RED: scalar-only acknowledgement accepted a different source body
because it checked the frozen witness but did not validate the owner/source
agreement. Acknowledgement now validates every changed owner witness, including
scalar-only plans. Another RED showed a missing body plus missing owner witness
could hide surviving placements for a new path. An indexed owner-existence
probe now rejects this; it does not enumerate all paths in that owner.

Tests cover pinned eager scalar changes/deletion, wrong acknowledged ordinary
body, missing mandatory witness, cross-lazy/eager mutable-child routing with the
sole registry and one hybrid acknowledgement. The proposed in-place authority
move was a fixture outside the approved source-copy upgrade design: it is now a
permanent rejection/atomic-source-preservation test. Duplicate/competing owner
source plans are rejected. Destination bootstrap remains explicit future work.

Affected gate: final catalog/coordinator/contracts, lazy identity reverse,
store and store failures — **100 passed in 26.44s** with the same interpreter
and `PYTHONPATH=.:simulation`. Log: `final-eager-identity-affected.log`. Existing
identity foundation metrics remain historical evidence on their recorded
earlier source; this acknowledgement closure requires fresh integrated metrics.

Next: typed sequence/reference and settlement equality/import compatibility;
catalog retirement ranges/large-group handling; runtime family callbacks and
frozen participant integration; lazy household headers and settlement fields.
Do not emit capability6 until complete authority/feature markers and explicit
checked copy upgrade are ready. Final P5/full suite/review remain pending.

## Sequence compatibility checkpoint (October 9, 2026)

Eager-owner checkpoint published as `5681038d8a7cb63ed84a9681d762ea4cde5e73cf`,
tree `ebca0eee46a82ed8d40bae725f8947f1dcc24933`; matches local
`f8ae0d0f295947ecf81ecc30bcf56eb3453406d7`.

Added an explicit native immutable-value mode to the counted sequence. Its
versioned descriptor preserves the mode; the original positive integer-ID
descriptor and element guard remain compatible. Integer membership indexes
include equal bool/float representatives while leaves retain their actual
types. Unsupported indexed probes use the native equality compatibility path.
Assignments between equal values of different types preserve the newly assigned
representative. Compact HistoryReference('sequence', incarnation), codec/frozen
snapshot handling, memoized portable materialization and frozen-plan save
acceptance are now available as integration interfaces.

RED: five focused compatibility tests initially failed on the missing value-mode
argument. Verified focused GREEN: **5 passed in 5.08s**. A previous redirected
invocation produced an empty log and was not treated as evidence; the foreground
rerun above is the verified result.

Affected exact-source gate:
`PYTHONPATH=.:simulation /workspace/scratch/c3a830e86cea/ownership-gate-venv/bin/python -m pytest -q --tb=short simulation/tests/test_stage_0_5_final_sequence.py simulation/tests/test_stage_0_5_final_sequence_compat.py simulation/tests/test_persistence_lazy_nested_history.py simulation/tests/test_persistence_lazy_cold_scalar_families.py simulation/tests/test_persistence_event_log.py simulation/tests/test_persistence_lifecycle.py`
— **99 passed in 147.91s**. This includes the three sequence subprocess-death
tests. Counts overlap earlier gates and are not final integrated acceptance.
Implementation source was unchanged throughout this gate.

Pending: World runtime sequence binders and owner callbacks, capability6 feature
markers and source-copy upgrade, household/settlement integration, and shared
cache/lifetime budgets. This checkpoint does not replace live household or
settlement fields. Native mode supports immutable schema values; it does not
claim closure over arbitrary mutable imported list elements or external NaN
identity after eviction. Those cases require explicit compatibility proof in
the integrated inventory. Earlier sequence measurements describe their recorded
source; the updated implementation needs new integrated measurements.

Next action: checked retirement ranges/large-group handling and runtime
catalog/coordinator/sequence participant integration. Final independent P5,
stable full simulation suite and architectural review remain pending. PR14 has
not changed, and no new endurance run or production promotion was started.

## Checked retirement checkpoint (October 9, 2026)

Sequence compatibility published as `bdd99adf973615d60e37896873555cea3a345a78`,
tree `2d13baf4858d9a478ecae0e42babfc98eb67f683`; matches local
`fb27a9d932be82046e2dcc4da72fc5c035035ab3`.

Added authenticated MVCC coalesced retired-ID ranges with local AVL edits,
subtree interval/ID counts, ordering/boundary commitments and a bounded clean
cache (64 entries AND 2MiB). The catalog v2 descriptor commits this mandatory
directory and the live-header/retired-ID inventory. Missing group headers are
accepted only with a checked range proof and zero current placements/links.
Retirement selection uses the existing checked current-query index, a pin-safe
retirement generation and explicit protected backing leases supplied by callers.
Plans contain <=256 version changes; source-copy upgrade/runtime lease wiring
and the shared physical maintenance budget remain pending.

Revival removes that same ID from its range and restores its group header in
the existing hybrid transaction. No ID is reused for another object by this
directory. Legacy catalog v1 remains readable/writable in compatibility mode;
it cannot enter retirement mode implicitly. Capability6 is still not emitted.

RED: missing range module and retirement preparation (7 failures initially).
Further permanent REDs: warmed payload corruption escaped full scrub; initial
directory construction could overwrite existing authority; allocator-only
reservations received no mandatory headers. Full scrub now bypasses clean
caches, initial construction rejects existing authority, and reservations
publish empty checked headers eligible for later retirement. Cancelling a
replacement does not cancel the consumed incarnation IDs. Cancellation tests
now require those exact reserved IDs, no placements/ordinary writes and no
rewrites of existing owners/groups. The standalone catalog no-op checks two
compact pin/allocator metadata rows; no archive payload/query/write work. The
coordinator true-no-op fast path retains its stricter zero-archive behavior.

Fixture corrections: retirement preparation, rather than a third-generation
commit, is checked while a generation1 pin is retained; the existing two-pin
generation-pressure contract is preserved. The scale-edit target initially
named an already-present ID; it now names an absent ID and asserts actual node
writes and membership after reopen. The measurement harness initially omitted
world_identity_links from its head inventory; checked full verification rejected
it, and the harness now supplies the required inventory.

Final affected gate on unchanged implementation:
`PYTHONPATH=.:simulation /workspace/scratch/c3a830e86cea/ownership-gate-venv/bin/python -m pytest -q --tb=short simulation/tests/test_stage_0_5_final_retired_identity.py simulation/tests/test_stage_0_5_final_identity_catalog.py simulation/tests/test_stage_0_5_final_identity_coordinator.py simulation/tests/test_stage_0_5_final_contracts.py simulation/tests/test_persistence_lazy_identity_reverse.py simulation/tests/test_persistence_lazy_store.py simulation/tests/test_persistence_lazy_store_failures.py`
— **118 passed in 37.54s**. Includes 18 new retirement tests, legacy/no-hidden
upgrade, protected IDs, old pins/revival, missing/corrupt authority, 600-ID churn
and three subprocess SIGKILL points. Counts overlap earlier gates.

Reproduce metrics with the same environment/interpreter and
`simulation/measure_stage_0_5_retired_identity.py --output simulation/stage_0_5_final_retired_identity_metrics.json`.
Source SHA256 values are embedded in that JSON. Explicit conversion is excluded.

| One interval edit | H1k | H10k |
| --- | ---: | ---: |
| Payload reads / bytes | 20 / 7,488 | 26 / 10,206 |
| Node changes | 10 | 13 |
| Total version changes | 11 | 14 |

An additional permanent RED caught shallow dirty-memory accounting that omitted
the journal's retained node objects. Recursive reporting now includes those
objects and baseline bytes: 13,942 / 18,921 estimated dirty bytes at H1k/H10k;
separate tracemalloc peaks are 26,531 / 28,098 bytes. Metrics were rerun on the
corrected implementation, matching the final gate above.

600 reserved unplaced IDs are reclaimed in three plans: 251/251/98 headers,
256/256/103 total version changes, leaving one interval/node and zero group
headers. Indexed selection is evidenced separately; actual SQL rows examined
remain unknown. These are standalone metadata fixtures, not World bounds.
The same metrics explicitly expose the old store's drain-loop work: commit
maintenance_rows 1518/1524/610 counts selection plus deletion. This does NOT
satisfy <=256 physical eligible-row removals per ordinary operation. Closing
that shared budget and proving point lookups against a cleanup backlog is the
next dependency of safe bounded retirement; do not conceal the old counters.

Next: bounded store maintenance and backlog-safe indexed reads, then large-group
stream/spill and World catalog/coordinator/frozen participant integration.
Household/settlement and nested-history integration, final P5/full suite/review,
release pressure decision and production acceptance remain outstanding.

## Bounded maintenance checkpoint (October 9, 2026)

Retirement published as `e48a41616b1059b6d4ff1f3ef30b3f4c7fd6bb4c`, tree
`62ad988962b2faa876cc69ad95d9ac84debc91ea`; matches local
`fbdbc1918bfaf75d4afa9ebf279b4434549362b2` (two coherent local commits).

Replaced the six drain loops with one shared <=256 physical eligible-row
removal budget. Selection uses each table's expiry index; ordinary commit and
pin release invoke it once. Explicit maintenance(row_budget=0..256) performs
one checked transaction with bounded reclamation, preserving head, live pins
and operational receipts. There is no hidden drain. Diagnostics now report
maintenance_removed_rows separately from inspected/deleted-row work.

Full verification reports expired_rows_pending_maintenance instead of rejecting
a legitimate backlog. Its existing all-row checksum/structural verification
remains active, including expired payloads, as a permanent corruption test
confirms. Precommit maintenance failure rolls back the rows and leaves receipts
resolvable. Fixed one-record churn drains a prior bulk backlog incrementally;
old pins retain payload/identity authority and prevent premature removal.

Added interval-leading indexes for key/owner/group/allocator/query point reads
on newly created stores and explicit copy upgrades. Reads seek current or
not-yet-expired intervals instead of walking all old versions to find a second
visible row. Overlap detection remains checked. Open only inspects index layout;
genuine legacy layouts stay unchanged and use their documented compatibility
query path. Final capability6 must require these indexes; it is not emitted yet.

Permanent REDs: pin release removed 2,002 eligible rows in one operation;
record lookup executed 7,025/70,025 SQLite instructions with H1k/H10k expired
versions; limited-query membership proof still scanned old rows; owner-witness
source probe took 7,180 instructions at H1k. Further measurement found ordinary
publication's SELECT DISTINCT namespace walked namespace history even with no
ordinary changes. Its H10k regression failed at 31,567 instructions with cleanup
suspended. Ordinary publication now checks only affected namespace declarations
by indexed existence probes and still rejects historical authority switches.
Fixture reinsertion flags now apply only after initial insertion, preserving the
store's existing reinsertion contract.

Affected gate (same interpreter and PYTHONPATH as above): maintenance,
retirement, final catalog/coordinator/contracts, lazy identity reverse, store and
store failures — **128 passed in 54.50s**. The subsequently added fixed-work churn
test passed separately (**1 passed in 0.43s**) on identical implementation.
Final focused maintenance gate, including that churn test:
`simulation/tests/test_stage_0_5_final_maintenance.py` — **11 passed in 13.06s**.
Existing World compatibility gate: lazy identity/currency, unloaded alias
routing, lifecycle, paged household World and household scoped index —
**73 passed in 55.20s** after the final namespace fix. Earlier sequence plus
World gate was **112 passed in 162.44s** before that fix; it is scoped historical
evidence, not the final integrated suite. Counts overlap and are not summed.

Reproduce store metrics:
`PYTHONPATH=.:simulation /workspace/scratch/c3a830e86cea/ownership-gate-venv/bin/python simulation/measure_stage_0_5_maintenance.py --output simulation/stage_0_5_final_maintenance_metrics.json`.
Fixture construction suspends cleanup only to create valid checksummed expired
versions. Real bounded cleanup is restored for measured ordinary publication.
Source hashes are embedded; final implementation stayed unchanged throughout
these gates and measurements.

| Measured operation | SQLite instructions H1k | H10k |
| --- | ---: | ---: |
| Checked record read | 120 | 120 |
| Order / namespace / allocator point | 39 / 36 / 32 | 39 / 36 / 32 |
| Exact identity occurrence | 43 | 43 |
| Reverse group / owner | 260 / 159 | 260 / 159 |
| Limited query with checked witness | 288 | 288 |
| Scalar commit including 256 removals | 19,005 | 19,005 |

Both ordinary commits removed exactly 256 rows; each explicit maintenance call
removed 64. Commit payload writes are one scalar, 14/15 bytes. Separate observed
tracemalloc peaks are 12,987/15,668 bytes; instrumented commit durations
0.0166/0.0112s are observations, not a latency guarantee. Remaining expired rows
5,742/59,742 are reported rather than hidden. VM instructions are distinct from
returned rows and actual SQL rows examined (still unknown). This is a store
backlog fixture, not integrated World or pressure acceptance. Prior retirement
JSON retains its source-pinned pre-budget counters as historical evidence.

Next: shared cache/lifetime budget integration, large-group stream/spill and
World catalog/coordinator/frozen participant integration. Retired backing-tree
leases/GC remain separate unfinished work. Household/settlement integration,
nested closure, exact pressure path, migration, independent P5/full suite/review
and production acceptance are still outstanding. No production ref changed.

## Shared history cache checkpoint (October 9, 2026)

Workspace execution recovered. Verified local implementation `66c550b`, tree
`2e462db3c35ea39ffb6bf2eafa3897dddf6ae651`, with only the six uncommitted
budget tests retained from the interruption; the attempted budget module had
not been written. Public implementation remains `d2081e8`; documentation-only
recovery commit `0744fac13adbd3cd378e629ae64a19919e0163ce`, tree
`182ce85e40bf66097143d7e0b13b764a5da95cfa`, is preserved in this local tree.
No implementation was silently overwritten or reset. See the recovery document
for the precise earlier interruption; it is historical, not the current state.

Implemented a shared clean LRU with simultaneous entry and byte limits,
weak owners (including unhashable proxies), owner-local eviction/forget/release,
and bounded teardown. Eviction never changes logical ownership, dirty state,
registry placements or persisted authority. Collected owners lose payload and
weak metadata; replacing an entry changes its charge without evicting the new
value. Oversized pages are returned without clean retention. Payload/sidecar
weights and recursively estimated manager metadata are separately reported;
these are not claimed as process RSS.

Counted sequences accept the manager and release it on clean-to-dirty transfer,
rollback, exact acknowledgement and clean pin advance. Typed lists/maps/sets
and compatibility household member pages share one session manager, capped at
64 entries AND 8 MiB. Existing smaller per-list four-page bounds remain.
Session close and portable materialization release the bounded clean inventory
without a registry walk. Dirty pages/baselines and detached aliases have separate
Python residency diagnostics. New tests cover cross-family World histories,
clean sidecar teardown, oversized page rejection, external proxy collection,
dirty survival and acknowledgement. Counted-sequence World ownership integration
is still pending; this change does not emit capability6 or upgrade any store.

RED evidence: six missing-module failures on resume (0.15s); typed list/map/set
and household constructors rejected cache_budget; World lacked the shared
manager and household sharing. A permanent additional RED found cancelled
typed-list edits retaining every touched dirty page/baseline after returning to
original bytes. Preparation now drops cancelled journals and unpublished empty
pages, preserving exact numeric representatives and real changed/deleted pages.

Commands use `PYTHONPATH=.:simulation` and
`/workspace/scratch/c3a830e86cea/ownership-gate-venv/bin/python -m pytest -q`.
Final source affected gate:
`simulation/tests/test_stage_0_5_final_budget.py simulation/tests/test_stage_0_5_final_world_budget.py simulation/tests/test_stage_0_5_household_sequence.py simulation/tests/test_stage_0_5_household_tail_delete.py simulation/tests/test_stage_0_5_paged_household_world.py simulation/tests/test_persistence_lazy_typed_property_histories.py simulation/tests/test_persistence_lazy_typed_institution_divinity.py simulation/tests/test_persistence_lazy_nested_history.py simulation/tests/test_persistence_lazy_nested_maps_sets.py`
— **99 passed in 84.69s**.
Sequence/lifecycle/alias/scoped-index gate:
`simulation/tests/test_stage_0_5_final_sequence.py simulation/tests/test_stage_0_5_final_sequence_compat.py simulation/tests/test_persistence_lifecycle.py simulation/tests/test_stage_0_5_unloaded_alias_routing.py simulation/tests/test_stage_0_5_household_scoped_index.py`
— **77 passed in 103.99s**. Both ran on unchanged implementation source;
counts overlap other gates. Earlier 87-test gate preceded the final household
and cancelled-journal changes and is not substituted for these final gates.
One initial command named a nonexistent advancement test file and collected no
tests; it was corrected before the actual gates. No failures are concealed.
Staged whitespace checking subsequently found trailing blank lines in two new
files; these were removed, the source-hashed measurements regenerated, and the
final focused budget/World gate passed **13 tests in 9.19s**. No behavior changed.

Reproduce metrics:
`PYTHONPATH=.:simulation /workspace/scratch/c3a830e86cea/ownership-gate-venv/bin/python simulation/measure_stage_0_5_history_budget.py --output simulation/stage_0_5_final_history_budget_metrics.json`.
Explicit construction/traversal is O(H), not ordinary-open acceptance. Long
fixtures use two histories; many-owner fixtures retain at most eight external
proxies. Source SHA-256, real checked read/commit counters, old-pin assertion,
dirty residency and cleanup results are embedded. SQL rows examined remain
unknown; returned counters are not presented as proof of absence of SQL scans.

| Fixture H1k / H10k | Peak clean entries | Clean weighted bytes | Traced Python peak bytes | Actual edit payload writes / bytes |
| --- | ---: | ---: | ---: | ---: |
| Two long histories | 8 / 8 | 37,504 / 34,336 | 83,802 / 91,311 | 1 / 1; 1,802 / 1,929 |
| Many owners, eight external aliases | 8 / 8 | 3,584 / 3,584 | 36,625 / 36,626 | 1 / 1; 108 / 108 |

World regression additionally traverses 39 independent Property/Infrastructure/
Household histories and verifies their combined 64-entry limit and release on
close. Component fixture clean weights stay bounded as H grows; this is not a
claim about all World caches, overall process RSS, or pressure latency.

Next: large identity-group streaming/spill, World catalog/coordinator/frozen
participant integration and household/settlement counted-sequence headers.
Shared 32-MiB record budget, lifetime leases, retired backing-tree reclamation,
nested closure/exceptional EventIdSet, exact pressure and migration remain.
Independent P5, stable final full suite and architectural review are not run.
Stage 0.5 is neither implementation complete, candidate validated nor accepted.

## 2026-10-09 checked identity membership streaming/spill

Resumed at public `14b278ca667c6ab468e338e5c833909bda16488f`, local
`f8789fec8c90639f083473ad1a80885f4a5b7fa8`, exact matching tree
`e8359f9c0b4e14b35ad05c61f3958b79b4c687c5`. PR14 remains untouched.

Checked reverse and link-projection iterators now close captured snapshots on
normal completion, explicit close and validation failure. Catalog readers
stream complete count/digest, owner/radix and exact occurrence proofs before
returning a group. Oversized captured membership, digest sorting and links use
private immutable checked SQLite spill buffers, whose checksums and captured
order/count seals reject later damage. These files are replay storage only;
the pinned catalog remains authority and the existing registry remains the
sole live-object identity registry. Small groups preserve native tuple results.

Coordinator membership overlays now replay captured placements and indexed
final additions without building an additional resident G-sized membership
dictionary. Output owners and actual unsaved peer installations remain G work;
dirty witnesses and external group references are separately retained. Each
spill database has a declared 128-KiB native SQLite page-cache limit, reported
separately from estimated Python residency. This is not an overall RSS bound.
Catalog publication preparation still builds affected dirty deltas; this change
does not claim that all large-group save preparation is bounded in memory.

Focused final source gate (unchanged implementation during run):
`PYTHONPATH=.:simulation /workspace/scratch/c3a830e86cea/ownership-gate-venv/bin/python -m pytest -q simulation/tests/test_stage_0_5_final_identity_spill.py simulation/tests/test_stage_0_5_final_identity_catalog.py simulation/tests/test_stage_0_5_final_identity_coordinator.py simulation/tests/test_stage_0_5_final_retired_identity.py simulation/tests/test_stage_0_5_final_maintenance.py simulation/tests/test_persistence_lazy_store_failures.py simulation/tests/test_persistence_lazy_identity_reverse.py`
— **110 passed in 64.27s**. Counts overlap earlier gates. Permanent regressions
cover missing occurrences, missing projection rows, recomputed spill row
checksums, partial-read snapshot closure, old pins and current reanchoring,
replacement filtering, exact representatives and final-reference file cleanup.
Initial missing-module/iterator/budget tests were RED. Two test-fixture errors
(list weak-reference eligibility and an unsupported list subclass) were repaired
using the existing registered Box record; registry/codec checks were preserved.

Next: integrate immutable family participants into the World hybrid save and
recovery path, then catalog/coordinator and household/settlement headers.
Capability6 is not emitted. Integrated H1k/H10k evidence, P5, final full suite,
independent architecture acceptance and production decisions remain pending.

## 2026-10-09 immutable World hybrid participants and receipt recovery

Continued from public `148b25a455da3198eecffb636bda35ae972f9cb0`, local
`0e689502107f77d68107aae2ac381771b8474104`, matching tree
`0858f6f23cf7b07b0f15155ed44168f4eb558663`. This checkpoint integrates
`persistence_lazy_participants.py` into actual World preparation, the existing
single store commit, checked acknowledgement and `resolve_save`.

Each changed namespace has a concrete participant holding immutable source
bytes. Prepared values and commit arguments are fresh detached decodes;
publication and retries replay those bytes, including eager writes, ordinary
query memberships, identity deltas, nested/auxiliary writes, event segments,
head metadata, layouts, allocator and reader floor. An explicit source-field
inventory rejects future omitted save fields. Namespace and source deltas
share immutable payload bytes. Pending-plan diagnostics report frozen bytes;
these are unsaved costs, not charged to clean caches or claimed as total RSS.

Common version/identity row proofs are consolidated in participants. Existing
specialized minimum/adoption/scalar-child checks and frozen cold event protocol
remain. Event controls join that existing descriptor/token proof before any
participant accepts; they are not redundantly reread or given another commit
path. Central publication still clears the existing runtime family journals
only after checked acknowledgement. No capability6, hidden open migration,
production branch modification or event-authority change is introduced.

RED evidence: ordinary ParticipantDelta discarded query memberships; World
plans had no participants and Person values still aliased live records.
New tests verify detached replay, immutable metadata, lost acknowledgement,
wrong delta/pin rejection and exhaustive source coverage. The initial combined
gate found duplicate proofs exceeding the unchanged H1k/H10k read-check limit
(12 then 11 checks versus <=10); consolidating common proofs and joining the
cold descriptor proof restored 9 checks. Nested corruption still raises the
existing diagnostic. A nonexistent lazy-cold-save test filename collected no
tests and was corrected; no passing result is attributed to that command.

Broader affected integration gate before the final receipt-exception correction:
`PYTHONPATH=.:simulation /workspace/scratch/c3a830e86cea/ownership-gate-venv/bin/python -m pytest -q simulation/tests/test_stage_0_5_final_contracts.py simulation/tests/test_stage_0_5_final_world_participants.py simulation/tests/test_persistence_lazy_people.py simulation/tests/test_stage_0_5_paged_household_world.py simulation/tests/test_persistence_lazy_typed_property_histories.py simulation/tests/test_persistence_cold_save.py simulation/tests/test_persistence_lifecycle.py simulation/tests/test_stage_0_5_r3_recovery_extra.py simulation/tests/test_persistence_lazy_cold_scalar_families.py simulation/tests/test_persistence_lazy_typed_institution_divinity.py simulation/tests/test_persistence_lazy_social.py simulation/tests/test_persistence_lazy_resources.py simulation/tests/test_persistence_lazy_materials.py`
— **153 passed in 193.74s**. This is affected evidence, not the final full suite.

Further adversarial REDs exposed postcommit exception-class handling that could
discard a durably committed plan on StoreConflictError or GenerationPressureError,
and a superseded-successor acknowledgement remaining recovery-required.
Exception handling now consults the durable matching attempt before classifying
any error (pending/committed/acknowledged preserves the plan). A genuinely newer
head marks the acknowledged session stale before participant acceptance.
The earlier supersede fixture accidentally reused a stale peer and was corrected
to open the peer after the first commit; the callback exception case became its
own permanent regression. Final changed-path gate:
`PYTHONPATH=.:simulation /workspace/scratch/c3a830e86cea/ownership-gate-venv/bin/python -m pytest -q simulation/tests/test_stage_0_5_final_world_participants.py simulation/tests/test_stage_0_5_final_contracts.py simulation/tests/test_persistence_lazy_people.py simulation/tests/test_stage_0_5_r3_recovery_extra.py simulation/tests/test_persistence_lifecycle.py`
— **62 passed in 39.09s**. Counts overlap the 153-test gate.

Final contract consumers gate on unchanged executable source:
`PYTHONPATH=.:simulation /workspace/scratch/c3a830e86cea/ownership-gate-venv/bin/python -m pytest -q simulation/tests/test_stage_0_5_final_identity_catalog.py simulation/tests/test_stage_0_5_final_identity_coordinator.py simulation/tests/test_stage_0_5_final_sequence.py simulation/tests/test_stage_0_5_final_sequence_compat.py`
— **71 passed in 154.94s**. Counts overlap prior component gates.

Reproduce focused metrics:
`PYTHONPATH=.:simulation /workspace/scratch/c3a830e86cea/ownership-gate-venv/bin/python simulation/measure_stage_0_5_participants.py --output simulation/stage_0_5_final_participants_metrics.json`.
Source SHA-256 values match the final source. Eight live candidates and one
Person scalar edit are fixed. This fixture has no cross-family sharing; alias
compatibility is covered by affected gates, not claimed by these numbers.

| Metric | H1k | H10k |
| --- | ---: | ---: |
| Frozen source payload bytes | 4,595 | 4,596 |
| Changed namespace participants | 2 | 2 |
| Payload reads / bytes | 7 / 505 | 7 / 505 |
| Checked payload reads / bytes | 9 / 1,747 | 9 / 1,747 |
| Payload writes / bytes | 3 / 767 | 3 / 767 |
| Metadata / returned query rows | 190 / 4 | 190 / 4 |
| Traced Python peak bytes during save | 449,555 | 154,268 |
| Save seconds, single observation | 0.1124 | 0.0645 |

First-use imports are included in the first traced peak; these observations are
not an RSS or latency guarantee. Fixture construction/native SQLite memory are
excluded. SQL rows examined remain unknown. Captured old-pin Person values
remain exact. Subsequent no-op writes zero payload rows; the legacy cold checker
reads three event-control descriptors (217 bytes), reported in full and traced
to `read_records(world_event_storage)`, with no fixture archive payload reads.
The original metrics assertion incorrectly equated all payload counters with
archive reads; it was corrected to trace both ordinary bulk/point and version
read APIs and retain the total counters, not hide the control reads.

Artifact manifest: new participant module, permanent World participant tests,
ordinary-membership contract regression, World integration changes,
`measure_stage_0_5_participants.py`, source-hashed JSON metrics and this ledger.
Resume by verifying `git log -1 --format='%H %T'` and the public branch ref; local
and API commit SHAs differ while their trees must match. No long Actions run
or endurance run is outstanding.

Next critical work: concrete runtime family adapters and World catalog/coordinator
integration; lazy Household headers and Settlement counted sequences; remaining
nested histories and exceptional EventIdSet; shared record budget and lifetime/
retirement closure; exact pressure and explicit copy upgrade. Then integrated
H1k/H10k/fault evidence, independent P5, one stable final full suite and final
independent architecture review. No routine package review is required.
Stage 0.5 remains implementation in progress, not candidate validated or accepted.

## Published immutable participant source checkpoint

Public implementation commit: `b4174345acaa0a315e4b01e8a27b002d8c3457ba`.
Local implementation commit: `edaf40032aaa67397bc5d1bd3ffe3027fe163c57`.
Matching implementation tree: `c3cd5822b75740ee3fa447db124001ed900ae91d`.
Public branch: `sol/stage-0-5-complete-closeout`. These source commits contain
both the implementation and the source-hashed measurement artifact above.
The following ledger-only commit changes no executable source or tests.
PR14 ref remains `c29e3d06a0c9d219235e2b3f0390271bd1245aea`.
All locally launched focused gates above have completed; no test/Actions job
is running. Resume with the next critical work listed above, preserving this
checkpoint and the accepted legacy behavior. No routine Astra approval is needed.

## Release decision still open

Implement exact bounded-memory ordered native pressure sum and measure O(H) cache misses. Owner has not authorized that latency exception or changed arithmetic. This does not block continued implementation; it blocks production acceptance. Endurance/restore retention and promotion remain separately authorized gates.

## Concrete runtime bindings and shared record bytes checkpoint (October 9, 2026)

Implementation local commit `23ee53eea937f14476fd38b726bd2849a051f5db`,
public commit `0d06148e8f03a993b194ae7e24dc2644000f43d3`, matching tree
`f620d0f6c84d97dd453bed1b39a7e598a54b32e9`. Native API publication explains
SHA differences; trees are verified identical. The live closeout branch had
not moved since the previous checkpoint. PR14 remains exactly
`c29e3d06a0c9d219235e2b3f0390271bd1245aea`; no production update, Actions,
endurance run or architectural-review request was made.

`RuntimeFamilyBindings` now binds concrete session/root authorities once,
without owner traversal or payload reads. Both shared-object routing and
IndexedRecord alias callbacks use its immutable maps. It includes skill and
lineage record authorities that the former callback map omitted. Scalar map
families are routing authorities, not falsely classified as record callbacks.
Wallet-first skill and soul children use their existing unrestricted
multi-owner adapters; this does not introduce a second live identity registry.
Child mutation resamples callbacks after binding cold current peer owners.

Permanent REDs: a lineage alias had no authoritative callback; a wallet-first
skill alias failed on its native nested list; a cold skill child mutation left
its authoritative table clean. These now preserve canonical identity through
mutation, save and reopen. Other legacy unsupported native nested containers
have not been claimed to be closed by this targeted change.

Every concrete lazy record family, including the separate lineage-child table,
and hot query LRUs now joins one shared 32MiB byte budget. Weights include
resident schema values and checked baseline payload/presence/incarnation/order/
identity sidecars. Python estimates avoid lazy readers and history iteration;
page-backed reference objects are charged here and their clean pages remain
in the existing shared history budget. Dirty owners are excluded from clean
admission. Eviction releases sidecars and weak budget metadata, and does not
retire persisted occurrences or detach a retained external canonical alias.
Oversized reads return their requested live object without retaining it as
clean. Budget eviction also removes step-touch metadata.

A second RED matrix exposed an oversized owner being evicted again during its
post-mutation rehydration. Eight scalar/history cases failed across skills,
souls, social edges and property. Actual mutation notifications now pin the
owner as dirty before checked loading, retaining exact dirty state on failures.
Tests also cover tiny-budget precommit rollback/lost acknowledgement,
resolve_save, accept-once/no-op and retained identity. A fixture correction in
the earlier retained-alias test adds ordinary people churn: rejecting oversized
skill entries correctly does not evict a smaller existing entry by itself.

Compatibility is explicit: format3/4/5 behavior and the accepted 400-current-
people hot-step regression remain. The shared byte budget applies inside steps;
the strict <=256 per-family clean count during new-format steps remains to be
activated with the complete capability6 runtime. Query budgets and ordinary
per-family count eviction retain existing interfaces. No capability6 floor or
feature marker is emitted; no hidden open-time migration occurs.

Final changed-source focused gate (counts overlap with previous gates):
`PYTHONPATH=.:simulation /workspace/scratch/c3a830e86cea/ownership-gate-venv/bin/python -m pytest -q --tb=short simulation/tests/test_stage_0_5_final_record_budget.py simulation/tests/test_stage_0_5_final_runtime_families.py simulation/tests/test_stage_0_5_final_world_participants.py simulation/tests/test_persistence_lazy_people.py simulation/tests/test_persistence_lazy_skills.py simulation/tests/test_persistence_lazy_lineage.py simulation/tests/test_stage_0_5_r3_recovery_extra.py simulation/tests/test_persistence_lifecycle.py`
— **92 passed in 54.31s**, `final-runtime-cache-final-recovery.log`.

Final cross-family/household gate on the same implementation:
`PYTHONPATH=.:simulation /workspace/scratch/c3a830e86cea/ownership-gate-venv/bin/python -m pytest -q --tb=short simulation/tests/test_persistence_lazy_typed_property_histories.py simulation/tests/test_persistence_lazy_typed_institution_divinity.py simulation/tests/test_persistence_lazy_materials.py simulation/tests/test_persistence_lazy_resources.py simulation/tests/test_persistence_lazy_social.py simulation/tests/test_persistence_lazy_souls.py simulation/tests/test_persistence_lazy_currency.py simulation/tests/test_stage_0_5_r3_cross_family_extra.py simulation/tests/test_stage_0_5_paged_household_world.py`
— **96 passed in 185.98s**, `final-runtime-cache-final-families.log`.
Earlier 72/98/47 gates cover intermediate source, not additional final acceptance.
One intermediate command named a nonexistent recovery file and collected no
cases; it was corrected before the recorded gates. `git diff --check` passed.

Independent eager-control compatibility P5:
`PYTHONPATH=.:simulation /workspace/scratch/c3a830e86cea/ownership-gate-venv/bin/python simulation/persistence_p5_validation.py --paged-households --output simulation/stage_0_5_runtime_cache_p5.json`
— **passed**, seed843000, 3-year prehistory +4 continuation +3 after reopen,
439 exact events, final digest
`3301d4e4a6a2f415679cabe62754813440034cf4c190035c79ba82cc7b8e378e`.
Checks include reopen, relocated backup and portable detach/checkpoint lanes.
This is an independent-control run for the compatibility runtime, not final
new-format acceptance. JSON records exact source hashes. Forced-pressure
float.hex/identity closure still require the final integrated acceptance matrix.
The harness verified then removed temporary restore files: retrievable final
restore artifacts remain outstanding, rather than being falsely declared saved.

Reproducible measurement:
`PYTHONPATH=.:simulation /workspace/scratch/c3a830e86cea/ownership-gate-venv/bin/python simulation/measure_stage_0_5_record_budget.py --output simulation/stage_0_5_final_record_budget_metrics.json`.
Eight live candidates, one scalar edit and two sharing placements are fixed.
Old pins retain the exact previous payload; retained aliases remain canonical.
Explicit archival cache churn is a separate O(H) read, not counted as the edit.

| Measurement | H1k | H10k |
| --- | ---: | ---: |
| Edit payload reads / bytes | 7 / 505 | 7 / 505 |
| Edit checked payloads / bytes | 11 / 3,047 | 11 / 3,047 |
| Edit writes / bytes | 4 / 1,417 | 4 / 1,417 |
| Edit metadata / returned query rows | 201 / 4 | 201 / 4 |
| Clean after edit: entries / Python bytes | 9 / 21,373 | 9 / 21,373 |
| Clean after explicit churn: entries / Python bytes | 257 / 610,406 | 257 / 610,662 |
| Clean manager metadata after churn | 122,464 | 122,464 |

The churn entries comprise <=256 people plus the wallet, not 257 in one family.
Budget byte evictions are separately tested with small limits across families,
inside simulation steps and with oversized query results. Native SQLite/RSS
and total dirty/registry/callback memory are not inferred from these estimates;
the JSON separately reports traced peaks and the two edited payload objects.
The source hashes match exactly. SQL examined rows remain unknown. Subsequent
no-op still honestly reports three checked event-control descriptor reads,
217bytes, zero writes, and no archive payload reads. Open remains the legacy
P2C path; these measurements do not assert a new-format global-scan bound.

**Assignment remains implementation-in-progress, not candidate validated or
production accepted.** Continue through the complete architecture: checked
catalog/coordinator activation and immutable owner publication; lazy household
headers and counted household/settlement histories; nested-history and
exceptional event-ID closure; exact pressure scalars/cache revisions; strict
new-format counts, detached alias leases and retired backing-tree reclamation;
complete capability6 source-copy upgrade; actual writer/guard inventory;
integrated corruption/recovery/H1k/H10k matrix; final-source independent P5 and
one final applicable full suite; final independent architectural review and
retrievable restore artifacts. Pressure latency/arithmetic, endurance policy
and production promotion remain separately owner-controlled release decisions.
No routine Astra approval is needed to implement the next package.

## 2026-10-09 — eager/lazy child publication and exact pressure regressions

Implementation local `750edbed60232c5ef23834da97078ea7e8f71e89`, public
`757e9a8d7a940eb2706e57671b005868b097b807`, matching tree
`3c80b056f9aa3eb99c0abcd6f63d9554c8204455`. Live publication verified with a
leased, non-force ref update. PR14 remains unchanged; no Actions or endurance
run was launched.

The eager-to-lazy seed bridge now shares the concrete runtime manifest. Its
third duplicated callback map previously omitted skill and lineage records;
its skill child type check wrongly expected SkillHistory for a provenance list.
Both legacy cross-boundary refresh filters now use the same manifest. This
repairs namespace drift but does not remove the legacy global refresh.

Concrete skill/soul/advancement list/set aliases bind their lazy owner before a
cold mutation. The eager tracker retains their existing weak object binding;
guards and changed notifications reach both current payload authorities.
Direct eager child aliases, deletion followed by retained-reference mutation,
closed backing, save/reopen and canonical sharing are covered. A retained alias
does not recreate a removed settlement placement.

RED tests then reproduced native partial writes with failing iterables: list
extend and set update/difference changed their value but never dirtied the
owner. Callbacks now run in finally when the actual container changed. Set
notifications also preserve changes in equal values' representatives. The
first broader advancement gate caught a duplicate own-owner notification
turning scalar edits into complete graph reconciliation. IndexedRecord already
delivers its exact field notification; shared notification now reaches peers
without repeating the original owner with field=None. The existing scalar
fast-path regression is preserved, not weakened.

Intermediate evidence (overlapping scopes, not final-source acceptance):
bridge RED3, bridge focused58/1 then59 passed65.13s; affected134 passed62.35s;
direct partial-write RED3/8; runtime11 passed1.05s; affected138 passed77.57s;
cross-family55/1 identified advancement; fixed advancement/runtime23 passed8.23s.
Logs are `/tmp/final-eager-bridge-*.log`; they are reproducible scratch logs.

Final stable-source command:
`PYTHONPATH=.:simulation /workspace/scratch/c3a830e86cea/ownership-gate-venv/bin/python -m pytest -q --tb=short simulation/tests/test_persistence_tracking.py simulation/tests/test_persistence_lifecycle.py simulation/tests/test_persistence_lazy_souls.py simulation/tests/test_persistence_cold_save.py simulation/tests/test_persistence_cold_save_failures.py simulation/tests/test_persistence_cold_identity_restore.py simulation/tests/test_stage_0_5_final_runtime_families.py simulation/tests/test_stage_0_5_final_pressure_arithmetic.py simulation/tests/test_stage_0_5_final_record_budget.py simulation/tests/test_persistence_lazy_advancement.py simulation/tests/test_persistence_lazy_skills.py simulation/tests/test_persistence_lazy_lineage.py simulation/tests/test_persistence_lazy_currency.py simulation/tests/test_stage_0_5_r3_cross_family_extra.py simulation/tests/test_stage_0_5_r3_recovery_extra.py simulation/tests/test_stage_0_5_paged_household_world.py`
— **194 passed177.06s**, `/tmp/final-eager-bridge-stable-gate.log`, exit0.
`git diff --check` passed. This affected suite is not the final applicable full suite.

The five new forced-pressure regressions preserve one native ordered sum,
duplicate/extinct occurrences, repeated unsaved preparedness assignments,
shared list mutation/first removal/replacement and reopen. Exact float.hex
events and forced RNG call sequences match independent eager worlds. Concrete
CPython3.12 counterexamples reject fsum, page subtotals and subtract/add. No
pressure arithmetic or engine implementation was changed. Checked scalar
streaming, complete cache revisions, H measurements and the owner's latency
exception decision remain outstanding.

Independent compatibility P5 rerun on this exact production source:
`PYTHONPATH=.:simulation /workspace/scratch/c3a830e86cea/ownership-gate-venv/bin/python simulation/persistence_p5_validation.py --paged-households --output simulation/stage_0_5_runtime_cache_p5.json`
— **passed**, seed843000 3+4+3, 439 events, exact final digest
`3301d4e4a6a2f415679cabe62754813440034cf4c190035c79ba82cc7b8e378e`.
Log `/tmp/final-eager-bridge-stable-p5.log`. JSON includes changed production
module hashes, engine/harness and pressure regression provenance; all verified.
Temporary restore files were verified then removed, not declared retrievable.

H1k/H10k rerun:
`PYTHONPATH=.:simulation /workspace/scratch/c3a830e86cea/ownership-gate-venv/bin/python simulation/measure_stage_0_5_record_budget.py --output simulation/stage_0_5_final_record_budget_metrics.json`
— exit0, `/tmp/final-eager-bridge-stable-metrics.log`. Both edits still read
7/505 payload rows/bytes, check11/3047, write4/1417, metadata201/query4,
clean9 entries/21373 estimated Python bytes. Source hashes now include the
eager tracker; every embedded hash verified. Existing legacy-open, SQL scan,
unpaged histories, dirty-memory and strict hot-step count caveats still apply.

**Next action:** finish compact family header comparison for the checked
coordinator without materializing page-backed histories, then activate the
complete checked catalog/coordinator through the integrated new-format runtime.
Continue all remaining packages listed above. Implementation remains in
progress; this passing checkpoint is not candidate validation or release acceptance.

## 2026-10-09 — compact checked identity placement headers

Local implementation `6847275e54ba540ff3e86dffd18e8108f6339a4f`, public
`ad5f699d673a1449c314f597c9361e82e0beb2c4`, matching tree
`710a8b7395ddb476c97f6dc1c083080f7d7945b1`. Publication and exact live ref verified.

FamilyAdapter now provides compact identity payload encoding. A private
WorldCodec subclass retains the closed schema and portable codec behavior,
but replaces checked typed history proxies with immutable references during
placement comparison. It validates the backing store, registered pin,
generation and lifecycle guard without reading history pages. Equal-valued
distinct sequence incarnations remain distinct. Incoming reference validity
and owner/group agreement remain the catalog's responsibility; these encoded
bytes are not a second identity or historical payload authority.

IdentityCoordinator accepts a concrete placement encoder. World family
adapters supply the compact header encoder; standalone scalar fixtures keep
their existing checked codec. The coordinator does not guess a namespace or
history type. All peer comparisons finish before any installation. A later
peer referencing another incarnation raises corruption with no installation
or dirty notification.

RED header5 failed because the adapter method was absent; initial focused5
passed82.18s. Coordinator RED2 failed for the missing encoder contract, then
coordinator/lease focused14 passed24.98s (two H-size cases deselected).
Final command:
`PYTHONPATH=.:simulation /workspace/scratch/c3a830e86cea/ownership-gate-venv/bin/python -m pytest -q --tb=short simulation/tests/test_stage_0_5_final_identity_headers.py simulation/tests/test_stage_0_5_final_identity_coordinator.py simulation/tests/test_stage_0_5_final_identity_catalog.py simulation/tests/test_stage_0_5_final_sequence_compat.py simulation/tests/test_stage_0_5_final_runtime_families.py`
— **55 passed120.11s**, `/tmp/final-identity-headers-stable-gate.log`, exit0.
H1k/H10k comparisons read zero history payloads; checked node reading is
forbidden in the regression. Explicit sequence construction is excluded from
that comparison bound. Wrong-store and wrong-generation leases are rejected.
`git diff --check` passed.

Compatibility P5 and shared record-budget measurements were rerun with the
same commands above, logs `/tmp/final-identity-headers-p5.log` and
`/tmp/final-identity-headers-metrics.log`, both exit0. P5 retains the exact
baseline final digest and439 events. H1k/H10k edit values remain7/505 reads,
11/3047 checked,4/1417 writes and9/21373 clean entries/bytes. Reports now carry
this source's hashes; P5 also identifies the compact-header/coordinator source
and regression. The 194-pass runtime gate belongs to the immediately preceding
alias checkpoint; the 55-pass gate is the new foundation's affected gate.
Neither is a final applicable full suite.

This component is ready for the concrete catalog runtime integration. It does
not activate the coordinator in ordinary World open/save, publish capability6,
replace eager household/settlement authority, or close nested histories.
**Next:** complete runtime adapter/coordinator publication and the dependent
household/sequence integrations. Preserve native exceptional list behavior
when closing the counted-sequence interfaces. All final release gates remain.

## 2026-10-10 — counted sequence iterator/freeze repair

Local implementation `27a3e48026d070dd1d263f76360c8f4ddf026091`, public
`2c4f70d56023079773d00f8669028a596ec95dec`, matching tree
`e126c3620e99a1968d463b7dfebe2a831f5402a4`. Non-force publication used the
previous exact public head lease.

Sequence extend now consumes caller input inside the guarded mutation, retaining
and notifying the successfully consumed prefix if the iterator raises, as native
list.extend does. Self-extension captures original occurrences once. Stored-value
validation and checked tree/index failures still roll back the complete operation.
Save preparation is blocked throughout the mutation, including its preflight
callback, so a reentrant iterator/guard cannot freeze an intermediate plan.

Permanent regressions cover failed input, iterator observations, frozen preflight,
self-extension, later corrupt member index rollback, reentrant input preparation
and reentrant guard preparation. Historical REDs reproduced lost prefix, stale
iterator observations, premature generator consumption, and both freeze holes.
Final affected gate:
`PYTHONPATH=.:simulation /workspace/scratch/c3a830e86cea/ownership-gate-venv/bin/python -m pytest -q --tb=short simulation/tests/test_stage_0_5_final_sequence_errors.py simulation/tests/test_stage_0_5_final_sequence.py simulation/tests/test_stage_0_5_final_sequence_compat.py simulation/tests/test_stage_0_5_final_budget.py`
— **58 passed178.43s**. Durable output: `stage_0_5_final_sequence_error_gate.txt`.
The process handle was lost across runtime restart; the completed output survived.
A fresh focused regression run independently returned exit0, **7 passed0.22s**.
`git diff --check` passed. Previous same-source gate58 passed127.99s belongs to
its own transient log; counts overlap.

The recorded compatibility P5/record metrics remain at the preceding compact
header source; they do not certify this unused World sequence primitive or a
complete new-format candidate. Numeric equal lookup routing and native sort
exception semantics still need closure. Catalog/household/nested integration and
all final acceptance/release gates remain outstanding. Next: runtime catalog
adapter/publication integration, preserving checked compact history comparisons.

## 2026-10-10 — checked owner retirement and numeric lookup closure

Owner retirement local `e92f1728d25b34bb58f4151fc84f517440c3c1f2`, public
`f7421344c03ec6995c1189a0247aea0c57e3aac1`, tree
`939d22cb48d0c8304fc18dcbcf4e35f5de65916c`. Numeric sequence local
`58eca6fe588e40b13cf6ecac65b7ba82c56a34e1`, public
`2b0c4672c15648c45f2c9cac4d86ad82bb5d7b39`, tree
`20ee6634422e64177fca119a70e4624440d88986`. Both non-force publications
matched their exact local trees and preceding public-head leases.

Store owner occurrence reads now have a streaming checked iterator, using the
owner-leading interval index. The compatibility tuple API delegates to it.
It validates canonical paths, allocator, checksums, intervals and overlapping
visible placements, and closes the snapshot/cursor after an early stop.
Catalog owner completeness compares checked spill buffers instead of allocating
two archive-sized native inventories. Requested owner rows remain O(D); this
does not inventory other owners or decode a child payload.

Coordinator.retire_owner validates the complete pinned owner and every affected
group before detaching anything. It overlays replacements/deletions and cancels
local-only placements, updates both overlay indexes and dirties only that owner.
The family participant still owns deletion of its header in the one transaction.
Retained original/replacement objects route to no removed placement; exact
acknowledgement clears the journal and an independently held old pin retains
its original group. Later corrupt group, corrupt owner and frozen-plan tests
fail without a partial retirement. Long owner membership spills and its private
file is explicitly reclaimed. This is the coordinator's integration seam, not
activation in ordinary World open/save. Bulk owner/subtree replacement remains
a next contract to close.

Affected command (four new owner tests at that run):
`PYTHONPATH=.:simulation /workspace/scratch/c3a830e86cea/ownership-gate-venv/bin/python -m pytest -q --tb=short simulation/tests/test_stage_0_5_final_owner_retirement.py simulation/tests/test_stage_0_5_final_identity_coordinator.py simulation/tests/test_stage_0_5_final_identity_catalog.py simulation/tests/test_persistence_lazy_store.py`
— exit0, **59 passed24.09s**, `stage_0_5_final_owner_retirement_gate.txt`.
Later complete six owner regressions plus spill/non-death failure cases:
`PYTHONPATH=.:simulation /workspace/scratch/c3a830e86cea/ownership-gate-venv/bin/python -m pytest -q --tb=short simulation/tests/test_stage_0_5_final_owner_retirement.py simulation/tests/test_stage_0_5_final_identity_spill.py simulation/tests/test_persistence_lazy_store_failures.py -k 'not process_death'`
— **39 passed,3 deselected,1.91s**, `stage_0_5_final_owner_retirement_fault_gate.txt`.
The attempted gate including process death ended after30 dots with no pytest
summary (tool reported exit0). It is not passing evidence. Death cases remain
unchanged and must be completed in a suitable final validation environment.
An initial command used nonexistent test_stage_0_5_final_spill.py and exited4;
it was corrected to the actual identity_spill file. Counts overlap.

Sequence occurrence/removal queries now normalize True and integral positive
floats through the existing stored membership key. Four REDs proved these
queries scanned history and ignored a deleted required membership node. Fixed
queries traverse checked occurrence order trees, preserving native numeric
representatives, first-equal removal, old pins and duplicate positions.
Unindexed values retain the explicit compatibility scan. Final command:
`PYTHONPATH=.:simulation /workspace/scratch/c3a830e86cea/ownership-gate-venv/bin/python -m pytest -q --tb=short simulation/tests/test_stage_0_5_final_sequence_numeric_index.py simulation/tests/test_stage_0_5_final_sequence_compat.py simulation/tests/test_stage_0_5_final_sequence_errors.py`
— exit0, **16 passed5.66s**, `stage_0_5_final_sequence_numeric_gate.txt`.
The earlier58-case sequence gate remains evidence at its own exact source.
`git diff --check` passed.

Compatibility P5/H-size reports remain recorded at the preceding header
checkpoint. No complete cap6 format, migration, lazy household activation,
nested closure or final integrated acceptance is claimed. Next: owner/subtree
replacement and concrete runtime catalog publication/adapters; then household
sequence and dependent remaining packages. No endurance or PR14 operation.

## 2026-10-10 — complete coordinator replacement interface

Local implementation `be6df5e6c74406bff3c05ae4316de78ed3800e22`, public
`737b46de63103d161e3ca3467744e6fc7c3df1db`, matching tree
`e8a5cc4ff599542fc4400e7e298076fafcb77fee`. Exact-tree non-force publication
completed. Coordinator now provides replace_owner and replace_subtree over
explicit adapter-supplied compact identity projections. It does not infer a
projection by traversing a record/history. All incoming paths, duplicate/scope
constraints, codec/lease eligibility and complete affected old groups are
validated before allocation/installation. Parents install before children.
Unrelated subtree paths remain unchanged. Retirement uses the same checked
metadata reducer; local-only canceled objects keep their reserved incarnation
and never revive removed placements. Missing present owner source/witness is
corruption; only the catalog's existing checked new-owner absence rule is used
for a genuinely unpublished owner. No historical ordinary payload is decoded.

Mutation scope covers input/preflight/peer loading and blocks reentrant save
preparation. Eight new regressions cover replacement publication and old pins,
peer aliases, subtree preservation, duplicate/out-of-scope/corrupt-group
failures before installation/allocation, failing input freeze, new-owner
retirement and no ID reuse, and peer-load freeze rejection. Initial RED6 failed
for the missing replacement APIs.

Final affected command:
`PYTHONPATH=.:simulation /workspace/scratch/c3a830e86cea/ownership-gate-venv/bin/python -m pytest -q --tb=short simulation/tests/test_stage_0_5_final_owner_replacement.py simulation/tests/test_stage_0_5_final_owner_retirement.py simulation/tests/test_stage_0_5_final_identity_coordinator.py simulation/tests/test_stage_0_5_final_identity_catalog.py simulation/tests/test_stage_0_5_final_identity_spill.py`
— exit0, **54 passed21.50s**, `stage_0_5_final_owner_replacement_gate.txt`.
Concrete compatibility runtime/header lease subset:
`PYTHONPATH=.:simulation /workspace/scratch/c3a830e86cea/ownership-gate-venv/bin/python -m pytest -q --tb=short simulation/tests/test_stage_0_5_final_identity_headers.py simulation/tests/test_stage_0_5_final_runtime_families.py -k 'not history'`
— exit0, **13 passed,5 deselected,0.73s**,
`stage_0_5_final_owner_replacement_runtime_gate.txt`. This broad expression
also deselected the two coordinator header cases, so they were explicitly run:
`PYTHONPATH=.:simulation /workspace/scratch/c3a830e86cea/ownership-gate-venv/bin/python -m pytest -q --tb=short simulation/tests/test_stage_0_5_final_identity_headers.py -k coordinator`
— exit0, **2 passed,5 deselected,8.29s**,
`stage_0_5_final_owner_replacement_header_gate.txt`. The two H-size standalone
header construction cases were not rerun; their prior zero-history proof stays
at its own checkpoint. Counts overlap. `git diff --check` passed.

Next integration concern: the legacy session resets known uncommitted plans;
new frozen sequence/coordinator participants need checked unfreeze on an exact
not-committed resolution, while committed/lost-ack/stale attempts must retain
their plan. Close that protocol before activating them in the hybrid publisher.
Then connect concrete catalog adapters, household sequences and all remaining
packages. This is still implementation in progress, not candidate/release
acceptance. Compatibility P5/H metrics retain their previous source boundary.

## 2026-10-10 — checked failed-publication release

Local implementation `f5f3f6dc545ccbd13a9b95beccb6f1c99c4cd753`, public
`b12a562120f33bc5cdd5bed000ad795e42dc6fb0`, matching tree
`29e44cf75738a491b83abb3f6ec98f6ec0a8d65c`. Non-force exact-tree publication
completed. Sequence and coordinator abort_delta release only their freeze,
retaining all dirty pages/routes and canonical objects, after checked existing
pin/attempt/receipt resolution proves the exact token not committed at the
unchanged parent. A preparation that never registered an attempt is provably
unpublished only with no attempt or the preceding acknowledged parent. Wrong
failed token, wrong delta, corrupt operational metadata, committed/lost-ack
and stale/superseded parent cannot thaw the plan. No replacement authority or
new receipt protocol was added. Checks inspect bounded operational pins/receipts,
not archive owners.

A further RED reproduced a committed sequence misclassified as unattempted
when the hybrid bridge advanced its lease before acceptance. Abort now checks
the captured prepared parent, so an advanced lease cannot unfreeze that delta.
Acknowledgement also requires the original writer pin token, not a separately
registered pin at the same generation. Closed backing is checked explicitly;
coordinator idempotent acceptance validates its surviving lease.

Nine new regressions cover failed retry with old-pin preservation, wrong
delta/token, lost acknowledgement and idempotent acceptance, stale competitor,
corrupt attempt, coordinator overlay preservation/replacement retry, unattempted
preparation, advanced lease and both unrelated-successor cases. Initial RED6
failed for missing abort methods; the advanced-lease RED failed DID NOT RAISE.
Final affected command:
`PYTHONPATH=.:simulation /workspace/scratch/c3a830e86cea/ownership-gate-venv/bin/python -m pytest -q --tb=short simulation/tests/test_stage_0_5_final_participant_abort.py simulation/tests/test_stage_0_5_final_owner_replacement.py simulation/tests/test_stage_0_5_final_identity_coordinator.py simulation/tests/test_stage_0_5_final_sequence_errors.py simulation/tests/test_stage_0_5_final_sequence_numeric_index.py simulation/tests/test_stage_0_5_final_sequence_compat.py simulation/tests/test_stage_0_5_final_world_participants.py`
— exit0, **49 passed16.01s**, `stage_0_5_final_participant_abort_gate.txt`.
`git diff --check` passed. This includes the existing actual World hybrid
participant tests, but sequence/catalog World activation remains pending.

Next: include catalog/coordinator deltas and exact failed-plan release in the
frozen central publication interface, then activate concrete adapters with the
complete new-format contracts. Do not emit an incomplete capability6 marker.
All household/nested/pressure/migration/final release gates remain outstanding;
P5/H-size reports retain their previous source boundary.
