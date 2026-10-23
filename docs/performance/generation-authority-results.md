# Inactive generation manifest bindings

The new `persistence_proof_generation.py` binds seven explicit component-root slots to exact store identity, generation/parent commitment, physical format/codec/schema/rules, raw head fields, incarnation allocator and existing encoded commit-token/receipt checksum. It provides a canonical2MiB-bounded binary codec, checked raw current/previous-generation reader, adjacent-successor binding and pure protected-root inventory. It adds no production root constructor, writer, format capability, World bypass or collector.

External expected authority is mandatory. Synthetic roots in tests only exercise binding behavior; hashing those roots does not verify complete World semantics. Current source reads compare physical head bytes, retained allocator and fixed metadata. Historical raw head/receipts rely on externally accepted immutable bytes because previous save_head rows and overwritten/released writer receipts are not permanently available. Historical ordinary payload availability remains gated.

Parent CI40013683423 was authenticated for09b8dc25/runtime985952d:3522tests +2subtests,428dedicated proof cases,9diagnostics. Both artifact ZIP SHA256s,11source receipts and XML zero errors/failures checked. Raw receipts in run-40013683423/.

Verification:34codec cases first failed with missing module, then passed.24source/protection cases failed with missing APIs, then passed alongside the34codec cases. An additional direct physical UUID mutation failed to reject before binding the actual store_metadata UUID. Independent review ran59cases, found no functional defect and one parser-test coverage gap; independently matching malformed hashes proved runtime rejection. Corrected ingress tests failed6cases with a temporary parser-bypass mutant and passed with the byte-identical production source restored. Final affected output/CI launch are recorded in the ledger and launch receipt.

The source fixture contains1000unrelated archive bodies. Checked source reads issue no queries to archive/body tables and invoke no World payload decoding. This package records no new World startup/save/year timing and makes no performance-target acceptance claim.

Next: complete verified component-root directory/target/inventory construction and retained ordinary content availability; then atomic generation proof publication through the existing store commit/frozen participant protocol, compatibility/fencing and canonical World admission. Changed-row/root bindings and recovery failure phases must pass before enabling the format. Protected root inventory is not garbage collection or proof of body availability.

All scope rulings and review limits: generation-authority-ledger.md and generation-authority-review.md.

Final affected suite:581 passed in57.09s, including60generation tests. Candidate [40028259840](https://github.com/rax0h/all-that-endures/actions/runs/40028259840), head`6d8f2193fd67fe94adde409c39525384115ca57d`, runtime`79a9ad08c0b77e09c24c23aef0573661af9353cf`. Queued at launch; full-suite acceptance pending.
