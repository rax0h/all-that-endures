"""Import only a canonical expectation from an authenticated accepted source."""
import copy
from pathlib import Path
from simulation import continuation_receipts as r
from simulation import stage_0_6_genesis_checkpoint as c

COMPATIBILITY='simulation/stage_0_6_genesis_control_compatibility.json'


def check_compatibility(root,*,historical_runtime_sha,historical_runtime_tree,current_runtime_tree):
    root=Path(root);manifest=r.load_receipt(root/COMPATIBILITY)
    if (manifest.get('schema')!='ate-accepted-source-canonical-compatibility/1'
            or manifest.get('historical_runtime_sha')!=historical_runtime_sha
            or manifest.get('historical_runtime_tree')!=historical_runtime_tree
            or manifest.get('current_runtime_tree')!=current_runtime_tree):
        raise ValueError('unreviewed canonical/runtime compatibility pair')
    for name,hashes in manifest['files'].items():
        path=root/name
        if path.is_symlink() or not path.is_file() or c.file_hash(path)!=hashes['current_sha256']:
            raise ValueError('canonical/schema/model/codec definition differs: '+name)
    return dict(manifest_sha256=c.file_hash(root/COMPATIBILITY),
        historical_runtime_tree=historical_runtime_tree,current_runtime_tree=current_runtime_tree)


def read_accepted_control(path,*,source,rules_id,authority,source_ref,acceptance_ref,
                          expected_member_bytes,expected_member_sha256):
    """Caller authenticates transport; this boundary revalidates the exact member."""
    path=Path(path);c.check_database(source)
    c.integer(expected_member_bytes,'accepted member bytes',1)
    c.hexadecimal(expected_member_sha256,64,'accepted member hash')
    if (source['format']!=6 or expected_member_bytes>r.METADATA_MAX_BYTES
            or path.is_symlink() or not path.is_file()
            or path.stat().st_size!=expected_member_bytes
            or c.file_hash(path)!=expected_member_sha256):
        raise ValueError('accepted source member/format differs')
    accepted=r.load_receipt(path)
    r.validate_year_acceptance(accepted,authority)
    r.match_producer(acceptance_ref,accepted['producer'],authority)
    binding=accepted['binding']
    database=dict(name='candidate.sqlite',bytes=source['bytes'],sha256=source['sha256'])
    if (not r.same(binding['candidate'],source_ref.to_dict())
            or not r.same(binding['database'],database)
            or binding['store_identity']!=source['store_identity']
            or binding['generation']!=source['generation'] or binding['year']!=source['year']
            or rules_id!=authority.source_config['rules_id']
            or source['seed']!=authority.source_config['seed']):
        raise ValueError('accepted source binding/rules differ')
    original=r.original_from_text(accepted['original_checkpoint'],authority)
    digest=accepted['digest']['observation']['digest']
    if digest!=original['state']['controls'][str(source['year'])]['digest']:
        raise ValueError('accepted source digest differs from original control')
    c.hexadecimal(digest,64,'accepted source digest')
    return dict(method='historical-control-reused',digest=digest,source=copy.deepcopy(source),
        rules_id=rules_id,source_artifact=source_ref.to_dict(),acceptance=acceptance_ref.to_dict(),
        acceptance_member_bytes=expected_member_bytes,acceptance_member_sha256=expected_member_sha256,
        original_checkpoint_sha256=authority.checkpoint_sha256,proofs=copy.deepcopy(accepted['proofs']))


def mature_control_contract(root,*,current_runtime_tree):
    """Expected bindings only. This never authenticates an accepted member."""
    from simulation import construction_mature_continuation_stages as stages
    root=Path(root);old=r.load_receipt(root/'simulation/stage_0_6_proof_genesis_request.json')
    pin=r.load_receipt(root/'simulation/stage_0_5_save1002_preflight.json')
    authority=stages.mature_authority()
    source_ref=r.ArtifactRef.from_dict(pin['inputs']['candidate'])
    accepted=r.ArtifactRef.from_dict(pin['inputs']['previous'])
    compatibility=check_compatibility(root,historical_runtime_sha=source_ref.runtime_sha,
        historical_runtime_tree=source_ref.runtime_tree,current_runtime_tree=current_runtime_tree)
    if (authority.execution_runtime_sha!=source_ref.runtime_sha
            or authority.execution_runtime_tree!=source_ref.runtime_tree):
        raise ValueError('historical source runtime authority differs')
    manifest=r.load_receipt(root/COMPATIBILITY)
    source=dict(bytes=old['database']['bytes'],sha256=old['database']['sha256'],
        store_identity=old['pin']['store_identity'],generation=old['pin']['captured_head'],
        format=6,year=old['world']['year'],seed=old['world']['seed'])
    c.check_database(source)
    return dict(method='historical-control-reused',digest=manifest['source_digest'],source=source,
        rules_id=authority.source_config['rules_id'],source_artifact=source_ref.to_dict(),
        acceptance=accepted.to_dict(),acceptance_member_bytes=pin['actual_predecessor_member_bytes'],
        acceptance_member_sha256=pin['actual_predecessor_member_sha256'],
        original_checkpoint_sha256=authority.checkpoint_sha256,proofs=manifest['expected_proofs'],
        compatibility=compatibility)


def mature_control(root,path,source,*,current_runtime_tree):
    """Use only the actual member supplied by unchanged prepare_retained."""
    from simulation import construction_mature_continuation_stages as stages
    expected=mature_control_contract(root,current_runtime_tree=current_runtime_tree)
    if source!=expected['source']:raise ValueError('mature source differs from original accepted database')
    result=read_accepted_control(path,source=source,rules_id=expected['rules_id'],
        authority=stages.mature_authority(),source_ref=r.ArtifactRef.from_dict(expected['source_artifact']),
        acceptance_ref=r.ArtifactRef.from_dict(expected['acceptance']),
        expected_member_bytes=expected['acceptance_member_bytes'],
        expected_member_sha256=expected['acceptance_member_sha256'])
    result['compatibility']=expected['compatibility']
    if not r.same(result,expected):raise ValueError('accepted source differs from reviewed canonical control')
    return result


def validate_control_chain(root,value,*,current_runtime_tree):
    """Bind imported baseline metadata to the exact original authority on use."""
    c.validate(value)
    if value['context']['mode']!='mature' or value['stage']=='source':return
    source=value
    while source['stage']!='source_digest':source=source['parent']['receipt']
    expected=mature_control_contract(root,current_runtime_tree=current_runtime_tree)
    if (source['context']['source']!=expected['source']
            or source['context']['rules_id']!=expected['rules_id']
            or source['baseline_digest']!=expected['digest']
            or not r.same(source['metrics'].get('source_control'),expected)):
        raise ValueError('imported baseline canonical authority differs')
