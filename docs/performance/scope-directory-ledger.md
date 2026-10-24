# Scope directory ledger

Accepted parent CI40051989785:3642tests+2subtests;548proof cases;10diagnostics. Artifact hashes/source receipts/XML verified in run-40051989785/acceptance.json.

Decision: generation-independent per-scope descriptors inside four generation-bound directory roots. Binding generation/allocator in every descriptor would rewrite all unchanged scopes each save. Existing ordered roots already exclude these fields; outer authority supplies them when resolving a certificate.

Scope: production bootstrap and actual writer integration for owner/group/query physical membership only. Full World topology/target inventory and remaining manifest slots are still required. No World selector or format capability is activated.

Initial bootstrap test run:17failures were fixture-invalid (ordinary and lazy authority shared the people namespace), not valid missing-module RED evidence. Fixed the fixture to a distinct ordinary namespace;17focused GREEN1.53s. Commit API RED13failed/18passed3.20s; first implementation26passed/5failed: cleanup removed parent rows before staging when no old pin, and spill budget(0,0) was an invalid test fixture. Scope saves now defer the same bounded cleanup until after final root staging in the same transaction; valid spill budget(1,1).31focused GREEN3.22s.

Additional adversarial RED2failed: missing old placement left a ghost accepted member; coherent old query+record-membership removal left a ghost query root. Fixed explicit parent owner-point comparison and a fourth directory for complete per-owner query sets. This reverse witness is necessary for bounded complete old membership authentication.33focused GREEN2.66s. More tests cover actual written coherent metadata tamper outside callbacks, strict types, descriptor scope binding, multiple changes/full reconstruction, combined lost ack and noncommitted recovery. External-write test initially performed an SQLite no-op (payload=payload) and was invalid; changed it to a real coherent payload mutation.46focused GREEN4.43s. Affected suite running.

Ruling: complete World topology/targets and remaining manifest producers stay gated; physical scoped membership is necessary but insufficient for admission. Cost of ignoring this boundary is exposing an authenticated relation whose targets or canonical objects have not been validated.
