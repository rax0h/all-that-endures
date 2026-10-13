"""Bounded diagnostic of a disposable copy of the verified complete restore.

Each phase has an alarm budget. An interrupted simulation is diagnostic only;
never save or reuse that World. cProfile timing includes instrumentation overhead.
"""
from __future__ import annotations

import argparse
import cProfile
from dataclasses import asdict
import hashlib
import io
import json
from pathlib import Path
import pstats
import shutil
import signal
import time

from ate_sim.engine import Simulation
from ate_sim.persistence_lazy import open_lazy_world_session
from persistence_p5_validation import _authority, _assert_authority, _run_unbound


class BudgetExpired(Exception):
    pass


def run(source, output, budget, *, profiled=True):
    output.mkdir(parents=True, exist_ok=False)
    target = output / "operational.sqlite"
    shutil.copyfile(source, target)
    result = {"source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
              "budget_seconds_per_phase": budget, "profiled": profiled,
              "phases": {}, "passed": False}
    session = None
    sql_ticks = 0

    def expired(*_args):
        raise BudgetExpired("phase diagnostic budget exhausted")

    def progress():
        nonlocal sql_ticks
        sql_ticks += 1
        return 0

    def phase(name, operation):
        nonlocal sql_ticks
        sql_ticks = 0
        if session is not None:
            session.store.reset_diagnostics()
        profiler = cProfile.Profile() if profiled else None
        started = time.perf_counter()
        status = "completed"
        signal.setitimer(signal.ITIMER_REAL, budget)
        if profiler is not None:
            profiler.enable()
        try:
            return operation()
        except BaseException as exc:
            status = f"{type(exc).__name__}: {exc}"
            result["passed"] = False
            raise
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            if profiler is not None:
                profiler.disable()
            elapsed = time.perf_counter() - started
            if profiler is not None:
                profiler.dump_stats(str(output / f"{name}.prof"))
                stream = io.StringIO()
                stats = pstats.Stats(profiler, stream=stream).strip_dirs()
                stats.sort_stats("cumulative").print_stats(50)
                stats.sort_stats("tottime").print_stats(30)
                (output / f"{name}.txt").write_text(stream.getvalue())
            record = {"status": status, "seconds": elapsed,
                      "sqlite_vm_instructions_approx": (
                          sql_ticks * 10000 if profiled and session is not None and name != "close" else None)}
            if session is not None:
                record["io"] = asdict(session.store.diagnostics())
            result["phases"][name] = record
            (output / "result.json").write_text(json.dumps(result, indent=2))
            print(name, json.dumps(record), flush=True)

    signal.signal(signal.SIGALRM, expired)
    try:
        session = phase("open", lambda: open_lazy_world_session(
            target, rules_id="stage-0-5-complete-final"))
        if profiled:
            session.store.db.set_progress_handler(progress, 10000)
        result["start_year"] = session.world.year
        result["start_generation"] = session.pin.captured_head
        control = _run_unbound(session.world.seed, session.world.year + 1)
        expected = _authority(control)
        phase("simulation", lambda: Simulation(session.world).run(1))
        phase("save", session.save)
        actual = phase("audit", lambda: _authority(session.world))
        _assert_authority("one-year verified restore", actual, expected)
        result["final_digest"] = actual["digest"]
        result["final_year"] = actual["year"]
        result["passed"] = True
    except BudgetExpired as exc:
        result["stopped"] = str(exc)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        if session is not None:
            session.store.db.set_progress_handler(None, 0)
            phase("close", session.close)
        (output / "result.json").write_text(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--budget", type=float, default=90)
    parser.add_argument("--unprofiled", action="store_true",
                        help="Disable cProfile and SQLite progress sampling; retain ordinary I/O counters")
    args = parser.parse_args()
    result = run(args.source, args.output, args.budget, profiled=not args.unprofiled)
    raise SystemExit(0 if result["passed"] else 1)
