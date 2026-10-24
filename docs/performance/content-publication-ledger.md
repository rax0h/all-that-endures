# Content publication ledger

Accepted exact parent CI40070133798:3697tests+2subtests,603proof cases,11diagnostics,13source receipts; artifact/source/XML verified. Restored pruned checkout from GitHub headcc76716e; accepted runtime770b634ceddae1aa6542b98f3861da6f1f7b0de9. Scope point saves110.57/112.23/119.45ms hosted; full World timings still unmeasured.

Ruling: complete version/event content construction and combine existing component publications in the same writer before complete manifest publication — these are missing production slots, and incomplete synthetic roots would not establish authority — cost if ignored is admitting a manifest whose contents were never verified.

Ruling: allow zero-element segment content preimages, as the existing physical store already permits them — positive preimages remain unchanged and strict integer/type checks remain — cost if wrong is rejecting legal archived empty segments during construction.

Pre-flight interfaces: ContentCertificate generation/store/codec must match ordinary/scope parent authority; the existing scope request owns early snapshots/guards and deferred cleanup. No second publisher or World capability. Task3 uses actual unified commit, not a standalone root edit.

Task1 RED:24failures,23missing module and1legal empty-segment preimage rejection. Added constructors/raw readers and extended count admissibility only; positive hash vectors unchanged. Initial GREEN attempt37passed/1failed because duplicate generation surfaced SQLite IntegrityError rather than StoreError; added explicit no-replace guard.38focused/content cases passed.

Task2 RED16missing-commit/recovery API failures with24existing cases green. Unified request checks actual affected predecessor version commitments before inherited writes and exact actual successor version/segment bytes at final stage, composing required ordinary+scope proofs. Initial implementation39passed/1invalid reinsert fixture: cleanup after releasing the old pin removed the historical row required by reinsertion=True. Corrected to the existing normal insertion semantics; no production behavior change.40cases GREEN4.74s, then50focused GREEN5.87s with empty append, exact aborted recovery, external epoch, main/temp triggers, stale conflict and strict types. Affected suite running.

Task3 driver: genuine unrelated version/placement/query/event inventories at1k/10k/100k. Full fixture and all component bootstraps separate; actual unified point save and metadata-only sharing. Raw old version comparison excludes mutable valid_to from immutable identity while requiring exact closure to2. Scope/ordinary/content roots share one receipt; complete conceptual seven-root manifest remains gated.

Pre-review affected746passed83.56s. Initial exact-runtime matrix at2ad91a0/runtime686ae88b:113.57/109.88/135.33ms at1k/10k/100k, zero unrelated bodies; current/retained exact and all implemented components share existing receipt. Superseded by review-fixed matrix below.

Fresh reviewer:64publication/content cases6.17s;2Important, noCritical/Minor. TEMP shadows could redirect durable roots; inherited full audit bypassed byte guards on non-content sources.17RED regressions (10shadow objects including ASCII case alias,7all-audit source categories). Single fix pass adds shared persistent-source guard to content/scope/ordinary schemas and complete pre-audit per-field type/byte/counter probes.67focused GREEN8.43s. All4declined-scope rulings/costs in content-publication-review.md. Final affected/matrix pending; no second review.

Final affected: command71899 exit0,763XML cases zero failures/errors/skips,91.549s. Background stdout/log truncated at progress despite valid final XML; explicitly named partial log and completion JSON retained, no full passing console log claim.

Final matrix measured2e5e576/runtime4233da09ca3b5057ef5a4dda6e4bd0bde3e52714:117.97/160.38/114.57ms at1k/10k/100k. Peaks231480/176411/170110bytes; VM24499/25199/25399;0unrelated bodies,4selected version/1ordinary/1event body SELECTs plus2boolean probes,5checked bodies and0World decodes. Metadata-only23.42/27.79/23.33ms shares all implemented roots. All3source/driver/fixture receipts and exact current/retained/successor values verified. Full100k fixture/audited construction100.03s outside timers. One sample per size, not World acceptance.

Local gates complete:67focused/763affected, one fresh review and one fix pass, all4review scope rulings/costs retained. Final workflow runs all existing diagnostics plus new content matrix (12total); full candidate acceptance pending. No main merge/endurance/long CI polling.

Publication complete: exact candidate 1573bd1bc3b702542aea3de2d512d349828756fa treef6197cb21f50a2ad7f85d2c99e403e2429c6aaa5 runtime4233da09ca3b5057ef5a4dda6e4bd0bde3e52714 equals local ac4b1868dfc717db7535c4332cdb402a736f1c55 and final measured runtime. CI40098756156 in progress at launch; full candidate suite/all12diagnostics acceptance pending. All code/receipts checkpointed on GitHub; no main merge/endurance/long polling.
