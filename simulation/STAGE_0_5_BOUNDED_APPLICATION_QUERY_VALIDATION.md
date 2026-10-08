# Bounded inquiry application query checkpoint

This completes the failed-application predicate slice of continuous repair Task6, and supplies the shared limited occurrence-query API for Task3. It does not complete the remaining scalar, household, identity-discovery or nested-history migrations.

`query_memberships` returns checked ordered `(key, ordinal)` occurrences with SQL-side exclusion and an optional exact nonnegative limit. It preserves repeated positions and pinned generations. Limited reads validate owner membership and use a bounded exact-marker witness to reject overlapping visible memberships hidden by the result boundary. The compatibility `query_keys` API retains its previous result shape.

Explicit conversion declares complete application `(branch, passed)` authority in the checked collection description and requires reader capability5. The lazy application threshold merges current touched candidates with only the needed persisted candidates. Inquiry close now uses that threshold. Legacy descriptions continue through their checked passed index and branch payload filter; ordinary open does not upgrade or interpret missing authority as an empty result. Native numeric/boolean equality is retained without replacing payload representatives.

Observed red cases included the unsupported inquiry predicate, a duplicate membership hidden by `limit=1`, numeric false representatives lost after reopen, and an application shared with a wallet acquiring the wrong absolute identity path. Each was repaired before the final focused gate. Existing people checks also detected two unrelated descriptor reads on ordinary saves; compact descriptor validation now runs when that authority actually changes.

Current-source verification:155 passed in37.99s across application threshold, limited query membership, lazy institutions, magic institutions, lazy people, compact event IDs, store and store-failure tests. The threshold and query tests include1k/10k histories at fixed current work, zero baseline application payload decodes, five checked candidates, overlay replacement/deletion/reversion, native eager agreement at4/5/6, legacy byte preservation, corruption, rollback/lost acknowledgement, reopen and shared identity.

P5 seed843000 with3 pre-conversion +4 continuation +3 reopened years, paged households:passed. Finalyear10/events439. Exact eager-control final digest:`3301d4e4a6a2f415679cabe62754813440034cf4c190035c79ba82cc7b8e378e`; total digest:`b31c2272d220a1624ff5ee204e229ccaf95adf9a7eaff86643b350567b5e9387`. Evidence:`continuous-repair-p5-application-query.json` in the run workspace. Portable detached and relocated checkpoints passed.

Limits:legacy query fallback can inspect historical candidates. Old-pin SQL branches are limited separately and merged; this checkpoint does not claim their physical query CPU is independent of all history. Complete combined storage proof, final Astra review and one final full-suite CI run remain pending.
