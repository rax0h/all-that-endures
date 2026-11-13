import sys,platform,sqlite3,hashlib,json,pathlib,_sqlite3
p=pathlib.Path('docs/performance/stage-0-6-current/fixture-construction/qualified-local-runtime.json')
expected=json.loads(p.read_text())
actual={
'executable':sys.executable,
'resolved_executable':str(pathlib.Path(sys.executable).resolve()),
'executable_sha256':hashlib.sha256(pathlib.Path(sys.executable).read_bytes()).hexdigest(),
'system_python_sha256':hashlib.sha256(pathlib.Path('/usr/bin/python3').read_bytes()).hexdigest(),
'python':sys.version,'compiler':platform.python_compiler(),'sqlite':sqlite3.sqlite_version,
'sqlite_source_id':sqlite3.connect(':memory:').execute('select sqlite_source_id()').fetchone()[0],
'sqlite_compile_options':[r[0] for r in sqlite3.connect(':memory:').execute('pragma compile_options')]}
actual['sqlite_extension_path']=_sqlite3.__file__
actual['sqlite_extension_sha256']=hashlib.sha256(pathlib.Path(_sqlite3.__file__).read_bytes()).hexdigest()
paths=sorted({line.split()[-1] for line in pathlib.Path('/proc/self/maps').read_text().splitlines() if 'libsqlite3' in line})
actual['loaded_sqlite_libraries']=[{'path':v,'sha256':hashlib.sha256(pathlib.Path(v).read_bytes()).hexdigest()} for v in paths]
receipt=json.loads((p.parent/expected['qualification_receipt']).resolve().read_text())
assert expected['runtime_tree'] in json.dumps(receipt)
for k,v in expected.items():
 if k in actual: assert actual[k]==v,(k,actual[k],v)
print(json.dumps({'verified':actual,'expected_additional_keys':[k for k in expected if k not in actual]},indent=2))
