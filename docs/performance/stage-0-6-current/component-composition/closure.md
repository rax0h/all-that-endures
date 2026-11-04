# Bounded source/catalog composition and scalar growth

Parent `bc96009` is verified green in run41891188691: both jobs successful,
4,504 full-suite passes plus two subtests. That closes the previous sequence
fallback repair; its raw/history register is retained.

## Implemented in the original publisher

Source and catalog row accounting now belongs to separate bounded validation
components:512 noncatalog source rows including ordinary rows,512 catalog rows.
The insertion validator retains its aggregate4MiB request/predecessor allowance.
Existing accepted lease updates retain their independent4096-row/4MiB budget.
Frontier validators receive sources plus required owner headers, capped at512
rows. Oversized prepared streams are not materialized. Every original row
still reaches the existing content, inventory and canonical catalog publisher.
Routing grants no certificate and creates no secondary transaction/graph.

Existing nonempty scalar map/set appends now certify up to16backings/128fresh
entries with512input rows and4MiB old-plus-new accepted source bytes. Require
contiguous fresh insertion ordinals, canonical equality keys and exact query
memberships, accepted entry and child absence, exact member-type deltas, empty
source-owner witnesses and unchanged possible integer/lineage-pair policies.
Compose backing/order facts, child roots, row counts and source witnesses with
sequence/list frontiers and new native owners. Unsupported empty, reference-
bearing, nonappend or over-budget shapes retain checked fallback.

## Verification

The native160-new-Person save reproduced the old total-row audit fallback RED;
its source and catalog components are individually below512, and the candidate
save/reopen passes without an audit. Native set/map growth independently
reproduced audit fallback RED, then passed. Final tests also cover canonical
catalog tamper/recovery above the old total cap, malformed entry/type/ordinal/
query/header rejection, exhaustion, oversized streams, before-head/commit/lost-
ack faults, unrelated history bodies, and fresh-process digest/sharing.

One independent Astra/high package review found no runtime soundness defect
and one Minor missing-coverage issue. Retained class-change fallback cases and
combined lineage-pair/map/sequence split/new-list-page/fresh-owner save with
fresh-process verification close that finding. Author test-sentinel and minimal-
request compatibility findings are tracked with evidence in `review.md`.
Final test counts, exact source mapping and hosted gate are recorded below
when all checks finish; no global suite success is inferred from local subsets.

## Complete-year result and exact remaining integration

The canonical generated seed843000 8x6 one-settlement eager-year2→proof-year3
probe passes raw and diagnostic saves, matches independent eager state in fresh
interpreters, and preserves the accepted source hash. The full year still uses
checked fallback: its new identities include ordinary mutable Events/data,
packed agency-action append members and replacements of12existing motive roots.
The insertion proof correctly refuses incomplete allocator coverage. Neither
component speed tests nor this passing fallback establish annual proof reuse.

The next integration group must authenticate ordinary new event sources and
packed action suffixes against accepted record roots; derive their exact
placements; certify existing scalar motive-root replacements and old/new alias
scope deltas; compose compact Event-ID range/backing/order facts, event-tail
controls, ordinary collection order/layout counts and next_event; replay the
canonical catalog once with all bounded source slices and require complete
allocator coverage. Existing sealed event history remains accepted authority.
Unsupported sealing/truncation/general graph replacement must retain fallback
until separately certified. Do not omit sources or infer these transitions from
namespace membership, allocator growth or dirty runtime state.

Mature10s open/2s save/1s warm-year targets, proof-reusing ordinary admission and
final Stage0.6 acceptance remain open. No mature benchmark, default activation,
main merge or endurance run is included.

## Final local source and checks

Runtime `93308f7124a6cd1ca73dd5d46421c23ed597d2ad`.
Published source checkpoint `e026be8d074e36e1707a92ff3675bc035815ba85`
has full tree `5f5d340d73ec0191897ec4bc3209744e422b3a2c`, identical to
locally validated `7cdfd1c2e46fbd7589a2908e0efba124df9aa3a3`.
Earlier feature checkpoint `0207c86` has the exact tree of published `4ddf99f`;
its pre-compatibility year receipt is retained as historical evidence only.

- Final **40 component/backing cases passed132.96s**, including all28new tests,
  both fixed classifier compatibility cases and both corrected body sentinels.
- Final clean-source **29 launcher cases passed23.61s**. Runtime pin, every
  launch fingerprint, workflow YAML/bash and diff whitespace checks pass.
- Initial broad run: **257passed,4failed in905.86s**. Its four failures are
  the two overstrict test sentinels and two minimal-request compatibility
  cases, all resolved and rerun in the final40cases. It is supporting evidence
  for its earlier runtime, not represented as a green exact-final full suite.
- One independent review Minor and both author findings are closed in the
  consolidated register. No second independent review is claimed.
- Canonical clean final-source year probe completes both raw/diagnostic saves,
  independent eager/fresh-interpreter checks and unchanged accepted input.
  `evidence/real-year-final.json` records separate operation timings. Local
  concurrent test load differs from previous runs; no controlled timing
  comparison or annual/mature performance improvement is inferred.

One evidence child and one branch update publish this package. The full/proof
hosted gate remains open until that exact published source passes. No mature,
default, merge or endurance action was launched. The next integration work is
ordinary event/action/motive replacement composition described above.
