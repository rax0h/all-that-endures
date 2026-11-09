# Independent review closure evidence

Whole-package review against BASE `7df089ff2b347ae8e36bb535291591a5bb6dfb82`.
Initial findings and raw reproductions remain in `initial-review.md` and adjacent
logs/scripts. This report supplies evidence to the group's consolidated closure
register; it does not replace that register.

At checkpoint `b628bd10739bcba660be9f6bf700765f25cb7be7`, independently verified:

| Initial finding | Action verified | Evidence |
| --- | --- | --- |
| Query rebase locator omitted ordinal | Locator and UPDATE identity include ordinal; two ordinals survive rebase and full audit | `closure-probes.log`, `closure-tests.log` |
| Per-sequence Python physical inventories | Expected keys/member relation use DiskSet; occurrence rank/value uses DiskLookup; structural/locator/member inventory checks remain | `closure-probes.log` |
| Frozen-map certification bulk entries | Clean conversion certification streams checked entries; an `_ordered_entries` guard remains uncalled | `closure-probes.log`, `closure-tests.log` |
| Construction algorithms reached default audited opener | Conversion ContextVar gates newly introduced workspace arguments; real audited opener outside construction passes no bounded workspace | `closure-default-audit.log`, `closure-tests.log` |
| Bounds documentation overstated disk and total RSS | Design explicitly distinguishes fixed physical-inventory memory, proportional disk, single-row costs, native canonical keys and restored World registry | Current design text reviewed |

The independent qualified-runtime sequence probe at length1k/10k measured Python
traced peak253593/207792bytes, versus initial523542/4156683bytes. Both current
runs used disk inventories for2020/20168 physical keys and1k/10k occurrences.
This is small-fixture physical-inventory evidence, not mature total-RSS or timing
acceptance. The frozen/shared-spool guard completed1000 empty iterations without
creating another workspace. Exact pre/post hashes of180 runtime/test/harness
files matched; see `closure-source-hashes.json`.

Fresh independent boundary and mature-harness verification:45 tests passed6.40s,
exit0, with JUnit evidence in `closure-tests.xml`. The full qualified runtime tuple
is recorded in `fingerprint.json`. No full suite or hosted cycle was launched by
this review.

**Review group remains open.** Finding6, the unchanged complete generated-year
construction failure, is still being investigated by the implementer. Preserve
`generated-year-construction-red.{json,log}`. Cause and baseline/introduced status
remain unassigned by this review. After repair, review that change and verify the
unchanged complete generated-year scenario, final request/runtime fingerprints,
and any affected boundary controls before marking the group complete.

Subsequent baseline/isolation evidence and the conditions for one bundled hosted
validation are recorded in `hosted-validation-disposition.md`. Finding6 remains
open; proceeding to evidence collection does not imply group completion.

No mature acceptance, publication, merge, default format activation or endurance
run is claimed.
