# Checked sealed tail authority

Continue the approved Stage0.5 execution. No new approval or capability activation.

Readonly descriptor roles alone cannot certify deep immutability: native freeze
preserves mutable record children. Extend the staged frozen list/map descriptor
with a mandatory exact boolean certification, computed from actual incoming D.
True requires immutable scalar/tuple values and recursively certified frozen
references. Record references and mutable history roles always make it false.
Reuse existing checked descriptor/version rows, registry, caches and publisher.

Bounded sealed suffix validation may use an explicit checked authority callback.
Pure P3B sealed segment validation continues to require standalone native frozen
values. The cold reader callback checks the frozen descriptor at its captured
transaction generation; runtime callbacks check their exact store/pin and pending
D. Full scrub recomputes certification from actual stored rows and checked child
flags; conversion must run it before publishing complete format6. No archive walk
on ordinary suffix open/save/header validation. Materializing detach and segment
packing are explicit value materialization paths.

1. RED/green descriptor certification, malformed/absent flags, mutable record child.
2. RED/green recursively backed Event seal/save/reopen as a World tail, no archive
   reads; preserve pure segment validator and fault behavior.
3. Integrate full certification scrub, lifecycle, actual segment packing, shared
   record retirement and measured paired H work; focused affected gates.

Complete format6 feature markers/source copy, legacy eager root normalization,
actual schema/byte closure, promotion, equality and final release gates remain.
