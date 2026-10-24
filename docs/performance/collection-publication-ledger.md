# Collection publication ledger

Baseline collection source20focused/768affected passed; CI40106928986 still in progress at start. No acceptance claim. Existing branch isolated sol/durable-proof-map.

Ruling: require collection authority for every touched lazy namespace, max128 accepted pairs — bound operation-local metadata without scanning unrelated owners — missing global inventory remains gated; cost if ignored is incomplete order publication.

Task1:7missing-module RED cases →27combined collection/publication GREEN4.08s. Added expected-comparison and nested-row cases:1RED expected-hook execution, nested-row test already green. Check expected type before comparison; defensively normalize recursive parser errors.29combined GREEN4.43s. Actual writer checks old order against content presence and order root, predicts existing ordinal allocation semantics, verifies final rows/counters and publishes all roots before cleanup. Value-only roots share unchanged; rollback/exact lost-ack covered.

One fresh review: no findings; independent96tests26.95s and all corruption/allocation probes passed. Parent expanded focused32GREEN19.11s, initial affected777GREEN170.04s; no runtime change from measured/reviewed9da877. All3size/source/driver/fixture receipts verified; actual saves97.23/129.07/101.40ms, zero unrelated version bodies. All reviewer scope rulings/costs recorded in review report. Full candidate CI remains pending; priorCI40106928986 not accepted this turn.

Exact CI [40108320565](https://github.com/rax0h/all-that-endures/actions/runs/40108320565), candidatedfc6cbd1d935bdf1fbbc42843bc7ffc6c864fc6a, tree92b7a87d0386f313a5d37ecbdd096b0448414954, runtimeb5da37e90bf5737b9d683f2da2aa6b65d3fbe4ba; pending at launch behind existing validation. Full candidate/all14diagnostics acceptance pending; priorCI40106928986 not accepted here. No main merge/endurance/long polling.
