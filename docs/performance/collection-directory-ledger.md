# Collection directory ledger

Base: e1780dceccb4dd3c3debae67bf7257d6efdcf283. CI40108320565 accepted from both digest-checked artifacts,3796 full-suite cases,702 dedicated cases,16 source receipts and14 complete matrices; see run-40108320565/acceptance.json.

Pre-flight: constructor helper supplies one audited-snapshot operation to the directory; readers supply current-generation per-namespace certificates to the unchanged bounded order reader. Shared descriptor values exclude generation.

Ruling: implement complete lazy collection directory source first, separately from save-head namespace inventory and allocator/target inventory — these are distinct authorities in current storage — cost if wrong: extra later composition, not permission to activate incomplete manifests.

Ruling: retain existing isolated branch and inline execution under prior user authorization — no routine approval questions — cost if wrong: the user reviews the saved branch before any main merge.

Task1: initial17 tests RED (missing module). Factoring initially omitted the helper state read, producing47 NameErrors; moved the read into the helper. An empty-store fixture omitted required create arguments; corrected fixture before its successful run. Final focused53 cases GREEN5.34s. AST/YAML/all workflow bash syntax checks passed. Affected suite and measured archive matrix are running; no claims yet.

Ruling: diagnostic varies archive members at fixed two lazy namespaces — this isolates historical payload independence without claiming namespace-fanout timings — cost if wrong: separate namespace-fanout measurements remain necessary before World adoption.

Final review: one fresh Astra high reviewer found two Important defects, no Critical/Minor. TEMP save_head callbacks executed before reader rejection; persistent-view replacements were accepted. Selected absence ignored orphan order/version sources. Review regressions:6 RED,1 already GREEN (bootstrap TEMP shadow was already rejected). Fixed source schemas before all inherited metadata reads and added indexed predecessor absence checks. Combined60 GREEN5.13s before additional coherent/expired and existing-proof rollback coverage. No re-review.

Ruling: absent collection namespaces cannot have any predecessor order/version rows, even expired ones — existing writer never undeclares introduced namespaces; namespace/start indexes avoid scanning future-only histories — cost if wrong: a future namespace-undeclaration feature must revise this contract rather than silently reuse it.

Final: Ruling: World admission/full manifest/inventory/successor directory remain gated — these components still lack complete semantic producers — cost if wrong: adoption waits, never a fabricated performance success.
Final: Ruling: namespace-fanout performance not measured — fixed2 namespace diagnostic establishes archive-size independence only — cost if wrong: no broad namespace-scaling acceptance.
Final: Ruling: larger checks executor-verified rather than duplicated by reviewer — source receipts and XML retained — cost if wrong: less independently repeated measurement.
Final: Ruling: unselected surplus and exhaustive historical orphan audits remain full-audit work — bounded readers only reject selected corruption, constructor current namespace inventory is explicit — cost if wrong: keep full audit before World admission.
Final: Ruling: inherited map/hash mechanisms and arbitrary Python mutation not re-proved — existing focused tests retained; no Python sandbox claim — cost if wrong: inherited defects remain possible.
Final: Ruling: directory lookup delegates payload integrity to downstream checked readers — no payload fetched here — cost if wrong: caller must not admit unchecked payloads.
Final: Ruling: cursor/budget/type/codec/pin/descriptor behaviors were inspected with no extra defect — retain coverage — cost if wrong: untested combinations may require new regressions.

Evidence note: initial RED console showed17 missing-module failures in2.02s, but redirected red.log retained only14 F characters. Preserve it as initial-red-partial.log, not a complete failure transcript. The review RED log is complete. Final focused63 cases GREEN5.54s including coherent/expired orphan sources and existing-proof rollback. Final source AST/YAML/bash syntax checks passed.

Final: fixed both Important findings — callback and orphan regressions RED→GREEN, final combined63 passed5.54s and affected811 passed79.70s; full candidate suite3827 collected6.25s, execution delegated to new CI. Final matrix9.62/7.04/8.67ms,0payload reads,3namespace-state probes,VM17199 at1k/10k/100k archive members. Fixed2 lazy namespaces; no namespace-fanout or World acceptance. Runtimecadce590652033a9d14f1bc5f3d25c9473b45b73.

Task1 implementation, review/fix, focused/affected/scaling verification complete. Prior authorization selects checkpoint and candidate CI, with no main merge or endurance. Full-suite acceptance remains pending.
