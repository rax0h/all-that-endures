# Fresh whole-package review and rulings

Independent read-only review of05c755ded89bb8cdde986308f0274380dec60745..608de851e40788bf8fa10fcd02fe025c46e88a4e; one reviewer, no nested review. Independent probes passed100 randomized build/update/delete/canonical-root trials with arbitrary absent cursors, plus UTF8 and zero-escape round trips. No runtime correctness defect or Critical issue found. Verdict: with fixes, not authorization to merge main.

## Important: newer frontier in both measured scopes

Finding: driver and parametrized test put all large newer archive placements into group2, whose old root was empty. Measured nonempty old group1 encountered only small reassignment/deletion changes. Thus first receipts did not demonstrate the nonempty-old-group1k/10k/100k gate.

Ruling: accepted. Population assertions reproduced two RED failures. One repair pass gives each measured group exactly size newer archive placements, asserts real database counts, preserves exact old pages, and verifies current root count plus literal current page. Fixture has2*size archive placements; index point measurements retain size entries. Initial scaling receipts are not accepted evidence and are superseded by the corrected clean-source matrix.

## Minor: parser boundary vectors

Finding: no committed direct UTF8/escaped-zero/prefix/malformed/surplus/invalid-UTF8/4096byte boundary tests, despite valid independent probes and no observed parser defect.

Ruling: accepted and addressed in the same pass with literal round-trip vectors, malformed stored-position rejection, and every individual field at4096/4097bytes with distinct budget errors. No runtime changes were needed for either review finding.

## Declined-to-judge rulings

- World activation, complete topology, atomic publication and ordinary-payload retention: correctly deferred, explicit integration gates remain; no World reader/writer changed.
- Unselected physical surplus/corruption: accepted bounded-proof/full-audit boundary. Such rows are never admitted; full inventory conformance remains a construction/transition gate.
- Mature save/open speeds, endurance, universal constant time: correctly outside this package. Prefix depth and page size still matter.
- Pending corrected scaling, successor CI and publication: completion must use their actual new receipts, never predecessor green. Full successor CI remains pending until authenticated.

No finding silently dropped. No second reviewer/re-review. Main merge and endurance remain out of scope.
