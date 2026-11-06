# Independent whole-package review

Result: **No actionable findings, including Minor, identified.** This is the single independent review requested for this package; it does not waive author validation/publication gates.

## Reviewed package and byte identity

Read `package.md`, repository `AGENTS.md`, the linked native-roster specification and plan, closure register, catalog composition coverage, and final working-tree implementation/tests against base `e423c94bdb41143f29fcb3f27a2803fac3ceffb1`. Inspected the workflow test inclusion and launcher runtime-tree change. The author created local checkpoint `53ed4842965ab250671aa7fc4a1626c7b52bce0a` during review; the two runtime files remained byte-identical throughout:

| File | SHA256 |
|---|---|
| `simulation/ate_sim/persistence_proof_native_sources.py` | `5ceab732806f3df99d6ae28f95ecd15b900594801323eb4484d3c8075cfe9eab` |
| `simulation/ate_sim/persistence_proof_native_roster.py` | `68dcd8978f46aa066cc64983e46b0f09a14b127ef81fcfaab43f1ae153343a69` |
| Final `simulation/tests/test_stage_0_6_proof_native_roster.py` | `9ae87b963be073dcff06c8b920f39748cd32d46b04de482bee25f3564d82fae2` |

The last test hash supersedes that file's entry in `reviewed-hashes.json`: the author corrected its missing-header/source fixture during review to use a registered identity owner. I inspected and independently ran the corrected test. No runtime change accompanied the correction.

## Contract review

- `expected_count` consumes the accepted manifest head, uses the existing closed metadata codec and strict `_namespace_counts` schema, and takes only the ordinary record field. Its immutable metadata cache is manifest-commitment keyed and operation/epoch constrained by `ValidationScope`. Physical validation is outside the cache.
- `record_rows` checks the accepted namespace declaration before count parsing, so a lazy namespace cannot be treated as an ordinary namespace even when its record count is absent. Its namespace-indexed physical COUNT occurs before payload cursor construction. Missing and extra cardinalities reject immediately; equal-cardinality replacement still encounters the existing individual accepted-root/source check. The final yielded-row count rejects an incomplete enumeration. Public `read_records` exhausts this iterator before returning its unchanged tuple shape.
- The count, payload cursor, source-root checks and final enumeration count remain inside the original checked snapshot. Existing cursor/finally and snapshot/finally paths cover schema and decoder exceptions. Count parsing does not invoke the caller's codec. Existing admission/publisher epoch, callback and recovery controls were inspected rather than replaced by new assumptions about a cache.
- Reviewed the surrounding `IdentityCatalog` descriptor, allocator, retirement, owner header/tree, exact membership, group placement and link projection paths, including the owner-cache epoch and borrowed-transaction invalidation rules. The new public corruption cases exercise those composition seams. The missing-owner fallback's second `_visible_record_row` remains a native accepted-version check, so missing physical header/source/placements do not silently turn an accepted owner into a new owner.
- The documented owner witness boundary is accurate: `_owner` compares source metadata to an authenticated header; it does not certify present source payload bytes. A separate native body proof remains necessary. The unchanged catalog code and documentation do not claim otherwise.
- The implementation does not introduce a whole ordinary-root scan, unrelated source-body read, persistent body cache, new publisher or alternative root. COUNT work scales with the selected namespace; the documentation correctly avoids a constant-time first-body claim.

## Independent execution

Commands used `PYTHONPATH=.:simulation` and `/tmp/ate-roster-venv/bin/python`. SQLite fixtures were created only under `/tmp`.

1. `independent-probes.py` / `independent-probes.log`: passed. Checked ordinary-versus-segment pair handling and absent namespaces; rejected six malformed count schemas and three malformed/oversized blob cases. On an admitted real fixture, three reads performed three physical COUNTs while count metadata was parsed once in each of two validation scopes. After warming an actual owner cache, deleting the link query projection caused public `read_identity_links` to reject with `native query window misses accepted position`; the snapshot was released.
2. `independent-pytest.log` / `independent-pytest.xml`: **8 passed, 18 deselected in 21.66s**, exit 0. Selection: `coherent_missing or count_precedes or missing_header_and_source or staging_callback` from the final roster test file. This covers all four coherent missing/extra/compensated/head-count cases, both payload-selection preflights, corrected missing-header/source/placements fallback, and staged publication callback rejection.

No independent product probe failed. No product/runtime/test modifications, commits, ref changes, CI launches or subagents were performed by this reviewer.

## Preserved exploratory mistakes and fixture correction

Three exploratory read/search commands used guessed module paths that do not exist. These were tooling/navigation mistakes, not product failures; later reads used the actual definitions in `persistence_lazy_store.py` and related files. Their error text is retained here:

```text
rg: simulation/ate_sim/persistence_lazy_snapshot.py: No such file or directory (os error 2)
sed: can't read simulation/ate_sim/persistence_proof_native_directory.py: No such file or directory
rg: simulation/ate_sim/persistence_lazy_schema.py: No such file or directory (os error 2)
```

The first and third searches used shell `&&`, so subsequent dependent reads in those calls did not run; they were subsequently executed against verified file paths. No fixture or product conclusions were drawn from those failures.

The author's separate `catalog-final.log/xml` preserves the initial fixture failure: `world.year` is not a registered identity owner. The author changed that case to the registered `world.skills.skills/(1,'craft')` owner and deleted its source, header and placements; `catalog-fixed.xml` reports nine passing cases. The corrected case also passed in my independent eight-case run. Historical author evidence was neither rewritten nor discarded.

## Assumptions and declined judgments

The completeness proof relies on the existing audited/atomic World invariant joining accepted manifest counts to the accepted ordinary root, plus the admitted physical primary-key/schema contract. I inspected relevant admission/count-schema/source checks; this review does not establish proof-only opening or certify the remaining raw metadata consumers. A metadata-only owner witness is explicitly not accepted as body authority.

The author's broad regression, final source pin/fingerprints, clean launcher, canonical eager/fresh/generated-year comparison, exact local/API source mapping, and single bundled hosted full/proof run are separate completion gates. I did not launch or independently certify them and do not waive them. The 1k/10k retained-value controls establish their stated selected-read instrumentation only; no mature-fixture timing or global constant-time performance judgment is made. No main/default/mature/endurance action is authorized by this report.
