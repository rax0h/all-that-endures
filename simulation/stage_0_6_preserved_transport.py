"""Read-only restoration of pinned, privately preserved original fixture ZIPs.

The committed manifests and independent original archive hashes grant transport
identity only. Existing six-member extraction and original accepted-year checks
still govern mature admission. Expired Actions carriers are never consulted.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import time

from simulation import stage_0_6_preserve_fixtures as preservation
from simulation.stage_0_6_retained_archive import extract_retained

ROOT = Path(__file__).resolve().parents[1]
PINS = ROOT/'simulation/stage_0_6_preserved_fixtures.json'


def original(key):
    matches=[value for value in preservation.sources(ROOT) if value['key']==key]
    if len(matches)!=1:raise ValueError('unknown preserved original fixture')
    return matches[0]


def manifest(key):
    expected=original(key)
    value=json.loads(PINS.read_text())
    if (value.get('schema')!='ate-preserved-fixtures/1'
            or value.get('release_id')!=preservation.RELEASE_ID):
        raise ValueError('preserved fixture release pin differs')
    entry=value['fixtures'][key];result=entry['manifest'];asset=entry['asset']
    raw=(json.dumps(result,sort_keys=True,indent=2)+'\n').encode()
    if (result.get('original')!=expected
            or result.get('release_id')!=preservation.RELEASE_ID
            or asset.get('sha256')!=hashlib.sha256(raw).hexdigest()
            or asset.get('bytes')!=len(raw)
            or type(asset.get('id')) is not int or asset['id']<1):
        raise ValueError('preserved manifest differs from original archive authority')
    return result


def inspect_preserved(key='mature-year1001'):
    value=manifest(key)
    release=preservation.ReleaseAPI().draft()  # Exact ID/tag/private visibility.
    return dict(kind='private-draft-preserved-original',release_id=release['id'],
        original=value['original'],parts=len(value['parts']))


def restore_archive(key,destination):
    destination=Path(destination)
    if destination.exists() or destination.is_symlink():raise FileExistsError(destination)
    value=manifest(key);authority=original(key)
    carrier=inspect_preserved(key)
    result=preservation.restore_file(preservation.ReleaseAPI(),value,destination,
        expected_bytes=authority['archive_bytes'],expected_sha256=authority['archive_sha256'])
    return dict(carrier=carrier,restored=result)


def download_retained(destination,*,database_bytes,metadata_max_bytes):
    destination=Path(destination)
    if destination.exists() or destination.is_symlink():raise FileExistsError(destination)
    if (type(database_bytes) is not int or database_bytes<1
            or type(metadata_max_bytes) is not int or metadata_max_bytes<1):
        raise ValueError('invalid retained database size or metadata cap')
    if destination.parent.is_symlink():raise ValueError('symlink destination parent')
    expected=original('mature-year1001');destination.parent.mkdir(parents=True,exist_ok=True)
    required=expected['archive_bytes']+database_bytes+preservation.CHUNK+preservation.RESERVE
    if shutil.disk_usage(destination.parent).free<required:raise ValueError('insufficient preserved input headroom')
    started=time.monotonic()
    with tempfile.TemporaryDirectory(prefix='.preserved-',dir=destination.parent) as directory:
        archive=Path(directory)/'original.zip'
        receipt=restore_archive('mature-year1001',archive)
        extracted=extract_retained(archive,destination,archive_sha256=expected['archive_sha256'],
            archive_bytes=expected['archive_bytes'],database_bytes=database_bytes,
            metadata_max_bytes=metadata_max_bytes)
    return dict(**receipt,extraction=extracted,download_seconds=time.monotonic()-started)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--key',choices=['small-year1','mature-year1001'],required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(restore_archive(args.key,args.output)),flush=True)


if __name__=='__main__':main()
