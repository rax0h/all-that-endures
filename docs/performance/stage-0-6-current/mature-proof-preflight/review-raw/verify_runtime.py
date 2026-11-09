import hashlib,json,platform,sqlite3,sys,sysconfig
from pathlib import Path
q=Path('docs/performance/stage-0-6-current/fixture-construction/qualified-local-runtime.json')
expected=json.loads(q.read_text())
def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
import _sqlite3
con=sqlite3.connect(':memory:')
observed=dict(executable=sys.executable,resolved_executable=str(Path(sys.executable).resolve()),executable_sha256=sha(sys.executable),system_python_sha256=sha('/usr/bin/python3'),python=sys.version,compiler=platform.python_compiler(),sqlite=sqlite3.sqlite_version,sqlite_source_id=con.execute('select sqlite_source_id()').fetchone()[0],sqlite_compile_options=sorted(x[0] for x in con.execute('pragma compile_options')),sqlite_extension_path=_sqlite3.__file__,sqlite_extension_sha256=sha(_sqlite3.__file__))
con.close()
libs=sorted({line.split()[-1] for line in Path('/proc/self/maps').read_text().splitlines() if 'libsqlite3.so' in line})
observed['loaded_sqlite_libraries']=[dict(path=p,sha256=sha(p)) for p in libs]
differences={k:dict(expected=v,observed=observed.get(k)) for k,v in expected.items() if k!='runtime_tree' and observed.get(k)!=v}
out=dict(matches=not differences,qualification_sha256=sha(q),observed=observed,differences=differences)
Path('/tmp/ate-mature-preflight-review/runtime.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(dict(matches=not differences,differences=differences)))
assert not differences
