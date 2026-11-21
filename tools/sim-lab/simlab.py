"""Entry point. Puts this install's packages on the path and never another checkout."""

from __future__ import annotations

import sys
from pathlib import Path

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]
sys.path.insert(0, str(LAB))
sys.path.insert(0, str(ROOT / "simulation"))

from ate_lab.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main())
