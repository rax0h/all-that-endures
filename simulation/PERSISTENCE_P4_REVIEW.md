# P4 preparation — architect review and next boundary

**Reviewed head:** `4a6e23feb52894b1298a5cc09914e77156446f12`.
**Date:** 2026-10-05. **Reviewer:** Astra.
**Disposition:** preparation accepted; P4.1 storage direction approved with the
binding corrections below. Production P4 and Stage 0.5 are not accepted.

## Evidence

- The live change contains five new preparation files and no production edits.
- Completed Actions run [37269630276](https://github.com/rax0h/all-that-endures/actions/runs/37269630276):
  five probe tests passed in 1.16 s; 1k/10k baseline completed.
- Every simulation Python blob matches that candidate,
  `5e91bebe5719ff674ca56edc62275a2749f7843c`.
- All measured fields extracted from the completed job's baseline JSON match
  the committed JSON exactly. Its additional provenance/observations/targets
  are documentation, not extra measured results.
- Independent review command:
  `PYTHONPATH=/tmp/ate-p4-deps:simulation:. python -m pytest -q simulation/tests/test_persistence_p4_probe.py`:
  **5 passed in 1.11 s**.
- No full-suite rerun or long history was needed for this diagnostic-only change.

The people pilot is justified. With 32 active people and 1k/10k inactive people,
open reads rose from 2,103 to 20,103 and peak traced allocation from about 3.8 MB
to 31.0 MB. One reactivation/save stayed at 3 payload writes / 795 bytes.
The offer probe establishes only its particular irrelevant-consumed-stock case;
it does not prove all active-stock query costs or total resource memory bounded.

## Binding decisions

### 1. Generation-versioned storage and two-generation retention

Approve versioned payload/order/query records, operation-scoped read transactions,
and a maximum of current plus previous **visible snapshots** for the opt-in P4
mode. Unchanged rows may have much older creation generations; never delete
them solely because their valid_from is old.

Accept fail-fast generation pressure as an explicit initial availability tradeoff.
An idle second session can prevent the winner's next advancing save; a crashed
session can leave a conservative durable pin. This is not a transparent
concurrency improvement over P3B and must be documented in the future API.
P3B stores retain their existing behavior.

The proposal does not yet specify a complete pin state machine. P4.1 must make
head capture plus pin registration atomic, move the committing writer's own pin
in the same transaction as publication, preserve acknowledgement recovery, and
bound/check pin bookkeeping. Otherwise a normal writer can block itself or
reclamation can race an opener. The next specification resolves this.

Orphan recovery must be a real, tested source-preserving current-head copy API,
not advice to manually delete pin rows. No clocks/PID guesses/automatic timeout
may release someone else's pin. Exact backup retains operational metadata;
current-head copying explicitly produces a separate unbound store.

### 2. Identity is not solved merely by a weak dictionary

Do not implement the proposed identity registry during P4.1. Before the people
pilot, give each record/object incarnation a defined identity across replacement,
delete/reinsert, nested replacement, and group merge/split. A retained old object
at key K must not be returned as a new replacement at K.

A group ID derived from the lowest owner occurrence is not stable when that
owner is deleted or when groups merge. Define it as derived metadata or introduce
an explicit stable identity; do not silently use it as both.

Prove mutation through a retained child after its parent was collected, including
dirty-owner capture/rebinding, and demonstrate that global bindings/owner maps
do not strongly retain the entire archive. Weak entries must be removed when
objects die, without id-reuse bugs. A bound measured in groups must also report
group sizes and retained bytes. These are required P4.2 design/proof conditions,
not failures of the accepted P3 implementation.

P2C current links remain the alias authority. Any sharing-group acceleration
must be a checked, rebuildable generation-consistent projection, not an
independent competing statement of sharing. Both links and derived group/order/
query metadata must correspond to the same captured generation.

### 3. Preserve the actual stale-state contract

PERSISTENCE_P4.md section 4.3 incorrectly allows local mutation after declaring
the session stale. Accepted P3B `_ensure_mutation_allowed` rejects mutations
when `cold_state != "active"`.

Preserve that guard. An active session may have local edits before it detects
a competing writer. Once conflict is detected, it becomes stale; retain those
edits for explicit materializing detach, but reject further bound mutations,
simulation and save. Generation-safe inspection and stale detach remain possible.
Do not change accepted P3B to match the proposal.

### 4. Integrity, cleanup and cost include metadata

Checksumming only payload bytes does not protect a wrong owner, validity interval,
collection ordinal or generation pin. Frame identity/schema/interval metadata
and validate consistency. Membership row checksums alone cannot detect an omitted
row: specify the ordinary verification boundary and full-scrub completeness.
Never label an index-driven ordinary query a full archive verification.

Bound generation cleanup by indexed expired-version candidates, not an archive
scan on each save. Measure maintenance rows and SQLite query work separately
from returned payload counters. Prove current and retained-previous lookups with
many irrelevant/expired/newer membership rows. O(log H) index navigation is
legitimate; decoding/scanning H unrelated records is not.

## Next task

Implement only [PERSISTENCE_P4_1.md](PERSISTENCE_P4_1.md).
It is the binding storage-foundation implementation contract and supersedes
ambiguous P4 proposal details for that tranche. No World/session lazy integration,
eviction, group registry, automatic conversion or gameplay changes yet.

When P4.1 returns, the review must cover its implementation evidence plus the
small P4.2 identity decision addendum requested by the next assignment. That
batches the next architecture decision with useful implementation work.
