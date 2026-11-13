"""Use the reviewed bounded pair runner on the action-retention engines."""
import importlib.util
from pathlib import Path

root = Path(__file__).resolve().parents[5]
path = root / 'docs/performance/stage-0-6-current/small-operation-profile/read-view-epoch/repeat-comparison/repeat.py'
spec = importlib.util.spec_from_file_location('action_lifetime_trials', path)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
runner.SOURCES = {'baseline': root.parent / 'action-retention-baseline', 'candidate': root}
runner.EXPECTED_TREES = {'baseline': '7347092a500a666710598fe4dcd31ae08d63848f',
                         'candidate': '8cc642b2a95d47b6d874dfe5260dacbe18f52d43'}
runner.main()
