# Independent retained-record review

Fresh-context Astra read4010a11..10b8e46, runtime/store transaction/recovery, proof helpers, source guards, tests and driver. Dedicated31cases passed independently in2.60s. Four Important findings independently reproduced in /tmp; no Critical/Minor findings.

1. Post-hoc phase-hook counters allowed COMMIT before proof staging, durably advancing data/head/receipt without the successor root. Fixed with a connection-owned read-only SQL authorizer scope covering every proof-aware hook (including before_transaction/after_commit), preserving/chaining any existing authorizer and forbidding callback removal. COMMIT, rollback/rebegin, executescript, SQL writes and authorizer-removal cases covered, including metadata-only saves. Actual successor head and changed-row binding are independently checked. This is a SQL capability guard, not an arbitrary-Python sandbox.
2. Noncommitted recovery returned a stale parent certificate with a newer resolved generation. Fixed exact pin/generation/source-root checks for noncommitted outcomes; pending and already-resolved latest attempts tested. Missing parent-root source also reproduced RED and now rejects.
3. Full bootstrap accepted coherently checksummed future ordinary revisions. Fixed pre-audit integer/range probe and construction-time range invariant.
4. Oversized checksum/locator/integer-affinity metadata transferred before rejection. Fixed SQL type/byte-length/range probes before inherited full audit; embedded-NUL and allocation bounds tested. Variable locators have an explicit metadata budget.

Regression run before fixes completed17failed/4passed/31deselected in2.02s. Its background redirected full log was not recovered; captured completion summary is retained separately and is not mislabeled as a full log. Focused final60cases passed in4.32s; affected final evidence and exact-source scaling recorded in ledger. Existing authorizer policies remain active during/after callbacks; no second independent review requested.

Strengths: actual written-row comparison at existing commit boundary; expected-authority/pin/path/retained-byte binding; clear ordinary-only scope; sorted SQL delta and replayable frozen inputs.

Declined: complete manifest/World/format/fencing/collection; full World performance/endurance/finalCI; inherited full-audit materialization of unrelated lazy/segment inventories; arbitrary Python replacement of private methods. Author rulings and costs in retained-record-ledger.md.
