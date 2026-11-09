"""Independent bounded read-only probes; all databases live in pytest tmp dirs."""
import copy,json,sqlite3
from pathlib import Path
from types import SimpleNamespace
import pytest
from simulation import stage_0_6_proof_mature_preflight as m
from simulation.tests.test_stage_0_5_packed_action_reconciliation_cost import fixture
from simulation.tests.test_stage_0_5_performance_runner import source_authority

@pytest.fixture
def source(tmp_path):
    path=fixture(tmp_path,4)
    return path,source_authority(path)

def refresh(path,authority):
    authority['database']=dict(bytes=path.stat().st_size,sha256=m.r.file_hash(path))

@pytest.mark.parametrize('bad',['metadata-key','metadata-value','namespace','generation','seed'])
def test_malformed_selected_metadata_fails_closed(source,tmp_path,bad):
    path,authority=source
    db=sqlite3.connect(path)
    if bad=='metadata-key':db.execute("UPDATE store_metadata SET key=? WHERE key='codec_version'",('x'*129,))
    elif bad=='metadata-value':db.execute("UPDATE store_metadata SET value=? WHERE key='codec_version'",('x'*4097,))
    elif bad=='namespace':db.execute("UPDATE records SET namespace=namespace||?",('x'*1025,))
    elif bad=='generation':db.execute('UPDATE save_head SET generation=?',(sqlite3.Binary(b'x'*32),))
    else:db.execute('UPDATE save_head SET seed=?',(sqlite3.Binary(b'x'*32),))
    db.commit();db.close();refresh(path,authority)
    before=m.r.file_hash(path)
    out=tmp_path/'result.json'
    with pytest.raises(ValueError):m.inspect_database(path,authority,output=out)
    assert m.r.load_receipt(out)['status']=='error'
    assert m.r.file_hash(path)==before

def test_connection_owns_readonly_transaction_and_closes(source,tmp_path,monkeypatch):
    path,authority=source;connect=sqlite3.connect;handles=[];queries=[]
    class Observed(sqlite3.Connection):
        def execute(self,sql,*a):
            queries.append(sql)
            return super().execute(sql,*a)
    def tracked(*a,**k):
        assert a[0].endswith('?mode=ro') and k['uri'] is True
        k['factory']=Observed
        db=connect(*a,**k);handles.append(db);return db
    monkeypatch.setattr(m.sqlite3,'connect',tracked)
    result=m.inspect_database(path,authority,output=tmp_path/'result.json')
    assert result['status']=='complete'
    for required in ('PRAGMA query_only=ON','PRAGMA trusted_schema=OFF','PRAGMA temp_store=FILE','BEGIN'):assert required in queries
    assert all('SELECT payload' not in s and 'SELECT *' not in s for s in queries)
    with pytest.raises(sqlite3.ProgrammingError):handles[0].execute('SELECT 1')

def test_collision_preserves_original_journal_and_final_error(source,tmp_path):
    path,authority=source;out=tmp_path/'result.json';journal=tmp_path/'records-result.json'
    journal.write_text('untouched')
    with pytest.raises(FileExistsError):m.inspect_database(path,authority,output=out)
    assert journal.read_text()=='untouched'
    assert m.r.load_receipt(out)['status']=='error'
    assert m.r.file_hash(path)==authority['database']['sha256']

def test_after_sql_change_is_not_complete(source,tmp_path,monkeypatch):
    path,authority=source;file_hash=m.r.file_hash;calls=[]
    def mutate(p):
        calls.append(p)
        if len(calls)==2:
            with Path(p).open('ab') as stream:stream.write(b'changed-after-closed-sql')
        return file_hash(p)
    monkeypatch.setattr(m.r,'file_hash',mutate)
    out=tmp_path/'result.json'
    with pytest.raises(ValueError,match='source changed'):m.inspect_database(path,authority,output=out)
    result=m.r.load_receipt(out)
    assert result['status']=='error' and not result.get('source_unchanged',False)
