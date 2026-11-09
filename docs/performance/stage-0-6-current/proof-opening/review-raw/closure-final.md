# Same-seat final closure verification

This closes R1/R2 from the initial independent whole-package review and the focused foreign-token follow-up. It is not a second independent package review.

**Verdict: R1 and R2 closed on the inspected final working-tree source. No remaining concrete issue was established in this closure verification.** The package may proceed to its authorized final source checkpoint, clean serial proof-only year and single bundled hosted full/proof gate. Those gates remain separate; this report does not claim their success or grant mature-world/final-architecture acceptance.

Final closure production/test hashes are recorded in `closure-final-source.json` against HEAD `276d323117cf059f9b6103110e8e6eef083098c2` plus the inspected working-tree fix. Default calls do not pass the new private resource kwargs. This reviewer made no checkout/index/HEAD/branch changes.

## R1 — closed

The lexical `_OpeningResources` now records the exact GenerationPin **after successful INSERT and before COMMIT**, so a rejected duplicate token never becomes owned and a cancellation after durable capture still has its original opaque lease for cleanup.

Fresh independent targeted run: **10 passed, 39 deselected in 13.46s**. This includes the promoted post-COMMIT return cancellation controls for KeyboardInterrupt/SystemExit with the existing foreign pin preserved byte-for-byte; duplicate-token rejection preserving that foreign pin and its connection; the partial/returned session teardown controls; existing borrowed-connection ownership; foreign private-capability rejection; and late-head/cancellation controls. Evidence: `closure-final-focused.log`, `closure-final-focused.xml`.

An additional independent real-SQLite probe cancels at `_remember_pin` entry, **after INSERT succeeded but before ownership registration**, with KeyboardInterrupt and SystemExit. At injection, the owned connection is in a transaction and its owner has no registered pin. Both failures preserve the primary cancellation, roll back the uncommitted INSERT, close the owned connection, and leave the existing foreign pin byte-for-byte unchanged with its connection usable. This verifies the safe side of moving registration after INSERT. Evidence: `probe_closure_insert_before_registration.py`, `closure-insert-before-registration.log`, `closure-insert-before-registration-result.json`.

The original leak and intermediate collision red evidence remain preserved in the initial report, `closure-iteration-1.md` and their linked probes/logs; neither is silently erased by this closed disposition.

## R2 — closed

The lexical owner remembers the session before registry allocation. Failure cleanup can therefore close an allocated registry at constructor handoff, set the session inactive/closed, and tolerate missing registry/state attributes during earlier partial construction. Both promoted allocation/return cases pass in the fresh final 10-case selection.

The independent earlier KeyboardInterrupt/SystemExit controls **before registry allocation** also passed: primary cancellation retained, no registry ever allocated, owned DB closed, zero remaining pins, inactive/closed session. Their evidence is `probe_closure_partial_session.py`, `closure-partial-session.log`, `closure-partial-session-result.json`. `closure-final-source.json` verifies the relevant R2 production source files (`persistence_lazy.py`, `persistence_proof_open.py`) are byte-identical to that verified iteration.

## Limits

The original report's declined-to-judge boundaries remain: externally accepted audited-construction/checked-publication commitments; selected-read corruption guarantees rather than certification of unvisited bytes; live-root/tail work allowed; small-world timing only; qualified workspace runtime only; hosted/full/endurance/mature-performance gates not inferred. No new broad suite or timing benchmark was run by this reviewer. All closure probes and evidence remain under `/tmp/ate-proof-opening-review` for the work group to preserve with its consolidated register.
