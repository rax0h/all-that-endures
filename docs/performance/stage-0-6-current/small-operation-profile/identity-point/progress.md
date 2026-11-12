# Placement read ledger — plan: docs/superpowers/plans/2026-11-11-proof-placement-read.md

Base local46494a0/published7261d615; engine0785bf9. Existing dedicated branch.
Specification is ../.. source review second candidate and the explicit design
under docs/superpowers/specs. User's Green continues authorized implementation.
Pre-flight: helper returns baseline+overlay incarnation; consumer compares only
expected incarnation and leaves all binding/synchronization behavior intact.

Ruling: select the existing native exact occurrence proof for proof-only reads,
not another catalog-root walk: accepted owner+group scope roots already bind the
physical exact occurrence. Ordinary/audited full-owner fallback remains. If wrong,
point proof could miss a required closure; tests and independent review must
verify this before publication.

Restart unit is one disposable small diagnostic; original input immutable.
Existing compare driver budgets: open60s, first/warm180s, save120s, fresh120s.
Each completed phase JSON survives later failure. No expensive preparation or
network publication occurs inside the local diagnostic. No green engine suite
is rerun until the complete candidate is ready for one bundled validation.

Initial test setup negatives preserved in red.log/xml: cold conversion rejects an alias targeting inside a tuple; registry correctly refuses plain list weak references. These were fixture construction errors before exercising the change. Corrected cold fixture uses mutable nested list and replacement uses an already canonically registered teachers history. No production change for either.

Fixture follow-through: even the corrected nested cold input is outside the
legacy converter contract; initial native seeding of both aliases retires the
last old owner and correctly refuses the separately checked partial-retirement
path. All negatives remain preserved. Work-count regression now uses actual
recursive decode against an already admitted reference; consumer-work-red
observed2owner scans for2reference reads. Recovery fixture seeds only skill1,
keeping original skill2 ownership so it does not request unsupported retirement.
No converter, retirement or publication limit was bypassed or changed.

Task1 local focused evidence:19passed29.45s, no warnings. Work-count assertion strengthened to count the complete call chain (so moving the same scan into the helper cannot pass); that case separately passes. Existing point controls reject coherent physical forgery with/without overlay, new-owner absence, local/external drift, uncertainty/released pin; native alias replacement and before/after-commit recovery pass. Default/audited fallback still scans the owner. Production change is22insertions/3deletions across two files. Candidate raw diagnostic active; no other tests/profiles run concurrently.

Task2 complete as measured rejected experiment. Baseline/candidate raw single
pair warm9.544→9.150s/save7.852→8.176s. Same exact saved and fresh continued state;
logicalSQL458816→416146 but only165actual owner-cache misses removed. Independent
6case boundary suite passed6.37s, no actionable safety finding; exact candidate
hashes captured before restore. Patch and candidate-tests.py preserve proposal.
Ruling: do not ship this standalone point path or spend another fullCI cycle on
it: no useful latency gain established. Cost if wrong is delaying its9.3%logical
SQL reduction/potential larger-owner scaling benefit until a batch design is
measured. Production, live tests and workflows now match green0785bf9exactly.
The next step is bounded closed-read proof/validation reuse, not redoing mature
construction. W3/U10 remain open; original green parsing improvement retained.

Follow-up custody probe completed on restored green source with exact saved/fresh state and no engine edits. All377warm group reads have an owned entry boundary;106save group reads are borrowed and excluded. Next investigation target is one closed proof-only identity-group read, not an entire step/save. Instrumented probe makes no latency claim.
