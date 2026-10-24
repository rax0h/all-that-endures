# Content publication ledger

Accepted exact parent CI40070133798:3697tests+2subtests,603proof cases,11diagnostics,13source receipts; artifact/source/XML verified. Restored pruned checkout from GitHub headcc76716e; accepted runtime770b634ceddae1aa6542b98f3861da6f1f7b0de9. Scope point saves110.57/112.23/119.45ms hosted; full World timings still unmeasured.

Ruling: complete version/event content construction and combine existing component publications in the same writer before complete manifest publication — these are missing production slots, and incomplete synthetic roots would not establish authority — cost if ignored is admitting a manifest whose contents were never verified.

Ruling: allow zero-element segment content preimages, as the existing physical store already permits them — positive preimages remain unchanged and strict integer/type checks remain — cost if wrong is rejecting legal archived empty segments during construction.

Pre-flight interfaces: ContentCertificate generation/store/codec must match ordinary/scope parent authority; the existing scope request owns early snapshots/guards and deferred cleanup. No second publisher or World capability. Task3 uses actual unified commit, not a standalone root edit.

Task1 RED:24failures,23missing module and1legal empty-segment preimage rejection. Added constructors/raw readers and extended count admissibility only; positive hash vectors unchanged. Initial GREEN attempt37passed/1failed because duplicate generation surfaced SQLite IntegrityError rather than StoreError; added explicit no-replace guard.38focused/content cases passed.

Task2 RED16missing-commit/recovery API failures with24existing cases green. Unified request checks actual affected predecessor version commitments before inherited writes and exact actual successor version/segment bytes at final stage, composing required ordinary+scope proofs. Initial implementation39passed/1invalid reinsert fixture: cleanup after releasing the old pin removed the historical row required by reinsertion=True. Corrected to the existing normal insertion semantics; no production behavior change.40cases GREEN4.74s, then50focused GREEN5.87s with empty append, exact aborted recovery, external epoch, main/temp triggers, stale conflict and strict types. Affected suite running.

Task3 driver: genuine unrelated version/placement/query/event inventories at1k/10k/100k. Full fixture and all component bootstraps separate; actual unified point save and metadata-only sharing. Raw old version comparison excludes mutable valid_to from immutable identity while requiring exact closure to2. Scope/ordinary/content roots share one receipt; complete conceptual seven-root manifest remains gated.
