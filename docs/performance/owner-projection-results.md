# Physical-owner reference projection checks

Accepted predecessor [CI39961497870](run-39961497870/acceptance.json):3407 tests plus2 subtests,313 proof cases and all seven diagnostics; downloaded hashes/source authenticated. This successor joins selected physical-owner content bytes to complete committed placements. It remains inactive in World.

## Implemented boundary

`read_owner_projection` requires both externally accepted version and owner-occurrence certificates in one owned guarded snapshot. It fetches/checks one actual source, privately parses closed storage values, validates the existing adapter's schema/key/memberships, and compares every projected raw path/incarnation against root-selected checked physical placements. It preserves original source bytes and returns a count; it does not restore a World object, discover targets or admit canonical objects.

Existing adapters cover history pages, entries, permanent-ID sequence leaves, registered-record headers and native NaN-key bodies. Key-side/frozenset/Ref references and all four existing reference tags retain their existing path semantics. Native mutable records/envelopes are rejected before restoration. Standard head metadata containers are allowed only through a closed preflight check before inherited snapshot decoding. Custom/subclass/instance codec hooks require another checked path. Actual canonical/cached record and occurrence/state interval indexes are mandatory, with no hidden construction or legacy fallback.

Default selected-body and metadata limits are1MiB each; max references4096; fields4096bytes; parsed JSON inventory32768 nodes/depth64. Arguments can request1..64MiB for bytes/metadata and1..4096 references; zero-reference bodies remain valid. Parsed memory follows the explicit selected-body budget, not a universal2MiB bound. Public budget failures use ProjectionProofBudgetError; schema/codec failures use StoreIntegrityError. Arbitrary borrowed transactions are rejected; nested checked snapshots share the owner and failures close only owned transactions.

## Measured work

| Unrelated physical bodies | Current / old / successor proof SELECTs | VM upper bounds | Current / old / successor heap | Current / old / successor time |
|---:|---:|---:|---:|---:|
| 1,000 | 20 / 20 / 6 | 3099 / 3599 / 2999 | 138,983 / 19,597 / 16,052 B | 46.029 / 20.916 / 15.601 ms |
| 10,000 | 21 / 21 / 7 | 3099 / 3599 / 3099 | 25,442 / 16,392 / 16,484 B | 16.685 / 12.868 / 7.911 ms |
| 100,000 | 22 / 22 / 8 | 3099 / 3699 / 2999 | 25,474 / 17,172 / 15,820 B | 15.469 / 14.879 / 14.866 ms |

Every result is exact. Each measured operation selects/checks exactly one source payload, with zero child/archive payload SELECTs and no store World decoding. Current/old bodies have4 references and187bytes; successor has1 reference and41bytes after real replacement/deletion. Original bytes are compared literally. The first1k current call includes a139KB allocation peak; later peaks are smaller. These are not cold/warm latency distributions.

[Clean measured source](owner-projection/scaling/source.json): 1dec047bf3b9262fa86b13b631eff970cecd4259, runtime c7c87217e0fb7ec67a93a49003767ef0d785480a; driver/fixture hashes recorded. [Complete repaired matrix](owner-projection/scaling/summary.json).

Instrumented single observations, no latency distribution or matched World speedup. Filesystem caches are sequential/warm/uncontrolled. SQLite main/temp caches2MiB each and temp_store FILE; Python clean-proof cache0. VM upper bounds use100-instruction ticks. One selected storage body IS privately parsed; the store's World-decode counter excludes that parser. Do not interpret its zero counter as no decoding work. Full fixture/row-verified proof construction, full successor reconstruction, genuine owner transition, database size and lifetime RSS are reported separately.

Synthetic full row verification is not complete production graph construction. Target bodies deliberately remain outside this component's responsibility. These observations prove bounded selected-owner work for this fixture, not complete production topology or World point-save acceptance.

## Review and tests

30 missing-module cases were RED. The initial implementation passed36 focused and113 projection/occurrence tests. Fresh review found three Important isolation/error-contract defects: inherited head metadata could restore native records, an escaped-surrogate path could raise outside StoreError, and delegated budgets escaped the declared exception type. Six regression cases reproduced RED before a single repair pass. A seventh test covers delegated occurrence-field budgets. Corrected evidence supersedes the pre-repair scaling run. [Review, all rulings and deferred minor](owner-projection/final-review.md).

43 projection cases and449 affected proof/store/failure/validation-scope/identity cases pass (209.69s affected suite). AST/YAML/bash checks pass. Source/config/docs whitespace checks pass with raw *.log evidence excluded. Full successor simulation suite remains pending CI; predecessor success does not establish this runtime.

Raw pytest logs are retained verbatim and contain trailing whitespace. Source/config/docs whitespace checks explicitly exclude *.log; a whole-range whitespace check including raw logs does not pass. AST/YAML/bash checks are independent of that evidence convention.

## Remaining gates

Complete owner/group/link/reference cross-consistency, owner catalog/radix agreement, target existence/kind, retirement/absence, namespace proofs, manifests, retained roots AND ordinary payload availability, verified-copy/writer fencing, atomic existing row/root/head/receipt publication and canonical World admission/consumption. Unselected surplus physical rows never enter a result and still require complete inventory audit. Ordinary World owners/custom codecs need separate checked paths. No format activation, main merge, endurance or mature speed claim; open<=10s/save<=2s/warm year<=1s remain unmeasured.

Successor full-suite and eight diagnostics CI awaits publication/launch. Parent acceptance remains separate; authenticate the new artifacts on green. No long-test polling.

## Published successor

Exact-tree candidate5da550512eb21bad44ea902612f0b1235fe0ad8b matches local51b3297f8ccbf2bb13b67d468d66af271bc7d725 tree58e6149064ce5c3ec49327d2e41dd50cf0ab2cb5 and measured runtimec7c87217e0fb7ec67a93a49003767ef0d785480a. Only sol/durable-proof-map advanced with the exact expected-parent lease. [Run39981711210](https://github.com/rax0h/all-that-endures/actions/runs/39981711210) is queued for the full simulation suite and eight diagnostics. Acceptance is pending; [launch/resume receipt](owner-projection/ci-launch.json). Authenticate new source/artifacts on green, inspect this run on failure. No long polling or predecessor-success substitution.
