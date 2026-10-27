# Native integer-list growth across physical pages

Appending integer tails to an existing nonempty integer list can add new pages without
full-history audits. Old descriptor/type/partial-tail bytes and semantic leaves are
authenticated. Each contiguous new page and its exact empty owner witness require
accepted absence. The expected complete child-directory successor and exact content
cardinality delta are independently checked at manifest publication. The existing
collection constructor derives changed auxiliary order roots from the validated frozen
delta; complete owner/group/sequence roots, allocator and head inventory stay unchanged.
No second publisher/registry or caller success flag is introduced.

Frozen bytes remain authoritative; all rows and source witnesses still participate.
New page bodies must contain exact ints, not bools/references.512 rows/4MiB and128
new-page limits keep the fast domain explicit. Page removal, retained-owner regrowth,
empty-parent growth, reference/noninteger edits and larger changes keep checked audit.
Admission/recovery remain audited. Broader structural/open/default/mature goals remain
active; no main merge, default activation or endurance occurs here.

Local tests include first/full/partial/multiple new pages, malformed bodies/witnesses,
all fault seams, deletion and retained-owner regrowth. Independent review probes cover
multiple parents and hidden new-page references/occurrences, with audited reopen.

Measurements include first native access,128 appended ints and complete native save.
A separate fresh session appends128 again with interval-one SQLite VM accounting.
Setup/audited admission stay separate. Final audited reopen checks exact size and shared
identity. Counts are selected payload SELECT requests, including absence probes, not
physical disk IO. Retained values are not mature records or simulation years.

| Retained values | First access + page-growth save (ms) | Selected page queries | Unrelated body queries | SQLite VM steps |
| ---: | ---: | ---: | ---: | ---: |
| 1,000 | 304.01 | 17 | 0 | 355,784 |
| 10,000 | 452.23 | 17 | 0 | 357,664 |
| 100,000 | 215.74 | 17 | 0 | 360,251 |

Local gates: 121 related tests, 120 native tests passed without failures/errors/skips. Full proof/full suite are hosted gates per the user’s no-long-polling instruction. Source hashes and exact receipts are in list-page-growth/verification.json.
