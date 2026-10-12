# Explicit Copy Backing Integrity Plan

The complete Stage0.5 directive authorizes implementation of converter integrity
checks and their focused regressions.

Counterexamples: checksum-valid self/two-backing cycles, an empty page with no
matching descriptor, an orphan locator in an existing counted sequence, and
sequence parent/locator/member/directory rows owned by an append backing were
accepted by the private copy. All eight RED cases reproduced actual publication.

Use current captured physical rows and existing owner adapters/dependency rosters
to prove each physical row has a backing of the right role. Traverse only this
existing relation with transient iterative cycle-check state during explicit full
copy; do not create another persisted ownership graph or ordinary-operation scan.
Run the existing full counted sequence scrub for every complete destination
sequence, including ones carried from the source. Checked partially retired
trees keep the existing retirement exception and type/queue checks.

Tasks:
- [x] Reproduce semantic graph and orphan-projection failures with checked rows.
- [x] Validate physical parent roles and reject cycles before publication.
- [x] Fully scrub preexisting counted sequences, not only new promotions.
- [x] Run focused/affected gates and checkpoint exact source/evidence.

Final focused9 passed in0.82s. Affected80 passed in8.80s precedes only the
additional valid shared-diamond test; production matches both gates. The diamond
copies and reopens with both parent paths resolving one canonical child. Sequence
directory keys use bytes prefixes; an initial overstrict integer check was
corrected against the existing concrete schema before the final gates.

No ordinary World open, capability6 marker, rank/gameplay, PR14, new P5 or endurance
claim is part of this correction.
