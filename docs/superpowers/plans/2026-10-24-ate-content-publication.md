# Content publication plan

> REQUIRED: superpowers:executing-plans inline; one fresh final independent review.

Spec: ../specs/2026-10-24-ate-content-publication.md

1. Tests first: real version/segment bootstrap, exact opaque bytes/current/retained/absence, empty segments, closed codec/context/budget/schema/transaction guards. Implement production roots and raw selected readers. Expected: RED missing module/empty-segment contract then focused GREEN.
2. Tests first: unified actual commit changes lazy version, membership, placement, ordinary body and appends an event; parent authentication, actual-written-row binding, delete/reinsert, metadata-only root sharing, rollback/SQL hooks/triggers, external epoch, lost ack/noncommitted mismatches and spilled input. Wire private content request into the existing writer, after checked predecessor guards and before cleanup. Expected: RED missing commit API/adversarial regressions then focused and affected GREEN.
3. Measure actual1k/10k/100k unrelated version/scope/event inventories with full bootstrap separate; assert exact current/retained versions/events and all component roots, zero unrelated body reads and bounded SQL/heap/VM work. One independent review, substantive single fix pass RED/GREEN plus affected suite, exact-tree CI candidate with all existing diagnostics and new content matrix. Leave CI running; no main merge/endurance/long polling.

Pre-flight: task1 ContentCertificate roots feed task2 writer/recovery and task3 diagnostics; ordinary/scope certificates must share exact store/codec/pin/generation. Existing segment preimage rejects0 although physical NewSegment accepts0: extend only the admissible count range, preserving positive preimages. Existing scope request supplies closed preliminary snapshots, source guards and cleanup deferral; compose it rather than adding a second writer.

Review focus: actual old version bytes with coherent physical checksum tampering; new version/segment source binding and zero segments; guards before inherited materialization; callbacks/triggers and epoch races; exact recovery parent/token; all roots atomic on injected faults; unchanged roots reused without archive payload reads. Tracked ledger: docs/performance/content-publication-ledger.md.

Tasks1/2 complete. Task3 local tests, final exact-runtime matrix and single review/fix pass complete; candidate launch recorded in launch receipt. Full CI acceptance remains a next-turn gate.
