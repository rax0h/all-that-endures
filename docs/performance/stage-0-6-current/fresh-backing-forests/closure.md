# Stage0.6: fresh backing forests in native World saves

Base81f40bd passed both jobs of41172952568:4450tests plus2subtests in4458.31s.
Both artifact ZIP digests and exact source receipts were verified and retained
in `../mixed-owner-transition/hosted-41172952568/`.

Exact final validation/measurement source:
`0f205f3843447ae8472c973fba5572704ce9bc2d`.
Runtime tree: `ec913495f7cd83dbef6b9eebe6c2a6dd9efe0bf7`.
This source commit is preserved as a parent of the final evidence publication;
creating the source object did not launch CI or move the working branch remotely.

## Implemented behavior

The existing native save publisher can now admit fresh list, map, set and mutable
registered-record backing forests alongside fresh World owners and the existing
value/tail changes. It authenticates complete finite extents from frozen rows,
member counts with exact types, backing dependencies and incoming policies.
Projection and type helpers accept an explicit checked header reader, so typing
new record references does not depend on unpublished database rows.

New edges must resolve to complete fresh backings or accepted old content and
semantic backing facts. Old history bodies are not traversed. Registered record
field policies apply to fresh and referenced old backed records, using projected
successor type witnesses where applicable. Fresh record edges participate in
cycle detection. Per-incarnation kind/fingerprint checks prevent inconsistent
aliases or competing inline/backed identities.

The same catalog primitive regenerates exact owner/group/link witnesses. Its
point readers authenticate and charge metadata, including retirement helper
reads. Accepted old alias counts are capped before regeneration; physical
occurrence/link rosters are checked with indexed count-plus-one probes, bounded
fields and byte accounting before legacy iterators can traverse them. Exact
owner, group and child successor roots, contiguous allocation and content count
deltas are compared to the actual publication. The established value/tail,
ordinary source, layout, query, head, event and inventory checks remain active.

Existing512-row/4MiB insertion-source budgets remain, with4096 projection and
accepted-old-alias caps. Reused validators retain separate limits; there is no
claim of one4MiB cap across every duplicate/helper read. No second publisher,
identity registry or storage format was introduced.

Unsupported fresh sequence/frozen/atom/event graphs and generic record container
representations choose checked fallback. Arbitrary existing backing-reference
replacement and retirement remain outside this slice. Supported sharing of old
backed history now uses proofs; the previous fallback-only tests were updated
to assert that behavior and identity preservation.

## Measured workload and scaling

The scenario creates a Person, a skill referencing existing shared history, and
a Practice with new maps, a set and a shared registered record with new history
lists. It also edits existing skill/ordinary values and advances year/counters.
Timing includes mutation and save. Separate fixtures use the same constructor;
baseline is the previous green81f40bd. Python3.12.14, SQLite3.53.1. Other local
tests were active; these are observations, not controlled repeated timing bounds.

| Retained history values | Previous green save | Candidate save | Candidate SQLite VM steps | Unrelated old history bodies | Full World audits during save |
|---|---:|---:|---:|---:|---:|
| 1,000 | 0.747374s | 0.390948s | 742,445 | 0 | 0 |
| 10,000 | 1.222306s | 0.333128s | 746,805 | 0 | 0 |
| 100,000 | 5.843948s | 0.361401s | 752,668 | 0 | 0 |

The baseline used2 full World audits per save. The100k observation is about16x
faster; candidate VM work rises1.38% across100x more retained values. Construction
and full admission, traced first save, raw second save and third-save VM work are
separate phases. Body attribution permits only newly allocated changed bodies;
explicit method guards forbid old page/entry reads in the10k sharing regression.
Fresh full audited reopen verifies all created objects, aliases, nested values,
old history length and existing edits. See `candidate/`, `baseline/`,
`comparison.json`, `baseline-probe.py` and the existing driver's `--scenario fresh`.
CPU time and database size are retained in machine-readable candidate receipts.

These archives contain retained values, not simulated years or100k backings.
They do not establish mature-world opening, simulation or complete-year save
acceptance. Full initial audit/admission remains outside the raw save metric.

## Review and verification

One independent review began with the design and covered the implementation.
Its original report and supplemental fallback closure are in `review.md`.

| IDs | Origin | Resolution / evidence | Status |
|---|---|---|---|
| F1 | Design / Important | Aggregate alias kind/fingerprint checks, unique backing authority, record-inclusive cycle detection; recataloged cyclic input rejected | Closed |
| F2 | Design/code / Important | Cap accepted aliases and bounded physical rosters; authenticate catalog, retirement and link sources; surplus tests forbid legacy scan, recover and retry | Closed |
| F3 | Design / Important | Use successor descriptors/type witnesses for new edges; independent stale-parent/successor-policy probe rejects wrong member policy | Closed |
| F4–F5 | Design/code / Important | Replay registered record incoming policies for new and old backed targets; both boolean-transfer bypass cases rejected | Closed |
| F6 | Completion / Minor | Correct scope comments, remove unused state and update newly supported alias expectations | Closed |
| F7 | Author / Important | Unsupported fresh kinds and alternate generic record representations select checked fallback; sequence and generic Household save/restore regressions pass | Closed |

The reviewer independently passed21 initial tests at98c44a5, then4 focused final
fallback/policy cases after F7, with no second whole-package cycle. No unresolved
actionable Critical, Important or Minor finding remains in this finite group.

Local evidence distinguishes source versions:

- 242 broad proof/native tests passed415.57s at the main98c44a5 implementation,
 before the final fallback-only correction. This includes World audit/helper,
 native session/value/backing/tail and complete generated-world continuation.
- 40 final tests passed136.78s on exact source0f205f3, including all23 new backing
 cases and generated years3/4 with independent eager control and fresh-process
 digest equality. The final correction is covered by this gate.
- 88 benchmark/retained-fixture harness tests passed35.53s; final clean exact
 launcher recheck29passed17.44s. One earlier exact-harness attempt correctly
 rejected report edits making tracked source dirty; it is not counted as green.
- Final runtime pin, every launch fingerprint, workflow YAML, shell blocks and
 whitespace checks pass. Logs/XML and `verification.json` preserve the evidence.

The prior hosted proof job used52m32s; its job cap is now90m to retain room for
the new matrix and observed hosted variance. Individual scaling timeouts stay
unchanged. This does not change performance targets or claim faster CI.

## Remaining acceptance gate

The observed real-year transition still exceeds512 rows and includes unsupported
sequence and existing backing/ownership changes. It retains checked fallback.
Next work must compose authenticated existing graph edits and retirement with
the remaining concrete backing kinds, while preserving complete-year exact
continuation. Raising row limits alone is insufficient. Initial mature opening
and simulation selection cost remain separate measured blockers.

| Mature operation | Current final source | Repository target | Acceptance |
|---|---|---|---|
| Open/restoration | Not measured on the retained year1001 checkpoint | 10s | Open |
| First simulation year | Not measured | No separate defined target | Not established |
| Warm simulation year | Not measured | 1s | Open |
| Incremental save | Not measured for a complete mature-world year | 2s | Open |
| Fresh restore after save | Not measured | No separate defined target | Not established |

The separate millennium generation120s benchmark is unchanged. No new mature
run, endurance, default format activation or main merge was launched. One
bundled full/proof CI validates the final runtime group, with long CI left to
complete without busy polling. Stage0.6 completion is not claimed.
