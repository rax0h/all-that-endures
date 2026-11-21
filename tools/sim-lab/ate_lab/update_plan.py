"""Decide whether a self-update is a clean fast-forward.

The decision is pure so it can be tested without touching a real checkout.
Applying the decision is separate and only ever runs inside the laboratory
install.
"""

from __future__ import annotations


def plan_update(*, fetch_ok: bool, dirty: bool, detached: bool, local: str, upstream: str, local_is_ancestor: bool) -> dict:
    if not fetch_ok:
        return {"action": "skip", "reason": "offline or fetch failed; launching the installed version"}
    if detached:
        return {"action": "skip", "reason": "detached HEAD; refusing to check out another branch"}
    if dirty:
        return {"action": "skip", "reason": "this install has uncommitted changes; refusing to merge"}
    if not local or not upstream:
        return {"action": "skip", "reason": "missing commit ids"}
    if local == upstream:
        return {"action": "up_to_date", "reason": "already at the tracked branch tip"}
    if local_is_ancestor:
        return {"action": "fast_forward", "reason": "upstream is a clean fast-forward of this install"}
    return {
        "action": "skip",
        "reason": "upstream is not a fast-forward of this install; refusing to merge or rebase",
    }
