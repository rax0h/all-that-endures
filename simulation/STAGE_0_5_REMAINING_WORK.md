# Stage 0.5 remaining work — October 12 checkpoint

Stage 0.5 is unfinished. This list names implementation and release gates;
passing component tests is not whole-stage acceptance. Rank issue17 is deferred.

| Work | Current boundary | Next concrete gate |
|---|---|---|
| Exact nonreflexive keys | Native registry, checked atom bodies, projection and physical key paths exist; live scalar histories have not selected them. | Atom backing metadata/lifetime in the existing registry and publisher; scalar admission/lookup/iteration; key/value alias sharing; all 12 RED cases green. |
| Complete graph compatibility | Checked copies cover many mutable records, Events, currency roots and compact Event-ID references. New NaN edges are explicitly rejected during copy. Other unsupported roots and exceptional imported shapes remain. | Complete root/consumer inventory, source-preserving key identity mapping, checked target roles, reopen/copy/detach and rejection/recovery cases. |
| Field and byte closure | Static field coverage exists; actual writer guards and unrestricted imported values still need final closure. | Verify growth writers and byte costs for every field; close remaining unbounded topology/root serialization paths or document concrete authorized boundaries. |
| Complete format activation | Capability6 and ordinary complete-format open are intentionally withheld. Private fixtures select checked authority explicitly. | Complete markers/reader floor, ordinary open without global/history scans, explicit no-overwrite source-copy upgrade, corruption-versus-legacy checks. |
| Integrated validation | Component gates are green at their own source boundaries. Prior P5 remains historical certification. | Final cross-family faults/recovery, fixed-work H1k/H10k bytes/reads/writes/cache/lifetime/maintenance checks, independent P5 continuation. Then one final applicable full suite on stable source. |
| Final independent review | Not requested yet; implementation is incomplete. | Astra review of stable source and full evidence; repair findings and rerun affected gates. |

The exact native ordered pressure cold-miss exception was already authorized;
do not ask for it again. Preserve that arithmetic and bounded-memory path.
No rank/gameplay work, PR14 mutation, force push, Stage1 or new endurance.

For the immediate key runtime step, float atoms need private backing metadata
without a second canonical-object registry. Native floats cannot support weak
references or assignment-binding attributes. The existing conditional registry
root can own private metadata while the native value has R/D; backing metadata
must not be registered as the canonical value. Hold new input D through the
frozen plan and release it at acknowledgement, then bound deferred cleanup.
Scalar constructors must preserve original member-type representatives while
projecting stored addresses/payloads. Both map keys and values can share a NaN.
Use the existing dependency/retirement machinery for held unowned aliases;
complete copy/detach identity mapping before removing the copy guard.
