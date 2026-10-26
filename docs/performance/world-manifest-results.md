# Audited complete World manifest production

This inactive producer constructs a real seven-root generation manifest from one
explicitly audited complete World snapshot. It publishes successor manifests and
recovers exact attempts through the existing inventory/component writer. It does
not enable ordinary World open/save or meet interactive save acceptance.

## Established authority

| Slot | Authority |
| --- | --- |
| Versions | Existing exact lazy-version content root |
| Ordinary records | Existing exact ordinary content root |
| Topology | Complete owner/group and physical-child scopes, structural backing inventory, actual owner projections |
| Queries | Declared lazy query projections and reverse scopes; ordinary query rows fail closed |
| Orders | Complete lazy directory, ordinary ordinal envelopes, history descriptors and query order |
| Events | Existing exact segment content root plus full prefix/suffix/descriptor audit |
| Inventory | Existing exact namespace/count/head/allocator authority |

Construction compares actual content to accepted components, reconstructs all six
scoped physical roots and the lazy directory, scrubs catalog/sequence/member types,
checks every registered owner placement and backing/child parent, and rejects wrong
family/field kinds. Effective cold layout cardinalities must match actual head counts;
packed actions and compact Event-IDs also match logical payload/descriptor sizes.
Native aliases bind complete value fingerprints during audit; topology excludes scalar
payload bytes while content roots retain them. Structural cardinality and order remain bound.

`copy_world_with_proofs` reuses the old checked-reader/explicit-copy engine, creates a
new store identity, rebases storage revisions/checksums and retirement query/membership
ordinals to generation zero, then proves pre/post-rebase canonical World digest equality.
It preserves the source file and refuses to overwrite an existing/racing destination.
Only a genuine new generation zero can lack predecessor authority. Positive-generation
manifests bind the exact parent and existing writer/token/receipt.

Proof files select format7 and reject default/unproved writers. Ordinary native World
open explicitly rejects these files pending integration; format6 readers remain intact.
There is no in-place migration, automatic repair, second publisher or canonical-object registry.

## Publication and cost boundary

A changed World publication runs the explicit full audit in the existing save transaction.
Its cost grows with history. A metadata-only checkpoint reuses the previous five semantic
facts only when all their complete component inputs remain unchanged; it publishes the
new manifest atomically without history-body reads. No-op saves remain not committed.
Before-head, before-commit and after-commit interruptions, reopen recovery, retained
manifests and wrong-token behavior are covered by the focused tests.

Full copy/audit construction, its inherited full capture, and long-term node storage
are not bounded-memory or latency claims. Partial-retirement jobs, mixed inline/backed
identity groups, cyclic backing graphs and inline World key/set reference routes fail
closed. Selected-closure mutable-cycle support in its separate raw reader is unchanged.

## Evidence and next boundary

- Baseline run40275423651: authenticated 4211 full-suite tests,1115 proof tests and26
  complete matrices; exact archive/source evidence in run-40275423651/acceptance.json.
- One fresh whole-package Astra/high review found four Important issues; one fix pass
  and explicit rulings are in world-manifest/review.md.
- Final local suite source/results and the 1k/10k/100k checkpoint matrix are retained in
  world-manifest/verification.json and world-manifest/scaling/. Construction timing is
  reported separately from checkpoint timing. The size unit is retained history values,
  not mature-world records or years. Hosted full-suite acceptance remains pending.

Next: integrate affected-owner semantic transitions and proof authority with the existing
frozen participant protocol and canonical native World admission, then validate upgrades,
recovery, first interactions and real point-edit saves before matched mature performance
acceptance. No main merge, endurance run or ordinary format7 activation occurs here.

## Corrected-source local measurements

All1151 proof tests (including35 World cases) and125 related runtime/copy tests passed,
with0 failures/errors/skips. Runtime tree: `18bccc1a775299e6770c051437e8be7035b9173d`.
The hosted full simulation suite is pending;4247 tests is an expectation, not a result.

| Retained values | Construction seconds | Checkpoint ms | Python peak bytes | SQLite VM steps | History bodies |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1000 | 2.272 | 300.306 | 207822 | 175387 | 0 |
| 10000 | 5.703 | 363.375 | 216398 | 175600 | 0 |
| 100000 | 53.093 | 295.881 | 223739 | 175520 | 0 |

VM work uses a separate interval-one guarded checkpoint; tracemalloc is active only
for the timed checkpoint. Construction includes fixture creation and explicit genesis
copy/audit. Each checkpoint reads one session commit-descriptor body. All preserve
semantic roots without reaudit. These are local checkpoint observations, not mature
point-edit, interactive-save or first-interaction measurements.
