exec(open('/tmp/ate_metadata_review_probe.py').read().split('s=session();d=s.store;pre=s.world.events._disk_prefix')[0])
s=session();d=s.store;pre=s.world.events._disk_prefix
print('journal',d.db.execute('pragma journal_mode').fetchone())
for mode in ('owned','nested','arbitrary','early-close','error'):
    try:
        if mode=='arbitrary':
            d.db.execute('BEGIN')
            try:print(mode,len(pre))
            finally:d.db.rollback()
        elif mode=='owned':
            with d.read_transaction() as gen:
                print(mode,gen,d.checked_head().generation,len(pre),d.db.in_transaction)
        elif mode=='nested':
            with d.read_snapshot(s.pin):
                print(mode,d.generation,len(pre),d.db.in_transaction)
        else:
            it=iter(pre);next(it)
            if mode=='early-close':it.close()
            else:
                try:it.throw(ValueError('test'))
                except ValueError:pass
            print(mode,'clean',not d.db.in_transaction,getattr(d,'_checked_snapshot_depth'))
    except Exception as e:print(mode,type(e).__name__,str(e),'clean',not d.db.in_transaction)
s.close()
