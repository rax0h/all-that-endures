# Scope directory implementation

> REQUIRED: superpowers:executing-plans inline, one final independent review.

Spec: ../specs/2026-10-24-ate-scope-directories.md

1. Write RED tests for complete bootstrap, stable scoped descriptors, exact current/retained/empty page composition, corruption, context and byte/type/transaction guards. Implement explicit checked construction and directory resolution.
2. Write RED for changed query membership and identity moves/deletion, allocator-only stable roots, combined ordinary publication, rollback/SQL callbacks, exact acknowledgement recovery, source tampering, default-writer gaps and spilled inputs. Implement private request staging at the existing final precommit boundary; authenticate actual old/new sources.
3. Measure genuine1k/10k/100k unrelated scope inventories with full bootstrap separate, actual point commits and old/current directory/page resolution. Assert zero unrelated body reads and bounded work. Run affected tests, one fresh review, substantive fix pass if required, final affected suite. Publish exact candidate full CI with existing diagnostics and new scope matrix; leave it running without long polling/main merge/endurance.

Evidence and rulings: docs/performance/scope-directory-ledger.md. Every deferred review finding must be recorded with reason and cost. Do not fill remaining manifest roots with synthetic flags.

Tasks1/2 complete. Task3 local verification, single review/fix pass and final matrix complete; exact candidate CI launch recorded in launch receipt. Full CI acceptance is a separate next-turn gate.
