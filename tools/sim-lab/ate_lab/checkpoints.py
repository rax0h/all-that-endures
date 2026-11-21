"""Read-only checkpoint discovery. Saves go only to the laboratory var directory."""

from __future__ import annotations

import hashlib
import pickle
import re
from pathlib import Path
from time import perf_counter

from .engine_loader import import_engine
from .errors import LabError
from .paths import checkpoint_write_dir, contained
from .values import measured, unavailable

CHECKPOINT_SUFFIXES = {".checkpoint", ".ckpt", ".pkl", ".pickle"}
FILENAME = re.compile(r"[A-Za-z0-9._-]{1,120}")


def is_checkpoint_name(path: Path) -> bool:
    return path.suffix.lower() in CHECKPOINT_SUFFIXES and not path.name.endswith(".partial")


def file_stat(path: Path) -> dict:
    stat = path.stat()
    return {
        "path": str(path.resolve()),
        "name": path.name,
        "bytes": stat.st_size,
        "mtime": stat.st_mtime,
    }


def read_header(path: Path) -> dict:
    """Unpickle metadata. Does not recompute the canonical digest and does not write."""
    engine = import_engine()
    checkpoint = engine["checkpoint"]
    data = path.read_bytes()
    file_sha = hashlib.sha256(data).hexdigest()
    base = {
        **file_stat(path),
        "file_sha256": measured(file_sha, "SHA-256 of the file bytes"),
    }
    try:
        loaded = pickle.loads(data)
    except Exception as exc:
        base["error"] = f"{type(exc).__name__}: {exc}"
        base["integrity"] = unavailable("file did not unpickle; integrity was not checked")
        return base
    if not isinstance(loaded, checkpoint.Checkpoint):
        base["error"] = "file is a pickle but not an ate_sim.checkpoint.Checkpoint"
        base["integrity"] = unavailable("not an ATE checkpoint")
        return base
    world = loaded.world
    try:
        base.update({
            "schema_stored": measured(loaded.schema, "Checkpoint.schema stored in the file"),
            "schema_supported": checkpoint.CHECKPOINT_SCHEMA,
            "schema_supported_ok": loaded.schema == checkpoint.CHECKPOINT_SCHEMA,
            "year": measured(loaded.year, "Checkpoint.year stored in the file"),
            "seed": measured(loaded.seed, "Checkpoint.seed stored in the file"),
            "digest_stored": measured(loaded.digest, "digest stored in the file; not recomputed"),
            "metadata_matches_world": measured(
                bool(getattr(world, "year", None) == loaded.year and getattr(world, "seed", None) == loaded.seed),
                "stored year and seed compared with the unpickled world fields",
            ),
            "integrity": unavailable("stored digest was not recomputed; use Verify for the official check"),
            "people": measured(len(world.people), "len(people) on the unpickled world, before the world is discarded"),
            "living": measured(sum(person.alive for person in world.people.values()), "count of alive people while reading the header"),
        })
    finally:
        del world
        del loaded
    return base


def verify(path: Path) -> dict:
    """Official ``checkpoint.load``. Read-only. Times the integrity check."""
    engine = import_engine()
    before = path.stat().st_mtime
    started = perf_counter()
    try:
        world = engine["checkpoint"].load(path)
    except Exception as exc:
        elapsed = perf_counter() - started
        return {
            "path": str(path.resolve()),
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
            "verify_seconds": measured(elapsed, "wall time of ate_sim.checkpoint.load until it raised"),
            "mtime_unchanged": measured(path.stat().st_mtime == before, "file mtime compared before and after the read"),
        }
    elapsed = perf_counter() - started
    result = {
        "path": str(path.resolve()),
        "ok": True,
        "year": measured(world.year, "world.year after official load"),
        "seed": measured(world.seed, "world.seed after official load"),
        "verify_seconds": measured(
            elapsed,
            "wall time of ate_sim.checkpoint.load, which recomputes the canonical digest and compares it to the stored digest",
        ),
        "integrity": measured(True, "ate_sim.checkpoint.load returned without an integrity error"),
        "mtime_unchanged": measured(path.stat().st_mtime == before, "file mtime compared before and after the read"),
    }
    del world
    return result


def safe_checkpoint_filename(name: str) -> str:
    base = Path(name).name
    if not FILENAME.fullmatch(base):
        raise LabError("checkpoint file name must use letters, numbers, dots, hyphens, or underscores")
    if Path(base).suffix.lower() not in CHECKPOINT_SUFFIXES:
        base += ".checkpoint"
    return base


def save_new(world, filename: str) -> dict:
    """Write a new file under the laboratory var directory. Refuses overwrite."""
    directory = checkpoint_write_dir().resolve()
    filename = safe_checkpoint_filename(filename)
    path = (directory / filename).resolve()
    if not contained(path, directory) or path.parent != directory:
        raise LabError("refusing to save a checkpoint outside the laboratory checkpoint directory")
    if path.exists() or path.is_symlink():
        raise LabError(f"refusing to overwrite {path.name}")
    partial = path.with_name(path.name + ".partial")
    if partial.exists():
        raise LabError(f"refusing to replace an existing partial file {partial.name}")
    engine = import_engine()
    started = perf_counter()
    try:
        file_sha = engine["checkpoint"].save(world, partial)
        partial.replace(path)
    except Exception:
        partial.unlink(missing_ok=True)
        raise
    elapsed = perf_counter() - started
    return {
        "path": str(path),
        "file_sha256": measured(file_sha, "SHA-256 returned by ate_sim.checkpoint.save"),
        "save_seconds": measured(elapsed, "wall time of ate_sim.checkpoint.save, including the canonical digest"),
        "bytes": measured(path.stat().st_size, "size of the new file"),
    }
