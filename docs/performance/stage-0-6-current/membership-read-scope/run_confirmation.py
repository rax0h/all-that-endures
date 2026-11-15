"""Pinned publication-scope engines using the unchanged reviewed raw runner."""
import importlib.util
import json
from pathlib import Path
root = Path(__file__).resolve().parents[4]
path = root/'docs/performance/stage-0-6-current/small-operation-profile/read-view-epoch/repeat-comparison/repeat.py'
spec = importlib.util.spec_from_file_location('membership_scope_raw_trials', path)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
runner.EXPECTED_TREES = json.loads((Path(__file__).parent/'pair-config.json').read_text())
runner.ORDER = [('confirm1', 'candidate'), ('confirm1', 'baseline'), ('confirm2', 'baseline'), ('confirm2', 'candidate')]
runner.main()
