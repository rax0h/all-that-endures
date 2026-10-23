# Pinned owner/group occurrence source proofs

Accepted parent [CI39899113040](run-39899113040/acceptance.json):3310 tests plus2 subtests,216 proof cases,all five diagnostics; downloaded hashes/source authenticated. This successor adds inactive raw occurrence pages for exact owner and group scopes. Existing World checks remain active.

## Implemented boundary

Mandatory externally accepted certificate commitments bind store/codec/generation/scope, ordered root/count/extrema and allocator. Group tuple order uses injective zero-escaped namespace/key/path fields matching SQLite BINARY order; owner order is exact path bytes. All fetched fields, intervals, allocator metadata, checksums, physical uniqueness and page boundaries are checked. An exact placement probe catches overlaps belonging to a different incarnation, even outside the selected group. Complete raw pages reject omission/surplus, false emptiness and rechecksummed membership replacement. No owner/history payload is selected or decoded; returning metadata does not admit an object.

Ordered indexes are explicit construction work in the caller transaction. Reads verify canonical index definitions, including predicate/collation/order, plus both inherited interval indexes and cached usable capabilities. No hidden index construction or legacy scan fallback. Oversized field bodies use a distinct fast-path budget error after SQL length/type guards; operational head/pin metadata uses the existing guarded snapshot seam.

## Measured work

Synthetic contents use actual version/occurrence schemas and commit APIs. Requested group fanout8,owners4,page4 and owner paths2 remain fixed while1k/10k/100k unrelated occurrence rows are present. Full verified test-only root/index construction is outside page timers. Baseline checked iterators validate individual rows; these proofs additionally establish page completeness, so timing is not a like-for-like speedup claim.

| Unrelated occurrences | Group / owner proof-node SELECTs | Group / owner traced heap | Group / owner time | Old-frontier rejection VM bound |
|---:|---:|---:|---:|---:|
| 1,000 | 9 / 4 | 25,082 / 15,629 B | 3.407 / 1.700 ms | 2599 |
| 10,000 | 10 / 4 | 26,985 / 16,221 B | 3.292 / 1.687 ms | 2599 |
| 100,000 | 10 / 4 | 25,348 / 15,509 B | 3.686 / 2.050 ms | 2599 |

All current and supported previous-pin page results match literal values and checked source rows. Owner/history payload SELECTs/checks/decodes are zero. Query plans show no temporary source sort. Python clean-node cache is zero; SQLite main/temp caches2MiB each, temp_store FILE. Receipts retain construction, lifetime RSS and all counters separately. SELECT counts do not alone bound rows visited; the repaired diagnostic also records SQLite VM upper bounds with100-instruction progress ticks. Tracemalloc and VM instrumentation are enabled; filesystem caches are sequential/warm/uncontrolled, no latency distribution is claimed.

The old-pin case uses BOTH still-open and just-closed rows within its returned page after two active placements change. A separate formerly empty old group is populated with1k/10k/100k newer head placements. Its fast read rejects at the same2599VM upper bound, rather than filtering/scanning the full newer relation.

[Source receipt](proof-occurrence/source.json) pins clean commit7c922158, runtime8bce1bd8ffca3ede10e729d8ab0ca375ecbb747f and driver/fixture hashes. [Raw complete measurements](proof-occurrence/summary.json) supersede pre-review current-only receipts. This is raw source access, not World/save/open/year acceptance.

## Review and validation

32 initial cases were missing-module RED. Three wrong-index predicate/collation/DESC cases were independently RED before repair. Fresh independent review found two Important work-bound gaps: inherited legacy interval fallback, and old-pin filtering that scans newer rows before LIMIT. Four capability/index and two old-frontier regressions reproduced RED; one fix pass requires exact interval capabilities and bounded candidate selection. Supporting diagnostic gap was addressed in that pass.44 source tests and353 affected proof/store/failure/validation-scope/identity tests pass (30.76s affected suite). AST/YAML/bash and diff checks pass. [Fresh review and rulings](proof-occurrence/final-review.md). No separate deferred minor; no re-review.

## Explicit remaining limits

When newer placements intervene in an old-pin candidate prefix, the reader raises OccurrenceProofBudgetError. It does NOT return a partial result or use an unbounded/unchecked fallback. General bounded certificate-checked old-pin selection is required before World adoption, as is the separately budgeted path for individual encoded fields above4096bytes. This component is not complete production previous-generation support.

Owner/group payload-reference projections, existing owner radix/header agreement, links, retirement/absence cross-consistency, production construction, namespace proofs, manifests, root AND ordinary payload retention, verified-copy/writer fencing, atomic row/root/head/receipt publication and World admission/consumption remain required. No format activation, main merge, endurance job or mature speed claim. Successor CI is pending publication/launch; parent green is separate evidence.

## Published successor

Exact-tree candidate3f57dfe48ccfa68478b2fbd37deb151e907b24ef matches local432fe6d579 rootbf1bdef3e867c7ea6445f4f647744ae0fc5667ee and measured runtime8bce1bd8ffca3ede10e729d8ab0ca375ecbb747f. Only sol/durable-proof-map advanced using the exact expected-parent lease. [Run39909955729](https://github.com/rax0h/all-that-endures/actions/runs/39909955729) is in progress with the separate full simulation suite and all six diagnostics. Candidate acceptance is pending. [Launch/resume receipt](proof-occurrence/ci-launch.json). First authenticate this run on green; on failure inspect its artifacts before edits. Next resolve general bounded old-pin selection before World adoption, then complete topology/manifests/publication gates. No long-test polling or parent-success substitution.
