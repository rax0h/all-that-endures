"""Persistent local settings. Stored outside every git working copy."""

from __future__ import annotations

import json
import os
from pathlib import Path

from .errors import LabError
from .paths import (
    checkpoint_write_dir,
    data_root_candidates,
    existing_dirs,
    lab_dir,
    output_write_dir,
    repo_root,
    settings_path,
)

MAX_YEAR_CAP = 250

DEFAULTS = {
    "update_on_launch": True,
    "data_root": "",
    "extra_checkpoint_dirs": [],
    "extra_output_dirs": [],
    "extra_benchmark_dirs": [],
    "year_cap": MAX_YEAR_CAP,
    "default_years": 25,
    "default_seed": 843000,
    "default_timebox_seconds": 60,
    "port": 8765,
}


def _normalize(raw: dict, *, fill_data_root_from_env: bool) -> dict:
    settings = dict(DEFAULTS)
    for key in DEFAULTS:
        if key in raw:
            settings[key] = raw[key]
    if fill_data_root_from_env and "data_root" not in raw:
        settings["data_root"] = os.environ.get("ATE_DATA_ROOT", "")
    try:
        settings["year_cap"] = max(1, min(MAX_YEAR_CAP, int(settings["year_cap"])))
        settings["default_years"] = max(1, min(settings["year_cap"], int(settings["default_years"])))
        settings["default_seed"] = int(settings["default_seed"])
        settings["default_timebox_seconds"] = max(0.0, float(settings["default_timebox_seconds"]))
        settings["port"] = int(settings["port"])
    except (TypeError, ValueError) as exc:
        raise LabError(f"settings contain a non-numeric value: {exc}") from exc
    settings["update_on_launch"] = bool(settings["update_on_launch"])
    settings["data_root"] = str(settings["data_root"] or "")
    for key in ("extra_checkpoint_dirs", "extra_output_dirs", "extra_benchmark_dirs"):
        value = settings[key]
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise LabError(f"{key} must be a list of paths")
    return settings


def load() -> dict:
    path = settings_path()
    raw: dict = {}
    if path.is_file():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise LabError(f"settings file is unreadable: {path}: {exc}") from exc
        if not isinstance(loaded, dict):
            raise LabError(f"settings file must be a JSON object: {path}")
        raw = loaded
    return _normalize(raw, fill_data_root_from_env=True)


def save(updates: dict) -> dict:
    current = load()
    for key in DEFAULTS:
        if key in updates:
            current[key] = updates[key]
    # The loaded object already applied the env default, so keep that explicit value.
    normalized = _normalize(current, fill_data_root_from_env=False)
    settings_path().write_text(json.dumps(normalized, indent=2) + "\n", encoding="utf-8")
    return normalized


def _extras(values: list[str]):
    return existing_dirs([Path(value) for value in values])


def watched_folders(settings: dict | None = None) -> dict[str, list[str]]:
    settings = settings or load()
    data = data_root_candidates(str(settings.get("data_root") or ""))
    benchmarks = existing_dirs(
        [repo_root() / "simulation" / "performance", output_write_dir()]
        + data["benchmarks"]
        + _extras(settings["extra_benchmark_dirs"])
    )
    checkpoints = existing_dirs(
        [checkpoint_write_dir()] + data["checkpoints"] + _extras(settings["extra_checkpoint_dirs"])
    )
    outputs = existing_dirs(
        [output_write_dir()] + data["outputs"] + _extras(settings["extra_output_dirs"])
    )
    return {
        "checkpoints": [str(path) for path in checkpoints],
        "outputs": [str(path) for path in outputs],
        "benchmarks": [str(path) for path in benchmarks],
        "checkpoint_write_dir": str(checkpoint_write_dir()),
        "output_write_dir": str(output_write_dir()),
        "data_root": str(settings.get("data_root") or ""),
        "lab_dir": str(lab_dir()),
        "writes_outside_lab_var": False,
    }
