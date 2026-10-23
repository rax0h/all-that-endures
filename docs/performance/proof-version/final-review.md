# Fresh package review and disposition

One gpt-6-astra high fresh-context read-only review of41962d2..2bd0d3c. No checkout/index writes or expensive scaling/full-suite duplication.

Strengths: independent exact-content binding defeats coherently rechecksummed replacement; expiry-aware LIMIT2 rejects overlaps; source BLOB/type/checksum guards handle early NUL; old pins keep exact bytes; nested failures preserve caller transaction; diagnostic and CI claims distinguish actual scope.

Important finding accepted: inherited _checked_head_row/_checked_pin_row could materialize multi-MiB corrupted operational fields before source guards. In-memory reviewer probes peaked2,101,454B for head_checksum and2,100,550B for pin checksum. Integrity already rejected, but memory remained unbounded.

One executor fix pass: eight cases reproduced RED; capacity case already rejected. A private optional snapshot preflight runs after BEGIN and before checked pin/head fetches, even nested scope reuse. Guarded constant-only metadata probes cover all inherited inventories, bound to existing MAX_PINS64 before bodies transfer. Encoded variable head/token fields share explicit max_metadata_bytes1MiB default, up to64MiB; legitimate large metadata can raise the budget. Semantics/checksums/lineage remain existing validators' authority. No second transaction/publisher/registry. Final54 source tests and306 affected tests passed22.50s. Post-repair scaling remeasured on clean9f26548. No second review.

Critical: none. Other Important: none. Minor: none; none deferred. Verdict: publish only after resolving metadata bound; fix above resolves the issue, with candidate full suite still required. No main merge/World activation endorsement.

Executor rulings on declined items: World activation/canonical admission/topology/manifests/writer fencing remain gated; ordinary overwritten payload/segment retention unresolved; mature speeds unproven; prior CI never substitutes for candidate CI; unread unrelated corruption is outside this point operation and remains fetched-data/full-scrub work. Cost if these rulings are wrong is additional integration/review before release, not weakened authority in the current World reader.
