# SDD ledger — plan: docs/superpowers/plans/2026-10-26-ate-durable-reference-proofs.md

Baseline cfdb974, hosted run40254037395 accepted:4170 simulation/1074 proof tests,25 complete 1k/10k/100k matrices, artifact/source hashes and zero XML failures/errors checked.

Pre-flight: Task1 descriptors consume the raw closure result and local sources; Task2 consumes those descriptors and successor content/scope/record/inventory authorities after the existing inventory stage; Task3 consumes both public APIs. No conflicting root encodings or publisher ownership.

Ruling: fixed bounded selected-root inventory for this milestone — it persists the exact selected-closure semantics already validated, while global World inventory remains in the following production milestone — claiming a complete World graph here would be unsound.
Ruling: scope roots plus exact positive/absence content paths are dependencies — source-key dirt alone misses newly added children/incoming owners — omitting a dependency would incorrectly retain stale semantic facts.
Ruling: changed closures are rechecked under existing bounded full-closure budgets; unchanged closures use only authenticated dependency metadata — per-node semantic production is later optimization if measurements require it — large affected closures still require a separately budgeted path.

Task1: complete —17 new tests initially failed for missing API; initial descriptor implementation plus existing closure tests51/51 passed. Component-binding regression then demonstrated four false accepts on altered persisted component roots; read now binds all four and metadata context. No graph bodies are read by fact lookup.
Task2: complete —12 publication tests failed for missing writer module before implementation. Focused reference/closure/inventory/content tests175/175 passed. Retained-pin test initially tried advancing while an older pin was held; fixed fixture to release it after verifying old semantics, preserving the existing two-snapshot pressure contract. Shared-owner fixture requires its real catalog owner revision delta even for identical replacement bytes; old source revision dependencies must be replaced while semantic digest can remain identical.

Task3: pre-review verification1115/1115 proof tests116.26s,128/128 related runtime tests27.94s;197 focused passed. Initial runtime command used three nonexistent filenames and ran zero cases; corrected existing filenames then128 passed, with four existing record_property/xunit2 warnings. Scaling d444dd1:1k/10k/100k point edits188.51/211.99/226.14ms; zero graph/unselected bodies, two changed-body reads, no graph rebuild, unchanged semantic root; metadata-only successors zero payload checks and228563/229103/229616 VM steps. Fresh Astra review dispatched on cfdb974..d444dd1.

Continuation: original reviewer interrupted by usage limit, then resumed same read-only review. Runtime/test/driver hashes match pre-interruption receipts. Scratch logs and installed dependencies were reset; pytest/pyyaml restored and40 reference tests passed afresh in8.77s. Remote branch remains accepted cfdb974.

Final review: same fresh Astra/high review completed after usage interruption; Critical0/Important0/Minor0. Independent actual-writer probes reject changed type witness, retirement header, owner-radix node and link body, retaining generation1. Reviewer observed37 dependencies in default graph; no independent pytest rerun claimed. No fix pass needed.
Final: Ruling: complete World inventory/unindexed owners/native admission/migration/fencing/full manifest — retain explicit selected-closure scope and deferred activation — premature activation could admit incomplete World state.
Final: Ruling: frozen certification cycles — preserve inherited fail-closed behavior pending separate validated path — some legitimate stores remain unsupported.
Final: Ruling: unfetched corruption/coherent authority replacement — retain fetched-byte verification, audits/scrubs and external checkpoint boundary — retained semantic facts cannot stand in for physical verification.
Final: Ruling: runtime policy/code upgrades — certificates apply to current checked implementation pending versioned activation — cross-policy reuse could carry stale semantics.
Final: Ruling: large graphs/fanout above budgets — reject pending separately budgeted path — legitimate large inputs remain unsupported.
Final: Ruling: mature World latency — accept component work evidence only and retain matched World performance gate — component timing is not user-visible speed.
Final: Ruling: ancestor artifact provenance — accept executor's hashed hosted acceptance, not a second review authentication — baseline validity rests on executor receipt.
Final: minor (deferred): none in this package.
Task3: complete — review clean, no implementation changes after verified d444dd1 source. Full simulation suite delegated to the next hosted candidate per explicit user no-long-poll workflow. Publication/CI launch receipt is the remote candidate itself.
