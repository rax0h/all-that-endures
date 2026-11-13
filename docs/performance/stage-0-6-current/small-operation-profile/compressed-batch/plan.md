# Skip virtual levels in compressed proof batch updates

Base source runtime4654b019 is now hosted-green43281031469:5088full tests and
32proof XMLs1931tests+scaling, overlapping. Actual archive hashes/source records
are retained in ../read-view-epoch/hosted-43281031469. The repeated timing
clarification and all harness findings are closed and published separately.

Root cause: actual small save profile calls merge61122times, includes1005848times
and _prefix164064times for the existing sorted batch. A stored compressed leaf
can still be carried through all64virtual hash positions, scanning16slots per
position, even when changing exactly that same leaf. Existing code already
checks its bytes/hash/count/path once and carries the decoded node; removing
virtual recursion must preserve those checks and the identical canonical root.

Alternatives: add a proof-node cache (new state/authority/budgets); optimize hash
framing (smaller CPU target); jump across the shared part of a compressed prefix
(selected). Modify only persistence_proof_batch.py. No format, SQL, cache,
authority, pin, source-read or publication boundary changes.

Algorithm: after checking a node, find common prefix with the next sorted change.
If it extends the current virtual prefix, recursively process that shared range
at once using the already checked node. Resume at the original prefix in a loop
for remaining changes, so many absent deletions cannot accumulate wrapper stack
frames. Empty result delegates to existing build; real branch handling, child
promotion checks, input validation/order and caller rollback contract remain.

- [x] RED single-leaf merge-call bound≤4 (old65), canonical-root equivalence under
  insert/update/delete/noop, forced long-prefix/before/after delta batches,
  thousands of absent deletes and corruption/generator-failure controls.
- [x] Implement jump/loop in merge; run focused +existing map/batch controls.
- [x] Commit a local source candidate only after focused green. Baseline isolated
  at this green source; candidate raw/profile imports bound to actual Git bytes.
- [x] Same-command A-B/B-A actual year1 save comparison and exact fresh-state
  verification. One instrumented actual save attribution, no latency claims from
  profile. No concurrent tests during raw timing; one independent package review.
- [ ] Close all findings in bounded-genesis/closure.md, affected tests and one
  bundled engine CI only if actual save improves. No per-finding CI cycles.

Restart unit is one disposable small input copy with independently retained
phase reports/logs. Source SHA2555675bd19ede5c6ed9b7619fab56d59098a8b358d9a9c3569cabccba22c554.
Use unchanged fully fingerprinted qualified313. Existing driver phase limits
60/180/120/180/120s; robust repeat harness caps each entire child120s plus bounded
process-group cleanup. Restart incomplete trial only; cross-session retries are
labelled. Reuse expires on source/input/runtime drift. Reserve15minutes for
publication. No mature constructor, main merge, format activation or endurance.

Measured decision: keep CPU-work reduction/paired save improvement11.2%/8.6%
with explicit warmer-step and fresh-verify increases; no overall/mature target
claim.391affected passes105.23s, independent review/probes closed. Full hosted
proof/simulation correctness is the next gate; one bundled publication.
