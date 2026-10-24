# SDD ledger — plan: docs/superpowers/plans/2026-10-23-ate-retained-record-proofs.md

Baseline local4010a11 equivalent published e441e0d2. Parent CI40028259840 accepted for6d8f2193/runtime79a9ad08:3582tests +2subtests,488dedicated proof cases; all9diagnostics green. Both artifact digests,11source receipts and zero-failure XML verified; raw evidence in run-40028259840.

Pre-flight: task1 certificate/body layout feeds task2 locked root publication and task3 measurements. Existing record_commitment excludes ordinary query memberships; this package claims content only. Manifest records slot gets a concrete retained content producer, other slots remain separate gates.

Ruling: finish retained ordinary bodies and atomic content-root publication before whole-manifest construction — current ordinary overwrite is an explicit prerequisite — cost if ignored is accepting an old root without readable old content. No World capability is activated.

Task1 complete:18missing-module RED cases, then18 GREEN in1.53s; constructor body-budget RED then added pre-audit metadata probe. Retained raw body reads survive default overwrite and reject missing current roots/corrupt selected bytes.

Task2 complete initial verification:9missing-commit-API RED failures with19existing cases green. Implemented private request at existing commit's final precommit boundary, actual written-row check, read/raise-only proof-aware fault hooks and exact existing recovery composition. Fixed initial CommitResult field mismatch (outcome). Duplicate conflicting2MiB body initially transferred2099439peak bytes and failed the bound; SQL-only equality now rejects without transfer. Final29 focused tests GREEN in2.58s, including rollback, late coherent tampering, lost ack/no replay, no-op and spilled inputs. No World selector/format activation/collector.

Author epoch check: coherent second-connection write during preparation originally escaped the operation's accepted-parent epoch (RED DID NOT RAISE). Request now captures data_version inside parent snapshot and checks after release and inside writer before proof publication. Added independent actual-written-row corruption test outside phase hooks, proving the staged byte comparison itself rejects.31 focused cases GREEN below; genuine scaling driver measures the actual existing commit separately from full fixture/audited bootstrap.

Final independent review:31cases passed in2.60s; four Important findings, no Critical/Minor. Pre-fix new regressions completed17failed/4passed/31deselected in2.02s (completion summary retained; full redirected background log unavailable). One fix pass: SQL read-only callback capability preserving existing authorizer prevents transaction escape/writes before execution; noncommitted recovery binds actual parent generation/pin/source; bootstrap guards ordinary source metadata/revision before audit. Added6executescript variants, preserved-authorizer/removal and missing recovery source. Final focused60passed in4.32s. Final broad suite and matrix below.

Final: Ruling: complete manifest, World admission, format activation, old-writer fencing and collection remain gated — this is one actual content root inside the existing transaction — cost if ignored is mistaking retained ordinary bytes for complete World authority.
Final: Ruling: full World performance/endurance/final CI are separate gates — actual ordinary point-save samples do not represent a whole mature-year save — cost if ignored is falsely claiming target latency.
Final: Ruling: inherited full audit of unrelated lazy/segment inventories is explicit bootstrap archive work — it stays outside point save/read timers and is not advertised as bounded by ordinary body limits — cost if ignored is unexpected bootstrap time/memory.
Final: Ruling: arbitrary Python replacement of private implementations is trusted-process behavior — the guard restricts SQL callbacks while preserving caller authorizers; it is not a Python sandbox — cost if ignored is treating in-process malicious code as an integrity boundary.

Final fix pass verified:60focused cases GREEN in4.32s;641affected cases GREEN in59.09s on native SQLite3.45.1. The4Important findings and additional missing recovery-source case are covered; all prior581affected cases retained. No second review. Source syntax/whitespace verified; final workflow checks below.

Final actual scaling: measured local48e7623/runtimefe161613. At1k/10k/100k unrelated ordinary records, actual existing proof-aware point commits24.18/21.49/22.49ms; Python peaks153141/108439/117934bytes, VM upper bounds2799/2999/2999, zero unrelated payload SELECTs. Exactly1written selected body checked per save; raw current/retained/successor exact with1selected body each. Full fixture/audited bootstrap outside timers. All3size/source/hash receipts verified. This supersedes pre-review samples.

Task3 local verification/review/scaling complete. Full candidate suite and all10scaling matrices will run in existing CI; full World timing/admission remain gated. Candidate/launch receipt below. No main merge/endurance/long polling.

CI allocation: proof job now has10full scaling matrices including an audited100k-record bootstrap. Increased aggregate job budget20→30minutes; each individual diagnostic retains its15minute bound. Workflow change launches the exact candidate after incremental skip-CI checkpoints; runtime is unchanged from verified scaling.

Task3 publication complete: candidate b80fd5a7c658e55963beba40123779287c8bae9b tree 853f88de5b0a315ac5725005bd32952edcfb8571 runtime fe161613a47b3a4eebebd58b1dd5c0b5da7dda8d matches exact local candidate and measured runtime. CI 40051989785 in progress at launch. Full-suite acceptance pending; no main merge/endurance/long polling. All implementation/receipts checkpointed on GitHub.

Accepted next turn: exact CI40051989785 successful;3642tests+2subtests,548proof cases,10diagnostics,12source receipts, both artifact digests and driver/fixture hashes authenticated. Hosted ordinary point save27.50/26.04/31.63ms with zero unrelated body reads. Full World timing remains unmeasured.
