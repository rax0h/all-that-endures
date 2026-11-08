# Native metadata and cached-prefix boundary

Execute inline under the existing Stage0.6 continuation authorization. Baseline
98eb84a is hosted green in42438098176:4872tests+2subtests9417.42s and proof-map
successful. Do not remove full audited admission or change persistence defaults.

## Contract and implementation

Direct public generation/checked_head reads must join the same accepted head
as head_metadata, within the caller's checked native snapshot, before decoding.
Retain legacy/admission/publisher behavior. Native cached sealed prefix reads
must retain accepted epoch, current authority pin and persistent source context,
without rereading cached segment bodies. Reader replacement/close semantics after legitimate same-session publication
remain unchanged. A replacement reader can warm and reuse its own cache. Explicit verify_full
still bypasses the cache and checks source bytes.

1. Reproduce coherent forged-head bypasses through generation and checked_head;
   snapshot/codec drift; warmed prefix reads after external writes/callbacks.
2. Add a small native metadata head-snapshot helper used by the three public
   head APIs; preserve arbitrary-transaction rejection and owned read nesting.
   Add native prefix guard before cached data/descriptor access, using existing
   source authority and original immutable prefix semantics.
3. Inventory remaining direct record/query/head/segment consumers and classify
   ordinary native, admission-only, owned publisher/recovery, diagnostics, and
   explicit conversion/audit paths. Negative controls must support coverage;
   the inventory is not approval for proof-only opening.
4. Focused/broad tests, one whole-package independent review, close all findings,
   eager/fresh continuation on clean source, then one bundled hosted full/proof
   gate. No per-finding CI, merge/default/mature/endurance action.

Review focus: six/seven-root compatibility, heads read inside existing owned
transactions, codec changes during decoding, cache hits after save/rollback,
and caller-pin/epoch validation before stale cached output. Final mature
10s/2s/1s performance acceptance remains separate.
