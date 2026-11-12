# Owned read-view epoch and standalone descriptor reuse

This package removes redundant source-epoch SQL while the same checked native
read view is owned, and lets standalone owner reads reuse the already admitted
immutable descriptor. No new authorizer, transaction, payload cache or final-exit
validation is installed. All physical source/Merkle proofs remain checking.

## Actual final small-input observation

Qualified Python3.13.5/GCC14.2.0/SQLite3.46.1 complete runtime fingerprint matches.
Immutable input SHA2562555675bd19ede5c6ed9b7619fab56d59098a8b358d9a9c3569cabccba22c554,
year1/seed843000. paired.py ran baseline then candidate in sequential child
processes of one command execution; source/import/input fences are in each
same-command-pair report. Parent CPU/affinity/cgroup context is recorded. No
concurrent tests or reviewer CPU probes ran during raw timing.

| Phase | Baseline seconds | Candidate seconds | Change |
|---|---:|---:|---:|
| Open | 1.986 | 1.944 | -2.1% |
| First step | 12.055 | 8.381 | -30.5% |
| Save | 7.722 | 8.152 | +5.6% |
| Warm step | 9.224 | 7.271 | -21.2% |
| Fresh restore and step | 24.073 | 19.389 | -19.5% |

Save does not improve. Targets10sopen/2ssave/1swarm remain OPEN and no mature
constructor is launched. These observations are not a distributional guarantee.
Candidate-raw immediately followed by reverse-baseline-raw also showed lower
first8.287vs11.448s/warm7.309vs9.091s; all results remain preserved. The older
baseline-raw was collected before the user interruption (first6.807/save5.312/
warm5.990); it is nonadjacent and demonstrates timing variability, not evidence
that the final adjacent pair shares that older execution context.

Both versions preserve source/input. Fresh saved year2/generation1 digest is
cebc2fcd2660db6e87b9c29c3c8e88536a831214c306991778fba6ee58cc7451;
continued year3 digest is
a46d627d11ce2c12ff8f6fe0f14d01af35006afd56bdad3bf16417379b0166f3.
Metadata rows first57461→39173 and warm47507→35843; save24929unchanged.
Final profile counts first528188→327965SQL and warm386922→245391SQL; save257723
unchanged. Profile elapsed times ran with affected tests and are attribution
only. The final source is exactly fenced in both raw and profile reports.

## Custody and fallback

Entry still performs original pre-BEGIN and established-view checks. Only actual
admitted proof-only authority with an owned internal nonyielding view captures
the accepted epoch. Reuse checks store/DB/codec, pin/generation, manifest/component
and accepted-epoch object identities, hook identity, transaction state, total
changes, schema/opaque/callback and transaction-control revisions. Any drift
permanently invalidates the scope and its immutable facts. No restored coarse
counter can reauthorize that scope.

Transaction control revision covers SQL BEGIN/COMMIT/ROLLBACK and public commit/
rollback plus autocommit/isolation_level setters (which can operate directly in
sqlite3 C). Unknown SQL and scripts already advance the separate SQL revision.
Callback-bearing/custom-cursor/opaque mutations disable reuse. Borrowed, audited,
opening and publisher paths retain original behavior. Explicit owner fallback
controls verify those selections. The supported boundary is the guarded public
SQL API, not arbitrary Python private/base-class object manipulation.

Standalone owner operations use zero transient scope fact-cache bytes. Bounded
custody references add only constant per-operation state; the accepted immutable
descriptor continues competing within existing combined owner-cache limits.
Existing owner buffers, returned spills and finally cleanup remain unchanged.

## Verification and findings

42focused controls passed20.38s, comprising13newread-view and29existingdescriptor
cases. Four additional owner-selection cases pass4.60s. The whole-package
review has13distinct independent green probes across compatible runs, including
pending RETURNING, mode/context-manager/script transaction controls, callback/
codec fallback, public iterator lifetime, zero-budget forced spill success/error,
external release/reopen and physical owner omission with coarse epoch manually
reaccepted. Initial diagnostic assumptions and their corrected2case rerun are
preserved. Consolidated W7 findings/disposition are in ../../bounded-genesis/closure.md.

Affected-suite result and final independent signoff are appended before commit.
Hosted final-source proof/full simulation validation remains required before
claiming engine green. No main merge, format activation or endurance is included.

Final affected batch passed328tests in327.84s with1deliberate deselection:
test_generated_world_continues_through_two_proof_saves rebuilds an unchanged
audited2save input constructor and is reserved for the hosted full suite. Exact
proof-only saved/fresh/continued state was already checked by all small raw/
profile runs. Four appended owner-fallback controls passed separately after
collection; they are included by the new focused hosted command. Counts overlap
and are not summed. No local full-suite or mature-constructor rerun was started.
Independent final signoff is in review-raw/report.md. Existing hosted limits
remain proof90min/full180min with15min publication reserve; original mature
request files remain unchanged, so no expensive mature conversion is requested.
