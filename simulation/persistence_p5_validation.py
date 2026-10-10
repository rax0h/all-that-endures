from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
import time
from pathlib import Path

from ate_sim import checkpoint
from ate_sim.engine import Simulation
from ate_sim.persistence_lazy import (
    convert_cold_to_lazy,
    open_lazy_world_session,
)
from ate_sim.persistence_session import write_cold_snapshot
from ate_sim.worldgen import generate_world


DEFAULT_RULES = "stage-0-5-p5-validation"


def _io(diag):
    return {
        "payload_reads": diag.payload_reads,
        "payload_read_bytes": diag.payload_read_bytes,
        "payload_writes": diag.payload_writes,
        "payload_write_bytes": diag.payload_write_bytes,
    }


def _ref(value):
    if value is None:
        return None
    return (value.kind, value.id)


def _event_projection(world):
    return tuple(
        (
            event.id,
            event.year,
            event.kind,
            event.layer.value,
            tuple((actor.kind, actor.id) for actor in event.actors),
            _ref(event.location),
            tuple(event.causes),
            event.data,
            bool(event.__dict__.get("_sealed", False)),
        )
        for event in world.events
    )


def _counters(world):
    result = {
        "next_person": world.next_person,
        "next_household": world.next_household,
        "next_settlement": world.next_settlement,
        "next_event": world.next_event,
    }
    for name in (
        "economy",
        "knowledge",
        "culture",
        "communities",
        "transmission",
        "infrastructure",
        "magic_resources",
        "institutions",
        "metaphysics",
        "divinity",
        "materials",
        "warfare",
        "society_accountability",
        "threat_ecology",
    ):
        state = getattr(world, name)
        for field, value in sorted(state.__dict__.items()):
            if field.startswith("next_") and type(value) is int:
                result[f"{name}.{field}"] = value
    return result


def _authority(world):
    return {
        "digest": world.digest(),
        "year": world.year,
        "seed": world.seed,
        "counters": _counters(world),
        "events": _event_projection(world),
    }


def _assert_authority(label, actual, expected):
    if actual["digest"] != expected["digest"]:
        raise AssertionError(
            f"{label}: digest mismatch {actual['digest']} != {expected['digest']}"
        )
    if actual["year"] != expected["year"] or actual["seed"] != expected["seed"]:
        raise AssertionError(f"{label}: seed/year mismatch")
    if actual["counters"] != expected["counters"]:
        raise AssertionError(f"{label}: counter mismatch")
    if actual["events"] != expected["events"]:
        raise AssertionError(f"{label}: exact event projection mismatch")


def _warm_queries(world):
    people = tuple(world.people)
    if people:
        pid = people[0]
        world.social.relationships_for(pid)
        world.social.neighbors(pid)
        world.communities.memberships_for(pid)

    transmissions = iter(world.transmission.records.values())
    first_transmission = next(transmissions, None)
    if first_transmission is not None:
        world.transmission.history(
            first_transmission.item_kind, first_transmission.item_id
        )

    settlements = tuple(world.settlements)
    if settlements:
        world.materials.available(settlements[0])


def _run_unbound(seed, years):
    world = generate_world(seed)
    Simulation(world).run(years)
    return world


def run(seed, pre_years, continuation_years, reopen_years, workdir, rules_id, paged_households=False, counted_households=False, native_graph_buckets=False):
    if counted_households or native_graph_buckets:
        paged_households = False
    total_years = pre_years + continuation_years
    final_years = total_years + reopen_years
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)

    timings = {}

    started = time.perf_counter()
    control_at_total = _run_unbound(seed, total_years)
    control_total = _authority(control_at_total)
    timings["control_total_seconds"] = time.perf_counter() - started

    started = time.perf_counter()
    control_at_final = _run_unbound(seed, final_years)
    control_final = _authority(control_at_final)
    timings["control_final_seconds"] = time.perf_counter() - started

    started = time.perf_counter()
    checkpoint_world = _run_unbound(seed, pre_years)
    checkpoint_bytes = checkpoint.dumps(checkpoint_world)
    checkpoint_restored = checkpoint.loads(checkpoint_bytes)
    Simulation(checkpoint_restored).run(continuation_years)
    checkpoint_total = _authority(checkpoint_restored)
    _assert_authority("checkpoint continuation", checkpoint_total, control_total)
    timings["checkpoint_lane_seconds"] = time.perf_counter() - started

    cold = workdir / "p5-cold.sqlite"
    lazy = workdir / "p5-lazy.sqlite"
    relocated = workdir / "p5-relocated.sqlite"
    for path in (cold, lazy, relocated):
        if path.exists():
            path.unlink()

    started = time.perf_counter()
    cold_source = _run_unbound(seed, pre_years)
    pre_digest = cold_source.digest()
    cold_result = write_cold_snapshot(cold_source, cold, rules_id=rules_id)
    if cold_source.digest() != pre_digest:
        raise AssertionError("cold bootstrap mutated its source World")
    conversion_result = convert_cold_to_lazy(cold, lazy, rules_id=rules_id, paged_household_members=paged_households, counted_households=counted_households, native_graph_buckets=native_graph_buckets)
    timings["fixture_creation_seconds"] = time.perf_counter() - started

    with open_lazy_world_session(lazy, rules_id=rules_id, paged_household_members=paged_households) as session:
        open_io = _io(session.store.diagnostics())
        _warm_queries(session.world)
        session.store.reset_diagnostics()

        started = time.perf_counter()
        Simulation(session.world).run(continuation_years)
        simulation_seconds = time.perf_counter() - started

        session.store.reset_diagnostics()
        generation_before = session.pin.captured_head
        saved_generation = session.save()
        save_io = _io(session.store.diagnostics())
        if saved_generation <= generation_before:
            raise AssertionError("lazy continuation did not publish a successor")

        session.store.reset_diagnostics()
        lazy_total = _authority(session.world)
        total_audit_io = _io(session.store.diagnostics())
        _assert_authority("lazy continuation", lazy_total, control_total)

        session.store.backup(relocated)

    with open_lazy_world_session(lazy, rules_id=rules_id, paged_household_members=paged_households) as reopened:
        reopened_total = _authority(reopened.world)
        _assert_authority("lazy reopen", reopened_total, control_total)

        started = time.perf_counter()
        Simulation(reopened.world).run(reopen_years)
        reopen_simulation_seconds = time.perf_counter() - started

        reopened.store.reset_diagnostics()
        reopened.save()
        reopen_save_io = _io(reopened.store.diagnostics())

        reopened.store.reset_diagnostics()
        lazy_final = _authority(reopened.world)
        final_audit_io = _io(reopened.store.diagnostics())
        _assert_authority("lazy second continuation", lazy_final, control_final)

        detached = reopened.detach(materialize_history=True)

    detached_final = _authority(detached)
    _assert_authority("materializing detach", detached_final, control_final)

    detached_checkpoint = checkpoint.dumps(detached)
    detached_restored = checkpoint.loads(detached_checkpoint)
    detached_checkpoint_final = _authority(detached_restored)
    _assert_authority(
        "detached checkpoint roundtrip",
        detached_checkpoint_final,
        control_final,
    )

    with open_lazy_world_session(relocated, rules_id=rules_id, paged_household_members=paged_households) as backup:
        backup_total = _authority(backup.world)
        _assert_authority("relocated backup", backup_total, control_total)

    summary = {
        "seed": seed,
        "pre_years": pre_years,
        "continuation_years": continuation_years,
        "reopen_years": reopen_years,
        "total_year": total_years,
        "final_year": final_years,
        "checkpoint_schema": checkpoint.CHECKPOINT_SCHEMA,
        "rules_id": rules_id,
        "control_total_digest": control_total["digest"],
        "control_final_digest": control_final["digest"],
        "events_total": len(control_final["events"]),
        "last_event_id": (
            control_final["events"][-1][0] if control_final["events"] else None
        ),
        "cold_file_bytes": cold.stat().st_size,
        "lazy_file_bytes": lazy.stat().st_size,
        "relocated_file_bytes": relocated.stat().st_size,
        "cold_sha256": hashlib.sha256(cold.read_bytes()).hexdigest(),
        "lazy_sha256": hashlib.sha256(lazy.read_bytes()).hexdigest(),
        "relocated_sha256": hashlib.sha256(relocated.read_bytes()).hexdigest(),
        "checkpoint_bytes": len(checkpoint_bytes),
        "detached_checkpoint_bytes": len(detached_checkpoint),
        "open_io": open_io,
        "first_continuation_simulation_seconds": simulation_seconds,
        "first_save_io": save_io,
        "first_full_audit_io": total_audit_io,
        "second_continuation_simulation_seconds": reopen_simulation_seconds,
        "second_save_io": reopen_save_io,
        "second_full_audit_io": final_audit_io,
        "fixture_creation": {
            "cold": cold_result,
            "lazy": conversion_result,
        },
        "timings": timings,
        "passed": True,
    }
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=843000)
    parser.add_argument("--pre-years", type=int, default=3)
    parser.add_argument("--continuation-years", type=int, default=4)
    parser.add_argument("--reopen-years", type=int, default=3)
    parser.add_argument("--rules-id", default=DEFAULT_RULES)
    parser.add_argument("--workdir")
    parser.add_argument("--output")
    parser.add_argument("--paged-households", action="store_true")
    parser.add_argument("--counted-households", action="store_true")
    parser.add_argument("--native-graph-buckets", action="store_true")
    args = parser.parse_args()

    if min(args.pre_years, args.continuation_years, args.reopen_years) < 0:
        raise SystemExit("year counts must be non-negative")

    if args.workdir:
        summary = run(
            args.seed,
            args.pre_years,
            args.continuation_years,
            args.reopen_years,
            args.workdir,
            args.rules_id,
            paged_households=args.paged_households,
            counted_households=args.counted_households,
            native_graph_buckets=args.native_graph_buckets,
        )
    else:
        with tempfile.TemporaryDirectory(prefix="ate-p5-") as directory:
            summary = run(
                args.seed,
                args.pre_years,
                args.continuation_years,
                args.reopen_years,
                directory,
                args.rules_id,
                paged_households=args.paged_households,
                counted_households=args.counted_households,
                native_graph_buckets=args.native_graph_buckets,
            )

    rendered = json.dumps(summary, indent=2, sort_keys=True)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
