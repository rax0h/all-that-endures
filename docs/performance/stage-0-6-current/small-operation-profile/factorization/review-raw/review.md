# Independent whole-package review: SQL proof-node factorization

Verdict: **PASS for the bounded implementation and local diagnostic claims.**
No actionable Critical, Important, or Minor findings were identified. This is the
one independent package review requested for this group, performed by one reviewer
without delegation. It is not a hosted engine-green receipt or mature readiness
approval. Those remain separate gates.

Reviewed local base: `aa35dfe2b47bbbb4b53c78fd9644bf96f0cd60a9`;
baseline engine tree: `94267bb00a219702a4bd1700a2fc0600a5c5aa56`.
`verification.json` records SHA-256 for every candidate engine source file, the new
test module, and the diagnostic driver. `evidence.json` records exact additional
reviewed file/artifact hashes and extracted observations. Runtime engine files
were unchanged throughout review. Reviewer writes are confined to this directory;
no tree/index/HEAD modification, publication, CI launch, or subagent was used.

## Scope and integrity assessment

| Boundary | Source location | Assessment |
|---|---|---|
| Physical SQL fetch | `simulation/ate_sim/persistence_proof_store.py:32` | Private fetch preserves exact address types, missing-row refusal, pre-transfer SQLite BLOB/length gates, bounded bytes, counters, and physical-domain digest validation. It grants no canonical certificate. |
| Public read and collision | `simulation/ate_sim/persistence_proof_store.py:27`, `:72` | Public read still decodes; unchanged INSERT OR IGNORE collision path calls public read before byte equality. |
| Outer map validation | `simulation/ate_sim/persistence_proof_map.py:33` | File unchanged. Exact Root validation, independent map-domain digest, canonical decode, child count and required-prefix checks remain on every fetched edge. |
| Direct canonical parser | `simulation/ate_sim/persistence_proof_nodes.py:90` | Tag, maximum size, exact leaf length, prefix length/padding, child inventory length and 2–16 count remain checked. Added direct checks retain strictly increasing 0–15 slots, positive counts and total MAX_COUNT limit. Eight-byte parsed counts cannot exceed MAX_COUNT individually. Exact-length inventory gives 32-byte digests; constructed tuples/Root/int/bytes preserve encoder type invariants. |
| Production SQL binding coverage | `persistence_proof_record.py:78`, `reference.py:49`, `scope.py:103`, `publication.py:50`, `world.py:42`, `occurrence.py:249`, `query.py:165`, `version.py:126` under `simulation/ate_sim/` | All eight callback sites switch only reads. Writes, memory-only maps, reference-only maps, hash domains, encoding and gameplay remain unchanged. |
| Regression CI wiring | `.github/workflows/stage-0-5-proof-map-validation.yml:99` | The 17 new controls are added to the existing proof primitive step under pipefail, with distinct log/XML. Existing artifact collection covers them. No extra job or change to mature-request activation. |

No cache, trusted flag, certificate reuse, placement optimization, wire/domain
change, gameplay change, old-trigger edit, or default-format activation is in the
reviewed engine/workflow diff. Canonical node bytes and deterministic map roots
retain the existing encoder and hash functions. This statement does not assert
identical whole-database bytes or per-attempt manifest commitments.

## Verification performed and evidence inspected

I ran `review-raw/verify.py` under the exact qualified313 interpreter, with
`PYTHONDONTWRITEBYTECODE=1` and `PYTHONPATH=simulation:.`. It completed with exit0
in under one second:

- 16,086 differential old-HEAD/candidate decoder cases: 8,617 accepted and
  7,469 rejected identically. Cases cover all 64 prefix lengths and 15 child
  inventory sizes, MAX_COUNT aggregate boundary, random and targeted mutations,
  truncation, surplus bytes, random byte strings and non-byte inputs. Accepted
  immutable node representations and re-encoded bytes match exactly.
- Nine direct private-boundary probes reject TEXT (including initial NUL),
  INTEGER, REAL, oversized BLOB, missing row, invalid address, mismatched outer
  count, mismatched required prefix and corrupted collision readback.
- Live interpreter hash, system interpreter hash, Python/compiler, SQLite version
  and source ID/options, extension hash, and loaded SQLite library paths/hashes
  exactly match both `runtime-fingerprint.json` and qualified-local-runtime.json.

I inspected the existing focused log/XML: **75 passed**, including the 17 new
controls and canonical bytes/domain vectors, malformed nodes, root/path/count
failures, transaction/rollback/savepoint/collision and BLOB-transfer bounds. I did
not repeat that unchanged green suite. The RED logs show doubled node parsing
across all factory families and all three checked readers, plus decoder encoder
work. Some initial RED cases also fail because the new private method does not
yet exist; those alone are not evidence of the duplicate-work defect.

I also ran `git diff --check` over the reviewed engine/workflow changes; it exited0.
The root agent's separate affected-suite result is recorded in `evidence.json`
when available and is not represented as a suite independently rerun by me.

## Diagnostic and claim assessment

`compare.py:23–35,53,116–127` records actual working engine-file hashes and checks
both parent/fresh-process ate_sim imports are confined to the selected source;
engine source is checked unchanged at completion. This fixes the earlier HEAD-only
labeling weakness for this bounded diagnostic. I independently compared every raw
baseline runtime hash against HEAD and every candidate raw/profile runtime hash
against current files. Exactly the ten declared engine modules differ. Both raw
reports record the same authenticated 26,206,208-byte generation0/year1 source,
SHA-256 `2555675bd19ede5c6ed9b7619fab56d59098a8b358d9a9c3569cabccba22c554`,
and source preservation. This is a controlled local diagnostic, not a reusable
security attestation against adversarial concurrent source/bytecode replacement.

Raw save improves6.245→4.964seconds and warm7.805→6.087seconds in the one recorded
sequential pair. The report correctly limits these to observations, explicitly
retains missed2s/1s targets, and keeps mature preparation paused. It does not add
nested cumulative profile times or conflate instrumented and raw latency.

Separate profile data confirms unchanged save/warm map reads54,080/42,840 and
physical SQL-node fetches54,366/42,840. Canonical decodes fall112,578→58,537 on save
and85,680→42,840 warm; encodes93,861→4,213 save and68,994→0 warm. Save includes
writes and public collision reads, so its decode count need not equal map reads.
The remaining1,295 owner-change and913 identity-descriptor calls are correctly
reported without implementing another optimization.

Both raw runs and the candidate profile freshly restore exact generation1/year2,
seed843000, digest
`cebc2fcd2660db6e87b9c29c3c8e88536a831214c306991778fba6ee58cc7451`.
Their fresh year3 continuation matches each in-memory warm continuation and equals
`a46d627d11ce2c12ff8f6fe0f14d01af35006afd56bdad3bf16417379b0166f3`.
`compare.py:90,103,109–115` supplies each attempt's saved commitment externally to
the fresh process. Different saved commitments are expected: unchanged
`persistence_lazy.py:14514` creates a UUID token;
`persistence_proof_manifest_publish.py:30–38,241` incorporates writer/token receipt
and token-bearing commit marker; `persistence_proof_generation.py:81–106` includes
receipt bytes in the manifest commitment. No cross-attempt commitment-equality
claim is supported or needed for this parser factorization.

## Declined to judge

- Hosted full-suite/proof green status for this exact candidate; new greens are
  mandatory before changing runtime/green authority. Old94267 greens do not apply.
- Mature performance, endurance, distributional latency or general scaling from a
  single small paired sample; the targets still miss.
- Universal Python/SQLite compatibility or an engine-only explanation of earlier
  runtime failures; qualification is scenario-specific.
- Remote branch/tree reconciliation or publication success; review is local and
  did not access or mutate the remote.
- Equal database bytes or equal per-attempt manifests, neither of which this
  diagnostic records or claims.
- Proposed future cache/placement changes, mature execution, or default activation.

There are no findings to defer. Recommendations are limited to preserving these
claim boundaries and completing the already required exact-candidate engine-green
gate before any harness authority update.
