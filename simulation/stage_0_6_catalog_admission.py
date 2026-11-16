"""Exact retained catalog admission. Ordinary checkpoint compatibility is unchanged."""
import copy
from pathlib import Path

from simulation import continuation_receipts as r
from simulation import stage_0_6_genesis_checkpoint as c
from simulation import stage_0_6_genesis_transport as t

CONTRACT='simulation/stage_0_6_catalog_admission.json'


def contract(root):
    path=Path(root)/CONTRACT
    if path.is_symlink() or not path.is_file() or path.stat().st_size>c.MAX_METADATA:
        raise ValueError('invalid catalog admission contract file')
    value=r.load_receipt(path)
    c.exact(value,{'schema','target_engine_tree','target_green_commit','engine_delta','catalogs'},'admission contract')
    if value['schema']!='ate-catalog-runtime-admission-contract/1':raise ValueError('wrong admission contract schema')
    c.exact(value['catalogs'],{'smoke','mature'},'admitted catalogs')
    for key in ('target_engine_tree','target_green_commit'):c.hexadecimal(value[key],40,key)
    c.exact(value['engine_delta'],{'path','before_blob','after_blob'},'admitted engine delta')
    for key in ('before_blob','after_blob'):c.hexadecimal(value['engine_delta'][key],40,key)
    for mode,pair in value['catalogs'].items():
        c.exact(pair,{'metadata','receipt_sha256','context','database','data_ref','source_control'},'admitted catalog')
        c.check_ref(pair['metadata'],remote=True);c.check_ref(pair['data_ref'],remote=True)
        c.check_context(pair['context']);c.check_database(pair['database']);c.hexadecimal(pair['receipt_sha256'],64,'old catalog hash')
        if pair['context']['mode']!=mode:raise ValueError('admitted catalog mode differs')
    return value


def eligible(root,mode,run_id,artifact_id=None):
    pair=contract(root)['catalogs'].get(mode)
    return bool(pair and pair['metadata']['run_id']==run_id
                and (artifact_id is None or pair['metadata']['artifact_id']==artifact_id))


def _target(root):
    from simulation import stage_0_6_genesis_resume as m
    value=contract(root);runtime,blobs=m.fence(root)
    if (runtime!=value['target_engine_tree'] or m.RUNTIME!=runtime
            or m.GREEN_SHA!=value['target_green_commit']
            or m.git(root,'rev-parse',m.GREEN_SHA+':simulation/ate_sim')!=runtime):
        raise ValueError('admission target is not the qualified engine')
    m.git(root,'merge-base','--is-ancestor',m.GREEN_SHA,'HEAD')
    return value,runtime,blobs


def verify_old_head(root,mode,head):
    from simulation import stage_0_6_genesis_resume as m
    value,_,_=_target(root);pair=value['catalogs'][mode]
    if head!=pair['metadata']['head_sha']:raise ValueError('wrong admitted catalog producer')
    m.git(root,'merge-base','--is-ancestor',head,'HEAD')
    if m.git(root,'rev-parse',head+':simulation/ate_sim')!=pair['context']['runtime_tree']:
        raise ValueError('admitted producer engine differs')
    for name,blob in pair['context']['critical_blobs'].items():
        if m.git(root,'rev-parse',head+':'+name)!=blob:raise ValueError('admitted producer helper differs')
    delta=value['engine_delta'];path=delta['path']
    if not path.startswith('simulation/ate_sim/') or '..' in path.split('/'):
        raise ValueError('invalid admitted engine path')
    if (m.git(root,'diff','--name-only',head+':simulation/ate_sim',value['target_green_commit']+':simulation/ate_sim')
            !=path.removeprefix('simulation/ate_sim/')):
        raise ValueError('unreviewed engine delta')
    if (m.git(root,'rev-parse',head+':'+path)!=delta['before_blob']
            or m.git(root,'rev-parse',value['target_green_commit']+':'+path)!=delta['after_blob']):
        raise ValueError('admitted engine helper differs')


def validate_prior(root,parent):
    c.validate(parent,require_remote=True)
    mode=parent['context']['mode'];pair=contract(root)['catalogs'][mode]
    if (parent['stage']!='catalog' or c.receipt_hash(parent)!=pair['receipt_sha256']
            or parent['context']!=pair['context'] or parent['database']!=pair['database']
            or parent['data_ref']!=pair['data_ref']):raise ValueError('old catalog differs from exact admitted receipt')
    from simulation import stage_0_6_genesis_resume as m
    m.match_receipt_reference(parent,pair['metadata'],mode=mode,stage='catalog')
    verify_old_head(root,mode,parent['producer']['head_sha'])
    if mode=='mature':
        source=parent
        while source['stage']!='source_digest':source=source['parent']['receipt']
        if source['metrics'].get('source_control')!=pair['source_control']:
            raise ValueError('old admitted source control differs')
        from simulation import stage_0_6_genesis_source_control as controls
        expected=controls.mature_control_contract(root,current_runtime_tree=contract(root)['target_engine_tree'])
        old=copy.deepcopy(pair['source_control']);new=copy.deepcopy(expected)
        old_compat=old.pop('compatibility');new_compat=new.pop('compatibility')
        if (old!=new or old_compat['historical_runtime_tree']!=new_compat['historical_runtime_tree']
                or old_compat['current_runtime_tree']!=parent['context']['runtime_tree']
                or new_compat['current_runtime_tree']!=contract(root)['target_engine_tree']):
            raise ValueError('admitted source authority changed')
    return pair


def attest(root,parent,successor_context):
    from simulation import stage_0_6_genesis_resume as m
    validate_prior(root,parent);m.check_context(root,successor_context,parent['context']['mode'])
    stamp=dict(schema='ate-catalog-runtime-admission/1',parent_sha256=c.receipt_hash(parent),
        parent_database=copy.deepcopy(parent['database']),from_context_sha256=c.receipt_hash(parent['context']),
        to_context_sha256=c.receipt_hash(successor_context),contract_sha256=c.file_hash(Path(root)/CONTRACT))
    c.check_admission(parent,successor_context,stamp)
    return stamp


def cut(value):
    c.validate(value)
    while True:
        if 'catalog_admission' in value['metrics']:return value
        if value['parent'] is None:return None
        value=value['parent']['receipt']


def validate_chain(root,value):
    transition=cut(value)
    if transition is None:return None
    parent=transition['parent']['receipt']
    expected=attest(root,parent,transition['context'])
    if transition['metrics']['catalog_admission']!=expected:
        raise ValueError('catalog admission attestation is not current committed authority')
    ref=contract(root)['catalogs'][parent['context']['mode']]['metadata']
    inspect_prior(root,parent['context']['mode'],ref['run_id'],ref['artifact_id'])
    return contract(root)['catalogs'][parent['context']['mode']]


def require_small_cut(root,value):
    pair=validate_chain(root,value)
    if pair is None or pair['context']['mode']!='smoke':raise ValueError('successful smoke lacks the admitted small catalog cut')
    return pair


def inspect_prior(root,mode,run_id,artifact_id=None):
    if not eligible(root,mode,run_id,artifact_id):raise ValueError('catalog resume is not admitted')
    pair=contract(root)['catalogs'][mode];ref=pair['metadata']
    callback=lambda head:verify_old_head(root,mode,head)
    t.inspect_reference(ref,compatible=callback)
    t.inspect_reference(pair['data_ref'],compatible=callback)
    return ref


def restore_prior(root,mode,run_id,artifact_id,destination):
    ref=inspect_prior(root,mode,run_id,artifact_id)
    t.restore(ref,destination,member='checkpoint.json',compatible=lambda head:verify_old_head(root,mode,head))
    parent=c.load(destination,require_remote=True);validate_prior(root,parent)
    return ref,parent
