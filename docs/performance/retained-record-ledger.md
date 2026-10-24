# SDD ledger — plan: docs/superpowers/plans/2026-10-23-ate-retained-record-proofs.md

Baseline local4010a11 equivalent published e441e0d2. Parent CI40028259840 accepted for6d8f2193/runtime79a9ad08:3582tests +2subtests,488dedicated proof cases; all9diagnostics green. Both artifact digests,11source receipts and zero-failure XML verified; raw evidence in run-40028259840.

Pre-flight: task1 certificate/body layout feeds task2 locked root publication and task3 measurements. Existing record_commitment excludes ordinary query memberships; this package claims content only. Manifest records slot gets a concrete retained content producer, other slots remain separate gates.

Ruling: finish retained ordinary bodies and atomic content-root publication before whole-manifest construction — current ordinary overwrite is an explicit prerequisite — cost if ignored is accepting an old root without readable old content. No World capability is activated.

Task1 complete:18missing-module RED cases, then18 GREEN in1.53s; constructor body-budget RED then added pre-audit metadata probe. Retained raw body reads survive default overwrite and reject missing current roots/corrupt selected bytes.

Task2 complete initial verification:9missing-commit-API RED failures with19existing cases green. Implemented private request at existing commit's final precommit boundary, actual written-row check, read/raise-only proof-aware fault hooks and exact existing recovery composition. Fixed initial CommitResult field mismatch (outcome). Duplicate conflicting2MiB body initially transferred2099439peak bytes and failed the bound; SQL-only equality now rejects without transfer. Final29 focused tests GREEN in2.58s, including rollback, late coherent tampering, lost ack/no replay, no-op and spilled inputs. No World selector/format activation/collector.
