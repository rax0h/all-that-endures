"""Preserved original carriers still require exact bytes and original authority."""
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import zipfile

import pytest

from simulation import stage_0_6_preserve_fixtures as preservation
from simulation.stage_0_6_retained_archive import MEMBERS


def api():
    name='simulation.stage_0_6_preserved_transport'
    assert importlib.util.find_spec(name) is not None, 'preserved carrier consumer is missing'
    return importlib.import_module(name)


@pytest.fixture
def carrier(tmp_path, monkeypatch):
    module=api();archive=tmp_path/'source.zip'
    with zipfile.ZipFile(archive,'w') as z:
        for name in sorted(MEMBERS):z.writestr(name,b'database' if name.endswith('.sqlite') else b'{}')
    original=dict(key='mature-year1001',archive_bytes=archive.stat().st_size,
        archive_sha256=preservation.sha(archive),source=dict(artifact_id=7,run_id=9,head_sha='a'*40))
    assets={};calls=[]
    class Remote:
        def put(self, release, path):
            data=path.read_bytes();row=dict(id=len(assets)+1,name=path.name,size=len(data),
                state='uploaded',digest='sha256:'+hashlib.sha256(data).hexdigest(),data=data)
            assets[row['id']]=row;return row
        def download(self, row, destination):destination.write_bytes(assets[row['id']]['data'])
    remote=Remote();release=dict(id=preservation.RELEASE_ID,draft=True,tag_name=preservation.TAG)
    complete=preservation.preserve_file(remote,release,archive,original,tmp_path/'proof',chunk_bytes=300)
    manifest=json.loads((tmp_path/'proof/manifest.json').read_text())
    def download(self,row,destination):
        calls.append(row['id']);remote.download(row,destination)
    def metadata(path):
        assert path==f'/releases/{preservation.RELEASE_ID}', 'must not ask expired Actions carrier for authority'
        return release
    monkeypatch.setattr(preservation.github,'_api',metadata)
    monkeypatch.setattr(preservation.ReleaseAPI,'download',download)
    monkeypatch.setattr(module,'original',lambda key:original)
    pins=tmp_path/'pins.json'
    asset=dict(id=complete['manifest_id'],name=complete['manifest_name'],
        bytes=(tmp_path/'proof/manifest.json').stat().st_size,sha256=complete['manifest_sha256'])
    value=dict(schema='ate-preserved-fixtures/1',release_id=preservation.RELEASE_ID,
        fixtures={'mature-year1001':dict(manifest=manifest,asset=asset)})
    pins.write_text(json.dumps(value));monkeypatch.setattr(module,'PINS',pins)
    return module,original,assets,calls,value,pins,release


def test_preserved_original_extracts_exact_six_members_without_actions_expiry_lookup(carrier,tmp_path):
    module,original,assets,calls,value,pins,release=carrier
    result=module.download_retained(tmp_path/'out',database_bytes=8,metadata_max_bytes=64)
    assert (tmp_path/'out/source/candidate.sqlite').read_bytes()==b'database'
    assert set(result['extraction']['members'])==MEMBERS
    assert result['carrier']['original']==original
    assert len(calls)==len(value['fixtures']['mature-year1001']['manifest']['parts'])
    assert not list(tmp_path.glob('.preserved-*'))


@pytest.mark.parametrize('damage',['archive_hash','archive_size','original_source','release','manifest_hash','public'])
def test_preserved_pin_or_visibility_drift_fails_before_asset_fetch(carrier,tmp_path,damage):
    module,original,assets,calls,value,pins,release=carrier
    entry=value['fixtures']['mature-year1001']
    if damage=='archive_hash':entry['manifest']['original']['archive_sha256']='0'*64
    elif damage=='archive_size':entry['manifest']['original']['archive_bytes']+=1
    elif damage=='original_source':entry['manifest']['original']['source']['artifact_id']=8
    elif damage=='release':value['release_id']+=1
    elif damage=='manifest_hash':entry['asset']['sha256']='0'*64
    else:release['draft']=False
    pins.write_text(json.dumps(value))
    with pytest.raises(ValueError):module.restore_archive('mature-year1001',tmp_path/'restored.zip')
    assert not calls and not (tmp_path/'restored.zip').exists()


def test_corrupt_preserved_part_never_publishes_source(carrier,tmp_path):
    module,original,assets,calls,value,pins,release=carrier
    first=next(iter(assets));assets[first]['data']=b'x'*len(assets[first]['data'])
    with pytest.raises(ValueError):module.download_retained(tmp_path/'out',database_bytes=8,metadata_max_bytes=64)
    assert not (tmp_path/'out').exists()


def test_repository_preservation_pins_match_original_independent_authorities():
    module=api()
    for key in ('small-year1','mature-year1001'):
        manifest=module.manifest(key)
        assert manifest['original']==module.original(key)
        assert manifest['verified_archive_sha256']==module.original(key)['archive_sha256']


def test_invalid_carrier_choice_refused_before_original_download(tmp_path):
    from simulation import stage_0_6_retained_transport as transport
    with pytest.raises(ValueError,match='carrier'):
        transport.download_retained(tmp_path/'out',database_bytes=8,metadata_max_bytes=64,carrier='unknown')


@pytest.mark.parametrize('problem',['metadata','database','capacity','symlink','exists'])
def test_bad_disposable_target_refused_before_any_asset_transfer(carrier,tmp_path,monkeypatch,problem):
    from types import SimpleNamespace
    module,original,assets,calls,value,pins,release=carrier
    target=tmp_path/'out';caps=dict(database_bytes=8,metadata_max_bytes=64)
    if problem=='metadata':caps['metadata_max_bytes']=0
    elif problem=='database':caps['database_bytes']=True
    elif problem=='capacity':monkeypatch.setattr(module.shutil,'disk_usage',lambda path:SimpleNamespace(free=0))
    elif problem=='symlink':
        link=tmp_path/'linked';link.symlink_to(tmp_path,target_is_directory=True);target=link/'out'
    else:target.mkdir()
    with pytest.raises((ValueError,FileExistsError)):module.download_retained(target,**caps)
    assert not calls
