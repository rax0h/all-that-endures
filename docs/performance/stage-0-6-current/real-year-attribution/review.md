# Independent finite review: real-year probe

Reviewed `a21954a..d58bfb9`, only `.github/tests/run_proof_real_year_probe.py`; runtime unchanged. Read AGENTS.md and native session/digest implementation. No source edits, full suite, hosted CI, additional agents, or duplicate benchmark run. Parent owns exact CLI run and 240s cap.

## Actionable findings

### R1 — Minor — identify parent-only CPU/RSS for subprocess restore

Lines 49,57–58 apply `time.process_time()` and `RUSAGE_SELF` to every phase, including lines 121–129 where all substantive restore/admission/digest work occurs in a child process. The resulting generic `cpu_seconds` and `process_peak_rss_kib` are easy to interpret as restore resource use but omit it entirely. RSS is also process-lifetime peak, not phase-local. Wall time remains valid. Independent minimal reproduction: parent CPU 0.000380104s for a child using 0.623312 user CPU seconds.

Concrete closure: explicitly name/document these as parent CPU and process-lifetime parent RSS, or return child CPU/peak RSS separately from the child and retain parent accounting separately. Do not substitute aggregate parent values for child restore resources. Check receipt field contract on a child workload.

### R2 — Minor — retain fresh-child failure evidence

Lines 122–126 use `capture_output=True, check=True`; lines 53–54,134–135 record only `str(exc)`. `CalledProcessError.__str__` excludes captured stdout/stderr, so a restore import/audit/digest/close failure leaves the receipt and ordinary uncaught parent traceback without the child traceback/root cause. TimeoutExpired can likewise hold partial output which is not preserved. This directly weakens the requested exception/timeout evidence.

Concrete closure: persist bounded captured stdout/stderr plus returncode/timeout metadata on child failure (a separate log file is also suitable), then re-raise. Preserve both expected and actual restored year/digest for an equality mismatch. Targeted forced child nonzero, timeout, and digest-mismatch checks should show useful evidence and failed status without invoking a full benchmark.

## Verified design strengths / boundaries

- Raw save runs first without profiler or audit/commit monkeypatch; diagnostic hooks apply only to save on a separate copy of the same accepted checkpoint and are removed in `finally`. Instrumented results are explicitly disclaimed.
- Parent open/admission, simulation, save, close and fresh subprocess restore+digest are distinct named wall phases. Restore wall time honestly includes interpreter startup, admission, digest, close and subprocess overhead; it is not a pure open measurement.
- Source receipt includes HEAD, runtime tree and driver SHA256; dirty tracked source is rejected. Fixture has fixed seed/config, accepted database SHA256 and independently advanced eager digest; accepted database mutation is checked after both passes. Exact executed runtime import path relies on launch environment (`PYTHONPATH=simulation`), which the parent's launch evidence should retain.
- Both raw and diagnostic reopened state must have year3 and complete canonical digest equal to eager control. Child uses the newly saved commitment, not the initial commitment. No in-process digest warms raw save.
- Failed actions mark phase and receipt failed; completed prior phases are atomically preserved. An external SIGTERM/KILL from the parent's 240s cap bypasses Python exception/finally handling and can leave status running, correctly indicating incomplete rather than success; retain wrapper exit/timing/log evidence and explicitly classify timeout externally. The internal 120s child timeout is a distinct bound.
- Small generated world is explicitly not retained millennium/mature-world/cold-cache acceptance. Raw vs diagnostic is a single ordered observation, not repeated controlled benchmarking.

Finite review disposition: two Minor findings above require closure within this work group per AGENTS.md. No Critical or Important source correctness issue identified. Actual complete benchmark execution remains parent-owned and is not claimed here.

Author closure: R1 closed with explicit parent CPU and parent process-lifetime RSS labels, child CPU deltas and child RSS high-water labels. Actual fresh restore recorded10.295child CPU seconds. R2 closed with serialized child stdout/stderr, exit/timeout and actual digest mismatch. Four targeted regressions passed0.02s. Final CLI completed both passes and exact fresh digest checks; prior superseded incomplete pass is not counted. No runtime changes or expensive CI launched.
