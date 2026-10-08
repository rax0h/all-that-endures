# Household implementation brief

Read `../STAGE_0_5_CONTINUOUS_REPAIR_SPEC.md`. Work only in household-work. No child agents, GitHub writes, full suite/endurance, or gameplay arithmetic changes. Design/plan then red tests, complete implementation, focused gates, local commits and `STAGE_0_5_HOUSEHOLD_HISTORY_VALIDATION.md`.

Implement lazy outer household records, indexed alive/settlement/settlement_alive, requested-only binding and touched-only sidecars. Introduce checked occurrence-position memberships (`member_by_backing`, `(backing_key,member_id)`, occurrenceoffset) and `query_memberships` shared API from spec. Living selector probes actual current living IDs against the authoritative sequence, preserving repeats/order and cross placements, never inferring membership solely from Person.household.

Implement sparse 128-slot pages with tombstones and checked vacancy rank/select nodes so first-occurrence remove, integer indexing/deletion and append avoid repaging history. Page cache4, rankcache64. Explicit full transformations may repack. Missing nonzero child fails closed. Preserve dense legacy and stable backing/incarnation. Page Settlement.households using the same specialized ordered-ID mechanism. Owner replacement normalized before return; use persisted reverse occurrences to retire backing only when truly unowned.

Route civilization household living/split, mortality.kill, engine._die, resource heir selection and engine_demography occupancy through exact living selector. Preserve engine._pressure ordered preparedness fold unchanged; report that unresolved ordinary scan separately.

H1k/10k separately outer records/memberhistory/settlementhistory, fixed8living.0 openhousehold payloads/pages;8matching occurrencequeries,0deadPersonloads,0page decodes forindexedselection. Cleancache≤256 householdrows,4pages512slots and64ranknodes. Normalappend2sequencewrites (awayheighttransition), remove≤6/10writes. Aliasretirement/merge/split/retainedchild/replacement/foreignownership; early/mid/late remove, negativeindices/slices, corruption, oldpin, fault/lostack/stale and materializingdetach mustpass. Exactshort eager/lazybehavior mandatory.

Coordinate reverse-occurrence API with identity_design, query_memberships with conflict_threat_design. Root will combine common monolith seams sequentially.
