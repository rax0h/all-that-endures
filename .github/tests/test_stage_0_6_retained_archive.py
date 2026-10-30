"""Standalone transport-boundary regressions; no mature fixture or CI network needed."""
import hashlib
from pathlib import Path
import stat
import zipfile
import pytest
from simulation.stage_0_6_retained_archive import MEMBERS, extract_retained


def archive(tmp_path, *, names=None, db=b'database', symlink=False, oversized=False):
    path=tmp_path/'fixture.zip'
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for name in (sorted(MEMBERS) if names is None else names):
            info=zipfile.ZipInfo(name)
            info.external_attr=((stat.S_IFLNK if symlink and name=='source/save.json' else stat.S_IFREG)|0o644)<<16
            data=db if name=='source/candidate.sqlite' else (b'X'*64 if oversized else b'{}')
            z.writestr(info,data)
    return path


def unpack(path,destination, *, digest=None, size=None, db_bytes=8, meta_cap=64):
    return extract_retained(path,destination,
        archive_sha256=digest or hashlib.sha256(path.read_bytes()).hexdigest(),
        archive_bytes=size if size is not None else path.stat().st_size,
        database_bytes=db_bytes,metadata_max_bytes=meta_cap)


def test_exact_six_nested_files_stage_without_flattening(tmp_path):
    path=archive(tmp_path);dest=tmp_path/'out'
    receipt=unpack(path,dest)
    assert set(receipt['members'])==MEMBERS
    assert (dest/'source/candidate.sqlite').read_bytes()==b'database'
    assert (dest/'accepted/year-verified.json').read_bytes()==b'{}'
    assert len(list(dest.rglob('*')))==9  # three dirs plus six files

@pytest.mark.parametrize('names',[
    sorted(MEMBERS)[:-1],
    sorted(MEMBERS)+['extra.json'],
    sorted(MEMBERS)[:-1]+['../evil'],
    sorted(MEMBERS)[:-1]+['source/../../evil'],
    sorted(MEMBERS)[:-1]+['source/candidate.sqlite'],
])
def test_reject_missing_extra_traversal_or_duplicate(tmp_path,names):
    path=archive(tmp_path,names=names);dest=tmp_path/'out'
    with pytest.raises(ValueError):unpack(path,dest)
    assert not dest.exists()

@pytest.mark.parametrize('alter', ['wrong_hash','wrong_size','symlink','oversized','wrong_db_size','already_exists'])
def test_reject_mismatched_transport_and_unsafe_members(tmp_path,alter):
    path=archive(tmp_path,symlink=alter=='symlink',oversized=alter=='oversized')
    dest=tmp_path/'out'
    if alter=='already_exists':dest.mkdir()
    with pytest.raises((ValueError,FileExistsError)):
        unpack(path,dest,digest='0'*64 if alter=='wrong_hash' else None,
               size=path.stat().st_size+1 if alter=='wrong_size' else None,
               db_bytes=7 if alter=='wrong_db_size' else 8,
               meta_cap=32 if alter=='oversized' else 64)
    if alter!='already_exists':assert not dest.exists()


def test_reject_bad_caps_and_preserve_existing_output(tmp_path):
    path=archive(tmp_path);dest=tmp_path/'out'
    with pytest.raises(ValueError):extract_retained(path,dest,archive_sha256='x',archive_bytes=path.stat().st_size,database_bytes=8,metadata_max_bytes=64)
    assert not dest.exists()
