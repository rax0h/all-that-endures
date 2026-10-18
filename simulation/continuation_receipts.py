"""Strict validation-only continuation metadata; CI origin is authenticated by callers."""
from collections.abc import Mapping
from dataclasses import dataclass, fields
import hashlib
import json
import math
import os
from pathlib import Path
import re
import tempfile
from types import MappingProxyType


SCHEMA = 'ate-validation-continuation/1'
METADATA_MAX_BYTES = 16 * 1024**2
SAVED_MEMBERS = {'candidate.sqlite', 'checkpoint.json', 'save.json'}
STAGES = {'save', 'audit', 'digest', 'accept-year', 'accept-continuation',
          'restore-values', 'restore-digest', 'accept-restore'}


def plain(value):
    if isinstance(value, Mapping):
        return {key: plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(item) for item in value]
    return value


def frozen(value):
    if isinstance(value, Mapping):
        return MappingProxyType({key: frozen(item) for key, item in value.items()})
    if isinstance(value, (tuple, list)):
        return tuple(frozen(item) for item in value)
    return value


def canonical(value):
    return json.dumps(plain(value), sort_keys=True, allow_nan=False, separators=(',', ':'))


def same(left, right):
    return canonical(left) == canonical(right)


def exact(value, keys, label):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ValueError(f'invalid {label} fields')


def integer(value, label, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(f'invalid {label}')
    return value


def hexadecimal(value, size, label):
    if type(value) is not str or not re.fullmatch(f'[0-9a-f]{{{size}}}', value):
        raise ValueError(f'invalid {label}')


def text_value(value, label):
    if type(value) is not str or not value or len(value) > 256 or any(ord(c) < 32 for c in value):
        raise ValueError(f'invalid {label}')


def file_hash(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load_receipt(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > METADATA_MAX_BYTES:
        raise ValueError('invalid or oversized metadata file')
    return decode_receipt(path.read_bytes())


def decode_receipt(data):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate JSON member')
            result[key] = value
        return result
    def nonfinite(_value):
        raise ValueError('nonfinite JSON number')
    try:
        result = json.loads(data, object_pairs_hook=pairs, parse_constant=nonfinite)
    except (RecursionError, UnicodeError) as error:
        raise ValueError('invalid metadata encoding/nesting') from error
    if type(result) is not dict:
        raise ValueError('metadata must be an object')
    return result


def receipt_bytes(value):
    return (json.dumps(plain(value),sort_keys=True,indent=2,allow_nan=False)+'\n').encode()


def receipt_hash(value):
    return hashlib.sha256(receipt_bytes(value)).hexdigest()


def fsync_dir(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def publish_receipt(path, value):
    """Publish one durable new JSON file, preserving any existing destination."""
    path = Path(path)
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    data = receipt_bytes(value)
    if len(data) > METADATA_MAX_BYTES:
        raise ValueError('receipt exceeds metadata limit')
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.parent.is_symlink():
        raise ValueError('symlink receipt directory')
    with tempfile.TemporaryDirectory(prefix='.continue-receipt-', dir=path.parent) as directory:
        pending = Path(directory) / 'pending.json'
        with pending.open('xb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        linked = False
        try:
            os.link(pending, path)
            linked = True
            fsync_dir(path.parent)
        except BaseException:
            if linked and path.exists() and os.path.samestat(path.stat(), pending.stat()):
                path.unlink()
            raise


@dataclass(frozen=True)
class ArtifactRef:
    artifact_id: int
    run_id: int
    workflow_sha: str
    workflow_path: str
    producer_job: str
    name: str
    archive_sha256: str
    archive_bytes: int
    harness_sha: str
    runtime_sha: str
    runtime_tree: str

    def __post_init__(self):
        for key in ('artifact_id', 'run_id', 'archive_bytes'):
            integer(getattr(self, key), key, 1)
        for key in ('workflow_sha', 'harness_sha', 'runtime_sha', 'runtime_tree'):
            hexadecimal(getattr(self, key), 40, key)
        hexadecimal(self.archive_sha256, 64, 'archive SHA256')
        if type(self.workflow_path) is not str or not re.fullmatch(r'\.github/workflows/[\w.-]+\.ya?ml', self.workflow_path):
            raise ValueError('invalid artifact workflow path')
        for key in ('producer_job', 'name'):
            text_value(getattr(self, key), key)

    def to_dict(self):
        return {field.name: getattr(self, field.name) for field in fields(self)}

    @classmethod
    def from_dict(cls, value):
        exact(value, (field.name for field in fields(cls)), 'artifact')
        return cls(**value)


@dataclass(frozen=True)
class Authority:
    checkpoint_sha256: str
    checkpoint_bytes: int
    context: dict
    source_config: dict
    publication: ArtifactRef
    published_database_sha256: str
    published_database_bytes: int
    checkpoint_runtime_sha: str
    execution_runtime_sha: str
    execution_runtime_tree: str
    bootstrap_generation: int
    store_identity: str
    output_max_bytes: int

    def __post_init__(self):
        for key in ('checkpoint_sha256', 'published_database_sha256'):
            hexadecimal(getattr(self, key), 64, key)
        for key in ('checkpoint_runtime_sha', 'execution_runtime_sha', 'execution_runtime_tree'):
            hexadecimal(getattr(self, key), 40, key)
        for key in ('checkpoint_bytes', 'published_database_bytes', 'output_max_bytes'):
            integer(getattr(self, key), key, 1)
        integer(self.bootstrap_generation, 'bootstrap generation')
        text_value(self.store_identity, 'store identity')
        if (self.checkpoint_bytes > METADATA_MAX_BYTES or self.published_database_bytes > self.output_max_bytes
                or type(self.publication) is not ArtifactRef):
            raise ValueError('invalid original authority sizes/publication')
        config, context = plain(self.source_config), plain(self.context)
        exact(config, ('seed', 'milestones', 'bootstrap_year', 'rules_id', 'product_sha',
                       'complete_format', 'initialization', 'simulation_schema'), 'source configuration')
        integer(config['seed'], 'seed'); integer(config['bootstrap_year'], 'bootstrap year')
        if (type(config['milestones']) is not list or len(config['milestones']) != 2
                or any(type(y) is not int for y in config['milestones'])
                or config['milestones'] != [config['bootstrap_year']+1, config['bootstrap_year']+2]
                or config['complete_format'] is not True
                or config['initialization'] not in ('mature', 'founders')
                or config['simulation_schema'] != 'ate-world-p2a/1'):
            raise ValueError('invalid original continuation configuration')
        hexadecimal(config['product_sha'], 40, 'original product')
        text_value(config['rules_id'], 'rules')
        exact(context, ('runtime_sha', 'harness_sha', 'source_artifact'), 'context')
        for key in ('runtime_sha', 'harness_sha'):
            hexadecimal(context[key], 40, 'original context commit')
        exact(context['source_artifact'], ('id', 'run_id', 'archive_sha256'), 'source artifact')
        for key in ('id', 'run_id'):
            integer(context['source_artifact'][key], key, 1)
        hexadecimal(context['source_artifact']['archive_sha256'], 64, 'source archive')
        object.__setattr__(self, 'context', frozen(context))
        object.__setattr__(self, 'source_config', frozen(config))

    def to_dict(self):
        return {field.name: (self.publication.to_dict() if field.name == 'publication'
                             else plain(getattr(self, field.name))) for field in fields(self)}

    @classmethod
    def from_dict(cls, value):
        exact(value, (field.name for field in fields(cls)), 'authority')
        return cls(**dict(value, publication=ArtifactRef.from_dict(value['publication'])))


def validate_producer(value, stage=None):
    exact(value, ('harness_sha', 'workflow_sha', 'run_id', 'job', 'stage'), 'producer')
    hexadecimal(value['harness_sha'], 40, 'producing harness')
    hexadecimal(value['workflow_sha'], 40, 'producing workflow')
    integer(value['run_id'], 'producing run', 1)
    text_value(value['job'], 'producing job')
    if value['stage'] not in STAGES or (stage is not None and value['stage'] != stage):
        raise ValueError('invalid producing stage')


def validate_original(checkpoint, authority):
    checkpoint = Path(checkpoint)
    if (checkpoint.is_symlink() or not checkpoint.is_file()
            or checkpoint.stat().st_size != authority.checkpoint_bytes
            or file_hash(checkpoint) != authority.checkpoint_sha256):
        raise ValueError('original checkpoint bytes differ')
    return _validate_original_record(load_receipt(checkpoint), authority)


def original_from_text(value, authority):
    if type(value) is not str:
        raise ValueError('missing exact original checkpoint text')
    data = value.encode()
    if len(data) != authority.checkpoint_bytes or hashlib.sha256(data).hexdigest() != authority.checkpoint_sha256:
        raise ValueError('original checkpoint text differs')
    return _validate_original_record(decode_receipt(data),authority)


def _validate_original_record(receipt, authority):
    config = dict(plain(authority.source_config), product_sha=authority.checkpoint_runtime_sha)
    if (type(receipt.get('schema')) is not int or receipt['schema'] != 1 or receipt.get('stage') != 'complete'
            or not same(receipt.get('config'), config)
            or receipt.get('workflow_sha') != authority.publication.workflow_sha
            or receipt.get('product_sha') != authority.checkpoint_runtime_sha
            or receipt.get('checkpoint_product_sha') != authority.source_config['product_sha']
            or receipt.get('database') != {'name': 'p5-long-complete.sqlite', 'sha256': authority.published_database_sha256}):
        raise ValueError('original checkpoint configuration/producer mismatch')
    state = receipt.get('state', {})
    conversion = state.get('conversion_result', {})
    expected = dict(source_generation=authority.bootstrap_generation-1,
        generation=authority.bootstrap_generation,store_identity=authority.store_identity,
        source_preserved=True,complete_format=True)
    controls = state.get('controls', {})
    if not same(conversion, expected) or set(controls) != {str(y) for y in authority.source_config['milestones']}:
        raise ValueError('original generation/control authority mismatch')
    for year in authority.source_config['milestones']:
        control = controls[str(year)]
        hexadecimal(control.get('digest'), 64, 'independent digest')
        validate_counters(control.get('counters'))
        if not isinstance(control.get('audit'), dict) or type(control['audit'].get('year')) is not int or control['audit']['year'] != year:
            raise ValueError('original audit authority mismatch')
    return receipt


def validate_counters(value):
    if type(value) is not dict or not value:
        raise ValueError('invalid counters')
    for key, count in value.items():
        text_value(key, 'counter name'); integer(count, 'counter')


def validate_metrics(value):
    exact(value, ('phases', 'io', 'working_set'), 'metrics')
    if any(type(value[key]) is not dict for key in value):
        raise ValueError('invalid metrics')
    def measurements(item):
        if type(item) is dict:
            for key, child in item.items():
                text_value(key, 'metric name'); measurements(child)
        elif item is not None and (type(item) not in (int, float) or not math.isfinite(item) or item < 0):
            raise ValueError('invalid metric value')
    measurements(value)


SAVE_KEYS = {'schema','stage','authority','producer','previous_year','year','previous_generation',
             'generation','store_identity','database','checkpoint','predecessor','live_before','live_after','metrics'}


def validate_save_manifest(saved, authority, original, *, expected_year, expected_predecessor, producer):
    exact(saved, SAVE_KEYS, 'saved manifest')
    validate_producer(saved['producer'], 'save')
    if (not same(saved['producer'], producer) or saved['schema'] != SCHEMA
            or saved['stage'] != 'year-saved-unverified' or not same(saved['authority'], authority.to_dict())
            or not same(saved['predecessor'], expected_predecessor)):
        raise ValueError('saved source/runtime/producer/predecessor mismatch')
    integer(expected_year, 'expected year')
    if expected_year not in authority.source_config['milestones']:
        raise ValueError('unexpected milestone')
    if expected_year == authority.source_config['milestones'][0]:
        if not same(saved['predecessor'], dict(kind='publication', artifact=authority.publication.to_dict())):
            raise ValueError('saved publication predecessor differs')
    else:
        exact(saved['predecessor'], ('kind','artifact','receipt_sha256','receipt'), 'year predecessor')
        if saved['predecessor']['kind'] != 'year-verified':
            raise ValueError('second year needs verified predecessor')
        predecessor_artifact = ArtifactRef.from_dict(saved['predecessor']['artifact'])
        hexadecimal(saved['predecessor']['receipt_sha256'], 64, 'predecessor receipt digest')
        previous = saved['predecessor']['receipt']
        if type(previous) is not dict or previous.get('binding',{}).get('year') != expected_year-1:
            raise ValueError('saved predecessor must be the first verified year')
        validate_year_acceptance(previous,authority)
        match_producer(predecessor_artifact,previous['producer'],authority)
        if receipt_hash(previous) != saved['predecessor']['receipt_sha256']:
            raise ValueError('saved predecessor receipt digest differs')
    for key in ('previous_year','year','previous_generation','generation'):
        integer(saved[key], key)
    generation = authority.bootstrap_generation + expected_year - authority.source_config['bootstrap_year']
    if (saved['year'] != expected_year or saved['previous_year'] != expected_year-1
            or saved['generation'] != generation or saved['previous_generation'] != generation-1
            or saved['store_identity'] != authority.store_identity):
        raise ValueError('saved year/generation/identity mismatch')
    exact(saved['database'], ('name','bytes','sha256'), 'saved database')
    integer(saved['database']['bytes'], 'database bytes', 1)
    hexadecimal(saved['database']['sha256'], 64, 'database digest')
    if saved['database']['name'] != 'candidate.sqlite' or saved['database']['bytes'] > authority.output_max_bytes:
        raise ValueError('saved database name/size mismatch')
    if not same(saved['checkpoint'], dict(name='checkpoint.json', bytes=authority.checkpoint_bytes, sha256=authority.checkpoint_sha256)):
        raise ValueError('saved original checkpoint mismatch')
    expected_live = dict(year=expected_year, counters=original['state']['controls'][str(expected_year)]['counters'])
    for key in ('live_before','live_after'):
        exact(saved[key], ('year','counters'), 'live counters')
        integer(saved[key]['year'], 'live year'); validate_counters(saved[key]['counters'])
        if not same(saved[key], expected_live):
            raise ValueError('saved live counters differ from independent control')
    validate_metrics(saved['metrics'])
    return saved


def validate_saved(bundle, *, authority, expected_year, expected_predecessor, producer):
    bundle = Path(bundle)
    if (bundle.is_symlink() or not bundle.is_dir() or {p.name for p in bundle.iterdir()} != SAVED_MEMBERS
            or any(p.is_symlink() or not p.is_file() for p in bundle.iterdir())):
        raise ValueError('unexpected saved bundle members')
    original = validate_original(bundle/'checkpoint.json', authority)
    saved = validate_save_manifest(load_receipt(bundle/'save.json'), authority, original,
        expected_year=expected_year, expected_predecessor=expected_predecessor, producer=producer)
    db = bundle/'candidate.sqlite'
    if db.stat().st_size != saved['database']['bytes'] or file_hash(db) != saved['database']['sha256']:
        raise ValueError('saved database bytes differ')
    return saved


def match_producer(artifact, producer, authority):
    validate_producer(producer)
    if (artifact.run_id != producer['run_id'] or artifact.workflow_sha != producer['workflow_sha']
            or artifact.harness_sha != producer['harness_sha'] or artifact.producer_job != producer['job']
            or artifact.runtime_sha != authority.execution_runtime_sha
            or artifact.runtime_tree != authority.execution_runtime_tree):
        raise ValueError('artifact producer/runtime differs from stage receipt')


def saved_binding(saved, candidate, manifest_sha256):
    return dict(year=saved['year'],generation=saved['generation'],store_identity=saved['store_identity'],
        database=saved['database'],save_sha256=manifest_sha256,candidate=candidate.to_dict(),
        checkpoint_sha256=saved['checkpoint']['sha256'],runtime_sha=saved['authority']['execution_runtime_sha'],
        runtime_tree=saved['authority']['execution_runtime_tree'])


def validate_binding(value, authority):
    exact(value, ('year','generation','store_identity','database','save_sha256','candidate',
                  'checkpoint_sha256','runtime_sha','runtime_tree'), 'candidate binding')
    integer(value['year'],'bound year'); integer(value['generation'],'bound generation')
    if (value['year'] not in authority.source_config['milestones']
            or value['generation'] != authority.bootstrap_generation+value['year']-authority.source_config['bootstrap_year']
            or value['store_identity'] != authority.store_identity
            or value['checkpoint_sha256'] != authority.checkpoint_sha256
            or value['runtime_sha'] != authority.execution_runtime_sha
            or value['runtime_tree'] != authority.execution_runtime_tree):
        raise ValueError('bound original year/generation/runtime differs')
    ArtifactRef.from_dict(value['candidate'])
    hexadecimal(value['save_sha256'],64,'saved manifest digest')
    exact(value['database'],('name','bytes','sha256'),'bound database')
    integer(value['database']['bytes'],'bound database bytes',1)
    hexadecimal(value['database']['sha256'],64,'bound database SHA256')
    if value['database']['name'] != 'candidate.sqlite' or value['database']['bytes'] > authority.output_max_bytes:
        raise ValueError('bound database differs')


VERIFICATION_KEYS = {'schema','stage','authority','producer','binding','observation',
                     'metrics','input_preserved','original_checkpoint','saved'}
VERIFICATION_STAGES = {'audit':'year-audited','digest':'year-digest-verified',
                       'restore-values':'restore-values-verified','restore-digest':'restore-digest-verified'}


def normalized_audit(value):
    return {key:item for key,item in value.items() if key != 'audit_seconds'}


def validate_verification(row, authority, *, kind, binding):
    keys = VERIFICATION_KEYS | ({'continuation'} if kind.startswith('restore-') else set())
    exact(row,keys,'verification receipt')
    validate_producer(row['producer'],kind)
    validate_binding(row['binding'],authority)
    if (row['schema'] != SCHEMA or row['stage'] != VERIFICATION_STAGES[kind]
            or not same(row['authority'],authority.to_dict()) or not same(row['binding'],binding)
            or row['input_preserved'] is not True):
        raise ValueError('verification candidate/authority mismatch')
    original = original_from_text(row['original_checkpoint'],authority)
    saved = row['saved']
    validate_save_manifest(saved,authority,original,expected_year=binding['year'],
        expected_predecessor=saved.get('predecessor'),producer=saved.get('producer'))
    candidate = ArtifactRef.from_dict(binding['candidate'])
    match_producer(candidate,saved['producer'],authority)
    if not same(binding,saved_binding(saved,candidate,receipt_hash(saved))):
        raise ValueError('verified saved manifest differs from candidate binding')
    control = original['state']['controls'][str(binding['year'])]
    observation = row['observation']
    extra = {'audit','audited_state'} if kind == 'audit' else {'snapshot','restored_state'} if kind == 'restore-values' else {'digest'}
    exact(observation,{'year','generation','store_identity','counters'}|extra,'verification observation')
    for key in ('year','generation'):
        integer(observation[key],key)
    validate_counters(observation['counters'])
    if (any(observation[key] != binding[key] for key in ('year','generation','store_identity'))
            or not same(observation['counters'],control['counters'])):
        raise ValueError('observed state/counters differ from original control')
    if kind == 'audit':
        if (observation['audited_state'] != 'saved-reopened' or type(observation['audit']) is not dict
                or not same(normalized_audit(observation['audit']),normalized_audit(control['audit']))):
            raise ValueError('full saved audit differs from original control')
    elif kind == 'restore-values':
        if observation['restored_state'] != 'downloaded-reopened' or not same(observation['snapshot'],control['audit']['snapshot']):
            raise ValueError('actual restored values differ from original control')
    elif observation['digest'] != control['digest']:
        raise ValueError('full reopened digest differs from original control')
    validate_metrics(row['metrics'])
    return row


YEAR_KEYS = {'schema','stage','stage_0_5_accepted','authority','producer','binding','saved',
             'audit','digest','proofs','previous_acceptance','original_checkpoint'}


def validate_year_acceptance(row, authority):
    exact(row,YEAR_KEYS,'year acceptance')
    validate_producer(row['producer'],'accept-year')
    validate_binding(row['binding'],authority)
    if (row['schema'] != SCHEMA or row['stage'] != 'year-verified'
            or row['stage_0_5_accepted'] is not False or not same(row['authority'],authority.to_dict())):
        raise ValueError('year acceptance authority/stage differs')
    original = original_from_text(row['original_checkpoint'],authority)
    year = row['binding']['year']
    previous = row['previous_acceptance']
    if year == authority.source_config['milestones'][0]:
        if previous is not None:
            raise ValueError('first year has a foreign prior acceptance')
    else:
        if type(previous) is not dict or previous.get('binding',{}).get('year') != year-1:
            raise ValueError('second year lacks the first verified year')
        validate_year_acceptance(previous,authority)
        if not same(row['saved'].get('predecessor',{}).get('receipt'),previous):
            raise ValueError('saved predecessor and accepted lineage differ')
        if not same(row['saved'].get('database'),row['binding']['database']):
            raise ValueError('saved candidate database differs')
    validate_save_manifest(row['saved'],authority,original,expected_year=year,
        expected_predecessor=row['saved'].get('predecessor'),producer=row['saved'].get('producer'))
    candidate = ArtifactRef.from_dict(row['binding']['candidate'])
    match_producer(candidate,row['saved']['producer'],authority)
    expected_binding = saved_binding(row['saved'],candidate,receipt_hash(row['saved']))
    if not same(row['binding'],expected_binding):
        raise ValueError('year acceptance saved manifest/candidate differs')
    exact(row['proofs'],('audit','digest'),'year verification proofs')
    for kind in ('audit','digest'):
        validate_verification(row[kind],authority,kind=kind,binding=row['binding'])
        proof = row['proofs'][kind]
        exact(proof,('artifact','receipt_sha256'),'verification artifact proof')
        ref = ArtifactRef.from_dict(proof['artifact'])
        match_producer(ref,row[kind]['producer'],authority)
        if proof['receipt_sha256'] != receipt_hash(row[kind]):
            raise ValueError('verification receipt member digest differs')
    return row


def accept_year(saved,audit,digest,*,authority,candidate,audit_proof,digest_proof,previous_acceptance,producer):
    row = dict(schema=SCHEMA,stage='year-verified',stage_0_5_accepted=False,
        authority=authority.to_dict(),producer=producer,
        binding=saved_binding(saved,candidate,receipt_hash(saved)),saved=saved,audit=audit,digest=digest,
        proofs=dict(audit=dict(artifact=audit_proof.to_dict(),receipt_sha256=receipt_hash(audit)),
            digest=dict(artifact=digest_proof.to_dict(),receipt_sha256=receipt_hash(digest))),
        previous_acceptance=previous_acceptance,original_checkpoint=audit.get('original_checkpoint'))
    validate_year_acceptance(row,authority)
    return decode_receipt(canonical(row))


CONTINUATION_KEYS = {'schema','stage','stage_0_5_accepted','authority','producer','first','second',
                     'final_binding','original_checkpoint'}


def validate_continuation(row,authority):
    exact(row,CONTINUATION_KEYS,'continuation acceptance')
    validate_producer(row['producer'],'accept-continuation')
    if (row['schema'] != SCHEMA or row['stage'] != 'continuation-verified'
            or row['stage_0_5_accepted'] is not False or not same(row['authority'],authority.to_dict())):
        raise ValueError('continuation acceptance authority differs')
    original_from_text(row['original_checkpoint'],authority)
    first,second = row['first'],row['second']
    validate_year_acceptance(first,authority); validate_year_acceptance(second,authority)
    if (first['binding']['year'] != authority.source_config['milestones'][0]
            or second['binding']['year'] != authority.source_config['milestones'][1]
            or not same(second['previous_acceptance'],first)
            or not same(row['final_binding'],second['binding'])):
        raise ValueError('continuation lacks exact ordered milestone lineage')
    return row


def accept_continuation(first,second,*,authority,producer):
    row = dict(schema=SCHEMA,stage='continuation-verified',stage_0_5_accepted=False,
        authority=authority.to_dict(),producer=producer,first=first,second=second,
        final_binding=second.get('binding'),original_checkpoint=first.get('original_checkpoint'))
    validate_continuation(row,authority)
    return decode_receipt(canonical(row))


def continuation_reference(continuation):
    return dict(receipt_sha256=receipt_hash(continuation),producer=continuation['producer'],
        final_binding=continuation['final_binding'])


RESTORE_KEYS = {'schema','stage','stage_0_5_accepted','authority','producer','binding',
                'values','digest','continuation','proofs','original_checkpoint'}


def validate_restore_acceptance(row,authority):
    exact(row,RESTORE_KEYS,'independent restore acceptance')
    validate_producer(row['producer'],'accept-restore')
    if (row['schema'] != SCHEMA or row['stage'] != 'restore-verified'
            or row['stage_0_5_accepted'] is not False or not same(row['authority'],authority.to_dict())):
        raise ValueError('independent restore authority differs')
    original_from_text(row['original_checkpoint'],authority)
    validate_continuation(row['continuation'],authority)
    binding = row['continuation']['final_binding']
    if not same(row['binding'],binding):
        raise ValueError('independent restore candidate differs')
    exact(row['proofs'],('values','digest','continuation'),'restore proofs')
    for label,kind in (('values','restore-values'),('digest','restore-digest'),('continuation','accept-continuation')):
        proof = row['proofs'][label]
        exact(proof,('artifact','receipt_sha256'),'restore artifact proof')
        ref = ArtifactRef.from_dict(proof['artifact'])
        source = row[label]
        match_producer(ref,source['producer'],authority)
        if proof['receipt_sha256'] != receipt_hash(source):
            raise ValueError('restored receipt member digest differs')
        if label != 'continuation':
            validate_verification(source,authority,kind=kind,binding=binding)
            if not same(source['continuation'],continuation_reference(row['continuation'])):
                raise ValueError('independent restore observed another continuation')
    return row


def accept_restore(values,digest,*,continuation,proofs,producer):
    authority = Authority.from_dict(continuation['authority'])
    exact(proofs,('values','digest','continuation'),'external restore proofs')
    sources = dict(values=values,digest=digest,continuation=continuation)
    refs = {key:(value if type(value) is ArtifactRef else ArtifactRef.from_dict(value)) for key,value in proofs.items()}
    row = dict(schema=SCHEMA,stage='restore-verified',stage_0_5_accepted=False,
        authority=authority.to_dict(),producer=producer,binding=continuation['final_binding'],
        values=values,digest=digest,continuation=continuation,
        proofs={key:dict(artifact=refs[key].to_dict(),receipt_sha256=receipt_hash(sources[key])) for key in refs},
        original_checkpoint=continuation['original_checkpoint'])
    validate_restore_acceptance(row,authority)
    return decode_receipt(canonical(row))
