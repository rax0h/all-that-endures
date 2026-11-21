"""Locations the laboratory may read or write.

The founder's main working copy is never a write target and is never put on
``sys.path``. Optional data roots are read-only folders of checkpoints,
outputs, and benchmark files.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from .errors import LabError


def repo_root() -> Path:
    root = Path(__file__).resolve().parents[3]
    if not (root / "simulation" / "ate_sim").is_dir():
        raise LabError(f"the laboratory is not inside an All That Endures checkout ({root})")
    return root


def lab_dir() -> Path:
    return repo_root() / "tools" / "sim-lab"


def var_dir() -> Path:
    override = os.environ.get("ATE_LAB_VAR")
    path = Path(override) if override else lab_dir() / "var"
    return path


def checkpoint_write_dir() -> Path:
    path = var_dir() / "checkpoints"
    path.mkdir(parents=True, exist_ok=True)
    return path


def output_write_dir() -> Path:
    path = var_dir() / "outputs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_dir() -> Path:
    override = os.environ.get("ATE_LAB_HOME")
    if override:
        path = Path(override)
    elif os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
        path = base / "ATE-SimLab"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
        path = base / "ATE-SimLab"
    path.mkdir(parents=True, exist_ok=True)
    return path


def settings_path() -> Path:
    return config_dir() / "settings.json"


def last_update_path() -> Path:
    return config_dir() / "last-update.json"


def contained(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def ensure_engine_path() -> Path:
    """Import the engine from this worktree only.

    Importing the founder's checkout would write ``__pycache__`` there and
    could execute uncommitted code. Bytecode writing is suppressed.
    """
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    simulation = repo_root() / "simulation"
    entry = str(simulation)
    if entry not in sys.path:
        sys.path.insert(0, entry)
    return simulation


def existing_dirs(candidates: list[Path]) -> list[Path]:
    found: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if resolved in seen or not resolved.is_dir():
            continue
        seen.add(resolved)
        found.append(resolved)
    return found


def data_root_candidates(data_root: str) -> dict[str, list[Path]]:
    """Existing folders under a read-only data root. Nothing is created."""
    if not data_root:
        return {"checkpoints": [], "outputs": [], "benchmarks": []}
    root = Path(data_root)
    if not root.is_dir():
        return {"checkpoints": [], "outputs": [], "benchmarks": []}
    return {
        "checkpoints": existing_dirs([
            root / "checkpoints",
            root / "simulation" / "checkpoints",
            root / "var" / "checkpoints",
        ]),
        "outputs": existing_dirs([
            root / "outputs",
            root / "simulation" / "outputs",
            root / "var" / "outputs",
        ]),
        "benchmarks": existing_dirs([
            root / "simulation" / "performance",
            root / "performance",
        ]),
    }
