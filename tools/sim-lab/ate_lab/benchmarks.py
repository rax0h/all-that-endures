"""Read benchmark files that already exist. This module never runs the 1,000-year gate."""

from __future__ import annotations

import json
from pathlib import Path

from .paths import repo_root
from .values import calculated, documented, measured, unavailable

GATE_SECONDS = 120
GATE_SEED = 843000
GATE_YEARS = 1000


def documented_gate(root: Path | None = None) -> dict:
    root = root or repo_root()
    document = root / "simulation" / "PERFORMANCE.md"
    if not document.is_file():
        return unavailable("simulation/PERFORMANCE.md is not in this install")
    text = document.read_text(encoding="utf-8")
    if "120-second" not in text and "120 second" not in text:
        return unavailable("PERFORMANCE.md does not currently state a 120-second benchmark")
    return documented(
        GATE_SECONDS,
        "simulation/PERFORMANCE.md states the enforced 120-second simulation benchmark "
        "for the unprofiled seed-843000, 1,000-year run. Not recomputed here.",
        seed=GATE_SEED,
        years=GATE_YEARS,
        metric="simulation_seconds",
        comparison="<=",
    )


def _optional(record: dict, key: str, method: str) -> dict:
    if key not in record or record[key] is None:
        return unavailable(f"{key} is not in this record")
    return measured(record[key], method)


def _gate_comparison(benchmark: dict) -> dict:
    seconds = benchmark.get("simulation_seconds")
    years = benchmark.get("years")
    seed = benchmark.get("seed")
    if seconds is None or years != GATE_YEARS or seed != GATE_SEED:
        return unavailable(
            "the documented 120-second gate applies to seed 843000 and 1,000 unprofiled years; "
            "this record is not that run"
        )
    return calculated(
        float(seconds) <= GATE_SECONDS,
        "recorded simulation_seconds compared with the documented 120-second threshold. "
        "This does not replace a performance_passed flag stored by the harness.",
    )


def _normalize_buckets(buckets) -> list[dict]:
    if not isinstance(buckets, list):
        return []
    rows = []
    for bucket in buckets:
        if not isinstance(bucket, dict):
            continue
        collections = bucket.get("collections") if isinstance(bucket.get("collections"), dict) else {}
        rows.append({
            "first_year": bucket.get("first_year"),
            "last_year": bucket.get("last_year"),
            "simulation_seconds": _optional(bucket, "simulation_seconds", "scaling bucket simulation_seconds stored in the file"),
            "seconds_per_year": _optional(bucket, "seconds_per_year", "scaling bucket seconds_per_year stored in the file"),
            "living": measured(collections["living"], "collections.living stored on this bucket")
            if "living" in collections else unavailable("collections.living is not on this bucket"),
            "subsystem_seconds": measured(bucket["subsystem_seconds"], "subsystem_seconds stored on this bucket")
            if isinstance(bucket.get("subsystem_seconds"), dict) else unavailable("subsystem_seconds is not on this bucket"),
        })
    return rows


def _snapshot_highlights(snapshot) -> dict:
    if not isinstance(snapshot, dict):
        return {"available": False, "reason": "no snapshot object in this record"}
    wanted = (
        "year", "alive", "people_total", "living_households", "households_total", "events_total",
        "relationships", "essence_users_living", "completed_loadouts", "magic_resources_total",
        "magic_resources_available", "material_lots_total", "crafted_items_total", "max_lineage_depth",
    )
    highlights = {}
    for key in wanted:
        if key in snapshot:
            highlights[key] = measured(snapshot[key], f"snapshot.{key} stored in the benchmark file")
    for key in ("settlement_population", "species_population", "event_kinds", "essence_user_ranks"):
        if key in snapshot and isinstance(snapshot[key], dict):
            highlights[key] = measured(snapshot[key], f"snapshot.{key} stored in the benchmark file")
    return {"available": True, "fields": highlights}


def parse_benchmark_object(record: dict, source: str, label: str) -> dict:
    method = f"field stored in {source}"
    return {
        "id": label,
        "title": label,
        "source": source,
        "metrics": {
            "simulation_seconds": _optional(record, "simulation_seconds", method),
            "diagnostic_seconds": _optional(record, "diagnostic_seconds", method),
            "digest_seconds": _optional(record, "digest_seconds", method),
            "validation_seconds": _optional(record, "validation_seconds", method),
            "digest": _optional(record, "digest", method),
            "seed": _optional(record, "seed", method),
            "years": _optional(record, "years", method),
            "max_seconds": _optional(record, "max_seconds", method),
            "performance_passed": _optional(record, "performance_passed", method + "; not recomputed by the laboratory"),
            "gate_comparison": _gate_comparison(record),
        },
    }


def parse_millennium(data: dict, path: Path) -> dict:
    runs = []
    for key in ("baseline", "first_accepted"):
        block = data.get(key)
        if not isinstance(block, dict):
            continue
        benchmark = block.get("benchmark") if isinstance(block.get("benchmark"), dict) else {}
        parsed = parse_benchmark_object(benchmark, f"{path.name}:{key}", f"{path.name}:{key}")
        if "process_seconds" in block:
            parsed["metrics"]["process_seconds"] = measured(
                block["process_seconds"], f"{key}.process_seconds stored in {path.name}"
            )
        else:
            parsed["metrics"]["process_seconds"] = unavailable(f"{key}.process_seconds is absent")
        parsed["commit"] = measured(block["commit"], f"{key}.commit stored in the file") if block.get("commit") else unavailable("commit absent")
        parsed["run_url"] = block.get("run_url")
        parsed["buckets"] = _normalize_buckets(block.get("buckets"))
        parsed["snapshot"] = _snapshot_highlights(block.get("snapshot"))
        parsed["title"] = key.replace("_", " ")
        runs.append(parsed)
    comparison = data.get("comparison") if isinstance(data.get("comparison"), dict) else {}
    return {
        "kind": "millennium-pass",
        "path": str(path),
        "seed": measured(data["seed"], "top-level seed in the file") if "seed" in data else unavailable("seed absent"),
        "years": measured(data["years"], "top-level years in the file") if "years" in data else unavailable("years absent"),
        "note": data.get("note"),
        "comparison": {
            "same_canonical_digest": measured(comparison["same_canonical_digest"], "comparison.same_canonical_digest stored in the file")
            if "same_canonical_digest" in comparison else unavailable("same_canonical_digest absent"),
            "shared_year1000_snapshot_fields": measured(
                comparison["shared_year1000_snapshot_fields"],
                "comparison.shared_year1000_snapshot_fields stored in the file",
            ) if "shared_year1000_snapshot_fields" in comparison else unavailable("shared field count absent"),
            "different_shared_fields": measured(
                comparison["different_shared_fields"],
                "comparison.different_shared_fields stored in the file",
            ) if "different_shared_fields" in comparison else unavailable("different field list absent"),
        },
        "runs": runs,
    }


def parse_jsonl(path: Path) -> dict:
    rows = []
    incomplete = 0
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            if line_number == len(lines) and not text.endswith("\n"):
                incomplete += 1
            else:
                rows.append({"record": "unreadable", "line": line_number})
    samples = []
    summaries = []
    buckets = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        kind = row.get("record")
        if kind == "lab_year":
            samples.append(row)
        elif kind in ("lab_run", "benchmark"):
            summaries.append(row)
        elif kind == "scaling_bucket":
            buckets.append(row)
    runs = []
    for index, summary in enumerate(summaries):
        label = f"{path.name}:{summary.get('record')}#{index}"
        parsed = parse_benchmark_object(summary, label, label)
        parsed["title"] = str(summary.get("record"))
        parsed["buckets"] = _normalize_buckets(buckets) if summary.get("record") == "benchmark" else []
        if summary.get("record") == "lab_run":
            parsed["metrics"]["performance_passed"] = unavailable(
                "laboratory runs do not execute the 1,000-year gate and do not record a pass"
            )
            parsed["metrics"]["gate_comparison"] = unavailable(
                "a laboratory run is not the documented 1,000-year benchmark"
            )
            parsed["metrics"]["simulation_seconds"] = _optional(
                summary, "simulation_seconds", "sum of measured per-year step times, excluding display pacing"
            )
        runs.append(parsed)
    if not runs and samples:
        runs.append({
            "id": f"{path.name}:samples",
            "title": "year samples",
            "source": str(path),
            "metrics": {
                "simulation_seconds": calculated(
                    sum(row.get("step_seconds", 0) for row in samples),
                    "sum of lab_year step_seconds in this file",
                ),
                "performance_passed": unavailable("no benchmark record in this file"),
                "gate_comparison": unavailable("no 1,000-year benchmark record in this file"),
            },
            "buckets": [],
        })
    return {
        "kind": "jsonl",
        "path": str(path),
        "runs": runs,
        "samples": samples,
        "unreadable_lines": sum(1 for row in rows if isinstance(row, dict) and row.get("record") == "unreadable"),
        "incomplete_tail": incomplete,
    }


def load_file(path: Path) -> dict:
    if path.suffix.lower() == ".jsonl":
        return parse_jsonl(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"kind": "unreadable", "path": str(path), "error": str(exc), "runs": []}
    if isinstance(data, dict) and "first_accepted" in data and "baseline" in data:
        return parse_millennium(data, path)
    if isinstance(data, dict) and data.get("record") in ("benchmark", "lab_run"):
        parsed = parse_benchmark_object(data, path.name, path.name)
        parsed["buckets"] = _normalize_buckets(data.get("buckets"))
        return {"kind": "benchmark-json", "path": str(path), "runs": [parsed]}
    keys = list(data)[:24] if isinstance(data, dict) else []
    return {
        "kind": "unparsed",
        "path": str(path),
        "runs": [],
        "detail": unavailable(
            "JSON does not match millennium-pass, a benchmark record, or JSONL. "
            f"Top-level keys: {keys}"
        ),
    }


def discover(folders: list[str]) -> dict:
    sources = []
    seen: set[Path] = set()
    for folder in folders:
        root = Path(folder)
        if not root.is_dir():
            continue
        files = sorted(
            [path for path in root.iterdir() if path.is_file() and path.suffix.lower() in {".json", ".jsonl"}],
            key=lambda path: path.name,
        )
        for path in files:
            resolved = path.resolve()
            if resolved in seen or path.name.endswith(".partial"):
                continue
            seen.add(resolved)
            try:
                loaded = load_file(path)
            except OSError as exc:
                loaded = {"kind": "unreadable", "path": str(path), "error": str(exc), "runs": []}
            loaded["bytes"] = measured(path.stat().st_size, "file size")
            loaded["mtime"] = measured(path.stat().st_mtime, "file mtime")
            sources.append(loaded)
    return {"gate": documented_gate(), "sources": sources}
