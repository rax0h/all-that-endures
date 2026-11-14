# Independent whole-package review — family publication scope

Review base: `9fe78c0`. Reviewed commit: `ba0cc454d74fb6b443a4beb8fde94082d2357a0c`.
Also reviewed the working-tree workflow addition that appends the new family test module to the existing publication-read-scope command, preserving its 2-minute timeout and existing artifact paths.

## Findings

- Critical: none.
- Important: none.
- Minor: none.

No actionable finding remains from this independent review. This is a source-correctness review with the bounded evidence below, not a performance promotion or hosted acceptance verdict.

## Scope and evidence

Read AGENTS.md, the family-publication-scope design/plan/ledger, the complete committed Python diff, the two participants and surrounding acknowledgement path, the existing validation scope, checked snapshot/pin/head/row implementations, native proof authority and source/metadata guards, and relevant existing scope, dependency, participant-abort and native recovery tests. All reads during raw timing were static; runtime qualification and probes began only after the coordinator explicitly reported benchmarks finished.

1. **Custody and authority.** The two production changes only replace the existing `read_snapshot` contexts with `checked_read_operation`. Family `_check` and dependency `_check_plan` still run before scope entry. The exact frozen delta identity, publisher token, store identity, generation and live registered pin remain checked. Every version, ordinary row, identity occurrence and backing-dependency value remains visited. No independent certificate, gameplay callback, public iterator yield, acceptance removal or alternate commit authority is introduced.
2. **Bytes and lifetime.** Both new callers use the established 256 KiB cap. Neither owns a smaller configurable catalog budget. Cache entries remain immutable and capped at 256 entries; scope cleanup invalidates and empties the cache in `finally`. The new callers do not lengthen scope lifetime into cold confirmation or runtime journal acknowledgement. The coordinator's existing smaller catalog-derived scope remains unchanged.
3. **Borrowed reads, writes and drift.** The existing eligibility rule excludes borrowed transactions/snapshots; native custody additionally rejects busy authority, active write guards, callback configurations and changed transaction/schema generations. During native saves, the existing busy/write-guard path continues its full source epoch checks. Generic scope reuse checks codec/connection identity, transaction existence and epoch including `total_changes`; rolled-back writes still invalidate reuse. Independent probes confirmed both new callers' borrowed-read ineligibility, codec-object replacement invalidation, and write/lease mutation plus rollback invalidation.
4. **Exceptions/corruption.** Family proof flags are cleared before validation, then set only after the scope completes. Pool validation does not clear its prepared state or advance persisted metadata. Independent injected exceptions and corruption after a prior successful validation both rejected without leaking a scope or accepting state. Existing mandatory-row missing/corrupt tests continue to target the unchanged dependency row checks. Native row-root proofs and local payload/row checksums are not removed.
5. **Callbacks and codec.** No gameplay callback was added inside either closed operation. Family decoding remains before its scope; dependency decoding remains inside its previous read boundary. Existing native source callback denial, publisher write guard, closed-codec settlement and epoch checks remain in place. Generic same-object method monkeypatch resistance is not a new guarantee of this change; the existing scope checks codec object identity. Review found no new callback crossing or native authority escape.
6. **Recovery.** Central order remains participant validation, nested/adoption/minimum successor checks, central cold successor capture, cold confirmation, then runtime acceptance. `DependencySaveParticipant` still validates the pool before acceptance and `BackingDependencyPool.accept_delta` still revalidates it; no second validation was removed. Already accepted dependency participants retain their existing retry behavior. The native partial-acknowledgement recovery test still exercises revalidation of the original committed manifest and exact reopen. No recovery logic changed.
7. **New tests.** The native case changes and reopens all 32 people with exact wealth values and asserts per-family head-check bounds and scope cleanup. The generic case creates actual 32 dependency rows, checks the head bound, accepts the original prepared delta and verifies all 32 token rosters. The historical first dependency fixture's vacuous passing result is explicitly preserved and corrected in the ledger. The second generic case itself does not reopen; independent two-row probes below additionally verified generic dependency persistence across reopen.
8. **Workflow.** The only reviewed workflow modification adds `simulation/tests/test_stage_0_6_family_publication_scope.py` to the existing bounded publication scope pytest invocation. Existing timeout, JUnit output and log artifact names are retained. Runtime adequacy of that timeout requires the coordinator's hosted run; this review does not infer it from local timings.

## Independent bounded probes

Executed `check_runtime.py` from the existing rank-up-publication independent-review directory with the qualified `/workspace/scratch/d88f8db353e8/ate-qualified-313/bin/python` before any acceptance probe. Its full fingerprint comparison passed, including executable/library hashes, Python 3.13.5/GCC 14.2.0/SQLite 3.46.1, SQLite source ID and compile options. Output: `runtime.json`.

`probe.py` ran with `PYTHONPATH=.:simulation` and an external 45-second timeout. Eighteen cases passed (nine modes for each of a two-row family and a two-row dependency publication): owned operation and exact reopen, borrowed read, injected exception, post-validation corruption, write plus rollback, codec object replacement, lease deletion plus rollback, wrong frozen delta object, wrong pin. Owned probes also populated the scope and checked entry/byte bounds; every completed operation checked emptied/invalidated scope and closed transaction. Output: `probe-result.json`. The probes completed in approximately 1.4 seconds; this is not comparative performance evidence.

Probe-development failure: the first attempt omitted the `people` namespace from a generic family fixture's head inventory and correctly failed at commit setup before tested validation. It was corrected to declare the retained namespace; no production change was made. This is a probe-fixture error, not a product finding.

## Source SHA256 fence

| File | SHA256 |
| --- | --- |
| simulation/ate_sim/persistence_lazy_participants.py | fc4a475dacb1d76cdbd40d569e62c92cb4ba0dd77883b726675235edde549594 |
| simulation/ate_sim/persistence_history_dependencies.py | 4a1176a04037870edfcbfe51ee0478b3a61d7d04bb9d06e95a5acb6a806a8aa8 |
| simulation/ate_sim/persistence_validation_scope.py | 998a91ebed682a88fbef38cab3e7842983412e11221185cd5dfebf1a49fa6a3f |
| simulation/tests/test_stage_0_6_family_publication_scope.py | 7a87c5974137a32eea272e75771eed80f2268a5d9b20cbb307292a78bc9f7f52 |
| .github/workflows/stage-0-5-proof-map-validation.yml (working tree) | 569471bdcf29c43c63749dc2388cbfe520065cd231ec2a2fde0f97ad410d6f43 |

The three production/support source hashes and new test hash matched before and after probes. No checkout, index or branch modification was performed by this reviewer. All reviewer-written files are confined to `/workspace/scratch/c88cf88fdaa2/family-review`.

## Declined-to-judge items and limits

- **Whole-save performance promotion and benchmark work attribution:** the coordinator owns the separately pinned raw A-B/B-A trials and attribution. No benchmark was rerun or interpreted as an independent performance verdict here.
- **Broad selected suites and hosted proof/full gate:** owned by the coordinator. Existing native callback/codec/corruption and partial-acknowledgement suites were inspected statically, not rerun by this reviewer. Independent execution was deliberately limited to tiny generic probes to avoid duplicating expensive work.
- **Mature-scale behavior, endurance, merge and default activation:** outside this authorized review and not established by these probes.
- **Arbitrary adversarial replacement of implementation methods on generic codec/participant instances:** not established as a supported threat model by the two-context change. This review checks the existing documented ownership/identity/transaction contract; it does not claim that Python object monkeypatching is a security isolation boundary.

No performance, mature, main/default activation, endurance or merge approval is implied.
