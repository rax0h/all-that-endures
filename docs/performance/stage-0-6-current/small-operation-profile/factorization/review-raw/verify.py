"""Independent bounded differential and SQL checks; writes only review evidence."""
from pathlib import Path
import hashlib, json, platform, random, sqlite3, subprocess, sys, types
import _sqlite3
from ate_sim import persistence_proof_nodes as new
from ate_sim.persistence_proof_store import ProofNodeStore
from ate_sim.persistence_proof_map import ProofMap
from ate_sim.incremental_store import StoreIntegrityError
root = Path.cwd()
out = root / 'docs/performance/stage-0-6-current/small-operation-profile/factorization/review-raw'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
old_source = subprocess.check_output(['git', 'show', 'HEAD:simulation/ate_sim/persistence_proof_nodes.py'])
old = types.ModuleType('ate_sim._review_old_nodes')
sys.modules[old.__name__] = old
old.__package__ = 'ate_sim'
exec(compile(old_source, '<HEAD:persistence_proof_nodes.py>', 'exec'), old.__dict__)
rng = random.Random(20261111)
checked = accepted = 0
def normalize(module, raw):
    try:
        decoded = module.decode_node(raw)
        return ('accepted', repr(decoded), module.encode_node(decoded))
    except StoreIntegrityError:
        return ('rejected',)
def compare(raw):
    global checked, accepted
    a, b = normalize(old, raw), normalize(new, raw)
    assert a == b, (raw, a, b)
    checked += 1
    accepted += a[0] == 'accepted'
for length in range(64):
    for count in range(2, 17):
        prefix = tuple(rng.randrange(16) for _ in range(length))
        slots = sorted(rng.sample(range(16), count))
        counts = [1] * count
        if (length + count) % 2:
            counts[-1] = new.MAX_COUNT - count + 1
        node = new.Branch(prefix, tuple((slot, new.Root(rng.randbytes(32), n)) for slot, n in zip(slots, counts)))
        raw = new.encode_node(node)
        compare(raw)
        for index in (0, 5, 6, 7+(length+1)//2, len(raw)-1):
            changed = bytearray(raw); changed[index] ^= 255; compare(bytes(changed))
        for _ in range(8):
            changed = bytearray(raw); changed[rng.randrange(len(raw))] = rng.randrange(256); compare(bytes(changed))
        compare(raw[:-1]); compare(raw+b'\0')
for length in range(720):
    compare(rng.randbytes(length))
for raw in [bytearray(), '', None, 1, b'ATEP\1L'+b'x'*64, b'ATEP\1L'+b'x'*63]:
    compare(raw)
sql_checks = []
def reject(label, operation):
    try: operation()
    except StoreIntegrityError: sql_checks.append(label)
    else: raise AssertionError('accepted '+label)
with sqlite3.connect(':memory:') as db:
    store = ProofNodeStore(db); store.create_schema()
    domain = b'review'; raw = new.encode_node(new.Leaf(b'k'*32,b'v'*32)); digest = new.node_digest(domain, raw)
    db.execute('PRAGMA ignore_check_constraints=ON')
    for label, body in [('TEXT', '\0'+'x'*2000), ('INTEGER', 7), ('REAL', 1.25), ('OVERSIZED', b'x'*697)]:
        db.execute('DELETE FROM ate_proof_nodes')
        db.execute('INSERT INTO ate_proof_nodes VALUES(?,?,?)', (domain, digest, body))
        reject(label, lambda: store._read_bound_bytes(domain, digest))
    db.execute('DELETE FROM ate_proof_nodes')
    reject('MISSING', lambda: store._read_bound_bytes(domain, digest))
    reject('ADDRESS', lambda: store._read_bound_bytes(domain, b'x'))
    db.execute('INSERT INTO ate_proof_nodes VALUES(?,?,?)', (domain,digest,raw))
    mapping=ProofMap(domain,lambda d:store._read_bound_bytes(domain,d),None)
    reject('ROOT_COUNT',lambda:mapping._read(new.Root(digest,2)))
    reject('REQUIRED_PREFIX',lambda:mapping._read(new.Root(digest,1),(0,)))
    corrupted=new.encode_node(new.Leaf(b'k'*32,b'z'*32))
    db.execute('UPDATE ate_proof_nodes SET node_bytes=?',(corrupted,))
    reject('COLLISION_READBACK',lambda:store.write(domain,digest,raw))
with sqlite3.connect(':memory:') as db:
    fingerprint=dict(python=sys.version,compiler=platform.python_compiler(),executable_sha256=sha(sys.executable),system_python_sha256=sha('/usr/bin/python3'),sqlite=sqlite3.sqlite_version,sqlite_source_id=db.execute('select sqlite_source_id()').fetchone()[0],sqlite_compile_options=sorted(x[0] for x in db.execute('pragma compile_options')),sqlite_extension_path=_sqlite3.__file__,sqlite_extension_sha256=sha(_sqlite3.__file__))
paths=sorted({line.split()[-1] for line in Path('/proc/self/maps').read_text().splitlines() if 'libsqlite3.so' in line})
fingerprint['loaded_sqlite_libraries']=[dict(path=p,sha256=sha(p)) for p in paths]
qualified=json.loads((root/'docs/performance/stage-0-6-current/fixture-construction/qualified-local-runtime.json').read_text())
assert all(v==qualified[k] for k,v in fingerprint.items())
assert fingerprint==json.loads((out.parent/'runtime-fingerprint.json').read_text())
report=dict(status='passed',differential_cases=checked,accepted_cases=accepted,rejected_cases=checked-accepted,sql_checks=sql_checks,fingerprint=fingerprint,head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),source_sha256={str(p.relative_to(root)):sha(p) for p in sorted((root/'simulation/ate_sim').glob('*.py'))},test_sha256=sha(root/'simulation/tests/test_stage_0_6_proof_node_factorization.py'),compare_sha256=sha(out.parent/'compare.py'),verification_script_sha256=sha(__file__))
(out/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('fingerprint','source_sha256')},indent=2))
