# Stage 0.6: bounded source/catalog composition

Continue the accepted whole-year integration on green `bc96009`, run
41891188691: both jobs successful, 4,504 passes plus two subtests.
The original sequence package's hosted regression is closed.

## Goal and existing authority

Route a finite whole-year batch through independently bounded existing
validators while retaining every frozen publication row. The existing native
publisher, content/inventory proofs, canonical catalog replay, source witnesses,
scoped relations and exact final root comparisons remain authoritative. No
private routing decision is a certificate.

The observed small generated year has 1,202 version rows, including 597
accepted existing lease updates. Its 605 remaining rows comprise 262 source
rows and 343 catalog rows. Source validation and canonical catalog replay are
different work components. The current total-row shape gate rejects their
composition before either can certify it.

## Approach and engineering decisions

Use one bounded classifier: at most 512 noncatalog source rows including
ordinary rows, and at most 512 catalog rows. Keep the insertion validator's
aggregate 4 MiB encoded request-plus-predecessor limit. Keep existing lease
budgets 4,096 rows / 4 MiB old-plus-new bytes. These are separate validation
contracts, not a larger single semantic cap or an assertion that all validators
share one cumulative byte budget.

Frontier validators receive source rows plus catalog owner headers needed by
page/leaf source witnesses; their complete input remains at most 512 rows.
The full source/catalog batch still reaches the insertion validator, which
must reproduce every catalog delta exactly. Existing value-only validation
retains its 512-row contract. Oversized, unsupported or incompletely certified
batches retain full checked fallback; partial certification grants no reuse.
Routing inspects only already prepared namespace labels, without decoding
unbounded source bodies or materializing streamed batches beyond the sum of
component row limits. Unknown namespaces consume source budget and remain
subject to existing rejection. All rows still reach the original publisher.

Alternatives considered: raising a global cap hides component work and was
rejected; splitting saves into separate transactions changes frozen identity
and recovery semantics and was rejected. Existing user authorization is for
bounded component composition in the original transaction. Detailed routing
is the implementer's decision under that authorization.

## Acceptance and limits

Real native saves above the old total-row cap must avoid full World audits
when each component is individually certifiable. Verify lease composition,
canonical catalog equality, exact source/type/owner witnesses, eager state,
fresh-process restore, identity sharing and fault recovery. Corrupt or omitted
catalog rows must reject and recover/retry. Over-budget source, catalog and
frontier shapes retain checked fallback; no alias/history scan is added.

Run the same complete generated year against its independent eager control,
then fresh-process verification. Report the first remaining unsupported shape
if composition alone does not cover it; preserve fallback rather than infer
coverage. This package does not promise new map-growth or ownership semantics
without their own bounded proof. One independent whole-package review closes
all findings, followed by one bundled hosted full/proof validation for runtime
changes. Mature measurement and targets, default activation, main merge and
endurance remain separate gates.

## Evidence-led scalar growth extension

The accepted diagnostic passed the count gate with scratch-only instrumentation
but next rejected fresh physical entries of existing nonempty sets (integer and
lineage-pair member policies). Add bounded append-only scalar map/set growth:
at most 16 changed backings / 128 appended entries / 512 input rows / 4 MiB
old-plus-new predecessor bytes, sharing the sequence proof's accepted-content
source reader. Require authenticated nonempty predecessor extent/type counts,
exact positive count/next-ordinal growth, contiguous unique fresh ordinals,
canonical keys and memberships from the registered physical owner adapter,
accepted entry/child absence, and exact empty source-owner witnesses. Update
backing/order facts, child extents and source counts. Preserve every possible
integer/lineage-pair incoming policy from nonempty accepted type counts. Empty
and reference-bearing shapes retain fallback. Reuse existing publishers and
canonical catalog replay; add no secondary graph or transaction authority.

The further diagnostic boundary is now known rather than guessed: full years
also allocate identities for ordinary Event records/data, packed agency-action
appends and replacements of existing agency motive records. These are not a
scalar set proof, and missing allocator coverage must still reject reuse. This
package closes source/catalog routing and scalar physical growth as one bounded
integration step; ordinary event/action and replacement composition remains the
next explicit integration gate, with exact real-year evidence preserved.
