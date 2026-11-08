exec(open('/tmp/ate_metadata_review_probe.py').read().split('s=session();d=s.store;pre=s.world.events._disk_prefix')[0])
s=session();d=s.store;pre=s.world.events._disk_prefix;authority=d._world_proof_authority
payload=d.db.execute('select payload from segments limit 1').fetchone()[0];decode=d.codec.decode;fired=[]
def hook(raw):
    if raw==payload and not fired:
        fired.append(True)
        d.db.execute("UPDATE segments set payload_checksum='corrupt'")
        d.db.commit()
        authority.epoch=authority._epoch()
    return decode(raw)
d.codec.decode=hook
try:print('cold prefix accepted and cached event',pre[0].id,'cache entries',pre.resident_segments,'physical source checksum',d.db.execute('select payload_checksum from segments limit 1').fetchone()[0])
finally:d.close()
