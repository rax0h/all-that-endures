"""Fast-forward this laboratory install. Never runs git in another checkout."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from .paths import last_update_path, repo_root
from .update_plan import plan_update
from .version import _git, describe


def _in_venv() -> bool:
    return sys.prefix != getattr(sys, "base_prefix", sys.prefix)


def _record(payload: dict) -> dict:
    payload["at"] = datetime.now(timezone.utc).isoformat()
    try:
        path = last_update_path()
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    except OSError:
        payload["record_error"] = "could not write last-update.json"
    return payload


def read_last_update() -> dict | None:
    path = last_update_path()
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"action": "skip", "reason": "last-update.json is unreadable"}
    return data if isinstance(data, dict) else None


def check_update(root: Path | None = None, *, apply: bool = False, pip: bool = True) -> dict:
    """Check the tracked branch. Apply only a clean fast-forward when asked.

    A failed fetch, a dirty tree, or a non-fast-forward history skips the
    update and leaves the files on disk unchanged.
    """
    root = (root or repo_root()).resolve()
    identity = describe(root)
    branch_metric = identity.get("branch") or {}
    branch = branch_metric.get("value") if isinstance(branch_metric, dict) else None
    detached = branch in (None, "HEAD")
    dirty_metric = identity.get("dirty") or {}
    dirty = bool(dirty_metric.get("value")) if isinstance(dirty_metric, dict) else True
    local_metric = identity.get("commit") or {}
    local = local_metric.get("value") if isinstance(local_metric, dict) else ""
    if not local:
        return _record({"action": "skip", "reason": "this install is not a git checkout", "apply": apply})

    fetch = _git(root, "fetch", "origin", branch if branch and branch != "HEAD" else "HEAD", timeout=40)
    fetch_ok = fetch.returncode == 0
    upstream = ""
    ancestor = False
    if fetch_ok and branch and branch != "HEAD":
        rev = _git(root, "rev-parse", f"origin/{branch}")
        if rev.returncode == 0:
            upstream = rev.stdout.strip()
            base = _git(root, "merge-base", "--is-ancestor", "HEAD", f"origin/{branch}")
            ancestor = base.returncode == 0
    decision = plan_update(
        fetch_ok=fetch_ok,
        dirty=dirty,
        detached=bool(detached),
        local=str(local or ""),
        upstream=upstream,
        local_is_ancestor=ancestor,
    )
    decision.update({
        "apply": apply,
        "branch": branch,
        "local": local,
        "upstream": upstream or None,
        "fetch_stderr": (fetch.stderr or "").strip()[-500:],
        "linked_worktree": (identity.get("linked_worktree") or {}).get("value"),
        "pip": "not requested",
    })
    if decision["action"] != "fast_forward" or not apply:
        if decision["action"] == "up_to_date":
            decision["pip"] = "not needed"
        return _record(decision)

    merge = _git(root, "merge", "--ff-only", f"origin/{branch}", timeout=60)
    if merge.returncode != 0:
        _git(root, "merge", "--abort")
        decision["action"] = "skip"
        decision["reason"] = "fast-forward failed; launching the installed version"
        decision["merge_stderr"] = (merge.stderr or "").strip()[-500:]
        return _record(decision)

    new_head = _git(root, "rev-parse", "HEAD").stdout.strip()
    decision["updated"] = True
    decision["new"] = new_head
    names = _git(root, "diff", "--name-only", str(local), new_head)
    changed = [line.strip() for line in names.stdout.splitlines() if line.strip()]
    decision["changed"] = changed
    requirements = "tools/sim-lab/requirements.txt"
    if pip and requirements in changed:
        if not _in_venv():
            decision["pip"] = "skipped: not running inside the laboratory virtual environment"
        else:
            req = root / requirements
            installed = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", str(req)],
                capture_output=True,
                text=True,
                timeout=300,
                check=False,
            )
            decision["pip"] = "installed" if installed.returncode == 0 else "failed"
            if installed.returncode != 0:
                decision["pip_stderr"] = (installed.stderr or "")[-500:]
    else:
        decision["pip"] = "requirements unchanged"
    return _record(decision)
