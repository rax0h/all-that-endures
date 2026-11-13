"""Reuse the reviewed bounded trial runner with these two pinned engines."""
import importlib.util
from pathlib import Path

root = Path(__file__).resolve().parents[5]
path = root / 'docs/performance/stage-0-6-current/small-operation-profile/read-view-epoch/repeat-comparison/repeat.py'
spec = importlib.util.spec_from_file_location('compressed_batch_trials', path)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
runner.SOURCES = {'baseline': root.parent / 'compressed-batch-baseline', 'candidate': root}
runner.EXPECTED_TREES = {'baseline': '4654b0194149f735a15c79507a6e57c88a7acbb2',
                         'candidate': '7347092a500a666710598fe4dcd31ae08d63848f'}
runner.main()
