"""Closed offline checkpoints. A receipt never grants ordinary reader authority."""
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import uuid

SCHEMA='ate-proof-genesis-checkpoint/1'
STAGES=('source_digest','capture','catalog','rebase','after_digest','proofs','measure','fresh_restore')
ORDER=('source',*STAGES)
JOB={stage:stage.replace('_','-') for stage in ORDER}
JOB['source']='gate'
WRITES=frozenset(('source','capture','catalog','rebase','proofs','measure'))
MAX_METADATA=2*1024*1024
WORKFLOW='.github/workflows/stage-0-6-resumable-proof-genesis.yml'
FIELDS={'schema','stage','context','parent','database','data_ref','baseline_digest','proof_commitment','producer','metrics'}
DB_FIELDS={'bytes','sha256','store_identity','generation','format','year','seed'}
CONTEXT_FIELDS={'mode','runtime_tree','critical_blobs','source','rules_id','rank_proofs','expected_saved_digest','execution_runtime'}


def exact(value,keys,label):
    if type(value) is not dict or set(value)!=set(keys):raise ValueError(label+' fields differ')


def integer(value,label,minimum=0):
    if type(value) is not int or value<minimum:raise ValueError('invalid '+label)


def hexadecimal(value,length,label):
    if type(value) is not str or re.fullmatch('[0-9a-f]{'+str(length)+'}',value) is None:raise ValueError('invalid '+label)


def file_hash(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def receipt_hash(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()).hexdigest()


def check_database(value):
    exact(value,DB_FIELDS,'database')
    for key in ('bytes','generation','year','seed'):integer(value[key],key,1 if key=='bytes' else 0)
    hexadecimal(value['sha256'],64,'database hash')
    if value['format'] not in (6,7) or type(value['format']) is not int:raise ValueError('invalid database format')
    try:
        if str(uuid.UUID(value['store_identity']))!=value['store_identity']:raise ValueError('noncanonical UUID')
    except (ValueError,AttributeError,TypeError) as exc:raise ValueError('invalid database identity') from exc


def check_context(value):
    exact(value,CONTEXT_FIELDS,'context');check_database(value['source'])
    if value['mode'] not in ('smoke','mature') or value['source']['format']!=6:raise ValueError('invalid source mode/format')
    if type(value['rules_id']) is not str or not value['rules_id'] or len(value['rules_id'])>256:raise ValueError('invalid rules')
    if value['rank_proofs'] is not True:raise ValueError('rank proofs required')
    exact(value['execution_runtime'],{'python','sqlite','signature'},'execution runtime')
    if any(type(value['execution_runtime'][k]) is not str or not value['execution_runtime'][k] for k in ('python','sqlite')):raise ValueError('invalid software versions')
    hexadecimal(value['execution_runtime']['signature'],64,'runtime signature')
    hexadecimal(value['runtime_tree'],40,'runtime tree');hexadecimal(value['expected_saved_digest'],64,'saved digest')
    if type(value['critical_blobs']) is not dict or not value['critical_blobs']:raise ValueError('missing critical code fence')
    for name,sha in value['critical_blobs'].items():
        if type(name) is not str or name.startswith('/') or '..' in name.split('/'):raise ValueError('invalid code path')
        hexadecimal(sha,40,'code blob')


def check_ref(value,*,remote=False):
    if value is None:
        if remote:raise ValueError('missing authenticated database reference')
        return
    if type(value) is not dict:raise ValueError('invalid data reference')
    if value=={'kind':'local'}:
        if remote:raise ValueError('local reference is not authenticated')
        return
    if value=={'kind':'retained-original'}:return
    exact(value,{'kind','artifact_id','run_id','head_sha','name','job','archive_sha256','archive_bytes','expires_at'},'artifact reference')
    if value['kind']!='github':raise ValueError('invalid artifact kind')
    for k in ('artifact_id','run_id','archive_bytes'):integer(value[k],k,1)
    hexadecimal(value['head_sha'],40,'producer head');hexadecimal(value['archive_sha256'],64,'archive digest')
    for k in ('name','job','expires_at'):
        if type(value[k]) is not str or not value[k] or len(value[k])>256:raise ValueError('invalid artifact '+k)


def validate(value,*,expected_context=None,require_remote=False,_depth=0):
    if _depth>=len(ORDER):raise ValueError('checkpoint chain too deep')
    exact(value,FIELDS,'checkpoint')
    if value['schema']!=SCHEMA or value['stage'] not in ORDER:raise ValueError('invalid checkpoint schema/stage')
    check_context(value['context']);check_database(value['database']);check_ref(value['data_ref'],remote=require_remote)
    if expected_context is not None and value['context']!=expected_context:raise ValueError('checkpoint context differs')
    if type(value['metrics']) is not dict:raise ValueError('invalid checkpoint metrics')
    p=value['producer'];exact(p,{'run_id','head_sha','job','attempt'},'producer')
    integer(p['run_id'],'run id',1);integer(p['attempt'],'run attempt',1);hexadecimal(p['head_sha'],40,'producer head')
    if p['job']!=JOB[value['stage']]:raise ValueError('wrong producing job')
    stage=value['stage'];index=ORDER.index(stage);parent=value['parent'];db=value['database'];ctx=value['context']
    if stage=='source':
        if parent is not None or db!=ctx['source'] or value['baseline_digest'] is not None or value['proof_commitment'] is not None:raise ValueError('invalid source receipt')
    else:
        exact(parent,{'sha256','receipt'},'parent')
        prior=validate(parent['receipt'],expected_context=ctx,require_remote=require_remote,_depth=_depth+1)
        if parent['sha256']!=receipt_hash(prior) or prior['stage']!=ORDER[index-1]:raise ValueError('checkpoint parent/order differs')
        if stage=='source_digest':hexadecimal(value['baseline_digest'],64,'baseline digest')
        elif value['baseline_digest']!=prior['baseline_digest']:raise ValueError('baseline digest changed')
        if stage in ('source_digest','after_digest','fresh_restore') and (db!=prior['database'] or value['data_ref']!=prior['data_ref']):raise ValueError('read-only checkpoint changed database')
        if stage=='capture' and db['generation']!=prior['database']['generation']:raise ValueError('capture generation changed')
        if stage in ('catalog','rebase','after_digest','proofs','measure','fresh_restore') and db['store_identity']!=prior['database']['store_identity']:raise ValueError('checkpoint identity changed')
        if stage=='catalog' and db['generation']!=prior['database']['generation']:raise ValueError('catalog generation changed')
        if stage in ('rebase','after_digest','proofs') and db['generation']!=0:raise ValueError('genesis generation differs')
        if stage in ('measure','fresh_restore') and db['generation']!=1:raise ValueError('saved successor generation differs')
        if stage in ('proofs','measure','fresh_restore'):hexadecimal(value['proof_commitment'],64,'proof commitment')
        elif value['proof_commitment'] is not None:raise ValueError('early proof commitment')
    if db['format']!=(7 if stage in ('proofs','measure','fresh_restore') else 6):raise ValueError('checkpoint format differs')
    if db['year']!=ctx['source']['year']+(stage in ('measure','fresh_restore')) or db['seed']!=ctx['source']['seed']:raise ValueError('checkpoint World differs')
    if value['data_ref']=={'kind':'retained-original'} and (ctx['mode']!='mature' or db!=ctx['source']):raise ValueError('retained source reference differs')
    if len(json.dumps(value,allow_nan=False))>MAX_METADATA:raise ValueError('checkpoint metadata exceeds cap')
    return value


def record(stage,context,database,producer,*,parent=None,data_ref=None,baseline_digest=None,proof_commitment=None,metrics=None):
    if parent is not None:
        if stage not in WRITES:data_ref=parent['data_ref']
        if stage!='source_digest':baseline_digest=parent['baseline_digest']
    row=copy.deepcopy(dict(schema=SCHEMA,stage=stage,context=context,
        parent=None if parent is None else dict(sha256=receipt_hash(parent),receipt=parent),database=database,
        data_ref=data_ref,baseline_digest=baseline_digest,proof_commitment=proof_commitment,producer=producer,metrics=metrics or {}))
    return validate(row,expected_context=context)


def describe(path,*,rules_id):
    from ate_sim.persistence_lazy_store import LazyRecordStore
    from ate_sim.persistence_adapters import WorldCodec,SCHEMA as SAVE_SCHEMA
    path=Path(path)
    if path.is_symlink() or not path.is_file() or any(Path(str(path)+suffix).exists() for suffix in ('-journal','-wal','-shm')):raise ValueError('checkpoint database must be closed and regular')
    with LazyRecordStore.open(path,codec=WorldCodec(identity_links_recorded=True),expected_simulation_schema=SAVE_SCHEMA,expected_rules_id=rules_id) as store:
        head=store.head_metadata()
        result=dict(bytes=path.stat().st_size,sha256=file_hash(path),store_identity=store.store_identity,
            generation=store.generation,format=int(store.db.execute("SELECT value FROM store_metadata WHERE key='format_version'").fetchone()[0]),year=head['simulation_position'],seed=head['seed'])
    check_database(result)
    return result


def verify_database(path,descriptor):
    path=Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size!=descriptor['bytes'] or file_hash(path)!=descriptor['sha256']:raise ValueError('checkpoint database bytes differ')


def publish(destination,value,*,database=None,move_owned=False):
    validate(value);destination=Path(destination)
    if destination.exists() or destination.is_symlink():raise FileExistsError(destination)
    destination.parent.mkdir(parents=True,exist_ok=True)
    if move_owned and (database is None or Path(database).name!='working.sqlite' or not Path(database).parent.name.startswith('.proof-stage-')):raise ValueError('transfer requires owned closed stage file')
    if database is not None:verify_database(database,value['database'])
    with tempfile.TemporaryDirectory(prefix='.genesis-seal-',dir=destination.parent) as directory:
        pending=Path(directory)
        if database is not None:
            if move_owned:Path(database).replace(pending/'candidate.sqlite')
            else:shutil.copyfile(database,pending/'candidate.sqlite')
            verify_database(pending/'candidate.sqlite',value['database'])
        data=(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
        if len(data)>MAX_METADATA:raise ValueError('checkpoint metadata exceeds cap')
        (pending/'checkpoint.json').write_bytes(data)
        for p in pending.iterdir():
            with p.open('rb') as stream:os.fsync(stream.fileno())
        destination.mkdir()
        try:
            # Metadata is published last; incomplete directories never validate.
            for name in ('candidate.sqlite','checkpoint.json'):
                if (pending/name).exists():os.link(pending/name,destination/name)
            from simulation.continuation_receipts import fsync_dir
            fsync_dir(destination);fsync_dir(destination.parent)
        except BaseException:
            shutil.rmtree(destination)
            raise
    return value


def load(directory,*,expected_context=None,require_remote=False):
    directory=Path(directory);p=directory/'checkpoint.json'
    if directory.is_symlink() or p.is_symlink() or not p.is_file() or p.stat().st_size>MAX_METADATA:raise ValueError('invalid checkpoint metadata file')
    if {x.name for x in directory.iterdir()} not in ({'checkpoint.json'},{'checkpoint.json','candidate.sqlite'}):raise ValueError('unexpected checkpoint files')
    value=validate(json.loads(p.read_text()),expected_context=expected_context,require_remote=require_remote)
    if (directory/'candidate.sqlite').exists():verify_database(directory/'candidate.sqlite',value['database'])
    return value
