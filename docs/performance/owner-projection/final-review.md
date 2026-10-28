# Fresh whole-package review and repair rulings

One independent read-only reviewer examined5db6178..d8e7ea6. No nested agent or second review; no Critical finding. Verdict with fixes. Strengths: exact two-authority count/path comparison, raw-byte preservation, existing physical adapters, coherent mismatch/absence tests, narrow default-preserving index checks, separate measured construction. Reviewer reproduced all three Important defects in small databases.

## Important findings and one repair pass

1. Inherited snapshot head validation decoded simulation_position/next_ids through WorldCodec, permitting rechecksummed Event restoration before the closed source parser. Exact class check also missed instance hooks. Accepted: two changed-head cases and one instance-hook case RED. Repair guards all four head blobs before inherited validation, allows ordinary metadata containers only through a closed storage subset, and rejects overridden codec methods. No World source object restoration.
2. Adapter/path encoding could raise UnicodeEncodeError outside StoreError. Accepted: authenticated escaped-surrogate Ref/frozenset path RED. Public boundary now normalizes codec/schema failures into StoreIntegrityError while preserving existing StoreError classes.
3. Delegated VersionProofBudgetError/OccurrenceProofBudgetError escaped the declared ProjectionProofBudgetError. Accepted: selected-body and metadata-budget regressions RED. Public boundary translates delegated budgets.

All six regressions reproduced RED before implementation. Initial pre-repair scaling is superseded, not accepted final evidence. Corrected runtime is measured separately. No re-review; all43 projection cases within449 affected cases pass after repairs. Repaired clean-source1k/10k/100k measurements also pass.

## Minor deferred

Raw pytest RED logs contain trailing whitespace. Preserve raw evidence verbatim; source/config/docs whitespace checks explicitly exclude *.log. A whole-range whitespace check including evidence does not pass. Earlier unqualified diff-check wording is superseded by this scoped result. No evidence rewriting.

## Declined-to-judge rulings

- Complete World topology, owner catalog/radix agreement, links, retirement, manifests, publication and admission: defer exactly as spec. Cost if wrong: unsafe admission; World remains inactive until all gates exist.
- Target-body existence: not established by projected IDs/allocator. Cost if wrong: dangling targets; canonical admission must prove target kind/existence.
- Ordinary World owners and overwritten ordinary payloads: unsupported here. Cost: later separate checked paths and immutable payload retention are required.
- Unselected surplus physical rows: never admitted; full inventory audit required. Cost: unread physical corruption is not detected by this bounded check.
- World activation and open/save/year performance: remain outside this component and unmeasured. Cost: no target-speed claim from these observations.

Initial implementation rulings retained: five existing physical adapters instead of a new object walker (more adapters remain necessary); closed codec subset instead of caller hooks (custom codecs require another checked path). No finding dropped silently.

Current disposition: see [consolidated cleanup register](../review-cleanup/register.md) for closure of this checkpoint's recorded Minor findings. Historical review evidence above is preserved.
