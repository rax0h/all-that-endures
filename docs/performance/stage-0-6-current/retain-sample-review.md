# Fixture retention/sample review and closure

One fresh independent Astra/high review of e3358b5..2efc088, read-only; no delegated implementers or second review. Initial result:0 Critical,3 Important,0 Minor. Reviewer ran8 focused tests and additional termination, delayed-unwind, close-error and read-only-source probes. Tracked checkout remained clean.

| Finding | Closure | Regression |
|---|---|---|
| S1 shell timeout can lose final result/profile | Existing command-exit machinery now supports the sample lane; actual workflow records numeric exit and preserves failure. Graceful TERM stops/flushed profiling and finalizes. Forced termination synthesizes censored diagnostic from phase journals, explicitly reports whether the profile exists, and never claims performance acceptance. | Actual workflow shell wrapper with real GNU timeout TERM/KILL; both RED then GREEN. TERM retains profile, KILL explicitly reports unavailable profile. |
| S2 profiler remains active during timeout exception cleanup | Existing Recorder accepts an optional budget-expiry callback. The diagnostic disables profiling before raising the budget exception, and separately records actual profiled versus remaining wall time. The command watchdog still bounds cleanup. | Delayed exception-finally stand-in: budget0.01s, cleanup0.2s; RED then GREEN. Cleanup function absent from profile; inclusive wall time and non-profiled time remain visible. |
| S3 close failure skips accepted-source rehash | Close and original-source verification use independent finalization blocks, preserving both error fields. | Injected close failure RED then GREEN; original-source hash and verification phase remain present. |

All3 findings addressed in one author fix pass; focused4-case regression gate passed7.38s before the final combined gate. No claim of independent reapproval after fixes. Final verification evidence is recorded alongside this report.

Declined judgments and author rulings:
- No mature speedup, bottleneck or acceptance verdict is inferred from small fixtures or profile prefixes. Hosted function evidence remains required; cost: optimization cannot be chosen from these harness tests.
- No successful uploaded replacement is inferred from workflow configuration. Artifact ID/digest, exact producer and original authority must be checked after the hosted run; cost: fixture retention remains open until that receipt exists.
- No full-year deterministic continuation is claimed from partial simulation work. The sample never saves; existing accepted continuation authority remains unchanged. Cost: a separate complete saved/restored candidate is still required for final performance acceptance.
- The read-only-source probe ran as root; it establishes unchanged bytes, not general permission-denied behavior. The harness authenticates/only reads original input and operates on a copied DB. Cost: OS permission semantics are not a new tested contract.
- Ordinary source/workflow/doc pushes cannot launch the expensive measurement; explicit request-file push is limited to retention/sample, and the full job requires explicit dispatch mode. Cost: full measurements remain manual operations.
- Signal delivery can be delayed by uninterruptible native work; actual profile wall time is retained and is not clamped to the requested interval. The shell watchdog remains the hard outer bound. Non-profiled wall time includes unwind and recorder overhead, rather than pretending to measure pure GC time.

Final gate:51 targeted/affected tests passed31.52s, including exact workflow sample CLI and real TERM/KILL shell wrappers. All workflow shell blocks/YAML/fingerprints and clean exact-source/runtime fence passed. Runtime unchanged63d5ac487d0157a5ef521b4def8ee9ce94532e0c. All3 actionable findings closed; no new findings deferred. Hosted fixture upload/sample result remains pending.
