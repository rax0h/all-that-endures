import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "sim-lab"))
sys.path.insert(0, str(ROOT / "simulation"))


def pytest_configure():
    import os
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
