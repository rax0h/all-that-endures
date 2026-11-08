# Native metadata boundary review register

One independent whole-package review found4Important+2Minor, no Critical.
All findings are accepted and fixed in this work group; none is deferred.

| ID | Finding and action | Evidence | Status |
|---|---|---|---|
| R1 Important | Decoder could replace snapshot or pin. Readonly SQL capability covers opener semantic decoding AND public result decoding; original pin/epoch/pair checked before return. SQLite denial normalizes to StoreError, preserving caller-owned nesting. | Four opener/result ROLLBACK+BEGIN/pin controls RED; final new39GREEN | Closed |
| R2 Important | Snapshot cleanup trace callback could invalidate epoch after last inner check. Check original binding/transaction ownership again after owned snapshot release; prefix guard no longer opens/releases a transaction. | Cleanup-update RED->GREEN | Closed |
| R3 Important | Cold reader postcheck captured a fresh epoch rather than original source context. Capture exact authority/pin/epoch/pair before read, compare it afterward, reject rebinding before cache insertion. | Cold decoder commit+rebind point and verify controls RED->GREEN | Closed |
| R4 Important | Last segment in verify_full could succeed after decoder mutation. Shared postcheck now belongs to _read_segment_from_store so both cold point reads and explicit scrub use it; verify_full still bypasses body cache. | Final-segment verify RED->GREEN | Closed |
| R5 Minor | Warm point redundantly opened two full metadata snapshots:54SQL statements. Use one bounded pin/epoch/persistent-source check and documented sole-caller precondition for private _load_segment. | SQL work RED54>25; final positive16statements/point, zero segment-body reads | Closed |
| R6 Minor | Arbitrary caller BEGIN leaked SQLite OperationalError. Explicit same store-level transaction guard for head and prefix; caller transaction retained. | Warm arbitrary-transaction StoreError plus owned/nested/iterator cleanup independent controls pass | Closed |
| A1 Author test contract | Old reader intentionally closes on publication; positive control now warms replacement cache and asserts old-reader rejection. | First19RED includes old-close fixture; first25GREEN49.38s | Closed |
| A2 Author recovery contract | Older fault/recovery tests used generation as unauthenticated diagnostic during uncertain/stale state. Keep public accepted read blocked, assert physical main.save_head generation separately and retain exact recovery/reopen/corruption checks. | Boundary63pass/2fail157.87s; broad276pass/1same-contract-fail707.50s; all3targeted recovery cases9.49s GREEN. Expanded consumer sweep64same-contract failures/10pass220.12s; all64failures independently checked to stop at the physical generation assertion;17further diagnostic sites corrected, preserving rejection/recovery/fresh assertions; final74case consumer rerun266.47s GREEN | Closed |

Independent owned/nested transaction, paused iterator early-close/error checks
pass. Fixed independent probe: point/cache length16SQL statements each versus
54/27 before. Point0.128ms locally; these are local controls, not mature-world
latency. Public head validation has extra bounded checks; no speedup is claimed.
39new cases70.00s pass. Source-level body/epoch tests include callback-safe
normal save/fresh restoration and full-audit preservation; final source/harness
and generated-year receipts are recorded in closure.md when complete.

Review scope rulings: captured_generation and cache counters describe immutable
capture/local diagnostics and are not new semantic source authority. Existing
publisher/admission/staging/recovery paths remain separate owned capabilities.
The170literal-site inventory is not exhaustive for dynamic SQL and does not
approve proof-only opening. Full audit removal, default activation, generic
reader redesign and mature target qualification remain outside this group;
those gates remain enforced. If relaxed prematurely, unverified restoration or
unmeasured latency could be exposed. No second review dispatched.
