# Bounded SQL node parsing comparison

The first runtime phase removes duplicate canonical node parsing and decoder
branch re-encoding. All eight production SQL readers retain physical storage
domain hashing and unchanged ProofMap domain/count/prefix checks. Public standalone
read and conflicting-write readback remain fully validating. No cache, format,
gameplay or mature constructor changes are included.

## Observed raw latency

These are one sequential before/after pair on independent byte-identical copies
of the authenticated small generation0/year1 input, using the same full qualified
Python3.13.5/GCC14.2.0/SQLite3.46.1 fingerprint. No profiling or concurrent tests
ran during either raw measurement. This is a diagnostic sample, not a statistical
latency guarantee or mature performance acceptance.

| Operation | Baseline seconds | Candidate seconds | Observed reduction |
|---|---:|---:|---:|
| Proof open | 1.393 | 1.165 | 16.4% |
| First year | 8.391 | 7.808 | 7.0% |
| Save | 6.245 | 4.964 | 20.5% |
| Warm year | 7.805 | 6.087 | 22.0% |

The save and warm-year targets still miss on this small case. Keep mature
preparation paused. Open is only a small-input observation, not the mature10s gate.

Both runs freshly restore saved generation1/year2/seed843000 and canonical digest
cebc2fcd2660db6e87b9c29c3c8e88536a831214c306991778fba6ee58cc7451. Fresh independent
continuation to year3 also equals each run's in-memory warm continuation, and the
two year3 digests match each other. Per-attempt saved manifest commitments differ:
the ordinary save creates a fresh UUID commit token (persistence_lazy.py,
_prepare_hybrid_save); each fresh reader authenticates its actual accepted saved
manifest. No byte-identical database or cross-attempt manifest claim is made.

## Separate work attribution

| Work | Previous profile | Candidate profile |
|---|---:|---:|
| Save ProofMap reads | 54,080 | 54,080 |
| Save canonical node parses | 112,578 | 58,537 |
| Save node encodes | 93,861 | 4,213 |
| Warm ProofMap reads | 42,840 | 42,840 |
| Warm canonical node parses | 85,680 | 42,840 |
| Warm node encodes | 68,994 | 0 |

SQL node fetch work is deliberately unchanged. Save also validates newly written
nodes/collision readback; its parse count is not expected to equal map reads.
These profiles are separate from raw latency. The original profile and candidate
profile use the same input and qualified software; instrumentation costs and
overlapping cumulative times are not performance acceptance or additive costs.

The remaining warm profile still records1,295_owner_changes calls and913identity
descriptor checks. The previously reviewed exact-placement-read candidate is
therefore still relevant; it is not implemented in this first phase.

## Evidence and gates

- baseline-raw-1 and candidate-raw-1 contain actual runtime file hash fences,
  imported module paths, immutable input authority, phase resources and fresh
  exact continuation. Candidate-profile separately records actual work counts.
  Source hashes are checked before/after; HEAD alone does not label dirty code.
- runtime-fingerprint.json matches the complete qualified local software record.
- red.log/xml reproduces duplicate work; checked-readers-red.log/xml separately
  covers query/version/occurrence production callbacks.
- focused.log/xml:75passed, including17new controls and existing canonical vectors,
  malformed bytes, caller transaction, rollback, collision and bounded storage.
- affected.log/xml:405passed in275.04s; seven JUnit-format warnings from
  record_property under xunit2 are preserved. Existing hosted CI uses legacy
  format; no test failure is hidden or rerun to discard warnings. Together with
  focused tests this is480disjoint targeted cases.
- Independent review-raw/review.md:PASS with no actionable findings;16,086old/new
  decoder comparisons and9SQL/root/collision probes passed. Hosted greens and
  mature readiness remain outside the local review verdict. Findings belong to
  the existing bounded-genesis closure register.
- Engine94267 greens apply only to the baseline. A new bundled full/proof CI is
  required for this candidate before updating any harness runtime/green authority.
  Original source-control pins and the old mature trigger remain untouched.
