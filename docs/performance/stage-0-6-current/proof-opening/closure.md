# Explicit proof-backed World opening

The new `open_proof_world_session` API in
`simulation/ate_sim/persistence_proof_world_session.py` accepts an external World
commitment from an audited construction or checked publisher. It restores a
complete seven-root/v4 World through existing authenticated native readers and
canonical identity restoration, without a full-history opening audit. Format7
and rank authority are required. Six-root snapshots reject on this API; the
existing audited opener remains their supported compatibility route.

The raw fixed head is joined to the externally accepted manifest before World
decoding. That binding protects pin capture and matching-snapshot entry. Component
authority is active before layout, selectors, event descriptors, ordinal metadata
or restored roots are read. Original store, codec, pin, component and epoch checks
span restoration and transaction cleanup. The existing registry, transaction
publisher and checked save/recovery fallback paths are retained.

Unvisited bytes are not certified healthy by opening. A coherently rechecksummed
archived segment can remain dormant, but its first selected read and explicit
full scrub reject before decoding it. Opening still materializes current resident
roots and the mutable event tail; it is not constant work for arbitrarily large
live state. Operational metadata budgets and physical completeness checks remain.

| Archived 2048-event segments | Proof-open segment payload bytes | First selected segment bytes | Audited-open segment payload bytes |
|---|---:|---:|---:|
| 1 | 0 | 649122 | 1947366 |
| 4 | 0 | 649122 | 7809444 |

These are actual returned BLOB materializations observed at the guarded cursor,
including an audited positive control. They do not measure physical SQLite page
I/O, filesystem cache misses or mature-world timing. Current-tail aliases share
the same canonical object without visiting archived bodies. No-op save leaves
dormant bytes unread; selected access and `verify_full` reject the corruption.

Failure controls cover forged raw heads/selected values/layout, metadata budgets,
wrong eligibility/context, capture races, late store/codec/pin/component/epoch
drift, borrowed handles, primary error preservation, cancellation and exact owned
lease cleanup. Original interruption/recovery outcomes retain their checked
publisher behavior. The single consolidated register is `review.md`; raw red and
green logs/XML are preserved.

The original small generated-year driver now has explicit `--rank-proofs
--proof-only` mode. Construction remains audited; parent continuation and the
fresh process select the actual proof opener and forbid World audits. Audited
default remains. Eager equality, fresh-process equality, accepted-source hash,
source/runtime/driver provenance and raw versus diagnostic phases are retained.

Local validation:469affected cases pass920.82s on the pre-cancellation handler;
final57opening/launcher cases pass72.55s including both cancellation outcomes.
All4955simulation tests collect; Python AST/YAML/all5Bash blocks and final tested
source hashes pass. No timing claim is based on concurrent correctness tests.
Serial qualified-runtime generated-year validation passes every13phases at
source276d323/runtime53a57cc04c39933bdf2d5d5650a840e267a8877f. Raw and diagnostic
continuations match the independently advanced eager World after fresh-process
restoration; the accepted template hash is unchanged. Actual parent continuation
and both fresh-child World-audit counters are zero; diagnostic save audits are
also zero. Construction still uses the existing full audit. See serial-year.json.

| Small-world raw phase | Wall seconds |
|---|---:|
| Proof-backed open | 1.841 |
| Simulation year | 9.504 |
| Native save | 7.140 |
| Fresh-process open plus full digest comparison | 11.557 |

Diagnostic save19.271s includes instrumentation and is not substituted for the
raw pass. This serial shared-host run is neither a controlled before/after speed
comparison nor mature-world acceptance. The local runtime qualification and its
unchanged fingerprints are in ../fixture-construction/qualified-local-runtime.json;
the bundled unqualified tuple remains unresolved. Hosted CI retains separate
runtime/result authority.

One independent whole-package review found R1Important pin handoff ownership and
R2Minor partial-session/registry ownership. Both are closed, including the
duplicate-token negative control discovered during R1 closure. Final113regression
cases pass78.38s,49opening/13launcher/51default-store; independent final10controls
pass13.46s, with additional after-INSERT/before-registration and pre-registry
cancellation probes. Final author/independent source hashes agree. Initial red,
intermediate collision red and final reports remain in review-raw/ and review.md.
Every finding, including Minor, closes in this group. All4960tests collect;
Python AST/YAML/all5Bash blocks/product whitespace pass.

Repeat the serial year on the corrected source checkpoint before publishing;
the bundled hosted full/proof gate remains pending.
Mature10sopening/2ssave/1syear and final architecture
acceptance remain separate Stage0.6 gates. No main merge, default activation or
endurance run is part of this package.
