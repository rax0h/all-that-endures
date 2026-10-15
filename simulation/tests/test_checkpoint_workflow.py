"""A diagnostics failure must not strand a completed immutable stage artifact."""
from pathlib import Path


def workflow():
    # Keep this test independent of optional YAML packages on CI runners.
    text=(Path(__file__).resolve().parents[2]/'.github/workflows/stage-0-5-final-release-validation.yml').read_text()
    return text


def test_successful_stage_upload_is_last_and_diagnostics_are_nonfatal():
    text=workflow()
    chunks=text.split('    - name: Execute bounded ')[1:]
    assert len(chunks)==8
    for chunk in chunks:
        assert 'continue-on-error: true' in chunk, 'diagnostics failure can strand immutable stage artifact'
        assert chunk.index('name: Retain completed stage') > chunk.index('if: always()')


def test_small_proof_has_no_mature_stage_or_long_command():
    text=workflow()
    assert 'initialization mature' not in text
    assert '360' not in text and '350m' not in text
    assert text.count('timeout-minutes: 20')==8
    assert '12m python -m simulation.checkpoint_validation_ci' in text
