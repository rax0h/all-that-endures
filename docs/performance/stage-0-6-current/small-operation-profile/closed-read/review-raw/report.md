# Independent whole-package review: closed proof metadata read

Local whole-package review complete. This is the one independent review for this work group,
covering the implementation, boundary probes, raw small-case pair, profile, and
final disposition. No production source/index/HEAD edits, publication, CI launch,
or mature construction were performed by the reviewer.

## Source and evidence identity

Base local c6c7fcca8c62c5bcba0f1528e137b86a3b03471d, validated engine0785bf9.
`raw-evidence.json` records SHA256 for all five changed runtime files, both
measured endpoints, and their current source identity. The original raw pair
uses database SHA2562555675bd19ede5c6ed9b7619fab56d59098a8b358d9a9c3569cabccba22c554.
All recorded runtime fingerprint fields exactly match the qualified313 record;
extra qualification bookkeeping fields are not runtime fingerprint fields.

Both runs report preserved source/input and runtime, matching saved generation1,
year2, seed843000, digestcebc2fcd2660db6e87b9c29c3c8e88536a831214c306991778fba6ee58cc7451,
and continued year3 digesta46d627d11ce2c12ff8f6fe0f14d01af35006afd56bdad3bf16417379b0166f3.
First-step latency rises from6.919s to8.158s and warm-step from5.751s to6.545s.
This single sequential pair does not establish a distributional regression,
but does not justify adopting this implementation as a performance improvement.

## Static review

The specialized scope is selected only by the group reader, only after exact
native authority discovery, only outside borrowed reads/publication/opening,
and only for an owned SQLite snapshot. Existing pre-BEGIN and established-view
epoch checks remain in place. Nested reuse checks authority identity, immutable
manifest/component object identity, full pin, accepted epoch, unchanged
connection/codec/hook/factories/read-view state, and retained authorizer custody.
SQL writes including TEMP, transaction controls, attachment, writable pragmas,
and load_extension are denied. Installation resets SQLite prepared statement
authorization. Denials persist even if callers swallow the immediate SQLite
exception. Callback source reentry is refused; callback exit checks poison
detected drift even where SQLite swallows a trace exception. Cache values remain
recursively immutable with entry/byte bounds; registry snapshot overhead is
reserved from the same operation budget.

No confirmed integrity bypass was found in this static pass. Public group
completeness, exact membership, occurrence and link commitments remain checked;
ordinary/audited/publisher/recovery/borrowed paths retain generic behavior.

## Original findings and disposition

1. Minor — the supplied cache-limit test passes1024bytes, forcing the generic
   fallback. It does not exercise the specialized cache plus registry budget.
   Independent probe uses32768bytes and asserts exact specialized type and total
   metadata+fact residency, eviction, and lifetime. Closed by verification and
   subsequent withdrawal of the specialized scope; replacement limits also pass.
2. Minor — plan wording says no certificate crosses a callback, while the code
   intentionally retains immutable facts across pre-existing SQLite callbacks
   and fully checks custody afterward. Contract must say no certificate use
   inside callbacks; no gameplay callback/public yield is permitted. Closed by
   withdrawal and the replacement's explicit callback-history fallback contract.
3. Minor — activation occurs outside the finally that releases the
   guard. Controlled post-install setup failure confirms failed deterministic
   cleanup. Closed by removing the entire new activation path.
4. Minor — retained spilled return buffers are excluded from the
   group's finally before the outer final custody check. A controlled final
   rejection confirms unreturned spills are not closed immediately.
   CheckedSpool.__del__ eventually closes them, so this is not claimed to be
   a permanent orphan after all references/tracebacks die. Closed by removing the
   new final-exit validation path.

## Original candidate probe results

`independent.log/xml` preserve the first run: six passes and three failures.
Two are confirmed Minor cleanup findings: setup failure after guard installation
leaves the capability installed; final custody rejection leaves an unreturned
spilled result open while references/tracebacks survive. These use explicit fault
injection at the new installation/exit seams and do not claim a normal SQL path
spontaneously takes those faults. Both require closure or removal before adoption.

The third failure was a reviewer fixture assumption: SQLite DELETE journaling
blocks writer commit during an active reader. A follow-up WAL attempt was also
invalid because the store explicitly rejects WAL at opening; its negative log is
preserved as `external-wal.log/xml`. The corrected supported-mode probe passes in
`external-delete.log/xml`: writer commit is locked during the read, the same view
remains readable, commit succeeds after read release, and fresh scope admission
rejects the altered epoch. This is a test repair, not a product failure or mode
change. Combined compatible results: seven passing boundary cases, two confirmed
Minor cleanup findings. The source fence remained exactly the measured candidate
through all these probes.

The six initial passing cases cover three previously prepared transaction-control
statements, prior authorizer restoration after success/body exception, permanent
poisoning after SQLite swallows trace-driven codec-registry drift, and actual
specialized metadata+LRU budget/eviction/lifetime. Existing focused tests supply
the complementary ordinary writes, TEMP, attach, pragma, callback registration,
factory, hook, and borrowed-transaction controls.

The owner is evaluating removal of this slower guarded scope and narrower reuse
of a bounded immutable descriptor fact behind fresh original native admission.
That replacement remains within this same whole-package review. No adoption
approval is issued before its final evidence/disposition review.

## Narrowed immutable descriptor cache review

The replacement restores original read-snapshot, epoch, and authorizer behavior.
One immutable schema-checked descriptor fact is retained by IdentityCatalog,
behind fresh original owned proof admission on every hit. Descriptor storage and
registry metadata compete with existing owner entries under the same byte/entry
caps; a fact has an additional32KiB maximum. A fallback connection does not gain
cached admission or lose full descriptor/source proof checks.

Initial static findings were resolved in revised source: registry stamps now
retain actual bounded key/value references and compare identities rather than
unretained numeric addresses; hook identity uses an id plus weak reference;
all callback-capable SQL precedes the final pure codec/context snapshot.
The connection tracks public callback registration monotonically. Any such
history (even after unregister) selects original fully checking behavior and
clears descriptor facts. Only repository-known schema types and bounded strings
can enter the registry fence; tuple/string retention is explicitly charged.

`descriptor-independent.log/xml` records four independent passes in2.53s against
exact hashes in `descriptor-source-before-opaque.json`. They verify trace-driven
Ref registry mutation cannot hit a warmed fact, unregistering does not re-enable
reuse, an expired/released pin cannot hit, one-entry/64KiB owner+descriptor limits
hold with a spilled returned group, and callback fallback retains original epoch
SQL and no new guard. The narrow path has no new post-return custody check or
guard installation, removing both confirmed original cleanup failure seams.

Final opaque API screening covers writable BLOB opening, deserialize, enabling
native extensions, and direct extension loading. Each advances the same monotonic
ineligibility history before calling SQLite, including failed attempts. Read-only
handles do not gain write capability. The implementer's four
opaque-API tests passed; source inspection independently confirmed each route.

`descriptor-corruption.log/xml` adds one independent pass in1.11s: corrupt the
physical catalog payload, commit, then manually acknowledge the new coarse native
epoch. The original proof path still rejects the bad descriptor and no fact hit
occurs. `descriptor-source-final.json` records exact final source/test/probe
SHA256 values. The earlier four probes remain compatible: the final change only
adds conservative ineligibility transitions for those opaque APIs. Combined
independent replacement evidence is five passing cases; no repeated green suite
was run merely because the opaque API addition followed the first probe batch.

## Replacement raw comparison

Independently parsed `fact-raw/report.json` and the immediately following
`reverse-baseline-raw/report.json`; derived evidence is
`descriptor-raw-evidence.json`. The reverse baseline has exactly the original
baseline runtime hashes. The candidate differs only in IdentityCatalog and
GuardedConnection, with hashes matching the final independently probed source.
Both runs use identical authenticated input descriptors, preserve original input
and runtime, and match all saved/year3 semantic state described above.

| Operation | Adjacent reverse baseline | Descriptor candidate | Candidate change |
|---|---:|---:|---:|
| Open |1.554s|1.642s|+5.7%|
| First step |12.377s|9.526s|-23.0%|
| Save |6.617s|6.345s|-4.1%|
| Warm step |8.698s|7.889s|-9.3%|
| Fresh verification |20.983s|18.554s|-11.6%|

First-step metadata rows fall61,171→57,461 and warm rows51,359→47,507;
save remains24,929. Those exact work reductions support the intended mechanism.
Earlier same-source baseline timing was substantially lower, so host/runtime
load drift is material. This adjacent reverse-order pair reports an observed
improvement, not a statistical speedup guarantee or mature interactive target.
No profile timings are substituted for the raw pair.

## Important late finding: public DDL can restore the coarse epoch

`descriptor-ddl-reset.log/xml` records a confirmed independent regression
(1.09s). Public guarded execute calls CREATE TABLE AS SELECT with altered catalog
payload, DROP the original table, RENAME the replacement, recreate named indexes,
then restore PRAGMA schema_version. SQLite total_changes and the entire native
authority epoch remain unchanged. The warmed fact accepts the group, while
clearing only that fact makes the original physical proof correctly reject the
same descriptor corruption. The attack does not reset private authority or use
base-class/reflection/native-memory bypasses.

This was an Important adoption blocker, separately reported immediately to the
owner. Closure is a monotonic guarded-public-SQL revision included in
the fact fence: only exact known engine read PRAGMAs/transaction strings and
literal SELECT avoid revision; every unrecognized statement increments and
executescript always increments. Custom cursor factories must force full
fallback before construction. Unknown SQL is conservatively invalidating,
not parsed into permission. Statement-cache reuse still traverses the wrapper.
The engine's generated WITH read is admitted by one narrow SQLite grammar rule:
raw literal-WITH text must contain no whole-word INSERT/UPDATE/DELETE/REPLACE,
case-insensitively, anywhere. This scans comments/literals too, deliberately
accepting harmless false invalidations rather than stripping or rewriting SQL.
SQLite WITH permits reads or those DML forms, not DDL/PRAGMA. Parent controls
exercise mixed case, comments, recursive SELECT, DML forms and failed scripts.

The reviewer independently inspected the final wrapper and both owner/descriptor
fence bindings. `descriptor-ddl-reset-green.log/xml` passes in1.26s. The probe
explicitly rewarms the descriptor after metadata/index discovery so a harmless
PRAGMA revision cannot produce a false green; the actual public DDL attack still
restores the exact SQLite epoch and is rejected through physical proof after
revision invalidation. Exact revised source/test/probe hashes are in
`descriptor-source-revision-final.json`. The Important finding is closed.

## Final-source raw evidence and bounded adoption assessment

The earlier pair is intermediate because the hot execute wrapper changed.
`final-raw-evidence.json` independently reconciles all four final raw reports,
both run orders, exact baseline/final source fingerprints, preserved input/runtime
and matching saved/year3 semantic state. Current runtime matches
`descriptor-source-revision-final.json`.

| Pair and order | Operation | Baseline seconds | Candidate seconds |
|---|---|---:|---:|
|1: candidate then baseline|Open|1.171|1.896|
|1: candidate then baseline|First step|9.854|8.185|
|1: candidate then baseline|Save|5.383|5.372|
|1: candidate then baseline|Warm step|8.051|8.558|
|1: candidate then baseline|Fresh verification|20.022|17.368|
|2: baseline then candidate|Open|1.310|1.871|
|2: baseline then candidate|First step|10.635|7.481|
|2: baseline then candidate|Save|9.071|5.240|
|2: baseline then candidate|Warm step|10.547|7.535|
|2: baseline then candidate|Fresh verification|22.603|20.463|

First-step latency improves16.9% and29.7% in these two observations, with the same
exact metadata-work reductions. Warm latency is mixed (+6.3% and−28.6%); opening
is slower in both (+62.0% and+42.8%). Save variation is large. Both pairs must
remain visible; no consistent warm/save/open improvement, latency distribution,
or mature/interactive acceptance follows. The owner elects to retain the bounded
proof-work/first-step improvement with those explicit tradeoffs.

Final focused XML records16passes;13additional distinct revision controls pass.
Earlier affected XML records301passes
and7warnings before the public SQL revision fix; it is intermediate evidence,
not a final-source full validation claim. It was not repeated merely to refresh
unchanged coverage. Final-source existing guard/scope XML records54passes in20.81s.
Hosted full validation remains a completion gate.

## Final local signoff

No remaining Critical, Important or Minor review finding. The original guarded
scope and both of its cleanup defects are withdrawn; replacement identity,
callback-ordering, memory, opaque-API and public-DDL findings are closed in code
and bounded tests. The consolidated W6a–l register accurately reconciles those
findings, diagnostic/test repairs, retained negative evidence and performance
limits. The current plan no longer asserts the withdrawn scope's contract.
Workflow change adds only the focused descriptor test command to the existing
proof-validation step. No new CI cycle was launched by the reviewer.

Independently checked final runtime hashes still exactly match
`descriptor-source-revision-final.json`; all four final raw source/input fences
and semantic state match. Final-source29focused/revision controls and54existing
guard/scope checks are green. Independent boundary evidence is six compatible
replacement cases across the recorded batches, including the last DDL attack
rerun on the exact final runtime. Historical301affected passes remain explicitly
intermediate rather than a final-source claim.

The package is suitable for the owner's one bundled hosted proof/full validation,
conditional on that gate succeeding before declaring the engine green. Adoption
is justified only as bounded proof-work reduction plus observed first-step
improvement, with both opening regressions and mixed warm observations explicit.
This signoff does not authorize main merge, default format activation, mature
construction/endurance, or closure of Stage0.6/U10 performance targets.

## Declined to judge

- Mature-world performance, interactive latency targets, endurance, and scaling
  beyond the authenticated small input; none were run or authorized here.
- A statistical latency distribution from the small number of sequential raw pairs.
- Hostile arbitrary Python reflection, base-class API bypasses, ctypes/native
  memory access, or process-level attacks; the existing connection guard is a
  SQL capability boundary rather than a Python sandbox.
- Unexecuted platform/runtime combinations or new hosted CI results.
- Byte-identical per-attempt publication commitments; semantic saved/continued
  state equality is the relevant independently observed diagnostic invariant.
