# Fresh package review and executor disposition

Reviewer: gpt-6-astra, high, fresh context, single read-only whole-package review. Range1f17ba8..c106feb. Original verdict: ready for this primitive branch WITH FIXES; no World activation or main merge. Reviewer independently ran31 source tests (2.59s).

Strengths: expected commitments bind store/codec/scope/generation/root before SQL consumption; no unchecked production constructor; raw repeated-key positions and page adjacency preserved; storage-class/byte-length guards run before transfer; full-verified test construction separate from timed reads; accurate diagnostic limitations and hashes.

## Important finding — accepted and repaired

`persistence_proof_query.py` original lines96–106,123–126,155–175 only rejected duplicates returned by limited optimized streams. Same-position duplicates could hide beyond a page/lookahead/predecessor/final LIMIT; a closed interval overlapping current head was excluded entirely. Correctly checksummed duplicates at lookahead ordinal4, predecessor1, empty-page final15 and closed ordinal2 were accepted against the original certificate.

Executor added five regressions: four independently reproduced RED, while the previous-pin closed-overlap case already rejected. Every fetched position now uses the existing `_interval_rows(...,'1',...,'lazy_query_interval',limit=2)` exact-position witness and requires one visible interval, before stream trimming. It reads constants only, handles open and all still-visible closed intervals, and reuses expiry-aware index seeks. Retained overlap-red.log records the failures. One fix pass, no second review.

GREEN:240 affected tests in16.22s, including36 source cases. Fresh1k/10k/100k diagnostic on repair commit49e7a8868c5d7849ca9fb770f8b83274880ef418/runtime de69bd0717240beb09b8d25bafda150cb8228497 confirms exact results, zero payload SELECT/checks, bounded memory and metadata reads. New receipts supersede the operation counts/timings under pre-review/; original receipts remain preserved.

Critical: none. Other Important: none. Minor: none. No deferred review findings.

## Declined-to-judge items — executor rulings

- World activation/object admission: excluded correctly; raw metadata does not expose objects. Still mandatory before adoption.
- Production certificate construction/manifests/publication/retained payload authority: explicit future gates; no substitute authority accepted.
- Keys above4096 bytes: distinct budget limitation; separately budgeted certificate-checked path required before World integration.
- Mature World/save/year speeds and latency distributions: unproven; synthetic metadata data must not be presented as meeting targets.
- Successor full-suite CI: independently pending publication; parent CI remains separate evidence.

These exclusions limit this package, not the final architecture. Ruling: publish only the repaired primitive branch and bounded successor CI; existing World path remains unchanged. If wrong, revise the adapter before integration rather than accepting weakened save authority.
