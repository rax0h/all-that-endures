"""Independent offline stages around the exact existing persistence runtime."""
from contextlib import contextmanager,nullcontext
import copy
import os
import json
import subprocess
import sys
from pathlib import Path
import shutil
import tempfile
import time
from unittest.mock import patch
from simulation import stage_0_6_genesis_checkpoint as c
from simulation.stage_0_6_mature_benchmark import Recorder


def canonical_digest(world,progress):
    from ate_sim.canonical_stream import digest
    from ate_sim.core import _canonical,_canonical_fields
    root=type(world)
    def fields(cls):
        for key,name in _canonical_fields(cls):
            if cls is root:progress('canonical.field.'+name)
            yield key,name
    return digest(world,_canonical,fields)


@contextmanager
def captured_transfer(source,receipt,private_parent):
    """Only the catalog helper's one native capture may reuse checked bytes."""
    from ate_sim import persistence_lazy_store as lazy
    from ate_sim.persistence_adapters import WorldCodec,SCHEMA
    if Path(source).is_symlink() or Path(private_parent).is_symlink():raise ValueError('capture transfer requires regular private paths')
    source=Path(source).resolve();private_parent=Path(private_parent).resolve()
    c.validate(receipt)
    if receipt['stage']!='capture':raise ValueError('catalog replay requires captured checkpoint')
    c.verify_database(source,receipt['database']);calls=0
    def replay(cls,actual,destination,*,codec,expected_simulation_schema,expected_rules_id,_defer_target_audit=False):
        nonlocal calls
        target=Path(destination)
        if (calls or cls is not lazy.LazyRecordStore or Path(actual).resolve()!=source
            or target.name!='destination.sqlite' or target.parent.is_symlink() or target.parent.resolve().parent!=private_parent
            or not target.parent.name.startswith('.ate-checked-current-copy-')
            or target.exists() or target.is_symlink() or source.is_symlink()
            or type(codec) is not WorldCodec or codec.identity_links_recorded is not True
            or expected_simulation_schema!=SCHEMA or expected_rules_id!=receipt['context']['rules_id']
            or _defer_target_audit is not True or not lazy._CONVERSION_AUDITS.get()):
            raise ValueError('unrelated or repeated capture transfer')
        calls+=1
        shutil.copyfile(source,target)
        c.verify_database(target,receipt['database'])
        return lazy.CopyResult(target,receipt['database']['store_identity'],receipt['database']['generation'])
    try:
        with patch.object(lazy.LazyRecordStore,'copy_current_head',classmethod(replay)):yield
        if calls!=1:raise ValueError('catalog did not consume exactly one captured transfer')
    finally:c.verify_database(source,receipt['database'])


def _digest(path,rules,progress):
    from ate_sim.persistence_lazy import open_lazy_world_session
    from ate_sim.persistence_genesis_transaction import catalog_snapshot
    with open_lazy_world_session(path,rules_id=rules) as session:
        with catalog_snapshot(session.store,session.pin):return canonical_digest(session.world,progress)


def _build_proofs(path,rules,progress):
    from ate_sim.persistence_lazy_store import LazyRecordStore
    from ate_sim.persistence_adapters import WorldCodec,SCHEMA
    from ate_sim.persistence_genesis_transaction import ProofGenesisTransaction
    from ate_sim.persistence_proof_record import bootstrap_record_proofs
    from ate_sim.persistence_proof_scope import bootstrap_scope_proofs
    from ate_sim.persistence_proof_publication import bootstrap_content_proofs
    from ate_sim.persistence_proof_collection_directory import bootstrap_collection_directory
    from ate_sim.persistence_proof_inventory import bootstrap_inventory
    from ate_sim.persistence_proof_manifest_publish import bootstrap_world_manifest
    with LazyRecordStore.open(path,codec=WorldCodec(identity_links_recorded=True),expected_simulation_schema=SCHEMA,expected_rules_id=rules) as store:
        store.db.execute("UPDATE store_metadata SET value='7' WHERE key='format_version'");store.db.commit()
        pin=store.capture_pin()
        try:
            with ProofGenesisTransaction(store,pin,rank=True):
                progress('bootstrap.records');ra=bootstrap_record_proofs(store,pin)
                progress('bootstrap.scopes');sa=bootstrap_scope_proofs(store,pin,include_children=True,include_sequence=True,include_rank=True)
                progress('bootstrap.content');ca=bootstrap_content_proofs(store,pin)
                progress('bootstrap.directory');da=bootstrap_collection_directory(store,pin)
                progress('bootstrap.inventory');ia=bootstrap_inventory(store,pin)
                progress('bootstrap.World_manifest');manifest,commitment=bootstrap_world_manifest(store,pin,ca,sa,ia,ra,da)
        finally:store.release_pin(pin)
    return commitment.hex()


FRESH_CODE="""
import json,sys
from ate_sim import persistence_proof_world as proof
from ate_sim.persistence_proof_world_session import open_proof_world_session
def reject(*a,**k):raise AssertionError('fresh proof opening attempted a full World audit')
proof._audit_world=reject
with open_proof_world_session(sys.argv[1],rules_id=sys.argv[2],expected_commitment=bytes.fromhex(sys.argv[3])) as s:
 print(json.dumps(dict(year=s.world.year,seed=s.world.seed,generation=s.proof_manifest[0].generation,digest=s.world.digest(),world_audits=0)))
"""


def restore_in_fresh_process(path,receipt,seconds):
    ctx=receipt['context']
    completed=subprocess.run([sys.executable,'-c',FRESH_CODE,str(path),ctx['rules_id'],receipt['proof_commitment']],
        check=True,text=True,capture_output=True,timeout=seconds)
    actual=json.loads(completed.stdout)
    expected=dict(year=ctx['source']['year']+1,seed=ctx['source']['seed'],generation=1,
        digest=ctx['expected_saved_digest'],world_audits=0)
    if actual!=expected:raise ValueError('fresh saved World differs from exact continuation control')
    return actual


def _measure(source,path,receipt,output,deadline):
    from ate_sim.persistence_proof_world_session import open_proof_world_session
    from ate_sim import persistence_proof_world as proof
    from ate_sim.engine import Simulation
    ctx=receipt['context'];year=ctx['source']['year'];session=None
    from simulation.profile_stage_0_5_performance import BudgetExpired
    limits=dict(working_copy=12600,open=60,first_step=300,save=60,warm_step=300,close=60)
    rec=Recorder(output,limits)
    def phase(name,operation):
        remaining=deadline-time.monotonic()
        if remaining<=0:raise BudgetExpired('measure aggregate budget exhausted')
        rec.budgets[name]=min(limits[name],remaining)
        return rec.measure(name,operation)
    phase('working_copy',lambda:shutil.copyfile(source,path))
    def reject(*a,**k):raise AssertionError('operational phase attempted full World audit')
    with patch.object(proof,'_audit_world',reject):
        try:
            session=phase('open',lambda:open_proof_world_session(path,rules_id=ctx['rules_id'],expected_commitment=bytes.fromhex(receipt['proof_commitment'])))
            rec.store=session.store
            if (session.world.year,session.world.seed,session.proof_manifest[0].generation)!=(year,ctx['source']['seed'],0):raise ValueError('proof input World differs')
            phase('first_step',lambda:Simulation(session.world).run(1))
            phase('save',session.save)
            manifest,commitment=session.proof_manifest
            if session.world.year!=year+1 or manifest.generation!=1:raise ValueError('save did not publish exact successor')
            phase('warm_step',lambda:Simulation(session.world).run(1))
            if session.world.year!=year+2:raise ValueError('warm continuation year differs')
            phase('close',session.close);session=None;rec.store=None
        finally:
            if session is not None:session.close()
    targets=dict(open=10,save=2,warm_step=1)
    return dict(phases=rec.phases,targets_seconds=targets,
        targets_met={name:rec.phases[name]['wall_seconds']<=seconds for name,seconds in targets.items()},
        saved_commitment=commitment.hex(),fresh_restore='pending separate durable stage')


def run_stage(stage,input_receipt,input_database,destination,*,producer,budget,progress=lambda _:None):
    """Caller must authenticate remote provenance before supplying its receipt.

    Successful publication is the only completion marker. A failure discards
    this private working copy; it does not remove or rewrite any prior input.
    """
    from ate_sim import persistence_lazy_store as lazy,persistence_catalog_copy as catalog,persistence_proof_world_copy as genesis
    from ate_sim.persistence_adapters import WorldCodec,SCHEMA
    from ate_sim.persistence_conversion_workspace import ConversionWorkspace
    from ate_sim.persistence_conversion_audit import construction_spills
    c.validate(input_receipt)
    if stage not in c.STAGES or input_receipt['stage']!=c.ORDER[c.ORDER.index(stage)-1]:raise ValueError('stage requires its exact predecessor')
    c.integer(budget,'stage budget',1)
    if budget>12600:raise ValueError('stage compute budget exceeds bound')
    source,destination=Path(input_database),Path(destination)
    if destination.exists() or destination.is_symlink():raise FileExistsError(destination)
    c.verify_database(source,input_receipt['database'])
    destination.parent.mkdir(parents=True,exist_ok=True)
    # Input + working growth + publication/SQLite journals; fail before work.
    size=input_receipt['database']['bytes']
    if shutil.disk_usage(destination.parent).free<2*size+64*1024*1024:raise ValueError('insufficient stage copy/journal headroom')
    ctx=input_receipt['context'];rules=ctx['rules_id'];metrics={};result=None
    rec=Recorder(Path(tempfile.mkdtemp(prefix='evidence-'+stage+'-',dir=destination.parent)),{} if stage=='measure' else {stage:budget})
    with tempfile.TemporaryDirectory(prefix='.proof-stage-',dir=destination.parent) as directory:
        private=Path(directory);working=private/'working.sqlite'
        def action():
            nonlocal result
            if stage=='measure':
                # Subphases own the one alarm, using the remaining aggregate.
                rec.phases[stage]['budget_seconds']=budget
                rec.phases[stage]['budget_policy']='aggregate deadline across copy/open/step/save/warm/close'
                result=_measure(source,working,input_receipt,rec.output/'operational',time.monotonic()+budget)
                return
            if stage=='capture':
                lazy.LazyRecordStore.copy_current_head(source,working,codec=WorldCodec(identity_links_recorded=True),
                    expected_simulation_schema=SCHEMA,expected_rules_id=rules,_defer_target_audit=True)
            elif stage=='catalog':
                with captured_transfer(source,input_receipt,private):
                    catalog._copy_current_checked_catalog(source,working,rules_id=rules,_for_proof_genesis=True)
            else:
                shutil.copyfile(source,working)
                if stage in ('source_digest','after_digest'):
                    result=_digest(working,rules,progress)
                    if stage=='after_digest' and result!=input_receipt['baseline_digest']:raise ValueError('native transfer/rebase changed canonical World')
                elif stage=='rebase':
                    with lazy.LazyRecordStore.open(working,codec=WorldCodec(identity_links_recorded=True),expected_simulation_schema=SCHEMA,expected_rules_id=rules) as store:
                        genesis._rebase_private_snapshot(store,_defer_final_audit=True)
                elif stage=='proofs':result=_build_proofs(working,rules,progress)
                elif stage=='fresh_restore':result=restore_in_fresh_process(working,input_receipt,budget)
        try:
            construction=stage not in ('measure','fresh_restore')
            with lazy._bounded_conversion_audits() if construction else nullcontext():
                with ConversionWorkspace(WorldCodec(identity_links_recorded=True),directory=private) if construction else nullcontext() as spill, construction_spills(spill) if construction else nullcontext():
                    with patch.object(genesis,'_genesis_phase',progress),patch.object(catalog,'_copy_phase',lambda at,*_:progress(at)),patch.object(lazy.LazyRecordStore,'_copy_phase_hook',staticmethod(progress)):
                        rec.measure(stage,action)
            metrics['compute']=rec.phases[stage]
            if stage=='measure':metrics['benchmark']=result
            if stage=='fresh_restore':metrics['restored']=result
            readonly=stage in ('source_digest','after_digest','fresh_restore')
            database=input_receipt['database'] if readonly else c.describe(working,rules_id=rules)
            receipt=c.record(stage,ctx,database,producer,parent=input_receipt,
                baseline_digest=result if stage=='source_digest' else None,
                proof_commitment=(result if stage=='proofs' else result['saved_commitment'] if stage=='measure' else input_receipt['proof_commitment'] if stage=='fresh_restore' else None),metrics=metrics)
            c.verify_database(source,input_receipt['database'])
            c.publish(destination,receipt,database=None if readonly else working,move_owned=not readonly)
            return receipt
        finally:c.verify_database(source,input_receipt['database'])
