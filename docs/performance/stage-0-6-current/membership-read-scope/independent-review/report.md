# Independent whole-package membership read-scope review

Result: no actionable findings, including Minors, in the reviewed engine/test/workflow package. No finding remains open from this review. This is a bounded correctness review, not performance-retention or promotion approval.

Reviewed checkout: `/workspace/scratch/d88f8db353e8/ate`. Base `fb41c31ade9d974bcc63aa4b0acd9effdaa4797f`; candidate HEAD `e32f95096b57f0dc821b6288370e65e29f7a7f61`, declared runtime tree `fd20cf1784a331de07f4979db71dda0f3d301771`. Also reviewed the subsequent unstaged workflow-only append described below. No checkout, index, HEAD, production file or repository test was changed by this reviewer. All reviewer output is confined to this directory.

## Scope and evidence

Read AGENTS.md, the membership-read-scope design and plan, its progress ledger, complete production/test diff, surrounding catalog/source/snapshot/custody code, existing validation-scope/read-view/descriptor/native-roster tests, and the supplied raw-pair/affected-test launcher sources. `git diff BASE --check` passed. The only production change imports and selects existing `checked_read_operation` in `IdentityCatalog.read_identity_membership`, with `min(256*1024, self.byte_limit//6)`. The rest of the method is unchanged. The four new repository tests cover generic present/absent operational work, actual native head-check work, small configured cache budget, and corruption following an earlier successful lookup.

The workflow addition appends only `simulation/tests/test_stage_0_6_membership_read_scope.py` to the existing publication/family read-scope command. It retains the 2-minute timeout, 10-second TERM cleanup, XML path, log path, and existing pipeline behavior. No additional hosted cycle was requested by this reviewer.

Raw A-B/B-A trials were running during the static review. No Python, tests, fixtures or probes ran until the parent explicitly reported their completion. Then the existing `rank-up-publication/independent-review/check_runtime.py` verified the complete qualified runtime fingerprint against `fixture-construction/qualified-local-runtime.json`; exit 0, saved as `runtime-fingerprint.json`. Probe interpreter was `/workspace/scratch/d88f8db353e8/ate-qualified-313/bin/python`, with `PYTHONPATH=.:simulation`.

Independent probe command, bounded to 120 seconds:

```sh
PYTHONPATH=.:simulation timeout --signal=TERM --kill-after=5s 120s /workspace/scratch/d88f8db353e8/ate-qualified-313/bin/python -m pytest -q /workspace/scratch/c88cf88fdaa2/membership-review/test_independent_membership.py --basetemp=/workspace/scratch/c88cf88fdaa2/membership-review/tmp --junitxml=/workspace/scratch/c88cf88fdaa2/membership-review/probes.xml
```

Observed: **22 passed in 3.02s**, exit 0; see `probes.log` and `probes.xml`. The native probes share one size=4 ranked fixture and copy it per case. No generated-year constructor or broad suite was run. These runs overlapped parent validation/instrumented attribution and make no timing claims.

## Checked behavior

| Area | Review and independent evidence |
| --- | --- |
| Exact membership | All original descriptor, header, node commitment/locator, path-hash collision and exact forward-occurrence agreement checks remain. Direct generic and native point membership succeeds. Forced generic hash collision raises. Deleting forward authority after successful lookup raises on both paths. |
| Exact absence | Generic genuinely new owner returns None; native absent path and genuinely new owner return None. Missing generic source, witness, or both while placements survive raises. Native source+witness+placement removal still raises even with the coarse authority epoch deliberately refreshed, proving accepted native source commitment remains effective. |
| Scope custody | Generic borrowed snapshot/read-transaction probes observe non-reusable scopes. Native borrowed and previously registered/unregistered callback contexts have no native custody. Existing native checks retain transaction/schema generation, pin, authority/pair/epoch/components identity, connection/codec identity, callback/factory state and write-guard checks. |
| Write, rollback and lease drift | Generic write inside an outer checked operation rejects damaged forward authority; rollback restores data but does not reactivate the invalidated scope. Released generic pins reject. Native write-and-rollback and deleted lease after a prior successful lookup reject. |
| Codec and callback boundaries | Native codec replacement after successful lookup rejects. Callback history disables native custody. The operation introduces no gameplay callback, iterator yield or asynchronous boundary; unchanged callback/source guards and descriptor-fact fences remain in use. |
| Cleanup | Injected node-read exceptions clean both generic and native scopes/transactions; a later valid lookup succeeds. Every probe asserts no leaked scope or transaction after its operation. Borrowed transactions remain open until the owning outer context closes them. |
| Budget | New repository test measures configured 128-byte catalog's scope limit and retained bytes. Independent 1-byte catalog probe observes zero scope cache budget and zero retained bytes while exact membership still succeeds. Existing cache admission/eviction remains bounded by both weight and 256 entries. No new catalog-wide enumeration or owner cache change. |
| Descriptor facts | Newly eligible standalone native membership reads can use the already implemented descriptor fact fence. Fresh entry validation and native custody precede fact reuse; owner/header/node/source/forward checks remain separate. Existing descriptor/read-view suites cover wider method/registry/schema and equal-coarse-epoch drift. |

The source owner check intentionally proves metadata agreement; this patch does not newly promise decoding and authenticating the complete owner body through membership lookup. Native accepted catalog-source proofs remain separate. Existing generic new-owner absence semantics are preserved, including their reliance on surviving source, witness or placement evidence; this patch does not introduce a new independently sealed inventory for generic stores.

## Consolidated closure register

| Origin | Finding | Action/evidence | Status |
| --- | --- | --- | --- |
| Independent whole-package review | No actionable correctness, integration or test defect found | Static review and 22 direct-entry probes above | Closed; zero open findings |

## Explicitly declined judgments

- No assertion of credible end-to-end speedup, save-phase causality, benchmark variance, benefit retention, or performance promotion. Parent reported mixed warm/save raw observations and owns their resolution; instrumented/probe durations are not raw performance evidence.
- No assertion that the parent's still-running 17-file tests or hosted proof/full gate have passed. They were not duplicated by this reviewer.
- No claim of whole-operation RSS bounded by the catalog byte limit; that limit governs existing retained-cache/spool contracts, and this change adds a bounded validation cache. No large/adversarial payload memory experiment or expensive history scaling run was performed.
- No exhaustive proof against arbitrary Python monkeypatching, unsupported cross-thread use, every SQLite callback API combination, or every historical store shape. Existing general scope/custody suites supply broader coverage; tiny probes target this entrypoint's changed composition.
- No mature/default/main/endurance/merge authority or recommendation is granted.

## SHA256 fences

Production/test/workflow source hashes were reread after the probes and matched the initial static-review hashes. Paths below are relative to the reviewed checkout unless specified otherwise.

```text
06e2f99a2398b40b78ad31e562ebccdb409e8330d15bd484e48bc7be9869ea4a  simulation/ate_sim/persistence_lazy_identity_catalog.py
998a91ebed682a88fbef38cab3e7842983412e11221185cd5dfebf1a49fa6a3f  simulation/ate_sim/persistence_validation_scope.py
b980a2e341bb1bae635a6889a9d5f754862a914717527539c624a589bfbcd405  simulation/ate_sim/persistence_lazy_store.py
5ceab732806f3df99d6ae28f95ecd15b900594801323eb4484d3c8075cfe9eab  simulation/ate_sim/persistence_proof_native_sources.py
9c194d2fb94bebffd49622795ed646eae7cf5391f0546b822a91440c5afe13c8  simulation/ate_sim/persistence_proof_world_session.py
f8c1208f7b1a41e17433f1990dc04f201d67b2a9b30ab3a0474c24362c945b88  simulation/ate_sim/persistence_sqlite_guard.py
60e82c1989f599191e090cf9b0fd3d9381f59a81eead1464729f53aff6a15814  simulation/tests/test_stage_0_6_membership_read_scope.py
0af11a1e54a089b0e81c4c1c81ef8ab1270476bd0c7bea7058c98d2f901ae890  .github/workflows/stage-0-5-proof-map-validation.yml
6f3d3f3638c31b9faf3aa4100390cb454783876348cfc28ef7d9d00dbf254515  docs/superpowers/specs/2026-11-14-membership-read-scope-design.md
915aa1be3c70937425b4459e914418594557c6a1305bab83b07835c9c1928e7d  docs/superpowers/plans/2026-11-14-membership-read-scope.md
```

Reviewer evidence hashes (relative to this report directory):

```text
3f241e6e39731ed3cdbcf9bbbc6ba0ad78f1e25b1ebce4c87add52fa582a962e  test_independent_membership.py
2e15ca3b8969a843c3daf32390bbea6ff1695e1da36e764f11edd7e264729c5a  runtime-fingerprint.json
448a877c56c60f891e922dfc6e0cc2368b97fbe3210b829e03ee1185f06f81cd  probes.log
fd2339fd4b56faad8bbc05fc3a920181c255b2c8a54b8113bd8f2e6cd3e33fcc  probes.xml
```
