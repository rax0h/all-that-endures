# Independent whole-package review — rank ecology operand lifetime

Reviewed 2026-11-13 against local base 69347b818340dfd85bf44dbdf87fb72a098822b2. Read-only production review; independent probes live beside this report. No production edits or full/mature suite runs.

Verdict: no actionable Critical, Important, or Minor findings in the reviewed package. Final acceptance remains conditional on the owner's pending bounded battery, pinned raw comparison, and bundled hosted gate; this report does not assert those outcomes.

Reviewed fingerprints (SHA256):

- rank_ecology.py: d888da6bd73e6496b0037843cf2966e01eeb21855eda3d70fb215425322ba0cd
- test_stage_0_6_rank_ecology_lifetime.py: c99c5ba60bc19cf1564691d393fe22888f59b819ce735216ca61d1fa3f017ca2
- run_pair.py: a7da79a67260a4bc5f62708e7213f54edaf92c700d9f8d259fe78452a01b918e

## Evidence and reasoning

The sole production change retains the already-existing indexed ability list before PracticeBatch and uses it for the ceiling scan. It does not alter indices, candidate order, random draws, mutation calls, or mastery invocation. PracticeBatch still computes and updates per-person rank counts, including mid-pass body transitions. Partial paths still use rank zero and their original ceiling calculation; empty paths still skip before list construction. Ceiling paths now retain their current operands until reassignment/function return. No session/global cache is introduced. A prior iteration's candidates/local ability can remain alive into the next iteration as before; the contract must not be read as a strict global twenty-live-body bound. Each new batch is created with the new person's ID and path, so previous-person values do not supply its rank/counts or candidates.

The new tests cover empty, partial, full, ceiling, milestone, body-transition and mastery cases, comparing eager/native world digest, RNG stream state, events and save/reopen identity. The mastery fixture correction supplies LocalState for the real training path; its retained targeted log is green. The transition case explicitly asserts rank advancement and further Bronze progress. Shared skill provenance identity is checked before and after save. Tests use the same current gameplay implementation for eager/native comparison; this is storage parity, not an independent baseline gameplay oracle. The tiny source diff supports the unchanged-gameplay conclusion separately.

Independent qualified313 probes (each invocation capped at60s):

- Initial probe.log: ceiling, injected exception after list/batch construction, and held ability/response-model across save all passed. Each recorded twenty observed ability identities and zero live bodies after return/unwinding or save. One normal-path probe failed due solely to reviewer harness using nonexistent `_dirty` rather than `_dirty_record`; raw failure retained.
- Corrected probe-followup.log: 3passed in13.36s. Normal return observed twenty abilities, four ordinarily dirty bodies, zero clean bodies retained. Actual mutation of persisted header-row payloads was rejected with StoreError. Explicit release of the owned pin was rejected with StoreError on annual access.
- Old-lease probe held the canonical ability and its response model over an unrelated save, asserted identity before and after annual practice, saved again, dropped caller aliases, and observed zero retained bodies. The runtime's existing load_record reuse calls backing._ensure; the patch does not bypass source or lease checks.

Exception release means after the caught exception and its traceback are discarded. Python callers retaining a traceback can retain frame locals; this existing language behavior is not a persistent cache leak. Dirty bodies intentionally remain strongly held until publication.

Inspected post-rank-profile source/runtime receipts and instrumented report, new design/plan, affected paths and bounded runner, workflow addition, and thin raw pair adapter. Profile timing is explicitly instrumented diagnostic data. The adapter resolves the repository correctly and changes only SOURCES/EXPECTED_TREES before invoking the unchanged reviewed runner. That runner checks input SHA, committed engine tree, dirty tracked engine changes, full importable Python inventory and blob identity, uses fresh disposable copies and A-B/B-A order with bounded process cleanup. The final pair-config and raw results were not yet present and are not accepted by this review. The workflow adds the new test module to the existing bounded bundle.

## Declined to judge / limits

- No latency improvement, raw trial outcome, or mature/generated-world scaling claim: raw trials had not started; profile timings are not raw evidence.
- No final hosted pass or completed related-battery claim: those remain owner-run gates.
- No exhaustive concurrent adversarial corruption during the synchronous pass; concrete cold corrupted source and released-pin boundaries reject. No new persistence authority mechanism was added.
- Next-person isolation is established by source inspection here, not a separate two-person native fixture probe.
- No unrelated persistence architecture or historical rank-up acceptance re-review. Prior rank-up evidence changes are separate documentation, per assigned scope.

All independent CPU probes are idle. Findings closure register: Critical0; Important0; Minor0; reviewer harness typo corrected and rerun with retained failure evidence.
