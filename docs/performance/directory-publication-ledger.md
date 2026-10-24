# Directory publication ledger

Base 41467a4. Work continues inline on the existing isolated sol/durable-proof-map checkout under prior authorization. No main merge, endurance or World activation.

Plan: authenticate the parent directory; derive only explicitly bounded touched namespace certificates (including checked absence); stage their successor descriptors/root inside the existing collection/content transaction; bind the directory row to exact parent/writer/token; recover against that receipt. Unchanged namespace descriptors are reused without copying per-namespace rows. Tests cover stale/forged sources, namespace introduction, deletion, unchanged namespaces across multiple saves, rollback and lost acknowledgement. Full World topology and manifests remain separate gates.

Pre-flight: per-namespace publication currently requires a generation row for every supplied parent. A complete directory must instead supply that authority for unchanged namespaces carried across generations. Ruling: directory-backed requests authenticate selected parent certificates against the accepted directory and physical state rather than requiring copied per-namespace generation rows — copying all namespaces would reintroduce global work — cost if wrong: this inactive path remains gated from World until complete manifest review.

Implementation: nine feature tests RED (missing module), then nine GREEN. Initial write guard incorrectly called the public reader's owned-transaction gate from inside the writer; factored its checked namespace lookup for reuse under the existing writer transaction. Expanded 20 tests GREEN1.88s. Reopen fixture initially omitted mandatory open arguments; wrong-token fixture initially expected a conflict result where the existing resolver raises StoreConflictError. Both test assumptions corrected; production resolver unchanged. First affected run began before fixture corrections and reported 752 pass/1 fixture failure; final source rerun pending.

Prior CI40126096856 accepted: digest-checked ZIPs,3829 full-suite cases,733 dedicated cases, source/runtime/driver/fixture hashes and complete archive matrices. Acceptance receipt and source/XML/summary evidence retained under run-40126096856.

Final review: fresh Astra high reviewer found one Important issue (empty directory bootstrap omitted per-collection publication schema) and one documentation Minor. Two empty-directory regression cases RED. Fix explicitly creates/checks the collection generation table during audited bootstrap even with zero namespaces. Documentation refresh was already part of this handoff; NEXT_INTEGRATION and module doc now describe the implemented inactive publisher. No deferred minors. No re-review.

Final: Ruling: full-suite compatibility, final scaling and CI completion are verification gates, not inferred from focused tests — final candidate CI must supply them — cost if wrong: candidate stays unaccepted until archived evidence is checked.
Final: Ruling: global namespace/allocator inventory, complete topology, World activation, manifest admission and node collection remain outside this package and gated — no complete-format or World speed claim — cost if wrong: subsequent integration work remains required.

The final reviewer deliberately did not duplicate full-suite or scaling execution. Source receipts and logs retain executor evidence. Archive-size diagnostic fixes two lazy namespaces and does not establish namespace-fanout bounds.

Final: fixed empty directory bootstrap — test_first_save_from_completely_empty_directory metadata-only/first-insert cases RED→GREEN; combined85 passed8.53s; final affected755 passed65.09s. AST/YAML/all workflow shell syntax and diff checks passed. Pre-fix runtime08b58f0 full archive matrix82.68/73.44/83.90ms at1k/10k/100k, zero unrelated version bodies; final candidate runtime differs only in audited constructor initialization, so final-source CI scaling remains required. Local all-proof suite passed; full simulation suite is assigned to candidate CI rather than duplicated locally. No local full-suite success claim.

Task1 implementation/review/fix/local verification complete; next checkpoint is published candidate CI, not full World admission. The reviewed directory-authority choice avoids copying untouched namespace rows but remains subject to complete-manifest review. No main merge or endurance.
