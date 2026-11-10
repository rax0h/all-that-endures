# Timeout repair: independent ordinary regression check

The existing `simulation/tests/test_stage_0_6_genesis_transaction.py` suite passed:
**37 tests,14.73seconds, exit0**. Raw output and JUnit are preserved in
`ordinary-transaction-regressions.log` and `.xml`.

Execution used `/workspace/scratch/d88f8db353e8/ate-qualified-313/bin/python` with
`PYTHONPATH=.:simulation`. The full executable/compiler/Python/SQLite source ID,
compile options, extension and loaded-library fingerprint matched the current
saved qualification JSON. `fingerprint.json` records zero differences. The
unchanged complete13phase qualification belongs to source85f87e1 before repair
edits; these37 regressions validate the repair's transaction controls separately.

## Reviewed flow and documented-case closure

| Earlier review case | Present control and existing passing regression |
| --- | --- |
| Savepoint rollback could remove the sealed manifest | All savepoint operations are denied and poison the build; `test_savepoint_control_is_not_permitted_after_world_seal` |
| Setup/commit callbacks ran outside the guard | Guard is installed before owned BEGIN/schema setup and remains active through commit/rollback. Only the owner's boundary is authorized; callback writes reject/interrupt the active statement. `test_sql_callbacks_stay_readonly_from_setup_through_commit` covers begin, schema and commit |
| Foreign store could borrow another source memo | `verify_all` binds exact transaction type, store, connection and codec before delegation; `test_source_audit_certificate_cannot_be_transferred_to_another_store` |
| Incremental BLOB mutation bypassed the SQL authorizer | Writable handles are wrapped/tracked, active mutation/open and deserialize reject, existing writable handles prevent custody; the two non-SQL mutation tests and existing-handle test pass |
| Result factory could hide a corrupted reachable proof root | Native result factories are required at entry and connection/cursor factory changes reject during custody; `test_result_factories_are_frozen_for_source_and_proof_checks` |

The high-level flow matches the design and plan:

- Catalog optimization requires an owned construction snapshot. Its fixed-size
  scope reuses operational/header/node facts; the checked owner walk also emits
  the physical node inventory. Default paths retain their ordinary checks.
- The format6 preparation keeps catalog, roster kind/inventory, reference and
  graph validation. Expired dependency-token clearing moves into rebase; its
  discarded intermediate storage generation is omitted. The default rebase
  still audits normally.
- Proof builders share one owned `BEGIN IMMEDIATE`; exact derived schemas and
  required indexes are prepared under the guard. One actual full source audit
  supplies reusable facts only inside that guarded transaction. Standalone
  bootstrap calls still require their own transaction boundary.
- Final World/source/proof correspondence runs before manifest sealing. Sealing
  prevents further main derived writes; final global integrity and foreign-key
  checks precede the single commit. Failure performs rollback before restoring
  the prior guard/authorizer/scope. Existing tests also cover incomplete builds,
  source-write denial, foreign writer locking, custody changes, corrupt new proof
  nodes and dependency-token validation/preservation.

No further concrete correctness issue arose from this bounded regression and
high-level flow review. Product code and hosted runs were outside this check.

## Remaining validation limits

This is not the final exact-source fence or a complete release/performance claim.
The plan still requires measured SQL/audit counts and bounded construction
scaling, affected checks, the unchanged complete generated-year scenario on the
final repair, final receipt/request fingerprints, and consolidated validation.
The previous hosted green results authorize only source85f87e1's recorded runtime.
The authenticated mature construction must still complete within its unchanged
budget and satisfy the source preservation and continuation gates. Stage0.6 and
the mature-timeout performance finding remain open until that evidence exists.
