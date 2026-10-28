"""Archive retention must preserve bytes and reject oversized/corrupt transport."""
import hashlib
import io

import pytest


@pytest.mark.parametrize('payload,expected_size,expected_hash,accepted', [
    (b'checkpoint', 10, hashlib.sha256(b'checkpoint').hexdigest(), True),
    (b'checkpoint', 10, '0'*64, False),
    (b'checkpoint-extra', 10, hashlib.sha256(b'checkpoint').hexdigest(), False),
    (b'short', 10, hashlib.sha256(b'checkpoint').hexdigest(), False),
])
def test_exact_archive_copy(tmp_path, payload, expected_size, expected_hash, accepted):
    from simulation.preserve_mature_inputs import copy_archive
    target = tmp_path/'archive.zip'
    if accepted:
        copy_archive(io.BytesIO(payload), target, expected_size, expected_hash)
        assert target.read_bytes() == payload
    else:
        with pytest.raises(ValueError, match='archive'):
            copy_archive(io.BytesIO(payload), target, expected_size, expected_hash)
        assert not target.exists()


def test_partial_retention_keeps_success_manifest(tmp_path, monkeypatch):
    from simulation import preserve_mature_inputs as retention
    from simulation import continuation_receipts as receipts
    monkeypatch.chdir(tmp_path)
    launch = {'inputs': {'candidate': {'role': 'candidate'}, 'previous': {'role': 'previous'}},
              'candidate_database': {'sha256': 'pinned'}}
    monkeypatch.setattr(retention.r, 'load_receipt', lambda path: launch)
    class Ref:
        archive_bytes = 10
        def __init__(self, row): self.role = row['role']
    monkeypatch.setattr(retention.r.ArtifactRef, 'from_dict', Ref)
    def retain(ref, directory):
        if ref.role == 'previous': raise ValueError('acceptance transport unavailable')
        (directory/'source.zip').write_bytes(b'checkpoint')
        return {'file': 'source.zip'}
    monkeypatch.setattr(retention, 'retain_archive', retain)
    monkeypatch.setenv('GITHUB_RUN_ID', '123')
    monkeypatch.setenv('GITHUB_SHA', 'commit')
    with pytest.raises(ValueError, match='acceptance transport'):
        retention.main()
    import json
    result = json.loads((tmp_path/'retained-mature-inputs/manifest.json').read_text())
    assert result['status'] == 'partial'
    assert result['inputs']['candidate']['file'] == 'source.zip'
