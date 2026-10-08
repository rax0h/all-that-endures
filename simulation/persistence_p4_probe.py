from __future__ import annotations

import argparse
import gc
import json
import os
import platform
import sqlite3
import sys
import tempfile
import time
import tracemalloc
from dataclasses import asdict
from pathlib import Path

from ate_sim.core import Person, World
from ate_sim.engine import Simulation
from ate_sim.history_archive import export_archive
from ate_sim.incremental_store import TransactionalStore
from ate_sim.magic_resources import MagicResource, MagicResourceState
from ate_sim.persistence_adapters import (
    META,
    RECORD_SCHEMA,
    SCHEMA,
    WorldCodec,
)
from ate_sim.persistence_session import open_world_session, write_cold_snapshot
from ate_sim.record_index import RecordTable
from ate_sim.resource_offers import ordered_resource_offers
from ate_sim.worldgen import generate_world


RULES = "stage-0.5-p4-preparation-probe"
PROBE_SCHEMA = 1
ACTIVE_PEOPLE = 32
OFFER_ACTIVE_PEOPLE = 8
OFFER_PUBLIC_IDS = (1, 2, 3, 4)


def _window(call):
    gc.collect()
    tracemalloc.start()
    base = tracemalloc.get_traced_memory()[0]
    started = time.perf_counter()
    value = call()
    seconds = time.perf_counter() - started
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return value, {
        "seconds": seconds,
        "peak_bytes": max(0, peak - base),
        "retained_bytes": max(0, current - base),
    }


def _io(value):
    return {
        "payload_reads": value.payload_reads,
        "payload_read_bytes": value.payload_read_bytes,
        "payload_writes": value.payload_writes,
        "payload_write_bytes": value.payload_write_bytes,
    }


def _store_namespace_stats(path):
    with TransactionalStore.open(
        path,
        codec=WorldCodec(identity_links_recorded=True),
        expected_simulation_schema=SCHEMA,
        expected_rules_id=RULES,
    ) as store:
        with store.read_transaction():
            manifest = store.read_record(
                META, "manifest", expected_record_schema=RECORD_SCHEMA
            )
            record_rows = {
                namespace: (count, payload_bytes or 0)
                for namespace, count, payload_bytes in store.db.execute(
                    "SELECT namespace,COUNT(*),SUM(LENGTH(payload)) "
                    "FROM records GROUP BY namespace"
                )
            }
            segment_rows = {
                namespace: (count, payload_bytes or 0)
                for namespace, count, payload_bytes in store.db.execute(
                    "SELECT namespace,COUNT(*),SUM(LENGTH(payload)) "
                    "FROM segments GROUP BY namespace"
                )
            }
            membership_rows = {
                namespace: (count, payload_bytes or 0)
                for namespace, count, payload_bytes in store.db.execute(
                    "SELECT namespace,COUNT(*),"
                    "SUM(LENGTH(index_value)+LENGTH(record_key)) "
                    "FROM query_membership GROUP BY namespace"
                )
            }
            identity_rows = store.db.execute(
                "SELECT COUNT(*) FROM records WHERE namespace='world_identity_links'"
            ).fetchone()[0]
            collections = {}
            for namespace, description in manifest["collections"].items():
                records, record_bytes = record_rows.get(namespace, (0, 0))
                segments, segment_bytes = segment_rows.get(namespace, (0, 0))
                memberships, membership_bytes = membership_rows.get(
                    namespace, (0, 0)
                )
                collections[namespace] = {
                    "kind": description[0],
                    "logical_count": description[1],
                    "logical_chunks": description[2],
                    "record_rows": records,
                    "record_payload_bytes": record_bytes,
                    "segment_rows": segments,
                    "segment_payload_bytes": segment_bytes,
                    "query_membership_rows": memberships,
                    "query_membership_key_bytes": membership_bytes,
                }
        return {
            "file_bytes": Path(path).stat().st_size,
            "identity_link_rows": identity_rows,
            "collections": collections,
        }


def build_people_fixture(inactive_count, *, active_count=ACTIVE_PEOPLE):
    if inactive_count < 1 or active_count < 1:
        raise ValueError("people fixture needs active and inactive records")
    world = World(740000 + inactive_count)
    for pid in range(1, active_count + 1):
        world.people[pid] = Person(
            pid,
            -30,
            1,
            1,
            alive=True,
            age=30,
            wealth=float(pid % 7),
            curiosity=0.45,
            inhibition=0.45,
        )
    for offset in range(inactive_count):
        pid = active_count + 1 + offset
        world.people[pid] = Person(
            pid,
            -80,
            1,
            1,
            alive=False,
            age=80,
            wealth=float(offset % 5),
            curiosity=0.35,
            inhibition=0.55,
        )
    world.next_person = active_count + inactive_count + 1

    # One fixed current alias group exercises current identity bookkeeping while
    # remaining independent of archive size.
    shared_wallet = {"iron": 7}
    world.currency.wallets[-1] = shared_wallet
    world.currency.wallets[-2] = shared_wallet
    return world


def _recordtable_index_stats(value):
    if not isinstance(value, RecordTable):
        return {}
    result = {}
    for key, row in getattr(value, "_indexes", {}).items():
        fields, buckets, previous, dirty = row
        result["|".join(fields)] = {
            "bucket_count": len(buckets),
            "bucket_members": sum(len(ids) for ids in buckets.values()),
            "previous_entries": len(previous),
            "dirty_entries": len(dirty),
        }
    return result


def _cache_size(value, name):
    cached = value.__dict__.get(name)
    if cached is None:
        return 0
    try:
        return len(cached)
    except TypeError:
        return 1


def _session_state(session):
    identity = (
        {}
        if session._identity_index is None
        else session._identity_index.diagnostics()
    )
    root_sizes = {}
    for namespace, value in session._root_containers.items():
        try:
            root_sizes[namespace] = len(value)
        except TypeError:
            pass
    world = session.world
    return {
        "people_resident": len(world.people),
        "people_container_type": type(world.people).__name__,
        "memo_entries": len(session._memo),
        "memo_reverse_entries": len(session._memo_reverse),
        "bound_ids": len(session._bound_ids),
        "baseline_ordinal_entries": sum(
            len(values) for values in session._baseline_ordinals.values()
        ),
        "cold_persisted_key_entries": sum(
            len(values) for values in session._cold_persisted_keys.values()
        ),
        "initial_identity_links": len(session._initial_links),
        "committed_identity_targets": len(session._committed_identity_targets),
        "live_identity_targets": len(session._live_identity_targets),
        "identity_index": identity,
        "root_sizes": root_sizes,
        "people_indexes": _recordtable_index_stats(world.people),
        "cache_occupancy": {
            "world_living": _cache_size(world, "_living_cache"),
            "social_relationships": _cache_size(
                world.social, "_relationships"
            ),
            "social_partnership_index": _cache_size(
                world.social, "_partnership_index"
            ),
            "community_membership": _cache_size(
                world.communities, "_membership_index"
            ),
            "resource_inventory": _cache_size(
                world.magic_resources, "_query_inventory"
            ),
            "resource_selection": _cache_size(
                world.magic_resources, "_query_selection"
            ),
            "resource_offer_books": _cache_size(
                world.magic_resources, "_query_offer_books"
            ),
            "material_selection": _cache_size(
                world.materials, "_selection_index"
            ),
            "material_rank_heaps": _cache_size(
                world.materials, "_rank_heaps"
            ),
            "material_selection_ids": _cache_size(
                world.materials, "_selection_ids"
            ),
            "advancement_rank": _cache_size(
                world.advancement, "_rank_cache"
            ),
        },
    }


def _operation(session, call):
    session.reset_diagnostics()
    value, allocation = _window(call)
    return {
        "allocation": allocation,
        "io": _io(session.diagnostics()),
        "value": value,
    }


def measure_people_case(base, inactive_count, *, active_count=ACTIVE_PEOPLE):
    base = Path(base)
    store_path = base / f"people-{inactive_count}.sqlite"
    archive_path = base / f"people-{inactive_count}-archive.sqlite"

    fixture = build_people_fixture(
        inactive_count, active_count=active_count
    )
    fixture_definition = {
        "inactive_people": inactive_count,
        "active_people": active_count,
        "total_people": inactive_count + active_count,
        "fixed_wallet_aliases": [-1, -2],
        "events": 0,
    }

    bootstrap, import_allocation = _window(
        lambda: write_cold_snapshot(
            fixture, store_path, rules_id=RULES
        )
    )
    namespace_stats = _store_namespace_stats(store_path)
    del fixture
    gc.collect()

    session, open_allocation = _window(
        lambda: open_world_session(store_path, rules_id=RULES)
    )
    open_io = _io(session.diagnostics())
    result = {
        "fixture": fixture_definition,
        "import": {
            "allocation": import_allocation,
            "reported": bootstrap,
            "namespace_stats": namespace_stats,
        },
        "open": {
            "allocation": open_allocation,
            "io": open_io,
            "state": _session_state(session),
        },
    }

    try:
        generation = session.generation
        noop = _operation(session, session.save)
        noop["generation_before"] = generation
        noop["generation_after"] = session.generation
        result["no_op_save"] = noop

        def first_query():
            with session.world.current_people_scope():
                people = session.world.current_people()
                return {
                    "ids": [person.id for person in people],
                    "living_cache_entries": len(
                        session.world.__dict__.get("_living_cache", ())
                    ),
                }

        first = _operation(session, first_query)
        first["source_rows_required_by_current_RecordTable"] = len(
            session.world.people
        )
        first["state_after"] = _session_state(session)
        result["first_current_query"] = first

        repeat = _operation(
            session,
            lambda: [person.id for person in session.world.current_people()],
        )
        repeat["people_index_before"] = _recordtable_index_stats(
            session.world.people
        )
        result["repeat_current_query"] = repeat

        archived_id = active_count + inactive_count
        point_world = _operation(
            session,
            lambda: session.world.people[archived_id].id,
        )
        result["resident_point_access"] = point_world

        point_store = _operation(
            session,
            lambda: session.store.read_record(
                "world.people",
                archived_id,
                expected_record_schema=RECORD_SCHEMA,
            )[1].id,
        )
        result["checked_store_point_access"] = point_store

        reactivated_id = active_count + 1
        session.reset_changed_member_work()
        reactivated = session.world.people[reactivated_id]
        reactivated.alive = True
        before_overlay = _recordtable_index_stats(session.world.people)
        overlay = _operation(
            session,
            lambda: [person.id for person in session.world.current_people()],
        )
        overlay["index_before_query"] = before_overlay
        overlay["state_after"] = _session_state(session)
        overlay["reactivated_id"] = reactivated_id
        overlay["changed_member_work"] = session.changed_member_work
        result["reactivation_query"] = overlay

        before_save = session.generation
        local_save = _operation(session, session.save)
        local_save["generation_before"] = before_save
        local_save["generation_after"] = session.generation
        local_save["dirty_after"] = sorted(
            (namespace, repr(key)) for namespace, key in session.dirty
        )
        local_save["state_after"] = _session_state(session)
        result["one_local_edit_save"] = local_save

        audit = _operation(session, session.store.verify_all)
        result["explicit_full_audit"] = audit

        archive = _operation(
            session,
            lambda: export_archive(session.world, archive_path),
        )
        archive["archive_bytes"] = archive["value"]["archive_bytes"]
        archive["logical_sha256"] = archive["value"]["logical_sha256"]
        result["explicit_archive"] = archive

        result["pre_close_state"] = _session_state(session)
        _ignored, close_allocation = _window(session.close)
        result["close"] = {
            "allocation": close_allocation,
            "store_closed": session.store._closed,
            "session_active": session._active,
        }
    finally:
        session.close()

    return result


def build_offer_fixture(
    irrelevant_count, *, active_people=OFFER_ACTIVE_PEOPLE
):
    world = World(750000 + irrelevant_count)
    for pid in range(1, active_people + 1):
        world.people[pid] = Person(
            pid,
            -25,
            1,
            1,
            alive=True,
            age=25,
            wealth=20.0,
            curiosity=0.2,
            inhibition=0.7,
        )
    world.next_person = active_people + 1

    public = (
        (1, "essence", "fire"),
        (2, "essence", "water"),
        (3, "awakening_stone", "stone-a"),
        (4, "awakening_stone", "stone-b"),
    )
    for rid, kind, key in public:
        resource = MagicResource(
            id=rid,
            kind=kind,
            key=key,
            rarity="Common",
            location=1,
            owner_kind="settlement",
            owner_id=1,
            created_year=0,
        )
        world.magic_resources.resources[rid] = resource
        world.magic_resources._index_add(resource)

    # Old/consumed resources remain authoritative records but are deliberately
    # irrelevant to current offers and absent from owner_index.
    for offset in range(irrelevant_count):
        rid = 100000 + offset
        world.magic_resources.resources[rid] = MagicResource(
            id=rid,
            kind="essence",
            key=f"old-{offset % 7}",
            rarity="Common",
            location=1,
            owner_kind=None,
            owner_id=None,
            created_year=-100,
            consumed_year=-1,
            consumed_by=1,
            consumed_event=None,
        )
    world.magic_resources.next_id = 100000 + irrelevant_count
    return world


def _offer_cache_state(world):
    resources = world.magic_resources
    offer = resources.__dict__.get("_query_offer_books")
    rows = 0
    members = 0
    if offer is not None:
        for book in offer.books.values():
            rows += sum(len(values) for values in book.rows.values())
            members += sum(len(values) for values in book.members.values())
    return {
        "resources_resident": len(resources.resources),
        "owner_index_buckets": len(resources.owner_index),
        "owner_index_ids": sum(
            len(ids) for ids in resources.owner_index.values()
        ),
        "inventory_cache_keys": _cache_size(resources, "_query_inventory"),
        "selection_cache_keys": _cache_size(resources, "_query_selection"),
        "offer_settlements": 0 if offer is None else len(offer.books),
        "offer_rows": rows,
        "offer_members": members,
    }


def measure_offer_case(irrelevant_count):
    world = build_offer_fixture(irrelevant_count)
    people = tuple(world.people[pid] for pid in sorted(world.people))
    original = MagicResourceState.inventory
    work = {"calls": 0, "candidate_ids": 0}

    def counted_inventory(self, owner_kind, owner_id, kind=None):
        work["calls"] += 1
        work["candidate_ids"] += len(
            self.owner_index.get((owner_kind, owner_id), ())
        )
        return original(self, owner_kind, owner_id, kind)

    MagicResourceState.inventory = counted_inventory
    try:
        work.update(calls=0, candidate_ids=0)
        first, first_allocation = _window(
            lambda: ordered_resource_offers(world, 1, people)
        )
        first_work = dict(work)
        first_ids = {
            kind: [resource.id for resource in resources]
            for kind, resources in first.items()
        }
        first_cache = _offer_cache_state(world)

        work.update(calls=0, candidate_ids=0)
        repeat, repeat_allocation = _window(
            lambda: ordered_resource_offers(world, 1, people)
        )
        repeat_work = dict(work)
        repeat_ids = {
            kind: [resource.id for resource in resources]
            for kind, resources in repeat.items()
        }
        repeat_cache = _offer_cache_state(world)
    finally:
        MagicResourceState.inventory = original

    return {
        "fixture": {
            "irrelevant_consumed_resources": irrelevant_count,
            "active_people": len(people),
            "public_offer_ids": list(OFFER_PUBLIC_IDS),
        },
        "first_query": {
            "allocation": first_allocation,
            "inventory_work": first_work,
            "offer_ids": first_ids,
            "cache": first_cache,
        },
        "repeat_query": {
            "allocation": repeat_allocation,
            "inventory_work": repeat_work,
            "offer_ids": repeat_ids,
            "cache": repeat_cache,
        },
    }


def independent_control(base):
    base = Path(base)
    seed = 991337
    source = Simulation(
        generate_world(seed, width=8, height=6, settlements=2, mature=False)
    ).run(2)
    control = Simulation(
        generate_world(seed, width=8, height=6, settlements=2, mature=False)
    ).run(2)
    initial_source = source.digest()
    initial_control = control.digest()
    if initial_source != initial_control:
        raise AssertionError("independent generated controls disagree")

    path = base / "independent-control.sqlite"
    write_cold_snapshot(source, path, rules_id=RULES)
    namespace_stats = _store_namespace_stats(path)
    del source
    gc.collect()

    session = open_world_session(path, rules_id=RULES)
    try:
        opened = session.world.digest()
        if opened != initial_control:
            raise AssertionError("cold open disagrees with independent control")

        Simulation(session.world).run(1)
        Simulation(control).run(1)
        after_one = session.world.digest()
        control_one = control.digest()
        if after_one != control_one:
            raise AssertionError("continued cold World diverged")

        session.save()
        session.close()
        session = open_world_session(path, rules_id=RULES)
        reopened = session.world.digest()
        if reopened != control_one:
            raise AssertionError("save/reopen diverged")

        Simulation(session.world).run(1)
        Simulation(control).run(1)
        final_cold = session.world.digest()
        final_control = control.digest()
        if final_cold != final_control:
            raise AssertionError("post-reopen continuation diverged")

        cold_events = [
            (
                event.id,
                event.year,
                event.kind,
                event.layer.value,
                event.causes,
                event.__dict__.get("_sealed", False),
            )
            for event in session.world.events
        ]
        control_events = [
            (
                event.id,
                event.year,
                event.kind,
                event.layer.value,
                event.causes,
                event.__dict__.get("_sealed", False),
            )
            for event in control.events
        ]
        if cold_events != control_events:
            raise AssertionError("future event sequence diverged")

        return {
            "seed": seed,
            "initial_years": 2,
            "continued_before_save": 1,
            "continued_after_reopen": 1,
            "initial_digest": initial_control,
            "after_one_digest": control_one,
            "final_digest": final_control,
            "event_count": len(cold_events),
            "next_event": session.world.next_event,
            "namespace_stats": namespace_stats,
        }
    finally:
        session.close()


def run_probe(sizes, *, source_sha):
    with tempfile.TemporaryDirectory(prefix="ate-p4-probe-") as directory:
        root = Path(directory)
        people = {
            str(size): measure_people_case(root, size)
            for size in sizes
        }
        offers = {
            str(size): measure_offer_case(size)
            for size in sizes
        }
        control = independent_control(root)

    return {
        "schema": PROBE_SCHEMA,
        "source_sha": source_sha,
        "runtime": {
            "python": sys.version.split()[0],
            "sqlite": sqlite3.sqlite_version,
            "platform": platform.platform(),
        },
        "measurement_method": {
            "fixture_setup": "outside tracemalloc operation windows",
            "allocation": (
                "tracemalloc incremental peak/retained bytes; gc.collect "
                "before each window"
            ),
            "io": (
                "TransactionalStore checked payload read/write counters; "
                "SQL namespace row/byte counts are diagnostic only"
            ),
            "wall_time": "time.perf_counter diagnostic, not an acceptance bound",
        },
        "fixtures": {
            "people": {
                "sizes": list(sizes),
                "active_people": ACTIVE_PEOPLE,
                "growth_axis": "inactive but still mutable Person records",
                "fixed_edit": "reactivate person id 33",
                "fixed_alias": "wallet ids -1/-2 share one mutable dict",
            },
            "offers": {
                "sizes": list(sizes),
                "active_people": OFFER_ACTIVE_PEOPLE,
                "public_offer_ids": list(OFFER_PUBLIC_IDS),
                "growth_axis": "consumed MagicResource records absent from owner_index",
            },
            "independent_control": {
                "seed": 991337,
                "worldgen": {
                    "width": 8,
                    "height": 6,
                    "settlements": 2,
                    "mature": False,
                },
            },
        },
        "people_cases": people,
        "offer_cases": offers,
        "independent_control": control,
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--sizes", nargs="+", type=int, default=[1000, 10000])
    parser.add_argument("--output")
    parser.add_argument(
        "--source-sha",
        default=os.environ.get("GITHUB_SHA", "unknown"),
    )
    args = parser.parse_args(argv)
    if any(size < 1 for size in args.sizes):
        raise SystemExit("sizes must be positive")
    result = run_probe(tuple(args.sizes), source_sha=args.source_sha)
    encoded = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        Path(args.output).write_text(encoded + "\n", encoding="utf-8")
    print("P4_BASELINE_JSON_BEGIN")
    print(encoded)
    print("P4_BASELINE_JSON_END")


if __name__ == "__main__":
    main()
