# Stage0.6 real-world proof continuation repair

This package repairs the existing explicit proof bridge; it does not activate
the format by default or establish mature-world performance acceptance.
Base:7b0f69451f98110af61450384919d268266f1f29, including the scheduled task's
profiling additions. Runtime repairs were developed againstb524bbe2; the rebase
changed only harness, attribution tests and documentation, not runtime code.

## Consolidated findings

| ID | Origin and defect | Resolution | Evidence/status |
|---|---|---|---|
| W1 | Generated-world bootstrap: partnership projection passed event ID without person-pair key | Supply the logical `(pair,event)` entry to the existing membership validator | Original generated-world failure reproduced; valid/self-pair and missing/wrong-person/wrong-order tests pass |
| W2 | Same bootstrap: runtime type hints cannot resolve type-only ResponseModel import | Supply the exact declared class locally for AbilityProgress hint resolution | Schema-wide persisted-field hint regression reproduced RED then GREEN |
| W3 | Same bootstrap: bare list annotation rejected valid ResponseModel sample backing | Treat bare container annotations like their parameterized origins | List/sequence/frozen-list accepted; map/set rejected; RED then GREEN |
| W4 | First complete-year save: social-edge collection ordinal disagrees with query membership ordinal | Order new/reinserted native owner slots by their recorded overlay order before freezing publication bytes | Reproduced ordinary save silently reordering reverse-key insertions; ordinary/proof tests preserve insertion, query and reopen order, reinsertion and discarded-new-key gaps |

W4 applies the repair centrally to the existing native owner plans, including
scalar families. It visits prepared changes and structural overlays only. It
does not enumerate unrelated history, invent another writer or change immutable
replay/recovery authority. Auxiliary rows and existing update slots retain their
order. W1 retains exact query-value/ordinal comparison; W2/W3 retain declared
container and record type validation. No corruption check was disabled.

The complete-year regression generates seed843000,8x6,one settlement,mature
initial magic, advances to year2, then runs years3 and4 through proof sessions.
Each year saves, closes and restores in a fresh interpreter using the externally
held commitment. Both restored canonical digests match an independent eager
control. Parent commitment continuity is asserted; no SQLite transaction spans
the simulation step. This is a small real world, not a1001year performance fixture.
Final new-test gate:17passed141.32s; complete-year case136.89s. Earlier same-process
variant passed119.36s. These are test execution times, not mature latency receipts.

## Remaining architectural performance gate

The native bridge already exists. Normal complete-year changes can create or
retire owners/backings, change queries, and advance allocators. In
`persistence_proof_manifest_publish._stage`, these invalidate the limited
value/tail reuse conditions and select `_audit_world`. `_WorldProofAuthority`
also audits reaudited committed saves. Explicit initial admission performs a
full audit. The integration failures above are repaired; the general transition
and admission paths still do history-wide work. The small continuation test
does not close this gate or justify running the old mature benchmark again.

Remediation must extend the existing authenticated transition machinery:

1. Attribute full-year proof save phases with the existing optional profiler;
   count full-audit fallback and unrelated owner/body reads explicitly.
2. Authenticate affected native owner changes, their old/new query projections,
   collection ordinals, identity occurrences and backing retirement closure
   against the accepted parent. Reuse existing content/scope/directory/inventory
   primitives; update only their touched paths and aggregate world facts.
3. Keep full-audit fallback for unsupported transitions until equivalent
   corruption-sensitive coverage is proven. Do not skip an audit solely because
   a previously trusted root exists, or weaken fresh admission guarantees.
4. Extend this real-world differential test with corruption/rollback/recovery
   and history-growth cases proving unchanged ancient owners are not read.
   Then measure the retained year1001 fixture at an exact candidate SHA.

Separate measured first-year target: the authenticated60second sample shows
repeated living-person selection and identity loading; its inclusive function
times overlap. Optimizing that selection must preserve Person identity,
birth/death/resurrection invalidation, ordering and duplicate household
occurrences. Do not substitute mapping keys for Person.id without proving that
contract, or mistake a sampled prefix for a full-year measurement.

The acceptance requirements remain mature open10s,warm year1s,incremental save2s;
first year/fresh restore have no separate established numeric target. Mature
performance and long-horizon scaling remain open in Issue18. This package is a
correctness integration repair, with the next performance work precisely located.

## Independent review and final validation

One completed independent Astra/high whole-package review:0Critical,0Important,
1Minor evidence housekeeping item. Its original report is preserved in review.md.
The prior review session was interrupted before a final result and is not counted
as approval. No second independent approval is claimed after author closure.

| ID | Origin | Action/evidence | Status |
|---|---|---|---|
| R1 | Independent review: partial/failed targeted-test log could be mistaken for evidence | Earlier90s run timed out without a verdict; resumed environment initially lacked pytest. Neither is counted as passed. Dependencies restored, replacement7-file regression completed124passed119.12s, targeted.log/targeted.xml | Closed |
| H1 | Exact benchmark launcher gate rejects the new runtime tree | Original27passed/2failed source-fence check correctly rejected old pinned tree; pin updated tod4b1e1edf9469c1672752260128749e4eef72d2f after independent runtime review. Source/fixture/green-ancestor checks retained; clean-checkout revalidation recorded below | Closed:29passed21.23s from clean checkout, harness.log/harness.xml |

The124-test gate includes proof-world admission/manifest/value, native sessions,
frozen publication and abort/recovery, ordinary social saves and the remote
profiling additions. New17-test continuation gate is recorded separately.

The scheduled continuation published harness-only additions through7b0f694 and
started run40878875434 before this package was ready. That run cannot validate
these runtime repairs. This runtime-changing package requires one bundled
full-suite/proof validation after local checks; no mature benchmark, retention
request, default activation, merge or endurance run is launched by it.

Clean-checkout benchmark fingerprints, proof workflow YAML/bash syntax and git diff whitespace checks passed. No full benchmark or fixture request was launched. The reviewed source pin identifies the candidate runtime, while green_commit continues to identify the historical correctness ancestor; a new full green is not invented. The reviewer's log observation refers to the working log during the failed setup attempt, not an assertion that that attempt passed.
