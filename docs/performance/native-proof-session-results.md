# Explicit audited native World session integration

`open_audited_proof_world_session(path, rules_id=..., expected_commitment=...)`
opens a proof-format7 World only after a full matching-snapshot audit against the
external accepted commitment. It returns the existing LazyWorldSession, preserves
its canonical registry and alias stitching, and exposes its accepted pair through
`session.proof_manifest` only while the native session is active and settled.
The default `open_lazy_world_session` format7 fence remains in force.

Native `save()` replays the existing frozen participant bytes, validates the exact
frozen commit descriptor and passes that attempt to the existing seven-root manifest
publisher. Version/ordinary/event/identity changes, component roots, manifest and
receipt share the existing SQLite transaction. Native acknowledgement still belongs
to the existing family/coordinator participants. `resolve_save()` retains the original
parent manifest/pin/token even after partial in-memory acceptance has advanced the
session pin; it resolves that exact attempt, audits the result and then acknowledges.
No second registry, native object graph, sidecar or publisher is introduced.

A conservative session epoch tracks DB/codec identity, SQLite data_version/total_changes and main/TEMP schema versions. Accepted epochs are captured inside the audited transaction; unchanged operations retain the exact unchanged sample. Same-
connection raw SQL and external writes invalidate ordinary proof-backed snapshots,
preparation and manifest exposure. Recovery remains available against its original
attempt and reauthenticates before native acceptance. No-op saves preserve generation
and manifest. Full committed/recovered source audits run before acknowledgement;
a further full audit reestablishes the epoch after operation SQL work. Uncertain saves
must resolve before native mutation or ordinary close, preserving the existing protocol.

This is an explicitly audited correctness integration, not ordinary proof-based fast
admission, affected-owner incremental semantic transitions or interactive save acceptance.
It reads full history, retains inherited eager-action restoration costs and may audit a
save more than once. No fast latency or memory bound is claimed. The producer's partial
retirement/mixed inline/backed/cyclic/key-reference exclusions still fail closed. Native
activation is opt-in through the named audited API; no automatic migration or main merge.

Tests cover canonical shared histories across reopen and append, scalar edits, event/ID/
year changes with exact old-format canonical digest equality, no-op, wrong/stale/cross-store
commitments, malformed external roots, all three writer fault seams, partial participant
acceptance, corruption before recovery acknowledgement, raw SQL invalidation and frozen
commit-descriptor mismatch. The remaining performance integration must replace these full
audits with authenticated affected-owner transitions and proof-based lazy admission, then
measure first interactions and matched mature saves. This package does not change that gate.

One fresh review found3 Important issues (epoch resampling, frozen token/generation
disagreement and schema invalidation); the single fix pass and exact regressions are
recorded in native-proof-session/review.md. One Minor remains: closed proof-session
save/resolve report SQLite ProgrammingError rather than StoreError. Both fail closed.

Final corrected runtime `40c93ec2522f2a434ab705189480f011399fd91f`:1177 proof tests,120 related native/copy
regressions and26 focused native session tests passed with0 failures/errors/skips.
All3 existing checkpoint controls passed with0 history bodies; these do not time native
session saves. Source hashes, exact durations and controls are retained in
native-proof-session/verification.json and checkpoint-scaling/. Hosted full suite pending.
