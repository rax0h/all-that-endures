# Stage 0.6: bounded new scalar World owners

Base `1de96bd4899f52a06be4f96e68af229abe36ce3b`; measured implementation
`3921aa9bb133d54f6c33b2563384520fba90ac0a`, runtime tree
`7e1965077091ef3cab5a8e9c7e1d7de1514e0ead`.

## Demonstrated problem and change

A real seed843000 8x6 generated world, initialized mature and advanced eagerly
through year2, produced 1202 version rows and18 ordinary rows when saving year3
through the explicit proof bridge. The observed small-world save took
23.063720243s. The receipt is `real-year-transition.json`; it is a local
observation, not a mature-world benchmark. It includes2 new people,2 new motive
states,2 new transmissions, new history backings, changed existing owners and
615 dependency lease rows. The limited value/tail path did not accept it.

This package handles a finite necessary part of that transition: creating fresh
scalar native dictionary owners, including Person, MotiveState, Transmission
and allocation-free partnerships. It authenticates their predecessor absence,
accepted lazy collection representation, fresh allocator range and exact
catalog witnesses. It uses the existing IdentityCatalog.prepare_delta and the
existing content/scope/collection/directory/inventory publishers. There is one
writer and one causal authority. Successor certification reconstructs touched
owner/group and semantic projection facts and checks query membership against
the actual successor ordinal. It does not read unrelated history bodies.

The bounded slice accepts at most512 changed source rows and4MiB combined
checked input/predecessor bytes. Always-read catalog and retirement singleton
predecessors are included in the byte budget even for allocation-free owners.
Other transitions use the existing fully checked path. Full initial admission
and unsupported structural saves continue to audit. Corruption sensitivity,
exact continuation, aliases, identity and historical information are preserved.

## Measured insertion scaling

Same fixture constructor and second new-Person insertion on separate fixtures,
Python3.12.14 / SQLite3.53.1, local shared hardware. Other tests were active;
cache/hardware were not controlled and there are no repeated-sample guarantees.
Baseline used `1de96bd`; candidate used the exact implementation above.

| Retained history values | Baseline save | Candidate save | Candidate SQLite VM steps | Candidate unrelated history bodies | Full World audits baseline → candidate |
|---|---:|---:|---:|---:|---:|
| 1,000 | 0.476253s | 0.178206s | 314,875 | 0 | 2 → 0 |
| 10,000 | 1.137070s | 0.122285s | 315,413 | 0 | 2 → 0 |
| 100,000 | 5.561773s | 0.135633s | 316,564 | 0 | 2 → 0 |

Candidate VM work increases0.54% across a100x increase in retained values. The
100k observation is about41x faster than baseline. Construction and admission,
traced first save, uninstrumented second save, and third-save VM work are
separate phases; fresh full audited reopening verifies all inserted people and
retained history length. See `candidate/`, `baseline/`, `comparison.json` and
the committed `baseline-probe.py`. The candidate driver is
`.github/tests/run_proof_native_insert_scaling.py` and is included in the
existing hosted proof job with separate evidence files.

These archives contain history values, not simulated years. Their save times
do not establish mature-world or complete simulation-year acceptance.

## Consolidated finding closure

One independent whole-package review; original final report: `review.md`.

| ID | Origin / severity | Action | Evidence / status |
|---|---|---|---|
| SI-R1 | Reviewer / Important: identical ordinary owner rewrite changed source revision without catalog witness | Exclude every ordinary World-family owner from this slice; retain checked fallback | Corrupt frozen save rolls back, recovery selects original generation, normal retry succeeds; closed |
| SI-R2 | Reviewer / Minor: allocation-free insert read unbudgeted/unauthenticated catalog singletons | Authenticate and charge both catalog and retired singleton predecessors through a cached bounded reader | Both self-checksummed forged headers fail accepted-content authentication and allow normal recovery/retry; closed |
| SI-R3 | Author / representation boundary: family membership alone cannot authorize lazy source insertion | Require a declared collection in accepted parent directory before projection | Eager-only world.local returns fallback before projection; normal Person path succeeds; closed |

Reviewer independently inspected final fixes and ran6 focused cases in10.67s.
The author review-regression subset passed4 cases in8.23s. No open actionable
Critical, Important or Minor finding remains in this finite group.

## Acceptance and next work

Repository targets remain mature open10s, warm simulation year1s and incremental
save2s. First year and fresh restore lack separate numeric targets. None is
claimed passed by this synthetic slice. The millennium generation120s target
is separate. The last mature timings and retained transport status remain in
the parent Stage0.6 ledger; no new mature run was launched by this package.

The complete observed year still exceeds the512-row limit and changes existing
owners/backings. It still takes the full-audit fallback. This is an explicit
performance limitation, not a deferred review defect or a Stage0.6 completion
claim. Next implementation: extend existing accepted-source/scope transitions
to mixed existing-owner edits, newly created backing closure, and retirement;
compose their exact touched facts in one transaction. Raising the row limit
alone does not authenticate those transitions. Preserve the complete-year
eager/proof differential and fresh-process checks while eliminating ancient
unrelated reads. Initial admission and mature simulation selection cost remain
separate measured blockers in Issue18.

This runtime-changing package warrants one bundled full simulation/proof CI to
validate that new topology publication does not regress older persistence and
simulation cases. No mature benchmark, endurance, default format activation or
main merge is initiated. Long CI will not be busy-polled.

## Final local verification

105 affected tests passed in254.37s, including two complete generated-world
years with independent eager control and fresh-process restored digest equality.
88 benchmark/retained-fixture harness tests passed in42.52s. Workflow YAML,
all shell blocks, runtime pin, every launch fingerprint and whitespace checks
passed. Original incomplete240s test attempt and initial malformed checksum
probe are not counted as success; these are the replacement final results.
See targeted.log/targeted.xml, harness.log/harness.xml and verification.json.

## Hosted closure

Published candidate d80ceb80c6add545e1da0a87cf3cc26c8aff38e0 has the exact
measured runtime and driver. Run41077846816 passed both jobs:4430 simulation
tests plus2 subtests in6965.50s, and proof/scaling validation. Both downloaded
artifact ZIP digests matched GitHub; both source receipts identify d80ceb8.
Hosted scalar insertion raw save at1k/10k/100k values was
0.126529/0.116393/0.127276s, with0unrelated history bodies and0full World
audits. Artifacts/source/summary retained in hosted-41077846816/. This closes
the package correctness gate, not the complete-year or mature performance gate.
