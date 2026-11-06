# Native head metadata — accepted-manifest read binding

Stage 0.6, dedicated proof branch; this package does not remove audited admission.

The pre-existing `LazyRecordStore.head_metadata()` returned a checksum-valid
current `save_head` row. Its local checksum alone could not prove that
coherently rewritten metadata was the externally accepted World head. The
new read uses the already admitted native authority and original generation pin,
compares all five encoded/typed published fields plus generation against the
accepted generation manifest **before decoding any changed row**, and leaves
non-proof/initial-admission/publisher paths on their existing behavior.

The comparison reuses `_checked_head_row` and its byte validation. There is
no second manifest, cache, publisher, schema revision or whole-history scan.
It keeps the existing transaction/snapshot rules. Sealed event descriptor
namespace decisions, which use `head_metadata`, thereby consume accepted
inventory rather than only a recomputable local checksum.

Tests cover the original manifest, same-session save, fresh-process restore,
nested read snapshots, and coherent tampering of position, seed, next IDs,
inventory and counts with a recomputed checksum. Tampered values must be
rejected before decoding. The original ordinary source check remains intact.

This is one metadata-reader slice, **not** a general proof-only-opening claim:
rank-neighbor global sorted selection, event/retirement prefix enumeration,
and raw metadata-reader consumers still require separate coverage. Current
full audited opening remains mandatory. No mature timing, default promotion,
main merge or endurance claim. Hosted CI must pass for completion.
