"""Isolated fail-closed retained launcher integration checks (no large fixture)."""
import importlib.util
import json
import sys
import types
from pathlib import Path
from types import SimpleNamespace
import pytest

PATH = Path(__file__).resolve().parents[2] / 'simulation/stage_0_6_retained_launch.py'


@pytest.fixture
def fixture(monkeypatch, tmp_path):
    simulation = types.ModuleType('simulation')
    simulation.__path__ = []
    receipts = types.ModuleType('simulation.continuation_receipts')
    receipts.METADATA_MAX_BYTES = 1000
    receipts.same = lambda a, b: a == b
    receipts.load_receipt = lambda p: json.loads(Path(p).read_text())
    receipts.validate_year_acceptance = lambda *a: None
    receipts.match_producer = lambda *a: None
    receipts.saved_binding = lambda saved, source, digest: {
        'year': saved['year'], 'candidate': source.to_dict(), 'hash': digest}
    checkpoint = types.ModuleType('simulation.continuation_checkpoint')
    saved = {'year': 1001, 'generation': 126, 'store_identity': 'abc',
             'database': {'sha256': 'd'*64, 'bytes': 100}}
    checkpoint._read_saved = lambda path, authority, source: (saved, {'save.json': 'e'*64})
    producer = types.ModuleType('simulation.stage_0_6_retained_producer')
    producer.PIN = SimpleNamespace(run_id=99, head_sha='f'*40)
    transport = types.ModuleType('simulation.stage_0_6_retained_transport')
    transport.download_retained = lambda *a, **k: None
    for name, module in [
        ('simulation', simulation),
        ('simulation.continuation_receipts', receipts),
        ('simulation.continuation_checkpoint', checkpoint),
        ('simulation.stage_0_6_retained_producer', producer),
        ('simulation.stage_0_6_retained_transport', transport),
    ]:
        monkeypatch.setitem(sys.modules, name, module)
    simulation.continuation_receipts = receipts
    simulation.continuation_checkpoint = checkpoint
    spec = importlib.util.spec_from_file_location('stage06_retained_launch_isolated', PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source = SimpleNamespace(
        artifact_id=1, run_id=2, workflow_sha='a'*40, archive_sha256='b'*64,
        archive_bytes=4, producer_job='save', to_dict=lambda: {'original': 'source'})
    accepted = SimpleNamespace(
        artifact_id=3, run_id=4, workflow_sha='c'*40, archive_sha256='d'*64,
        archive_bytes=5, producer_job='accept', to_dict=lambda: {'original': 'accepted'})
    config = {'world': {'year': 1001, 'seed': 843000},
              'pin': {'store_identity': 'abc', 'captured_head': 126}}
    identity = {'head': 'f'*40, 'committed_tree': 'x'*40}
    authority = SimpleNamespace(source_config={'seed': 843000, 'rules_id': 'test'})
    database = saved['database']
    expected = dict(
        schema='ate-performance-source/1', database=database, rules_id='test',
        pin={'token': None, 'store_identity': 'abc', 'captured_head': 126},
        world=config['world'],
        provenance={'kind': 'authenticated-accepted-saved-artifact',
                    'artifact': source.to_dict(), 'acceptance': accepted.to_dict(),
                    'save_sha256': 'e'*64,
                    'source_lease': 'closed retained artifact; measured sessions record actual lease'})
    def proof(ref):
        return dict(artifact_id=ref.artifact_id, run_id=ref.run_id,
                    workflow_sha=ref.workflow_sha, archive_sha256=ref.archive_sha256,
                    archive_bytes=ref.archive_bytes, producer_job=ref.producer_job)
    historical = dict(
        source=proof(source), acceptance=proof(accepted), saved_manifest=saved,
        accepted_binding=receipts.saved_binding(saved, source, 'e'*64),
        producer={'run_id': '99', 'sha': 'f'*40}, runtime=identity)
    def download(destination, **kwargs):
        destination = Path(destination)
        for folder in ('source', 'accepted', 'evidence'):
            (destination/folder).mkdir(parents=True)
        (destination/'accepted/year-verified.json').write_text(json.dumps({
            'producer': {}, 'binding': historical['accepted_binding']}))
        (destination/'evidence/source-authority.json').write_text(json.dumps(expected))
        (destination/'evidence/source-transport.json').write_text(json.dumps(historical))
        return {'verified': True}
    module.download_retained = download
    return SimpleNamespace(
        mod=module, root=tmp_path, config=config, identity=identity, source=source,
        accepted=accepted, database=database, authority=authority,
        historical=historical, expected=expected)


def call(f):
    return f.mod.prepare_retained(
        f.root, f.config, f.identity, f.source, f.accepted, f.database, f.authority)


def test_retained_transport_preserves_original_source_authority(fixture):
    f = fixture
    performance, transport = call(f)
    assert performance == f.expected
    assert transport['historical_producer'] == f.historical['producer']
    assert (f.root/'source').is_dir() and (f.root/'accepted').is_dir()
    assert not (f.root/'.stage06-retained-input').exists()


@pytest.mark.parametrize('mutation', [
    'source_ref', 'accept_ref', 'authority', 'accepted_binding', 'producer', 'runtime'])
def test_retained_tampering_fails_before_publication(fixture, mutation):
    f = fixture
    original = f.mod.download_retained
    def corrupt(destination, **kwargs):
        result = original(destination, **kwargs)
        authority_file = Path(destination)/'evidence/source-authority.json'
        transport_file = Path(destination)/'evidence/source-transport.json'
        if mutation == 'authority':
            data = json.loads(authority_file.read_text())
            data['world']['year'] = 1002
            authority_file.write_text(json.dumps(data))
        else:
            data = json.loads(transport_file.read_text())
            if mutation == 'source_ref':
                data['source']['artifact_id'] = 777
            elif mutation == 'accept_ref':
                data['acceptance']['archive_bytes'] = 99
            elif mutation == 'accepted_binding':
                data['accepted_binding']['year'] = 1002
            elif mutation == 'producer':
                data['producer']['sha'] = '0'*40
            elif mutation == 'runtime':
                data['runtime']['committed_tree'] = '0'*40
            transport_file.write_text(json.dumps(data))
        return result
    f.mod.download_retained = corrupt
    with pytest.raises(ValueError):
        call(f)
    assert not (f.root/'source').exists() and not (f.root/'accepted').exists()
    assert not (f.root/'.stage06-retained-input').exists()


def test_publication_rolls_back_on_second_rename_failure(fixture, monkeypatch):
    f = fixture
    original = f.mod.os.rename
    def fail_accepted(a, b):
        if str(b).endswith('/accepted'):
            raise OSError('injected rename failure')
        return original(a, b)
    monkeypatch.setattr(f.mod.os, 'rename', fail_accepted)
    with pytest.raises(OSError, match='injected'):
        call(f)
    assert not (f.root/'source').exists() and not (f.root/'accepted').exists()


def test_existing_source_cannot_be_overwritten(fixture):
    f = fixture
    (f.root/'source').mkdir()
    with pytest.raises(FileExistsError):
        call(f)
    assert (f.root/'source').is_dir()
