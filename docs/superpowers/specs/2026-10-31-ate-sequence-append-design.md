# Stage 0.6: authenticated existing-sequence append composition

Continue the whole-year work from `lease-composition/closure.md`, against green
`19c903f` / run 41251612123 (4,482 full-suite passes, both jobs successful).

Certify finite append-only transitions of existing nonempty counted sequences
using the existing `LazyOrderedSequence` transition algorithm in a private
replay. The replay receives a read-only predecessor view: every fetched source
or absence must match the accepted content root, with aggregate row/byte limits.
It has no World registration, canonical identity, publisher participant, or SQL
write capability. Its only output is an expected frozen delta. Compare that
delta byte for byte to the actual prepared sequence/type rows before admission.
Reuse the existing main-tree, membership AVL and radix-directory implementation,
including leaf/root splits, instead of adding another tree algorithm.

Extract new occurrences from changed leaf rows; require contiguous fresh IDs,
matching length/occurrence growth and an increased descriptor revision. The
revision is storage mutation metadata: append calls and extend can have different
revision increments with the same final tree. Preserve the exact supplied
revision after validating monotonicity. Scalar immutable members only; touched
reference-bearing leaves retain fallback. Preserve any possible existing integer
or lineage-pair incoming policy from the accepted nonempty member-type witness.
Empty-sequence appends and other edits remain checked fallback in this group.

The existing central publisher retains every original row. Compose exact
backing/order facts, physical child and sequence locator scopes, content counts,
and empty leaf-owner source witnesses. Existing scalar leaves keep their exact
owner witnesses; new scalar leaves require accepted absence or an authenticated
inactive empty owner. Catalog/source/scope checks and recovery remain mandatory.
Allow composition with existing values/list tails and fresh native owners.

Budgets: at most 512 semantic input rows / 4 MiB as before; sequence replay at
most 16 changed backings, 128 appended values, 512 distinct predecessor reads and
4 MiB old-plus-new encoded source bytes for the entire request. Exhaustion or
unsupported shapes retains the full checked path, never partial acceptance.
No catalog-cap increase or unrelated history scan is a substitute for coverage.

Acceptance: no-audit actual native saves across leaf/root splits and deep trees,
exact values, sharing, occurrence/membership order and fresh-process digest;
adversarial missing/wrong sidecars, descriptor/type/owner witnesses, rollback and
lost acknowledgement; bounded reads beside retained unrelated history. One
independent package review, all findings closed, then one bundled full/proof CI.
Measure the same complete real-year scenario and state remaining unsupported
transitions. This group alone does not claim mature target attainment, default
activation, merge or endurance authorization.
