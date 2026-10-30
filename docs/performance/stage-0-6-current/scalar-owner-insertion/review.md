# Independent whole-package review: bounded fresh scalar-owner insertion

Reviewed the working package against base `1de96bd`: `persistence_proof_world_insert.py`, its manifest publisher integration, `test_stage_0_6_proof_world_insert.py`, and the added native insertion scaling driver. Read-only review; only this review record was written. No hosted actions or full suite were run by the reviewer.

Final disposition: no open actionable Critical, Important, or Minor findings after the fixes below. This is a bounded topology transition, not evidence of whole-year or mature-world latency acceptance.

## Closure register

| ID | Origin / severity | Finding and concrete action | Evidence | Status |
| --- | --- | --- | --- | --- |
| SI-R1 | Independent reviewer / Important | Identical ordinary World owner bytes still acquire a new source revision/checksum. The original insertion validator accepted such a rewrite without advancing its catalog owner witness. Reject every ordinary `world.FAMILIES` owner from this insertion slice so the existing checked fallback validates the complete source transition. | Before the fix, injecting an unchanged `world.settlements` record alongside a new Person committed generation 1 with `reaudited=False`; fresh audited reopen failed `identity owner/header commitment disagreement`. The final ordinary-owner corruption regression requires rollback, exact recovery, and successful normal retry. | Closed: code inspected and focused regression passed. |
| SI-R2 | Independent reviewer / Minor | Allocation-free scalar partnerships omit catalog singleton writes, while `IdentityCatalog.prepare_delta` still reads CATALOG/0 and RETIRED/0. The original path did not authenticate or budget those reads. Authenticate both singletons against the parent content root through the shared cached predecessor helper, charging payload plus memberships before catalog regeneration. | Before the fix, an allocation-free save had no singleton input rows and read both through `read_version`, with neither passing through `_source_version`. Final self-checksummed-forgery regressions for both singleton namespaces reject with `insertion predecessor lacks accepted content`, then recover and retry normally. | Closed: code inspected and both focused regressions passed. |
| SI-R3 | Root author / representation boundary | A family name alone cannot authorize introducing lazy authority for an eager-only collection. Require a declared collection in the authenticated parent directory before accepting a fresh owner. | Final guard uses the accepted parent directory lookup before projection. The `world.local` regression returns fallback before lazy projection; normal Person insertion still succeeds. | Closed: guard inspected and focused regression passed. |

## Integrity assessment

The final path authenticates changed version predecessors and the always-read catalog singleton dependencies, reconstructs canonical catalog rows with the existing participant, and compares the complete frozen catalog transition. It proves new owner placement absence, limits fresh inline records to one root placement, and requires fresh incarnation IDs to be a contiguous allocation from the accepted allocator.

Successor certification reconstructs the exact changed owner/group directories and compares those roots and allocator to the actual scope publication. Extra, missing, or misassigned identity changes cannot be hidden in the successor roots. Fresh inline semantic placements require absence in the accepted owner-projection and backing-inventory facts. Other topology inventories remain unchanged.

Layout handling authenticates the previous overlay or original manifest and increments each collection by exactly the new owner count. Head scalars retain the existing checked head/source comparison; `next_event`, event roots and event sources remain unchanged in this slice. Query memberships are checked against the actual successor order. Lease updates retain the existing mandatory ownership validator. Existing owner edits, backings, aliases, retirement and events retain the checked fallback. The existing publisher remains the sole writer.

The scaling driver separates construction/admission, traced first save, raw later save, bounded SQLite work, and fresh audited reopening. Its synthetic retained-value archives are explicitly distinguished from simulated years. The reviewer inspected the harness but did not run its full archive matrix.

## Reviewer verification

Final focused command:

```text
PYTHONPATH=simulation:. python -m pytest -q simulation/tests/test_stage_0_6_proof_world_insert.py -k 'allocation_free or eager_family or ordinary-owner or native_new_person or native_new_scalar_partnership'
6 passed, 13 deselected in 10.67s
```

These checks cover both supported native shapes, both singleton-authentication regressions, the representation boundary and the previously reproduced ordinary-owner bypass. Broader package gates, fault cases, fresh-process mixed-family checks and archive scaling are owned by the root author; this review does not claim their results independently.
