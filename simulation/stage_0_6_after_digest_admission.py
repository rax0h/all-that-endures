"""Pinned proofs-only recovery; inherited catalog authority stays historical."""
import copy
from pathlib import Path
from simulation import continuation_receipts as r
from simulation import stage_0_6_genesis_checkpoint as c
from simulation import stage_0_6_genesis_transport as t
from simulation import stage_0_6_catalog_admission as legacy

CONTRACT='simulation/stage_0_6_after_digest_admission.json'
SUCCESSOR_CONTRACT='simulation/stage_0_6_after_digest_successor.json'


def contract(root):
    path=Path(root)/CONTRACT
    if path.is_symlink() or not path.is_file() or path.stat().st_size>c.MAX_METADATA:raise ValueError('invalid after-digest contract file')
    value=r.load_receipt(path)
    c.exact(value,{'schema','target_engine_tree','target_green_commit','engine_delta','historical_catalog_contract','after_digests'},'after-digest contract')
    if value['schema']!='ate-after-digest-runtime-admission-contract/1':raise ValueError('wrong after-digest contract schema')
    for key in ('target_engine_tree','target_green_commit'):c.hexadecimal(value[key],40,key)
    c.exact(value['engine_delta'],{'path','before_blob','after_blob'},'proof engine delta')
    for key in ('before_blob','after_blob'):c.hexadecimal(value['engine_delta'][key],40,key)
    old=value['historical_catalog_contract'];c.exact(old,{'path','blob','sha256'},'historical catalog contract')
    if old['path']!=legacy.CONTRACT:raise ValueError('wrong historical catalog contract path')
    c.hexadecimal(old['blob'],40,'old contract blob');c.hexadecimal(old['sha256'],64,'old contract hash')
    c.exact(value['after_digests'],{'smoke','mature'},'after-digest modes')
    for mode,pair in value['after_digests'].items():
        c.exact(pair,{'metadata','receipt_sha256','context','database','data_ref','source_control'},'after-digest input')
        c.check_ref(pair['metadata'],remote=True);c.check_ref(pair['data_ref'],remote=True)
        c.hexadecimal(pair['receipt_sha256'],64,'after-digest receipt hash');c.check_context(pair['context']);c.check_database(pair['database'])
        if pair['context']['mode']!=mode or pair['database']['format']!=6 or pair['database']['generation']!=0:raise ValueError('wrong after-digest mode/format/generation')
    return value


def eligible(root,mode,run_id,artifact_id=None):
    pair=contract(root)['after_digests'].get(mode)
    return bool(pair and pair['metadata']['run_id']==run_id and (artifact_id is None or pair['metadata']['artifact_id']==artifact_id))


def _target(root):
    from simulation import stage_0_6_genesis_resume as m
    base=contract(root);runtime,_=m.fence(root)
    successor=_successor(root,base) if runtime!=base['target_engine_tree'] else None
    target=successor or base
    if (runtime!=target['target_engine_tree'] or m.RUNTIME!=runtime or m.GREEN_SHA!=target['target_green_commit']
            or m.git(root,'rev-parse',m.GREEN_SHA+':simulation/ate_sim')!=runtime):raise ValueError('proof recovery target is not qualified')
    m.git(root,'merge-base','--is-ancestor',m.GREEN_SHA,'HEAD')
    return base,successor


def _successor(root,base):
    from simulation import stage_0_6_genesis_resume as m
    from simulation import stage_0_6_genesis_source_control as controls
    root=Path(root);path=root/SUCCESSOR_CONTRACT
    if path.is_symlink() or not path.is_file() or path.stat().st_size>c.MAX_METADATA:
        raise ValueError('invalid proof successor contract file')
    value=r.load_receipt(path)
    c.exact(value,{'schema','base_sha256','canonical_sha256','target_engine_tree','target_green_commit','engine_delta'},'proof successor')
    if (value['schema']!='ate-after-digest-proof-successor/1'
            or value['target_engine_tree']!=m.RUNTIME or value['target_green_commit']!=m.GREEN_SHA
            or c.file_hash(root/CONTRACT)!=value['base_sha256']
            or c.file_hash(root/controls.COMPATIBILITY)!=value['canonical_sha256']):
        raise ValueError('proof successor contract authority differs')
    old=base['target_green_commit'];new=value['target_green_commit']
    m.git(root,'merge-base','--is-ancestor',old,new)
    if m.git(root,'rev-parse',old+':simulation/ate_sim')!=base['target_engine_tree']:
        raise ValueError('proof successor base tree differs')
    delta=value['engine_delta']
    if type(delta) is not list or not delta:raise ValueError('proof successor engine delta is missing')
    expected=[]
    for entry in delta:
        c.exact(entry,{'path','before_blob','after_blob'},'proof successor engine delta')
        path=entry['path'];before=entry['before_blob'];after=entry['after_blob']
        c.hexadecimal(before,40,'proof successor before blob')
        c.hexadecimal(after,40,'proof successor after blob')
        if type(path) is not str or not path.startswith('simulation/ate_sim/') or '..' in path.split('/'):
            raise ValueError('invalid proof successor engine path')
        expected.append(f':100644 100644 {before} {after} M\t{path}')
    actual=m.git(root,'diff','--raw','--no-abbrev','--no-renames',old,new,'--','simulation/ate_sim')
    if sorted(actual.splitlines())!=sorted(expected):raise ValueError('unreviewed proof successor engine delta')
    return value


def canonical_successor(root,runtime,canonical_hash):
    from simulation import stage_0_6_genesis_resume as m
    if runtime!=m.RUNTIME:raise ValueError('unreviewed canonical/runtime compatibility pair')
    _,successor=_target(root)
    if successor is None or successor['canonical_sha256']!=canonical_hash:
        raise ValueError('unreviewed canonical/runtime compatibility pair')
    return c.file_hash(Path(root)/SUCCESSOR_CONTRACT)


def _historical_contract(root,value):
    from simulation import stage_0_6_genesis_resume as m
    old=value['historical_catalog_contract'];path=old['path']
    if c.file_hash(Path(root)/path)!=old['sha256'] or m.git(root,'rev-parse','HEAD:'+path)!=old['blob']:
        raise ValueError('historical catalog contract changed')
    return legacy.contract(root)


def _producer(root,head,context):
    from simulation import stage_0_6_genesis_resume as m
    m.git(root,'merge-base','--is-ancestor',head,'HEAD')
    if m.git(root,'rev-parse',head+':simulation/ate_sim')!=context['runtime_tree']:raise ValueError('historical producer engine differs')
    for path,blob in context['critical_blobs'].items():
        if m.git(root,'rev-parse',head+':'+path)!=blob:raise ValueError('historical producer helper differs')


def _delta(root,head,green,delta):
    from simulation import stage_0_6_genesis_resume as m
    path=delta['path']
    if not path.startswith('simulation/ate_sim/') or '..' in path.split('/'):raise ValueError('invalid proof recovery engine path')
    m.git(root,'merge-base','--is-ancestor',green,'HEAD')
    if (m.git(root,'diff','--name-only',head+':simulation/ate_sim',green+':simulation/ate_sim')!=path.removeprefix('simulation/ate_sim/')
            or m.git(root,'rev-parse',head+':'+path)!=delta['before_blob']
            or m.git(root,'rev-parse',green+':'+path)!=delta['after_blob']):raise ValueError('unreviewed historical proof engine delta')


def _verify_historical_head(root,value,old,mode,head):
    from simulation import stage_0_6_genesis_resume as m
    pair=value['after_digests'][mode];catalog=old['catalogs'][mode]
    if head==pair['metadata']['head_sha']:
        _producer(root,head,pair['context'])
        if m.git(root,'rev-parse',head+':'+legacy.CONTRACT)!=value['historical_catalog_contract']['blob']:raise ValueError('producer inherited different catalog contract')
        _delta(root,head,value['target_green_commit'],value['engine_delta'])
    elif head==catalog['metadata']['head_sha']:
        _producer(root,head,catalog['context']);_delta(root,head,old['target_green_commit'],old['engine_delta'])
    else:raise ValueError('unadmitted historical producer')


def verify_old_head(root,mode,head):
    value,_=_target(root)
    _verify_historical_head(root,value,_historical_contract(root,value),mode,head)


def _validate_prior(root,parent):
    from simulation import stage_0_6_genesis_resume as m
    c.validate(parent,require_remote=True);value,successor=_target(root);mode=parent['context']['mode'];pair=value['after_digests'][mode]
    if (parent['stage']!='after_digest' or c.receipt_hash(parent)!=pair['receipt_sha256']
            or parent['context']!=pair['context'] or parent['database']!=pair['database'] or parent['data_ref']!=pair['data_ref']):
        raise ValueError('historical after-digest differs from exact admitted receipt')
    m.match_receipt_reference(parent,pair['metadata'],mode=mode,stage='after_digest')
    old=_historical_contract(root,value);catalog=old['catalogs'][mode]
    _verify_historical_head(root,value,old,mode,parent['producer']['head_sha'])
    rebased=parent['parent']['receipt'];prior=rebased['parent']['receipt']
    if (old['target_engine_tree']!=parent['context']['runtime_tree']
            or m.git(root,'rev-parse',old['target_green_commit']+':simulation/ate_sim')!=old['target_engine_tree']
            or c.receipt_hash(prior)!=catalog['receipt_sha256'] or prior['context']!=catalog['context']
            or prior['database']!=catalog['database'] or prior['data_ref']!=catalog['data_ref']
            or rebased['metrics']['catalog_admission']['contract_sha256']!=value['historical_catalog_contract']['sha256']):
        raise ValueError('inherited historical catalog authority differs')
    m.match_receipt_reference(prior,catalog['metadata'],mode=mode,stage='catalog')
    _verify_historical_head(root,value,old,mode,prior['producer']['head_sha'])
    if pair['source_control']!=catalog['source_control']:raise ValueError('inherited source control differs')
    if mode=='mature':
        from simulation import stage_0_6_genesis_source_control as controls
        source=prior
        while source['stage']!='source_digest':source=source['parent']['receipt']
        if source['metrics'].get('source_control')!=pair['source_control']:raise ValueError('historical source control changed')
        runtime=(successor or value)['target_engine_tree']
        expected=controls.mature_control_contract(root,current_runtime_tree=runtime)
        previous=copy.deepcopy(pair['source_control']);current=copy.deepcopy(expected)
        before=previous.pop('compatibility');after=current.pop('compatibility')
        if (previous!=current or before['historical_runtime_tree']!=after['historical_runtime_tree']
                or before['current_runtime_tree']!=prior['context']['runtime_tree']
                or after['current_runtime_tree']!=runtime):raise ValueError('proof recovery canonical authority changed')
    return pair,successor


def validate_prior(root,parent):
    return _validate_prior(root,parent)[0]


def attest(root,parent,successor_context):
    from simulation import stage_0_6_genesis_resume as m
    _,successor=_validate_prior(root,parent)
    m.check_context(root,successor_context,parent['context']['mode'])
    path=SUCCESSOR_CONTRACT if successor is not None else CONTRACT
    stamp=dict(schema='ate-after-digest-runtime-admission/1',parent_sha256=c.receipt_hash(parent),
        parent_database=copy.deepcopy(parent['database']),from_context_sha256=c.receipt_hash(parent['context']),
        to_context_sha256=c.receipt_hash(successor_context),contract_sha256=c.file_hash(Path(root)/path))
    c.check_proofs_admission(parent,successor_context,stamp)
    return stamp


def cut(value):
    c.validate(value)
    while True:
        if 'proofs_admission' in value['metrics']:return value
        if value['parent'] is None:return None
        value=value['parent']['receipt']


def inspect_prior(root,mode,run_id,artifact_id=None):
    if not eligible(root,mode,run_id,artifact_id):raise ValueError('after-digest resume is not admitted')
    value,_=_target(root);pair=value['after_digests'][mode];old=_historical_contract(root,value)
    catalog=old['catalogs'][mode]
    for ref in (pair['metadata'],pair['data_ref'],catalog['metadata'],catalog['data_ref']):
        t.inspect_reference(ref,compatible=lambda head:_verify_historical_head(root,value,old,mode,head))
    return pair['metadata']


def validate_chain(root,value):
    transition=cut(value)
    if transition is None:return None
    parent=transition['parent']['receipt'];expected=attest(root,parent,transition['context'])
    if transition['metrics']['proofs_admission']!=expected:raise ValueError('proof recovery attestation differs from committed authority')
    pair=contract(root)['after_digests'][parent['context']['mode']]
    inspect_prior(root,parent['context']['mode'],pair['metadata']['run_id'],pair['metadata']['artifact_id'])
    return pair


def require_small_cut(root,value):
    pair=validate_chain(root,value)
    if pair is None or pair['context']['mode']!='smoke':raise ValueError('successful smoke lacks admitted after-digest cut')
    return pair


def restore_prior(root,mode,run_id,artifact_id,destination):
    ref=inspect_prior(root,mode,run_id,artifact_id)
    t.restore(ref,destination,member='checkpoint.json',compatible=lambda head:verify_old_head(root,mode,head))
    parent=c.load(destination,require_remote=True);validate_prior(root,parent)
    return ref,parent
