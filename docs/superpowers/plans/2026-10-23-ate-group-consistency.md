# Group consistency recovery execution plan

Spec: ../specs/2026-10-23-ate-group-consistency.md

1. Reconstruct root-selected query source and test-only verified constructor. Check pagination, retained scopes, exact physical corruption/overlap, authority, transactions, codec hooks, budgets and indexes. Extract closed codec/head preflight helpers without changing projection behavior.
2. Reconstruct group fixtures and complete group composition. Check literal groups, reanchoring, live empty versus range retirement, missing/coherently inconsistent metadata, owner point paths, link ordering, authority/budgets and source interval types. Prove no owner/archive bodies or World restoration.
3. Commit clean sources; measure 1k/10k/100k archive and newer-query populations separately from full fixture/root construction. Run affected suite, one independent branch review, fix substantive findings RED/GREEN, publish exact-tree candidate and launch full CI. Record evidence and remaining integration boundaries. Do not poll long CI.

Review focus: exact namespace/key/path canonicalization; strict integer versus bool counts; selected interval storage classes; closed private decoding; absence/retirement and allocator completeness; owner-radix branch path and count/hash bindings; raw SQL order versus encoded absolute-path link order; aggregate budgets; no hidden scans or payload restoration.
