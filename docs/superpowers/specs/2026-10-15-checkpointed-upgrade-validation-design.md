# Checkpointed complete-upgrade validation

## Purpose

Finish Stage 0.5 acceptance while protecting completed conversion work against
another GitHub job timeout. Daniel explicitly wants runtime evidence before a
large retry and does not want another six-hour attempt to discard its progress.
The sequence-scan repair is implemented and green. This document proposes a
validation-harness extension; it is not an implemented resume protocol.

## Verified state

- Runtime candidate: `24cc39974b0762e428e2a5a0d7581f7f92216310`.
- Its tested repository tree: `4b446d49ea9f4bdb23e7337124e0cd1203f0a095`.
- Green preflight: [38690643226](https://github.com/rax0h/all-that-endures/actions/runs/38690643226),
  workflow `2f0cf55331382a925e060223f583c72c0079978a`.
- Full suite: 2,522 tests and 2 subtests passed in 5,614.84 seconds.
- Fresh recovery: 186 regressions and exact complete-format 3+4+3 passed.
- Retained source: 9,601,409,024 bytes; 8,440 sequence descriptors and 108,468
  physical sequence rows. The old inventory formula implies 915,469,920 key visits.
- Synthetic complete conversions: 2,000 people/events in 117.50 seconds and
  8,000 in 473.49 seconds, both with exact restored-world digests. These fixtures
  have no counted sequence descriptors; they measure the other conversion work.
  Separate sequence fixtures and real-source samples cover the sequence path.
- The failed real conversion reached its post-commit boundary in 11,575.96
  seconds, then spent about 47 minutes in ordinal restoration plus full-store
  verification before entering catalog verification. It timed out after 350
  minutes. The log does not separate the catalog substages.

These results establish correctness on the tested gates and removal of the
repeated sequence scan. They do not establish a safe total runtime for the
mature-world upgrade. The giant job remains explicitly disabled.

## Options and recommendation

| Approach | Benefit | Remaining problem |
|---|---|---|
| Retry the current combined job | No new harness behavior | Insufficient evidence of timeout headroom; intermediate work is disposable |
| Add durable validation boundaries | Retains completed construction; each verification stage has its own job budget | Needs a tested, provenance-checked intermediate-artifact protocol |
| Optimize more before retrying | May shorten later work | Further speedups are unmeasured and do not preserve work after a timeout |

Recommend durable boundaries first. Continue performance work when measured
stage times require it; keep all existing integrity checks.

## Boundary and stages

The construction boundary is after the existing catalog commit and successful
`_restore_copy_ordinals`, before `verify_all` and `_verify_catalog`. At that point
there is a coherent committed private database, but it has not passed complete
validation and must not be described or published as an accepted World checkpoint.

1. **Construct an unverified candidate.** Run the existing pinned converter.
   Preserve its private database at this boundary, close all writers, and retain
   it as a clearly named unverified artifact. Retain the checked generation pin
   needed for later verification. This stage does not emit a P5 `complete`
   receipt and does not create the accepted destination.
2. **Verify storage.** On a fresh runner, authenticate the unverified artifact
   and run the existing full-store verifier. Issue a storage-verification receipt
   only after success. Preserve the original database artifact byte-for-byte.
3. **Verify catalog.** On another fresh runner, authenticate the original
   database and storage receipt, then run the existing complete catalog checks,
   including type witnesses, structural sequence checks and the repaired shared
   inventories. Issue a catalog-verification receipt only after success. Record
   group/owner/type/sequence progress and timings. Preserve the original artifact.
4. **Finish normal publication and acceptance.** Require both verification
   receipts for the exact database/runtime/harness lineage. Work on a disposable
   private copy, perform the existing complete-open checks, release its checked
   pin through the existing API and use the existing no-overwrite publisher.
   Only then create the normal complete checkpoint. Continue through the existing
   independent exact year-1001/year-1002 and downloaded-restore gates.

The intermediate artifact is validation working data. It is not a new save
format, catalog authority, application backend or replacement publication path.
No changes to simulation behavior, rank ecology, identity allocation, World
serialization, ordinary save/open or format capability 6 are proposed.

## Integrity and lineage

The intermediate manifest binds stage, schema, rules/configuration, runtime SHA,
harness SHA, original retained-checkpoint receipt/hash, database hash and byte
size, store identity, generation and checked pin. Its filenames are fixed and
local; path traversal and unexpected archive members reject before extraction.
Finalize the manifest only after the writer is closed and the stable database
has been hashed. Existing bundles and destinations must never be overwritten.

Each verification receipt binds the same immutable database and complete prior
receipt lineage. GitHub jobs must additionally verify the producing artifact's
run/workflow/candidate provenance and dependencies; a self-declared JSON stage
flag is not sufficient evidence of successful verification. A corrupted, missing,
foreign or incomplete receipt rejects before publication. Ordinary application
readers must not be taught to trust an unverified-stage receipt.

Storage and catalog verification use the same checked captured generation. No
raw deletion of pins, leases, attempts or receipts is permitted. Any operational
cleanup needed before accepted publication uses the existing checked store API
on the private operational copy. The original retained source and intermediate
artifact remain unchanged. Every existing corruption check is retained.

## Time and failure policy

Keep the existing 8 GiB Python address-space guard. Give construction and each
verification phase separate job budgets, leaving explicit time for artifact
upload. Do not claim that splitting guarantees a particular overall runtime.
Measure artifact size/upload time as well as conversion and verification times.

A later timeout must leave the completed unverified database artifact and all
successful earlier verification receipts available. Retrying a verification
stage must neither reconstruct the database nor rerun an already certified stage
whose exact immutable database lineage still matches. If a stage's measured
progress projects beyond its budget, pause the next large stage and investigate
that stage before another retry. Do not relabel partial evidence as acceptance.

## Required proof before a large construction stage

- Small complete World: ordinary upgrade and checkpointed upgrade restore the
  same exact World values, aliases, RNG state, ordering and counters.
- Capture survives original private-directory cleanup and a fresh process; no
  accepted complete destination or receipt exists after capture alone.
- Storage and catalog stages each execute their original verifier. Corruption
  rejected by the ordinary path is rejected by the staged path.
- Missing, reordered, replayed, corrupted and foreign-database/runtime/harness
  manifests or receipts cannot advance the pipeline or publish a destination.
- Verified artifacts preserve their bytes; checked pin handling still permits
  ordinary continuation after final publication.
- Injected capture, verification, receipt-write, destination-race and publication
  failures preserve source bytes, retained checkpoints and earlier stage evidence.
- A fresh-runner small end-to-end pipeline proves artifact download and receipt
  lineage, then exact continuation/restore. One independent scoped review checks
  the harness and provenance protocol before the mature-world construction starts.

## Review and implementation status

Design only. No intermediate-capture or resume code has been implemented, no
large construction has restarted, and Stage 0.5 remains unaccepted. After this
design is approved, write the implementation plan and execute it inline, retaining
one independent final review. Reuse the green runtime evidence only if its exact
runtime blobs remain unchanged; changed runtime code requires applicable fresh
whole-suite/recovery evidence.
