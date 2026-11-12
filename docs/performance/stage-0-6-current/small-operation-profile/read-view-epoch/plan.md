# Stage0.6 owned read-view epoch reuse

Authorized scope: continue toward interactive targets while preserving exact
state, complete history, identity and corruption detection. Base local1b6e770 /
remote f6d5d2ba, runtime41d21d8. Full hosted43227352719 is verified5071tests;
proof31XMLs1914tests plus scaling (overlapping suites). Archived ZIP hashes and
source records are in ../closed-read/hosted-43227352719.

Root-cause evidence: existing instrumented small warm step executes386922SQL
statements, save257723. _WorldProofAuthority._epoch repeats3PRAGMAs at every
nested source boundary; ValidationScope.can_reuse repeats2 more while the same
owned read transaction remains open. Earlier per-operation authorizer guard was
rejected because installation evicted prepared statements and custody checks
added overhead. The accepted connection now tracks schema-changing SQL and
opaque/callback history, providing a cheaper basis for view custody.

Approaches: retain all repeated checks (safe baseline, no improvement); install
a new SQL guard per operation (rejected measured design); reuse admitted epoch
only during one actual owned closed read operation (selected). Physical source and payload proofs remain checking; repeated descriptor proof
work uses the existing admitted immutable fact. Redundant epoch SQL is reusable. No additional
cache, authorizer, transaction or final-exit validator is introduced.

Design: ValidationScope may capture actual admitted proof-only authority,
pin/manifest/accepted epoch, exact store/DB/codec and owned snapshot context,
hook identity, total_changes, existing SQL/callback revisions and a new monotonic
transaction-control revision. The latter covers public commit/rollback and SQL
BEGIN/COMMIT/ROLLBACK, including release/reopen of an apparently unchanged view.
Unknown SQL and scripts already advance the existing SQL revision. Any custody
change permanently invalidates this scope and its facts; no restored coarse
epoch can reauthorize them. Callback-bearing/custom-cursor/opaque mutation,
borrowed, audited, opening, publisher and recovery paths keep full checks.
All public/nonnested entry and established-view checks remain full; the physical
source/proof checks remain unchanged. Capture eligibility automatically from
actual authority/custody, not a trusted caller flag. Existing scopes are internal
bounded non-yielding batches only (three callsites inspected).

Tasks: (1) exact final baseline profile + full runtime qualification fingerprint;
(2) RED nested-PRAGMA bound and transaction/callback/schema/opaque drift controls;
(3) one small implementation in validation scope, connection and authority epoch;
(4) focused controls, raw candidate/baseline pair without concurrent CPU work;
(5) final affected tests and one fresh independent whole-package review; close
all findings in bounded-genesis/closure.md; one bundled CI if worth retaining.
Do not stack another guard/cache redesign on an unmeasured result.

Restart unit: one disposable copy of immutable small year1 input. Retain closed
phase JSONs, profiles, tests, archived hosted evidence; no reconstruction of
completed compatible prerequisites. Existing driver budgets open60s/first180s/
save120s/warm180s/fresh120s. Profile is attribution only. Reuse expires on relevant
runtime/source/input drift. Baseline and candidate use unchanged qualified313;
verify full binary/extension/library/SQLite options fingerprint first. Reserve
15minutes for publication; existing hosted proof90min/full180+15reserve apply.
No mature constructor until small unknown is resolved. No main merge, format
activation or endurance. Interactive acceptance remains open until measured.

## Implementation contract and review focus

Files: persistence_validation_scope.py owns captured custody and invalidation;
persistence_sqlite_guard.py owns monotonic transaction revision;
persistence_proof_world_session.py selects captured epoch only through actual
ValidationScope authority. New tests test_stage_0_6_read_view_epoch.py.

Interfaces: ValidationScope.native_epoch(store, authority) -> accepted tuple or
None, never SQL; can_reuse(store,pin) keeps its existing bool interface. A captured
custody tuple is created after original _current_epoch and owned snapshot
admission; native_epoch never recursively calls authority._epoch. Transaction
revision is connection-local and not persisted, distinct from descriptor SQL
revision so normal read-scope enter/exit does not destroy descriptor reuse.

Review focus: released/reopened views with equal SQLite coarse epochs; registered
then removed callbacks or custom cursors; pending DML RETURNING and opaque blob/
deserialize; borrowed/public iterator and publisher entry; invalidation and
spilled-result cleanup without introducing a new final-exit throw site.

- [x] Baseline profile complete, source/input/runtime preserved.
- [x] Add nested group PRAGMA bound (<=12 for8reads after scope admission),
  transaction-control / callback / schema-reset / opaque revision invalidation
  and external-writer-release controls. Observe performance/semantic RED first.
- [x] Add transaction revision before exact transaction SQL and public commit/
  rollback; unknown script/SQL already has separate revision. Capture read
  custody only for actual admitted proof-only, owned nonpublisher snapshots.
- [x] can_reuse checks captured custody cheaply; any drift invalidates caches
  permanently. native_epoch requires same authority/epoch/manifest/component
  identities and same current scope and view. Authority._epoch otherwise
  executes original full SQL. Do not add a final-exit validator or authorizer.
- [x] Focused controls green; run exact-state raw small input comparison; keep
  only measured benefit. Then affected paths and fresh whole-package review.
- [ ] Record actual evidence and findings, commit exact tree, one bundledCI.

Ruling after final baseline profile: epoch SQL alone is ~0.67s cumulative of
instrumented14.36s warm, so it cannot explain the whole miss. The same profile
shows919descriptor calls (~4.10s) and1296owner reads, including542descriptor
misses outside an existing ValidationScope. Extend existing scope admission to
standalone admitted proof-only read_owner_identity as well. Ordinary/audited,
borrowed and frozen-construction paths remain exact original read_snapshot.
Owner operation uses zero transient scope-cache bytes: only bounded custody and
existing shared descriptor/owner cache; no new node/owner fact LRU is allocated.
ValidationScope.remember returns immediately for zero budget. Existing spool
budgets and cleanup remain unchanged. This is the same owned-view boundary,
selected before implementation based on attribution, not a stacked guard design.
New RED test uses distinct owners so an owner-cache hit cannot hide descriptor
proof repetition. File persistence_lazy_identity_catalog.py joins this package.

Resumed work:42focused cases passed20.38s before interruption; retained XML
avoids repeating that completed step. Full fingerprint still matches. Candidate
raw metadata first57461→39173, warm47507→35843; save unchanged. Old baseline
was collected before the interruption, so its timing is not contemporaneous.
A fresh reverse baseline is retained, then one explicit paired orchestrator will
run baseline and candidate as sequential child processes of the SAME command
execution, recording CPU/affinity/cgroup context and per-version source fences.
This controls cross-command scheduling context without assuming it caused all
variance. No concurrent tests/review CPU. Same per-phase restart/budgets/input
and15minute publication reserve; no mature constructor or repeated full suite.

Local completion:328affected passes327.84s/1deliberate constructor deselection;
4additional ownerfallback cases pass4.60s. Independent13probes closed, no
remaining code findings. Full hosted validation will run the reserved constructor
and every new control once as one bundle. Exactsource publication remains next.
