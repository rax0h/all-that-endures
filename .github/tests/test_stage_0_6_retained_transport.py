"""Focused, network-free validation of retained ZIP signed transport."""
import hashlib
import io
import urllib.error
from pathlib import Path
from types import SimpleNamespace

import pytest

from simulation import stage_0_6_retained_transport as transport


class FakeResponse(io.BytesIO):
    def __init__(self, data, url='https://objects.example.com/signed'):
        super().__init__(data)
        self.url = url

    def geturl(self):
        return self.url


def test_signed_url_never_forwards_token_to_redirect(monkeypatch):
    seen = []

    class FakeOpener:
        def open(self, request, timeout):
            seen.append((request.full_url, request.get_header('Authorization')))
            raise urllib.error.HTTPError(request.full_url, 302, 'Found',
                                         {'Location': 'https://objects.example.com/signed'}, None)

    monkeypatch.setenv('GH_TOKEN', 'secret')
    monkeypatch.setattr(transport.urllib.request, 'build_opener', lambda handler: FakeOpener())
    assert transport._signed_url(123) == 'https://objects.example.com/signed'
    assert seen[0][1] == 'Bearer secret'


@pytest.mark.parametrize('url', [
    'http://objects.example.com/signed', 'https://user:pass@objects.example.com/signed',
    'https://objects.example.com:8080/signed', 'https://objects.example.com/signed#fragment',
    '//objects.example.com/signed'])
def test_signed_url_rejects_unsafe_redirect(monkeypatch, url):
    class FakeOpener:
        def open(self, request, timeout):
            raise urllib.error.HTTPError(request.full_url, 302, 'Found', {'Location': url}, None)

    monkeypatch.setenv('GH_TOKEN', 'secret')
    monkeypatch.setattr(transport.urllib.request, 'build_opener', lambda handler: FakeOpener())
    with pytest.raises(ValueError):
        transport._signed_url(123)


@pytest.mark.parametrize('payload,expected_error', [
    (b'12345', None), (b'1234', 'checksum or size'), (b'123456', 'exceeds pinned'),
    (b'abcde', 'checksum or size')])
def test_stream_archive_bounded_and_authenticated(tmp_path, monkeypatch, payload, expected_error):
    monkeypatch.setattr(transport.urllib.request, 'urlopen',
                        lambda url, timeout: FakeResponse(payload))
    dest = tmp_path / 'archive.zip'
    if expected_error:
        with pytest.raises(ValueError, match=expected_error):
            transport._stream_archive('https://objects.example.com/signed', dest,
                                      archive_sha256=hashlib.sha256(b'12345').hexdigest(),
                                      archive_bytes=5)
    else:
        assert transport._stream_archive('https://objects.example.com/signed', dest,
                                         archive_sha256=hashlib.sha256(b'12345').hexdigest(),
                                         archive_bytes=5) == 5


def test_stream_rejects_http_downgrade(tmp_path, monkeypatch):
    monkeypatch.setattr(transport.urllib.request, 'urlopen',
                        lambda url, timeout: FakeResponse(b'12345', 'http://objects.example.com/signed'))
    with pytest.raises(ValueError, match='insecure'):
        transport._stream_archive('https://objects.example.com/signed', tmp_path / 'archive.zip',
                                  archive_sha256=hashlib.sha256(b'12345').hexdigest(),
                                  archive_bytes=5)


def test_download_retained_rejects_producer_mismatch_before_network(tmp_path, monkeypatch):
    monkeypatch.setattr(transport, 'inspect_retained_producer', lambda: {'artifact_id': 0})
    monkeypatch.setattr(transport, '_signed_url',
                        lambda *_: pytest.fail('network before authentication'))
    with pytest.raises(ValueError, match='immutable pin'):
        transport.download_retained(tmp_path / 'source', database_bytes=100, metadata_max_bytes=100)
    assert not (tmp_path / 'source').exists()


def test_download_retained_calls_authenticated_extractor(tmp_path, monkeypatch):
    payload = b'12345'
    pin = SimpleNamespace(artifact_id=123, archive_sha256=hashlib.sha256(payload).hexdigest(),
                          archive_bytes=5)
    monkeypatch.setattr(transport, 'PIN', pin)
    monkeypatch.setattr(transport, 'inspect_retained_producer', lambda: {
        'artifact_id': pin.artifact_id, 'archive_sha256': pin.archive_sha256,
        'archive_bytes': pin.archive_bytes})
    monkeypatch.setattr(transport, '_signed_url',
                        lambda artifact_id: 'https://objects.example.com/signed')
    monkeypatch.setattr(transport.urllib.request, 'urlopen',
                        lambda url, timeout: FakeResponse(payload))
    observed = []

    def extract(archive, destination, **kwargs):
        assert Path(archive).read_bytes() == payload
        observed.append((destination, kwargs))
        Path(destination).mkdir()
        return {'verified': True}

    monkeypatch.setattr(transport, 'extract_retained', extract)
    dest = tmp_path / 'bundle'
    result = transport.download_retained(dest, database_bytes=300, metadata_max_bytes=400)
    assert result['extraction'] == {'verified': True} and dest.is_dir()
    assert observed[0][1]['archive_sha256'] == pin.archive_sha256
    assert observed[0][1]['database_bytes'] == 300
    assert not list(tmp_path.glob('.stage06-download-*'))
