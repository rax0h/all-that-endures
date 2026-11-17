# Proof source audit repair

## Observed failure

[Mature run 43918798385](https://github.com/rax0h/all-that-endures/actions/runs/43918798385), public `71967a3d`, failed in **proofs** at its 12,600-second compute cap. This was not the 350-minute job timeout. Gate passed 399 cases; rebase and exact after-digest both completed. Measure/fresh-restore/acceptance never ran. There are no new mature operation timings.

Construction reached records at 20:31:36 UTC, scopes at 21:07:03, content at 21:37:24, directory at 22:15:55, inventory at 22:39:01 and World manifest at 22:42:31. The final interrupt at 23:58:32 was in `_check_sources`'s version loop, `ProofMap.get -> _read -> decode_node`. Process logical read counters are not physical disk reads. The interrupt location alone does not establish a node-decoder bug.

## Measured cause and bounded change

The old complete source comparison separately traversed a checked proof path for every version, ordinary record and event segment. Proof-node SQL uses the `(map_domain,digest)` primary key; the generation-zero source interval lookup is keyed. This investigation found repeated indexed reads, hashes and decodes, not evidence of the earlier quadratic namespace scan.

The qualified local reproduction uses real `LazyRecordStore` source validation and SQLite proof storage. At 8,193 version rows, the initial comparison performed 40,772 checked proof-node reads. Profiling attributed most of this loop's time to repeated `ProofMap.get` traversal. The candidate compares a SQLite temporary spool of fixed-size `(locator,commitment)` pairs against one checked `iter_leaves` traversal. The initial candidate made 11,347 node reads and was approximately 2.9 times faster for this synthetic loop. Final exact observations and profiles are in `validation.zip`; these are not mature or end-to-end speed claims.

All original physical version/event validators and ordinary commitment inputs remain. Duplicate source locators are rejected. Both streams must match in order and exhaust together; source count must match the accepted root. Every reachable node is fetched, digest/encoding/path/count checked through the existing reader. There is no retained node cache, no changed schema or stored format, and no new World authority. The spool belongs to the existing owned audit transaction, stores no payload bodies and is removed on success or failure. Root/component/custody checks and the rest of `_audit_world` remain.

The regression ran the real full World audit before repair: 4,573 version proof reads for 1,460 distinct reachable nodes. Rechecking that identical retained input with the candidate reads those same 1,460 nodes once. Additional controls cover missing/extra/replaced/altered commitments, duplicate locators, corrupt/missing nodes, child paths, wrong domains/counts, canonical empty roots, unowned transactions, repeat audits after corruption and cleanup after source failure. Cleanup retains a primary failure and attaches a secondary cleanup note; cleanup-only failures remain fatal.

## Retained restart boundary

The last completed restart unit is **after_digest**, metadata **14267625292**, receipt SHA256 `8ecefa051366563baa88a93efa3e4eb169335f351af8370bce846d5796aa5792`. Its closed database is the rebase output **14261110486**, 29,409,034,240 raw bytes, SHA256 `b1c7ffcd9379d246002d9052065a44d5de539606bb00c43ef7997785962521a5`, format 6, generation 0, year 1001, seed 843000, identity `6d0b5191-fd61-4bb8-845a-4dddbd0e3213`. ZIP size is 4,447,495,807 bytes and SHA256 `bc71ac9e13f1d422cb2e242a9ae17613c9d1dc60a9e0db0ad52a668cf31ffd82`; expires December 16, 2026 at 19:08:03 UTC.

`authenticate-retained.py` checks exact downloaded metadata/evidence archives against raw API metadata, successful producing jobs and their exact successful upload/seal/publication-step windows, recursive receipts, all 50 original producer helper blobs, engine/ancestry, original catalog cut, historical contract bytes, unchanged original source-control receipt and hosted runtime signature. The production authenticator receives untouched raw jobs so ambiguous duplicate publications are rejected. Exact checkpoint/database refs match retained failure/input references. The 4.4 GB database was not downloaded for this investigation; its previously published raw hash is a retained descriptor, not a new local hash measurement. `retained-authenticated.json` records the result.

The incomplete proof transaction has no retained closed output. Its restart unit remains the entire **proofs** stage. Rebase/after_digest must not be rebuilt blindly. Current ordinary compatibility correctly rejects a changed engine; **new-engine checkpoint admission is not implemented by this repair**. The inherited catalog cut must remain attached and must be validated against its original producer contract. A later explicit proofs-to-after_digest handoff must pin both chains, exact old/new engines/helpers, actual new green qualification, source/rules/digests and runtime, and prove small crash/transport/retry/fresh restore. Do not relabel receipts or widen the old catalog contract.

## Qualification and next measurement

Candidate engine is `5464caa49acc4c27f24c247b60ee639afd9d150d`; previous qualified engine remains `0d9dab5d`, green `1de9adc6`. Only `persistence_proof_world.py` changes in the engine. The canonical-source compatibility declaration names the candidate tree; only its exact fingerprint changes in the old launch request. Historical source, gameplay, control and expected year-1002 digest are unchanged. This declaration does not qualify or admit the candidate; launch constants and the existing mature request stay bound to the old green engine.

1. Finish bounded regressions, affected integrity/recovery checks and one independent whole-package review; close every finding in the consolidated register.
2. Run one bundled hosted harness/proof/full-engine qualification. This push must not activate a mature run.
3. Authenticate the successful new qualification before implementing a separate reviewed after-digest transition and small hosted recovery proof.
4. Measure remaining full scope/collection reconstruction, catalog/topology/fact audits and source comparison before committing to another mature execution budget. The observed loop improvement alone cannot establish that the whole proofs stage fits.

The existing job budgets remain unchanged: proofs compute 210 minutes, restore 30, data upload 45, metadata 5, diagnostics 5 within a 350-minute job. Working-space checks, closed publication reserves and parent preservation remain mandatory. No budget increase, mature retry, Stage 0.6 acceptance, main merge, default activation, gameplay migration or endurance run is part of this qualification package.

Hosted qualification has separate restart units for harness, proof-map and full-suite jobs. Full-suite compute is capped at180minutes within a195-minute job, retaining15minutes for setup/publication; the previous actual suite took9,643.06seconds. Proof-map job cap is90minutes with individual scaling commands bounded; harness compute10minutes plus a2-minute preserved-input consumer within15minutes. Do not rerun completed compatible sibling jobs merely because another job fails. `qualification-preflight.json` records these boundaries before launch.

Local validation:171affected tests passed before review;61focused cases passed after cleanup/authentication/fixture corrections. The complete clean helper run then passed403cases in148.58seconds. After the final duplicate-publication evidence correction,5targeted evidence cases passed; the hosted complete helper gate will include404cases. The first local helper run's398pass/1fail, the intermediate misplaced fixture decorator, review REDs and exact final evidence are preserved rather than treated as green. The qualified engine baseline has not been changed to this untested candidate.
