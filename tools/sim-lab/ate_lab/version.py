"""Identity of the laboratory install. Git output is data, not instructions."""

from __future__ import annotations

import subprocess
from pathlib import Path

from . import __version__
from .paths import repo_root
from .values import measured, unavailable


def _git(root: Path, *args: str, timeout: float = 8) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def describe(root: Path | None = None) -> dict:
    root = root or repo_root()
    info = {
        "lab_version": __version__,
        "repo_root": str(root),
        "engine_root": str(root / "simulation"),
        "engine_note": "The laboratory imports ate_sim from this install, not from any other working copy.",
    }
    try:
        head = _git(root, "rev-parse", "HEAD")
        branch = _git(root, "rev-parse", "--abbrev-ref", "HEAD")
        short = _git(root, "rev-parse", "--short", "HEAD")
        dirty = _git(root, "status", "--porcelain")
        common = _git(root, "rev-parse", "--git-common-dir")
        git_dir = _git(root, "rev-parse", "--git-dir")
    except (OSError, subprocess.TimeoutExpired) as exc:
        info["commit"] = unavailable(f"git is not usable here: {exc}")
        return info
    if head.returncode != 0:
        info["commit"] = unavailable(head.stderr.strip() or "not a git checkout")
        return info
    commit = head.stdout.strip()
    info["commit"] = measured(commit, "git rev-parse HEAD")
    info["commit_short"] = measured(short.stdout.strip(), "git rev-parse --short HEAD")
    info["branch"] = measured(branch.stdout.strip(), "git rev-parse --abbrev-ref HEAD")
    info["dirty"] = measured(bool(dirty.stdout.strip()), "git status --porcelain")
    common_path = Path(common.stdout.strip() or ".").resolve()
    git_path = Path(git_dir.stdout.strip() or ".").resolve()
    info["linked_worktree"] = measured(
        common_path != git_path,
        "git common dir differs from this worktree git dir",
    )
    return info
