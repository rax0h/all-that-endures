"""Short cross-family fault/copy evidence through actual complete-format open."""
import argparse
import json
import tempfile
from pathlib import Path
from ate_sim.core import Layer
from ate_sim.persistence_complete_format import upgrade_lazy_snapshot
from ate_sim.persistence_lazy import open_lazy_world_session
from ate_sim.persistence_lazy_store import LazyRecordStore
from ate_sim.persistence_adapters import WorldCodec,SCHEMA
from simulation.tests.test_stage_0_5_final_catalog_copy import legacy_lazy,RULES


def run(folder):
    rows=[]
    for phase in ('during_version_writes','during_ordinary_writes','before_commit','after_commit'):
        directory=folder/phase;directory.mkdir()
        source=legacy_lazy(directory);target=directory/'complete.sqlite'
        upgrade_lazy_snapshot(source,target,rules_id=RULES)
        with open_lazy_world_session(target,rules_id=RULES) as s:
            child=s.skills[1,'craft'].provenance;child.append(99)
            nan=float('nan');s.world.event_ids.add(nan)
            s.wallets[1]={'child':child,'key':nan,'ids':s.world.event_ids}
            event=s.world.emit('cross_family_complete_probe',Layer.SOCIETY,child=child)
            generation=s.pin.captured_head
            def fail(at):
                if at==phase:raise OSError(phase)
            s.store._phase_hook=fail
            try:s.save()
            except OSError as error:assert str(error)==phase
            else:raise AssertionError('requested save phase was not exercised')
            s.store._phase_hook=lambda _at:None
            # Copy committed authority before resolving the live acknowledgement.
            copied=directory/'recovered.sqlite'
            result=LazyRecordStore.copy_current_head(target,copied,codec=WorldCodec(identity_links_recorded=True),
                expected_simulation_schema=SCHEMA,expected_rules_id=RULES)
            with open_lazy_world_session(copied,rules_id=RULES) as restored:
                assert restored._identity_coordinator is not None
                if phase=='after_commit':
                    shared=restored.skills[1,'craft'].provenance
                    assert shared[-1]==99 and shared is restored.skills[2,'craft'].provenance
                    assert shared is restored.wallets[1]['child'] is restored.world.events[-1].data['child']
                    assert restored.wallets[1]['key'] in restored.world.event_ids
                else:
                    assert len(restored.world.events)==0 and len(restored.skills[1,'craft'].provenance)==32
            resolved=s.resolve_save();assert resolved==generation+(phase=='after_commit')
            if phase!='after_commit':s.save()
            assert child is s.skills[2,'craft'].provenance and nan in s.world.event_ids
            assert event is s.world.events[-1]
        with open_lazy_world_session(target,rules_id=RULES) as reopened:
            child=reopened.skills[1,'craft'].provenance
            assert child is reopened.skills[2,'craft'].provenance is reopened.wallets[1]['child']
            assert child is reopened.world.events[-1].data['child'] and child[-1]==99
            assert reopened.wallets[1]['key'] in reopened.world.event_ids
        rows.append({'phase':phase,'resolved_generation':resolved,'copied_generation':result.generation,
            'shared_skill_wallet_event_identity':True,'exact_native_key_membership':True,'passed':True})
    return {'passed':True,'complete_format':True,'cases':rows}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='ate-complete-recovery-') as directory:
        result=run(Path(directory))
    Path(args.output).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':main()
