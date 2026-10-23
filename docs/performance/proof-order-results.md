# Ordered relation proof results

The previous package passed [run 39866293343](https://github.com/rax0h/all-that-endures/actions/runs/39866293343): **3164 tests plus two subtests**, one warning, in 5262.29 seconds. Its full-suite and both scaling artifacts were downloaded and checked against GitHub's SHA256 digests; [acceptance and raw evidence](run-39866293343/acceptance.json) are retained.

This package adds complete ordered relation certificates and verified local transitions, another prerequisite of [Astra's approved architecture](../superpowers/specs/2026-10-21-ate-incremental-proof-design.md). No existing World reader/publisher selects them. No format activation, bypass, main merge or mature speed acceptance is performed.

## Implemented behavior

An immutable ordered entry binds exact key, 32-byte relation value and immediate predecessor/successor. A descriptor binds the existing ProofMap root/count and first/last positions. Page verification requires its expected descriptor commitment from accepted outer authority, then authenticates entries, adjacency and range boundaries. It rejects missing/reordered/duplicate/surplus rows and false empty/short results. Empty byte keys remain distinct from absent endpoints. Raw pages must be verified before exclusions/decoding; existing canonical object admission remains separate.

Construction consumes a strictly ordered stream, computes links with bounded lookahead and spills locator-sorted changes to SQLite. Updates authenticate old entries and immediate parent neighbors or an insertion gap. All batch witnesses refer to one parent, including adjacent changes. Disposable SQL staging retains boundary keys for disjoint changed regions, derives final neighbors and applies one final-path delta. It never commits or chooses a head; caller rollback is mandatory on failure. No full Python relation/delta, retained clean-node cache or second object registry.

Seeded mixed transitions agree with an independent logical mapping and complete canonical rebuilds. Tests cover head/tail/all deletion, reinsertion/reordering, no-op identity/zero writes, parent/neighbor/absence corruption, missing caller transactions and late malformed/generator/post-insertion callback failures. A regression caught None being mistaken for end-of-source; a unique sentinel now rejects malformed source rows instead of silently truncating.

## Exact scaling evidence

Measured source `0aa776e263933575ae6ae8fd09d747ddfe57e8a2`, runtime tree `d22ff20b5b6ca33f804b0a065da4435d56a907ec`, driver SHA256 `51f3f7091edee67f6f6513f4d8aa5f77fd7e98ca8ab05ed3043c3a6b25b92aab`. [Source/environment receipt](proof-order/source.json): Python 3.12.14, SQLite 3.53.1, SQLite main/temp caches 2MiB each, temp_store=FILE, zero Python clean-node cache. The fixed changed position is ordinal500; its parent neighbors remain ordinals499/501 while unrelated entries grow. Keys use SQL-compatible ordinal plus exact typed record bytes, including repeated record keys at distinct positions.

Each independent SQLite case stores relation commitments and a synthetic unrelated-history payload table. The measured transition includes collecting the old/immediate-neighbor source metadata, authenticating witnesses, staging the delta, writing nodes, updating the relation row and caller commit. Tracemalloc is enabled. Each case then verifies exact old/new commitments, a fixed 16-row ordered page and equality with a complete rebuild. Fixture setup, full construction/rebuild and page verification are outside the transition timer; their separate timings are retained.

| Relation rows | Proof node reads | New proof nodes | Relation SELECTs | Staging SELECTs | History payload SELECTs | Traced point heap | Point time |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1,000 | 23 | 5 | 9 | 7 | 0 | 94,764 B | 21.953 ms |
| 10,000 | 27 | 5 | 9 | 7 | 0 | 98,305 B | 24.962 ms |
| 100,000 | 33 | 6 | 9 | 7 | 0 | 103,248 B | 26.622 ms |

Initial construction took 0.126 / 1.492 / 14.653 seconds with traced peaks 81,233 / 331,970 / 779,032 bytes. Each local transition met its declared <=512 node reads, <=256 new nodes and <2MiB point-heap workload gates. These gates do not promise universal constant work: actual changed count, alias fanout, key size, locator depth and deduplication affect cost. SQLite staging is charged separately from Python memory. Process RSS is lifetime peak, including previous cases. Temporary ordered staging tables were removed after every operation. [Raw per-case JSON and summary](proof-order/summary.json) retain all observations.

This diagnostic proves work bounds and ordered completeness for the component. The synthetic historical-payload SELECT count is not a real World history-read measurement. Millisecond primitive times are not save latency, and a complete 100k rebuild is not ordinary open. Existing targets remain warm year <=1s, incremental save <=2s and open <=10s; none are established here.

## Verification and remaining integration

Tests were observed failing before each module existed; malformed-source regression was RED before its fix. The affected proof/incremental-store/failure suite passed **181 tests in 7.19 seconds** ([log](proof-order/final-focused.log)). A fresh [independent final review](proof-order/final-review.md) found no Critical, Important or Minor issues; it independently ran all126 proof tests and reported additional exhaustive transition/page probes. It checked the receipt/source identities without rerunning 100k timing. The separate full successor CI gate remains required; parent green results are not successor acceptance.

Next source adapters must specify exact query/group/owner relation values/order, authenticate actual fetched bytes/interval selection and validate changed payload reference projections against topology. Retain existing owner trees and the identity registry. Group/link/owner cross-consistency, retirement/allocator proofs, manifests, root AND ordinary-payload retention, verified copy/writer fencing and atomic existing commit/receipt publication remain prerequisites to World authority. Then consume the proofs in actual save/open, preserve canonical lazy action admission and measure mature equivalence/latency. No node collection is active.

## Published successor validation

Candidate `7d6226d08071c5b7048325a2b8affa7e22803e83` has root tree `66b85cfe15d2a485feff9ac6ff19b4633fb62417`, exactly local `74276566107fde5dbf1fbe677bcd56634c4a2d4b`; runtime `d22ff20b5b6ca33f804b0a065da4435d56a907ec` matches the measured source. Publication advanced only `sol/durable-proof-map` using the exact parent lease. [Run 39878709646](https://github.com/rax0h/all-that-endures/actions/runs/39878709646) is running all proof tests, three bounded scaling diagnostics and the separate full simulation suite. Its results are pending. A final affected-suite rerun passed181tests/6.61s. No main merge or World activation.
