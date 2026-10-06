from __future__ import annotations

import argparse
from collections import Counter
import gc
import hashlib
import json
import os
from pathlib import Path
import time

from ate_sim.engine import Simulation
from ate_sim.persistence_adapters import SCHEMA
from ate_sim.persistence_lazy import convert_cold_to_lazy, open_lazy_world_session
from ate_sim.persistence_session import write_cold_snapshot
from ate_sim.worldgen import generate_world
from long_history_scaling import current_audit
from run_long_history import snapshot


DEFAULT_RULES = "stage-0-5-p5-long-v1"


def _io(diag):
    return {
        "payload_reads": diag.payload_reads,
        "payload_read_bytes": diag.payload_read_bytes,
        "payload_writes": diag.payload_writes,
        "payload_write_bytes": diag.payload_write_bytes,
    }


def _counters(world):
    result = {
        "next_person": world.next_person,
        "next_household": world.next_household,
        "next_settlement": world.next_settlement,
        "next_event": world.next_event,
    }
    for name in (
        "economy", "knowledge", "culture", "communities", "transmission",
        "infrastructure", "magic_resources", "institutions", "metaphysics",
        "divinity", "materials", "warfare", "society_accountability",
        "threat_ecology",
    ):
        state = getattr(world, name)
        for field, value in sorted(state.__dict__.items()):
            if field.startswith("next_") and type(value) is int:
                result[f"{name}.{field}"] = value
    return result


def _digest(world):
    started = time.perf_counter()
    value = world.digest()
    return value, time.perf_counter() - started


def _compact_working_set(diag):
    result = {}
    for name, value in diag.items():
        if isinstance(value, dict):
            keep = {}
            for key, item in value.items():
                if (
                    key.startswith("logical_")
                    or key.startswith("resident_")
                    or key.startswith("dirty_")
                    or key.startswith("removed_")
                    or key.startswith("new_")
                    or key.startswith("reinserted_")
                    or key.endswith("_payload_loads")
                    or key in {"clean_cache_entries", "clean_cache_limit", "live_objects",
                               "live_incarnations", "occurrences"}
                ):
                    if isinstance(item, (str, int, float, bool)) or item is None:
                        keep[key] = item
            if keep:
                result[name] = keep
        elif name in (
            "eager_dirty_owners", "eager_deleted_owners", "eager_bound_objects",
            "cross_boundary_identity_links", "event_disk_events",
            "event_pending_chunks", "event_tail_events",
        ):
            result[name] = value
    return result


def _audit(world):
    started = time.perf_counter()
    state = current_audit(world)
    if state["state_violations"]:
        raise AssertionError(f"current-state violations: {state['state_violations'][:5]}")
    if any(state["currency_imbalance"].values()):
        raise AssertionError(f"currency imbalance: {state['currency_imbalance']}")

    seen = set()
    previous_id = 0
    previous_year = -1
    chronology_violations = 0
    causal_violations = 0
    kinds = Counter()
    irons = Counter()
    for event in world.events:
        if event.id <= previous_id or event.year < previous_year:
            chronology_violations += 1
        for cause in event.causes:
            if cause >= event.id or cause not in seen:
                causal_violations += 1
        seen.add(event.id)
        previous_id = event.id
        previous_year = event.year
        kinds[event.kind] += 1
        if (
            event.kind == "rank_advanced"
            and event.data.get("from_rank") == 0
            and event.data.get("to_rank") == 1
        ):
            irons[event.year] += 1
    if chronology_violations or causal_violations:
        raise AssertionError(
            f"history integrity failed: chronology={chronology_violations}, "
            f"causal={causal_violations}"
        )

    bad_lot_origins = sum(
        lot.origin_event not in seen for lot in world.materials.lots.values()
    )
    lot_ids = set(world.materials.lots)
    bad_item_origins = 0
    bad_item_materials = 0
    for item in world.materials.items.values():
        bad_item_origins += item.origin_event not in seen
        bad_item_materials += sum(material not in lot_ids for material in item.materials)
    if bad_lot_origins or bad_item_origins or bad_item_materials:
        raise AssertionError(
            "material provenance failed: "
            f"lots={bad_lot_origins}, items={bad_item_origins}, "
            f"material_refs={bad_item_materials}"
        )

    report = json.loads(json.dumps(snapshot(world, include_digest=False), sort_keys=True))
    threat_words = ("monster", "threat", "war", "raid", "attack", "flood", "drought", "fire", "storm")
    threat_events = {
        kind: count for kind, count in sorted(kinds.items())
        if any(word in kind for word in threat_words)
    }
    economy_names = (
        "trade_exchange", "material_purchased", "magic_resource_purchased",
        "magic_resource_transferred", "inheritance", "property_inherited",
        "society_apprentice_work", "society_change_exchanged",
    )
    economy_events = {name: kinds[name] for name in economy_names if kinds[name]}

    return {
        "year": world.year,
        "event_count": len(seen),
        "last_event_id": previous_id if seen else None,
        "chronology_violations": chronology_violations,
        "causal_violations": causal_violations,
        "currency_imbalance": state["currency_imbalance"],
        "new_irons_total": sum(irons.values()),
        "new_irons_by_year": dict(sorted(irons.items())),
        "threat_events": threat_events,
        "economy_events": economy_events,
        "provenance_violations": {
            "lot_origins": bad_lot_origins,
            "item_origins": bad_item_origins,
            "item_material_refs": bad_item_materials,
        },
        "snapshot": report,
        "audit_seconds": time.perf_counter() - started,
    }


def _control(seed, milestones):
    world = generate_world(seed)
    sim = Simulation(world)
    rows = {}
    for mark in milestones:
        started = time.perf_counter()
        sim.run(mark - world.year)
        simulation_seconds = time.perf_counter() - started
        digest, digest_seconds = _digest(world)
        audit = _audit(world)
        rows[str(mark)] = {
            "simulation_seconds": simulation_seconds,
            "digest": digest,
            "digest_seconds": digest_seconds,
            "counters": _counters(world),
            "audit": audit,
        }
    return rows


def run(seed, milestones, bootstrap_year, workdir, rules_id, product_sha, workflow_sha):
    milestones = tuple(sorted(set(int(value) for value in milestones)))
    if not milestones or milestones[0] <= bootstrap_year:
        raise ValueError("milestones must be strictly after bootstrap year")
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    cold = workdir / "p5-long-cold.sqlite"
    lazy = workdir / "p5-long-lazy.sqlite"
    restore = workdir / "p5-long-restore.sqlite"
    for path in (cold, lazy, restore):
        if path.exists():
            path.unlink()

    control_started = time.perf_counter()
    controls = _control(seed, milestones)
    control_seconds = time.perf_counter() - control_started
    gc.collect()

    source = generate_world(seed)
    started = time.perf_counter()
    Simulation(source).run(bootstrap_year)
    bootstrap_simulation_seconds = time.perf_counter() - started
    source_digest, source_digest_seconds = _digest(source)

    cold_result = write_cold_snapshot(source, cold, rules_id=rules_id)
    cold_hash_before = hashlib.sha256(cold.read_bytes()).hexdigest()
    conversion_result = convert_cold_to_lazy(cold, lazy, rules_id=rules_id)
    cold_hash_after = hashlib.sha256(cold.read_bytes()).hexdigest()
    if cold_hash_before != cold_hash_after:
        raise AssertionError("cold source changed during lazy conversion")
    if source.digest() != source_digest:
        raise AssertionError("bootstrap persistence mutated source World")
    del source
    gc.collect()

    lazy_rows = {}
    session = open_lazy_world_session(lazy, rules_id=rules_id)
    try:
        if session.world.year != bootstrap_year:
            raise AssertionError("lazy bootstrap opened at wrong year")
        for mark in milestones:
            session.store.reset_diagnostics()
            started = time.perf_counter()
            Simulation(session.world).run(mark - session.world.year)
            simulation_seconds = time.perf_counter() - started
            simulation_io = _io(session.store.diagnostics())

            session.store.reset_diagnostics()
            live_digest_before_save, live_digest_seconds = _digest(
                session.world
            )
            control_before_save = controls[str(mark)]["digest"]
            print(
                "LIVE_BEFORE_SAVE",
                mark,
                live_digest_before_save,
                "MATCH",
                live_digest_before_save == control_before_save,
                "DIGEST_SECONDS",
                live_digest_seconds,
            )

            started = time.perf_counter()
            generation = session.save()
            save_seconds = time.perf_counter() - started
            save_io = _io(session.store.diagnostics())
            working_before_audit = _compact_working_set(session.diagnostics())

            session.store.reset_diagnostics()
            audit = _audit(session.world)
            audit_io = _io(session.store.diagnostics())
            working_after_audit = _compact_working_set(session.diagnostics())
            live_counters = _counters(session.world)

            session.close()
            session = open_lazy_world_session(lazy, rules_id=rules_id)
            session.store.reset_diagnostics()
            reopened_digest, reopened_digest_seconds = _digest(session.world)
            reopened_digest_io = _io(session.store.diagnostics())
            control = controls[str(mark)]
            if reopened_digest != control["digest"]:
                raise AssertionError(
                    f"year {mark}: P4 digest mismatch "
                    f"{reopened_digest} != {control['digest']}"
                )
            if live_counters != control["counters"]:
                raise AssertionError(f"year {mark}: P4 counter mismatch")
            if audit["event_count"] != control["audit"]["event_count"]:
                raise AssertionError(f"year {mark}: P4 event-count mismatch")
            if audit["last_event_id"] != control["audit"]["last_event_id"]:
                raise AssertionError(f"year {mark}: P4 last-event mismatch")

            lazy_rows[str(mark)] = {
                "generation": generation,
                "simulation_seconds": simulation_seconds,
                "simulation_io": simulation_io,
                "save_seconds": save_seconds,
                "save_io": save_io,
                "audit": audit,
                "audit_io": audit_io,
                "working_set_before_audit": working_before_audit,
                "working_set_after_audit": working_after_audit,
                "reopen_digest": reopened_digest,
                "reopen_digest_seconds": reopened_digest_seconds,
                "reopen_digest_io": reopened_digest_io,
                "matches_control": True,
            }

        started = time.perf_counter()
        session.store.backup(restore)
        backup_seconds = time.perf_counter() - started
    finally:
        if session._active:
            session.close()

    with open_lazy_world_session(restore, rules_id=rules_id) as restored:
        restore_generation = restored.pin.captured_head
        restored_digest, restore_digest_seconds = _digest(restored.world)
        final_control = controls[str(milestones[-1])]
        if restored_digest != final_control["digest"]:
            raise AssertionError("durable restore artifact digest mismatch")
        if _counters(restored.world) != final_control["counters"]:
            raise AssertionError("durable restore artifact counter mismatch")
        restore_year = restored.world.year

    restore_sha256 = hashlib.sha256(restore.read_bytes()).hexdigest()
    summary = {
        "schema": 1,
        "passed": True,
        "seed": seed,
        "simulation_schema": SCHEMA,
        "rules_id": rules_id,
        "bootstrap_year": bootstrap_year,
        "milestones": milestones,
        "product_sha": product_sha,
        "workflow_sha": workflow_sha,
        "control_wall_seconds": control_seconds,
        "bootstrap_simulation_seconds": bootstrap_simulation_seconds,
        "bootstrap_digest": source_digest,
        "bootstrap_digest_seconds": source_digest_seconds,
        "cold_source_preserved": cold_hash_before == cold_hash_after,
        "cold_result": cold_result,
        "conversion_result": conversion_result,
        "control": controls,
        "p4": lazy_rows,
        "restore_artifact": {
            "path": str(restore),
            "year": restore_year,
            "generation": restore_generation,
            "bytes": restore.stat().st_size,
            "sha256": restore_sha256,
            "digest": restored_digest,
            "digest_seconds": restore_digest_seconds,
            "backup_seconds": backup_seconds,
            "restore_command": (
                "PYTHONPATH=simulation:. python -c "
                f"'from ate_sim.persistence_lazy import open_lazy_world_session; "
                f"s=open_lazy_world_session(\"{restore.name}\", rules_id=\"{rules_id}\"); "
                "print(s.world.year, s.world.digest()); s.close()'"
            ),
        },
    }
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=843000)
    parser.add_argument("--milestones", nargs="+", type=int, default=[100, 500, 1000])
    parser.add_argument("--bootstrap-year", type=int, default=3)
    parser.add_argument("--rules-id", default=DEFAULT_RULES)
    parser.add_argument("--workdir", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--product-sha", default="")
    parser.add_argument("--workflow-sha", default=os.environ.get("GITHUB_SHA", ""))
    args = parser.parse_args()

    summary = run(
        args.seed,
        args.milestones,
        args.bootstrap_year,
        args.workdir,
        args.rules_id,
        args.product_sha,
        args.workflow_sha,
    )
    rendered = json.dumps(summary, indent=2, sort_keys=True)
    Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
