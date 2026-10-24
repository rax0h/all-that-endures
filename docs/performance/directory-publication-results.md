# Inactive atomic directory publication

Prior CI40126096856 accepted from digest-checked ZIPs:3829 full cases,733 dedicated cases, source/runtime and driver/fixture hashes, complete1k/10k/100k matrices. Evidence under run-40126096856.

The inactive commit_directory wrapper authenticates the accepted complete lazy namespace directory and at most128 named touched namespaces (including checked absence), then publishes successor collection descriptors and the directory root through the existing unified writer transaction. No copying of untouched namespace rows. Old generation-independent descriptor bodies remain shared. Recovery checks exact parent/writer/token/generation against the same existing save receipt. Metadata-only and no-op saves, first creation from an empty directory, absent deletion, retained reads and reopen are covered.

Fresh independent review: one Important empty-bootstrap defect reproduced by two RED regressions, fixed by explicitly initializing the collection publication schema during audited bootstrap. Final combined85 tests passed8.53s. Planned documentation refresh resolves the stale-gate note. No deferred minors. Final affected755 cases passed65.09s. AST/YAML/workflow shell syntax and diff checks passed. Full simulation suite and final-source measurements remain pending candidate CI.

The complete pre-fix diagnostic measured82.68/73.44/83.90ms at1k/10k/100k archive members, zero unrelated version-body reads and60299/60399/61099 VM-step upper bounds. Exact diagnostic values are retained in pre-fix-scaling/. It fixes two lazy namespaces and varies archive members. It does not establish namespace-count scaling or World latency. Final CI must measure the final source. Full construction/audit is outside operation timers.

Next: separate save-head namespace inventory, allocator/target existence and complete topology producers; full generation manifest and verified-copy/fencing; World save/open consumption and matched mature-world timings. Complete integrity admission and exact continuation remain mandatory. No World format activation, main merge, endurance or node garbage collection.

Decisions and review limitations are recorded in directory-publication-ledger.md.
