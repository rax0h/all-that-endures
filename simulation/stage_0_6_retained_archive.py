"""Fail-closed extraction of the pinned Stage 0.6 retained fixture ZIP.

This only stages transport bytes. The benchmark launcher must separately authenticate
GitHub producer metadata and the ORIGINAL candidate/acceptance receipts before use.
No Stage 0.5 artifact extraction behavior is modified here.
"""
import hashlib
import os
from pathlib import Path
import re
import stat
import tempfile
import zipfile


MEMBERS = frozenset({
    'source/candidate.sqlite',
    'source/checkpoint.json',
    'source/save.json',
    'accepted/year-verified.json',
    'evidence/source-authority.json',
    'evidence/source-transport.json',
})


def extract_retained(archive, destination, *, archive_sha256, archive_bytes,
                     database_bytes, metadata_max_bytes):
    """Authenticate ZIP bytes, then atomically stage six bounded regular files.

    The destination must not exist. The caller must subsequently validate the
    original source and acceptance bindings; this function does not confer them.
    """
    archive, destination = Path(archive), Path(destination)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(destination)
    if not (isinstance(archive_bytes, int) and not isinstance(archive_bytes, bool)
            and isinstance(database_bytes, int) and not isinstance(database_bytes, bool)
            and isinstance(metadata_max_bytes, int) and not isinstance(metadata_max_bytes, bool)
            and archive_bytes > 0 and database_bytes > 0 and metadata_max_bytes > 0
            and isinstance(archive_sha256, str)
            and re.fullmatch(r'[0-9a-f]{64}', archive_sha256)):
        raise ValueError('invalid retained archive pin or size caps')
    if not archive.is_file() or archive.is_symlink() or archive.stat().st_size != archive_bytes:
        raise ValueError('retained archive size/type differs')
    with archive.open('rb') as stream:
        if hashlib.file_digest(stream, 'sha256').hexdigest() != archive_sha256:
            raise ValueError('retained archive checksum differs')
    with zipfile.ZipFile(archive) as zipped:
        entries = zipped.infolist()
        if len(entries) != len(MEMBERS) or {entry.filename for entry in entries} != MEMBERS:
            raise ValueError('retained archive member inventory differs')
        for entry in entries:
            mode = entry.external_attr >> 16
            kind = stat.S_IFMT(mode)
            limit = database_bytes if entry.filename == 'source/candidate.sqlite' else metadata_max_bytes
            if (entry.is_dir() or (kind not in (0, stat.S_IFREG))
                    or entry.flag_bits & 1 or entry.file_size < 0
                    or entry.file_size > limit or
                    (entry.filename == 'source/candidate.sqlite' and entry.file_size != database_bytes)):
                raise ValueError('unsafe or oversized retained archive member')
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.parent.is_symlink():
            raise ValueError('symlink destination parent')
        with tempfile.TemporaryDirectory(prefix='.stage06-retained-', dir=destination.parent) as temporary:
            pending = Path(temporary)/'bundle'
            for entry in entries:
                target = pending.joinpath(*entry.filename.split('/'))
                target.parent.mkdir(parents=True, exist_ok=True)
                limit = database_bytes if entry.filename == 'source/candidate.sqlite' else metadata_max_bytes
                copied = 0
                with zipped.open(entry) as source, target.open('xb') as output:
                    while True:
                        chunk = source.read(min(1024*1024, limit-copied+1))
                        if not chunk:
                            break
                        copied += len(chunk)
                        if copied > limit:
                            raise ValueError('decompressed retained member exceeds cap')
                        output.write(chunk)
                if copied != entry.file_size:
                    raise ValueError('retained member decompressed size differs')
            if destination.exists() or destination.is_symlink():
                raise FileExistsError(destination)
            os.rename(pending, destination)
    return {'archive_sha256': archive_sha256, 'archive_bytes': archive_bytes,
            'members': sorted(MEMBERS), 'database_bytes': database_bytes}
