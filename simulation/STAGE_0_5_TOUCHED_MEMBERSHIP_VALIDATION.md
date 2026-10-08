# Current touched-membership overlay repair

Before implementation, one dirty notice with1,000/10,000 status edits retained every obsolete status bucket. Both scaling regressions failed in0.43s.

The repair indexes current membership markers per touched key. A change removes old-only markers, prunes empty buckets and adds new-only markers; deletion removes only that key's candidates; successful publication clears both overlay maps. No cold row scan or change to persistent memberships/query selection is introduced.

Focused checks verify exact current-width retention at both edit counts, old/current status queries, save/reopen, another record sharing a candidate bucket, deletion and before-commit failure/resolve/retry. Existing lazy institution and transmission/scalar-archive consumers are also exercised. The institution/scalar/facade gate passed57 tests in1.20s before additional facade checks. Final combined component/storage/owner/institution gate: **143 passed in10.30s**. P5 seed843000,3+4+3 with paged households also passed with the unchanged control digest.

This fixes the overlay accumulation defect in existing lazy tables. It does not complete remaining scalar-family migrations or the application branch/passed threshold/index upgrade. No full suite, long run or production promotion was performed.
