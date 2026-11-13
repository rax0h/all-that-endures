# Repeated small-world comparison

Daniel noted that the latest absolute times were longer than earlier reports.
That observation was correct, and the earlier absolute measurements should have
been presented alongside the adjacent pair rather than leaving a misleading
impression that all reported times had fallen.

An earlier run of the same baseline engine and exact same year1 input recorded
5.312s save and 5.990s warm. In the prior same-command pair, the same baseline
engine and input recorded 7.722s save and 9.224s warm; the candidate recorded
8.152s save and 7.271s warm. All three use the same fully qualified Python and
SQLite fingerprints. The older baseline's CPU model was not recorded; its
cause of variation is unknown. The prior same-command pair recorded an Intel
Xeon Platinum 8573C, while this recheck recorded an AMD EPYC 9V74. Different
CPU models are observed across sessions; that alone does not establish why the
older baseline took 5.990s or how much of any difference the CPU caused.

## Same-session A-B/B-A recheck

Each trial starts from its own copy of the same 26,206,208-byte year1/seed843000
database SHA256 2555675bd19ede5c6ed9b7619fab56d59098a8b358d9a9c3569cabccba22c554.
Baseline is runtime41d21d8; candidate is runtime4654b019. Both use qualified
Python3.13.5/GCC14.2.0/SQLite3.46.1, proof-only opening and the same driver.
The four trials run as sequential children of one command. A-B then B-A balances
order but does not eliminate dynamic CPU/cache effects. No other local tests ran
during the measurement.

| Observation | Baseline seconds | Candidate seconds |
|---|---:|---:|
| Pair1 first step | 7.659 | 6.019 |
| Pair1 save | 5.624 | 5.595 |
| Pair1 warm step | 6.457 | 4.868 |
| Pair2 first step | 7.483 | 5.678 |
| Pair2 save | 4.945 | 5.289 |
| Pair2 warm step | 5.682 | 4.917 |

Warm-step decreases24.6% and13.5% in these two observations. Save changes
-0.5% and+7.0%: no save improvement is established. Four trials are not a
reliable latency distribution or mature-world benchmark. All source/runtime
fences, input SHA and fresh saved year2 and continued year3 digests match. Per-
phase raw CPU/wall, host context, logs and restartable trial evidence are in
run-1/manifest.json and its child reports; plan.md records caps and restart units.

## Earlier faster annual result

The Nov5 annual-ordinary receipt did report1.870s for a simulated year and
4.636s to save. It used a different accepted database SHA256 beginning bd8b3e,
starting at year2, an older engine/Python3.12.3/SQLite3.45.1 and an audited
opening that took9.252s before the measured year. The current recheck starts
with a different year1 accepted database (SHA256 255567), advances, saves and
then measures its warm next year using proof-only opening. Its year3 digest is
also different. Therefore these are real results for different workloads and
opening contracts; they cannot establish the cause of their gap or prove that
the current engine matches the old1.870s workload. The exact old bd8b3e input
was not found among the searched local 25–35MB SQLite files; do not substitute
another fixture or rebuild a costly prefix as if byte-identical.

The earlier sub-second results were selected small edits/saves against history-size
fixtures, with construction/admission and complete simulated-year work excluded.
They are useful bounded-path evidence, not end-to-end full-year acceptance; see
../../../benchmark-scope.md.

Target acceptance remains OPEN: mature-world open≤10s, save≤2s, warm step≤1s.
Neither the small fixture nor its relative improvement proves those targets.
The existing hosted full/proof CI is a separate correctness gate and continues
on the unchanged engine; this diagnostic does not launch another engine CI.

## Diagnostic review and cleanup

An independent review confirmed all four measured runtime-file SHA256 sets
against the pinned Git blobs, input and fresh-state fences and the reported
arithmetic. It found two harness issues that did not affect completed trials:
termination could leave a descendant alive after its leader exited, and the
preflight did not reject staged or untracked/ignored engine Python sources.
Five focused regressions reproduce these issues and pass after correction. The
future runner now signals the entire process group even if its leader has
already exited, then kills any remaining processes after its bounded grace; it
checks engine Python inventory/bytes against the pinned Git tree and also
checks tracked runtime changes against HEAD. The original measured script is
retained as run-1/repeat-measured.py with SHA256
45b37efd0ef67802bf8d414cdb82b13ceef24c02386b2898728ae1945597b543.
No performance trial was rerun after these diagnostic-only repairs.
The full runtime fingerprint was verified once for the measurement session;
each trial independently checked Python version, engine sources, input and
saved/continued state. Libraries were not rehashed between trials.
