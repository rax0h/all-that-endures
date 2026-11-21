"""Labels for numbers the interface is allowed to show."""

from __future__ import annotations

import math
from enum import Enum
from typing import Any


def measured(value: Any, method: str, **extra: Any) -> dict:
    return {"quality": "measured", "value": _clean(value), "method": method, **extra}


def calculated(value: Any, method: str, **extra: Any) -> dict:
    return {"quality": "calculated", "value": _clean(value), "method": method, **extra}


def unavailable(method: str, **extra: Any) -> dict:
    return {"quality": "unavailable", "value": None, "method": method, **extra}


def documented(value: Any, method: str, **extra: Any) -> dict:
    """A figure copied from project documentation, not from a fresh run."""
    return {"quality": "documented", "value": _clean(value), "method": method, **extra}


def _clean(value: Any) -> Any:
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(v) for v in value]
    if value is None or isinstance(value, (str, int, bool)):
        return value
    return str(value)


def jsonable(value: Any) -> Any:
    return _clean(value)
