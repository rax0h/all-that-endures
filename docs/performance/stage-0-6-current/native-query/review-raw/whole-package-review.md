# Independent native query whole-package review

Reviewed the dirty implementation against baseline
`2fc836aaf02374a795b217d928935bca5ed0ef45`, its specification and implementation
plan, and the repository working agreement. This is the single package review;
no sub-reviewer or re-review was used. Product files, Git index, HEAD and branch
were not modified by the reviewer.

## Findings

### NQ-R1 — Minor — obsolete query API docstring

Location at review: `simulation/ate_sim/persistence_lazy_store.py:1540`,
`LazyRecordStore.query_memberships` docstring (approximately; the enclosing
method is the stable location).

Reproduction: inspect the docstring's claim “with SQL-side limit/exclusion” and
follow the new native route. Native reads intentionally validate the exact
physical proof window first, then apply exclusions and limit in Python before
selected owner-body reads. SQL-side filtering would break the stated security
contract, so the existing wording describes the fallback rather than the whole
public method.

Closure criterion: describe optional limit/exclusions without promising
SQL-side filtering. No runtime behavior or new behavioral test is necessary.
The author reported changing it to “with optional limit/exclusions” and
inspecting the final Git diff during this review. Status: closed by the author
within this package; no second independent review was performed.

No Critical, Important, or other Minor finding was identified in the reviewed
runtime changes.

## Review conclusions

- Accepted scope resolution uses the already-bound component context and
  preserves actual caller pin validation, including zero-limit and absent
  scopes. Cached summaries are immutable and scoped; physical windows still run.
- Limits and exclusions do not alter physical positions. Bounded physical
  windows, lookahead and final surplus checks precede selected key decoding.
  Future closures and current duplicate intervals fail; limited prefixes do not
  promise inspection of unvisited suffix bytes.
- Selected owners use the existing native source proof route and exact encoded
  membership comparison. Excluded owners are not fetched. Page-owned snapshots
  and source-row locals are released before visible yields. Resume checks bind
  the original accepted epoch and authority.
- The extracted native-window SQL preserves order-reader behavior while adding
  shared locator-budget accounting. Scalar preflight and materialized-column
  guards bound untrusted variable fields. Existing publisher and callback
  authority boundaries are unchanged.

## Verification evidence

Executed independently:

```
PYTHONPATH=.:simulation /tmp/ate-query-venv/bin/python -m pytest -q -p no:cacheprovider simulation/tests/test_stage_0_6_proof_native_query.py simulation/tests/test_stage_0_6_proof_native_order.py --basetemp=/tmp/ate-query-independent-review
101 passed in 180.64s (0:03:00)
```

Two additional independent probes passed in 12.33s, and both passed again in
the expanded exploratory invocation. They cover duplicate open intervals at an
admitted positive generation (including limits, exclusions and streaming), and
132 large query keys forcing metadata-driven window shrink without skipping.
Code and raw result history are retained beside this report. The author reports
promoting these positive cases into product tests and rerunning them successfully
(2 passed in 12.01s); that promotion is not a second review.

One attempted old-household-projection fixture was invalid for the normalized
format and returned the correct empty scope. Its failed expectation and
disposition are preserved in `reviewer-probe-history.txt`; it is not a product
failure or counted positive evidence.

## Declined to judge

- Hosted CI publication, final runtime/source fingerprints and final clean-tree
  mapping: these were still pending and not available in the reviewed snapshot.
- Completion of the author's separate broad regression/generated-year run:
  the independent evidence above is limited to the executed 101 tests and two
  valid probes. No separate eager/fresh generated-year equivalence claim is made.
- Performance improvement, mature acceptance, full-audit removal, default
  activation, main merge and endurance behavior: outside this package's
  authorized acceptance claim.

These exclusions do not defer an identified runtime defect. The single Minor
documentation finding has an explicit closure action and must remain in this
package's consolidated closure register.
