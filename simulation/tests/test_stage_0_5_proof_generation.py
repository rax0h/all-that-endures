"""Manifest bindings are data, never proof that synthetic roots are complete."""
import hashlib
import importlib
from dataclasses import replace
import pytest
from ate_sim.incremental_store import StoreError,StoreIntegrityError,StoreConflictError
from ate_sim.persistence_lazy_store import _receipt_checksum
from ate_sim.persistence_proof_nodes import Root


def module():return importlib.import_module('ate_sim.persistence_proof_generation')


def specimen(generation=1,parent=b'p'*32):
    m=module();head=m.ManifestHead(b'position',b'ids',b'namespaces',b'counts',7,4)
    receipt=None if generation==0 else m.ManifestReceipt('writer',b'encoded-token',_receipt_checksum('writer',b'encoded-token',generation,generation-1,'committed'))
    return m.GenerationManifest('store',generation,None if generation==0 else parent,'3',1,'8','rules',head,
        tuple(Root(bytes([i+1])*32,i) for i in range(7)),receipt)


def test_independent_binary_vector_and_digest():
    m=module();value=specimen();raw=m.encode_manifest(value)
    fields=[b'store',(1).to_bytes(8,'big'),(0).to_bytes(8,'big'),b'p'*32,b'3',(1).to_bytes(8,'big'),b'8',b'rules',
        (4).to_bytes(8,'big'),b'\x01'+(7).to_bytes(8,'big',signed=True),b'position',b'ids',b'namespaces',b'counts']
    fields += [bytes([i+1])*32+i.to_bytes(8,'big') for i in range(7)]
    fields += [b'writer',b'encoded-token',value.receipt.checksum.encode('ascii')]
    expected=b'ATEG\x01'+b''.join(len(p).to_bytes(4,'big')+p for p in fields)
    assert raw==expected
    tag=b'ate-generation-manifest/1'
    digest=hashlib.sha256(len(tag).to_bytes(8,'big')+tag+len(expected).to_bytes(8,'big')+expected).digest()
    assert m.manifest_commitment(value)==digest and m.decode_manifest(expected,digest)==value


@pytest.mark.parametrize('generation',[0,1,2,2**63-1])
def test_round_trip(generation):
    m=module();v=specimen(generation);assert m.decode_manifest(m.encode_manifest(v),m.manifest_commitment(v))==v


@pytest.mark.parametrize('fault',['gen-bool','negative','parent-missing','gen0-parent','codec-bool','store-empty','store-nul','schema-surrogate','format-empty',
    'allocator-bool','seed-bool','root-count-bool','root-digest','root-missing','root-list','receipt-missing','receipt-token','receipt-checksum'])
def test_malformed_fields_reject(fault):
    m=module();v=specimen()
    if fault=='gen-bool':v=replace(v,generation=True)
    elif fault=='negative':v=replace(v,generation=-1)
    elif fault=='parent-missing':v=replace(v,parent_commitment=None)
    elif fault=='gen0-parent':v=replace(specimen(0),parent_commitment=b'p'*32)
    elif fault=='codec-bool':v=replace(v,codec_version=True)
    elif fault=='store-empty':v=replace(v,store_identity='')
    elif fault=='store-nul':v=replace(v,store_identity='s\x00')
    elif fault=='schema-surrogate':v=replace(v,simulation_schema='\ud800')
    elif fault=='format-empty':v=replace(v,format_version='')
    elif fault=='allocator-bool':v=replace(v,head=replace(v.head,next_incarnation_id=True))
    elif fault=='seed-bool':v=replace(v,head=replace(v.head,seed=True))
    elif fault=='root-count-bool':v=replace(v,roots=(Root(b'x'*32,True),)+v.roots[1:])
    elif fault=='root-digest':v=replace(v,roots=(Root(b'x',1),)+v.roots[1:])
    elif fault=='root-missing':v=replace(v,roots=v.roots[:-1])
    elif fault=='root-list':v=replace(v,roots=list(v.roots))
    elif fault=='receipt-missing':v=replace(v,receipt=None)
    elif fault=='receipt-token':v=replace(v,receipt=replace(v.receipt,encoded_commit_token='token'))
    else:v=replace(v,receipt=replace(v.receipt,checksum='0'*64))
    with pytest.raises(StoreIntegrityError):m.encode_manifest(v)


@pytest.mark.parametrize('fault',['expected','trailing','truncated','tag','parent-generation','huge-field'])
def test_ingress_bytes_and_expected_reject(fault):
    m=module();v=specimen();raw=m.encode_manifest(v);expected=m.manifest_commitment(v)
    if fault=='expected':expected=b'x'*32
    elif fault=='trailing':raw+=b'\x00'
    elif fault=='truncated':raw=raw[:-1]
    elif fault=='tag':raw=b'OTHER'+raw[5:]
    elif fault=='huge-field':raw=raw[:5]+(2**32-1).to_bytes(4,'big')+raw[9:]
    else:
        # First field length5 + frame4, generation8 +frame4, then parent frame.
        start=5+4+5+4+8+4;raw=raw[:start]+(9).to_bytes(8,'big')+raw[start+8:]
    with pytest.raises(StoreIntegrityError):m.decode_manifest(raw,expected)


@pytest.mark.parametrize('fault',['parent','token','store','rules','allocator'])
def test_successor_exact_parent_token_context(fault):
    m=module();parent=specimen();expected=m.manifest_commitment(parent);child=specimen(2,expected)
    assert m.validate_successor(parent,expected,child,m.manifest_commitment(child),b'encoded-token') is None
    token=b'encoded-token'
    if fault=='parent':child=replace(child,parent_commitment=b'x'*32)
    elif fault=='token':token=b'other'
    elif fault=='store':child=replace(child,store_identity='other')
    elif fault=='rules':child=replace(child,rules_id='other')
    else:child=replace(child,head=replace(child.head,next_incarnation_id=3))
    with pytest.raises((StoreIntegrityError,StoreConflictError)):m.validate_successor(parent,expected,child,m.manifest_commitment(child),token)


def test_source_current_retained_and_zero_body_reads(tmp_path):
    from simulation.tests.proof_generation_fixtures import make_generation_store,metadata,install
    from ate_sim.persistence_lazy_store import VersionChange
    m=module();store,pin,pair=make_generation_store(tmp_path/'manifest.sqlite');old=store.capture_pin();sql=[]
    store.db.set_trace_callback(sql.append);store.reset_diagnostics()
    assert m.read_generation_manifest(store,pin,pair[1])==pair[0]
    assert store.diagnostics().payload_reads==0 and not any('then payload end' in s.lower() for s in sql)
    writer=store.commit(pin,commit_token='next',version_changes=(VersionChange('archive',0,b'new'),),changes=(),new_segments=(),metadata=metadata(2)).pin
    successor=install(store,writer,pair[1])
    assert m.read_generation_manifest(store,old,pair[1])==pair[0]
    assert m.read_generation_manifest(store,writer,successor[1])==successor[0]
    m.validate_successor(*pair,*successor,store.codec.encode('next'))
    store.close()


@pytest.mark.parametrize('fault',['missing','bytes','digest','text','head','allocator','format','uuid','expected','released','transaction','hook','budget','metadata-budget','schema'])
def test_source_authority_context_corruption(tmp_path,fault):
    from simulation.tests.proof_generation_fixtures import make_generation_store
    from ate_sim.incremental_store import _head_checksum
    m=module();store,pin,pair=make_generation_store(tmp_path/'bad.sqlite');expected=pair[1];kwargs={}
    if fault=='missing':store.db.execute('DELETE FROM ate_generation_manifests WHERE generation=1')
    elif fault=='bytes':store.db.execute("UPDATE ate_generation_manifests SET manifest=x'00' WHERE generation=1")
    elif fault=='digest':store.db.execute('UPDATE ate_generation_manifests SET commitment=? WHERE generation=1',(b'x'*32,))
    elif fault=='text':store.db.execute("UPDATE ate_generation_manifests SET manifest='x' WHERE generation=1")
    elif fault=='head':
        store.db.execute('UPDATE save_head SET seed=8');row=store.db.execute('SELECT generation,parent_generation,simulation_position,seed,next_ids,namespace_inventory,namespace_counts FROM save_head').fetchone()
        store.db.execute('UPDATE save_head SET head_checksum=?',(_head_checksum(*row),))
    elif fault=='allocator':
        changed=replace(pair[0],head=replace(pair[0].head,next_incarnation_id=5));expected=m.manifest_commitment(changed)
        store.db.execute('UPDATE ate_generation_manifests SET commitment=?,manifest=? WHERE generation=1',(expected,m.encode_manifest(changed)))
    elif fault=='format':store.db.execute("UPDATE store_metadata SET value='5' WHERE key='format_version'")
    elif fault=='uuid':store.db.execute("UPDATE store_metadata SET value='other-store' WHERE key='store_uuid'")
    elif fault=='expected':expected=b'x'*32
    elif fault=='released':store.release_pin(pin)
    elif fault=='hook':store.codec.decode=lambda _:pytest.fail('caller hook invoked')
    elif fault=='budget':kwargs['max_bytes']=1
    elif fault=='metadata-budget':kwargs['max_metadata_bytes']=1
    elif fault=='schema':
        store.db.execute('ALTER TABLE ate_generation_manifests RENAME TO old_manifests')
        store.db.execute('CREATE TABLE ate_generation_manifests AS SELECT * FROM old_manifests')
    store.db.commit()
    if fault=='transaction':store.db.execute('BEGIN')
    with pytest.raises(StoreError):m.read_generation_manifest(store,pin,expected,**kwargs)
    if store.db.in_transaction:store.db.rollback()
    store.close()


def test_nested_snapshot_and_released_writer_receipt(tmp_path):
    from simulation.tests.proof_generation_fixtures import make_generation_store
    m=module();store,pin,pair=make_generation_store(tmp_path/'nested.sqlite');reader=store.capture_pin();store.release_pin(pin)
    with store.read_transaction():
        with store.read_snapshot(reader):assert m.read_generation_manifest(store,reader,pair[1])==pair[0]
    store.close()


def test_protected_root_inventory_exact_roles_and_deduplication():
    m=module();parent=specimen();p=m.manifest_commitment(parent);child=specimen(2,p);c=m.manifest_commitment(child)
    result=m.retained_roots(((parent,p),(child,c)),head=c,pins=(p,),unresolved=((p,c),),checkpoints=(p,))
    assert result.manifests==tuple(sorted((p,c))) and len(result.roots)==7
    assert tuple(r[2] for r in result.roots)==tuple(sorted(('versions','records','topology','queries','orders','events','inventory')))


@pytest.mark.parametrize('fault',['missing','conflict','foreign','old-pin','unused','bad-unresolved','types'])
def test_protection_inventory_fails_closed(fault):
    m=module();parent=specimen();p=m.manifest_commitment(parent);child=specimen(2,p);c=m.manifest_commitment(child)
    pairs=((parent,p),(child,c));kwargs=dict(head=c,pins=(p,))
    if fault=='missing':pairs=pairs[1:]
    elif fault=='conflict':
        other=replace(child,head=replace(child.head,seed=8));d=m.manifest_commitment(other);pairs+=((other,d),);kwargs['checkpoints']=(d,)
    elif fault=='foreign':
        other=replace(parent,store_identity='other');d=m.manifest_commitment(other);pairs=((other,d),(child,c));kwargs['pins']=(d,)
    elif fault=='old-pin':
        other=specimen(0);d=m.manifest_commitment(other);pairs=((other,d),(child,c));kwargs['pins']=(d,)
    elif fault=='unused':kwargs['pins']=()
    elif fault=='bad-unresolved':kwargs['unresolved']=((c,p),)
    else:kwargs['pins']=[p]
    with pytest.raises(StoreError):m.retained_roots(pairs,**kwargs)
