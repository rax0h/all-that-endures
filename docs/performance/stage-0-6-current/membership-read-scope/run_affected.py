"""Bounded per-file validation, preserving completed compatible receipts."""
import argparse, hashlib, importlib.util, json, os, subprocess, sys, time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
HERE=Path(__file__).resolve().parent
EXCLUDE='not test_generated_world_continues_through_two_proof_saves'

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def record(path,value):
    temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value,indent=2)+'\n')
    temporary.replace(path)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--resume',action='store_true')
    args=parser.parse_args()
    out=args.output.resolve()
    out.mkdir(parents=True,exist_ok=args.resume)
    path=ROOT/'docs/performance/stage-0-6-current/small-operation-profile/read-view-epoch/repeat-comparison/repeat.py'
    spec=importlib.util.spec_from_file_location('bounded_group_cleanup',path)
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    fence=helper.runtime_files(ROOT)
    paths=json.loads((HERE/'affected-paths.json').read_text())
    summary=dict(status='running',runtime_files=fence,excluded=EXCLUDE,per_file_seconds=300,
        invocation_seconds=900,files=[])
    deadline=time.monotonic()+900
    for index,test in enumerate(paths):
        receipt=out/(Path(test).stem+'.json')
        context=dict(runtime_files=fence,test=test,test_sha256=sha(ROOT/test),excluded=EXCLUDE)
        if args.resume and receipt.exists():
            prior=json.loads(receipt.read_text())
            if (prior['context']==context and prior['status']=='passed'
                    and sha(out/prior['xml'])==prior['xml_sha256']
                    and sha(out/prior['log'])==prior['log_sha256']):
                summary['files'].append(prior);continue
        remaining=deadline-time.monotonic()
        if remaining<=310:
            summary['status']='incomplete';record(out/'summary.json',summary);print('Restart before next file: reserve its full300s plus cleanup',flush=True);return 2
        row=dict(context=context,status='running',xml=Path(test).stem+'.xml',log=Path(test).stem+'.log')
        record(receipt,row);record(out/'summary.json',summary)
        proc=None
        started=time.monotonic()
        try:
            with (out/row['log']).open('w') as log:
                proc=subprocess.Popen([sys.executable,'-m','pytest','-q',test,'-k',EXCLUDE,
                    '--junitxml='+str(out/row['xml'])],cwd=ROOT,
                    env=dict(os.environ,PYTHONPATH='.:simulation'),stdout=log,stderr=subprocess.STDOUT,
                    start_new_session=True)
                code=proc.wait(timeout=min(300,remaining-10))
            if code!=0:raise RuntimeError(f'pytest exited {code}')
            if helper.runtime_files(ROOT)!=fence:raise RuntimeError('runtime bytes changed during validation')
            import xml.etree.ElementTree as ET
            suites=list(ET.parse(out/row['xml']).getroot().iter('testsuite'))
            if any(int(s.get('errors',0))+int(s.get('failures',0)) for s in suites):
                raise RuntimeError('test XML contains failures')
            row.update(status='passed',seconds=time.monotonic()-started,
                tests=sum(int(s.get('tests',0)) for s in suites),
                xml_sha256=sha(out/row['xml']),log_sha256=sha(out/row['log']))
        except BaseException as exc:
            helper.stop_group(proc)
            row.update(status='failed',error=f'{type(exc).__name__}: {exc}',seconds=time.monotonic()-started)
            record(receipt,row);summary['files'].append(row)
            summary['status']='incomplete';record(out/'summary.json',summary)
            print(test,row['error'],flush=True);return 1
        record(receipt,row);summary['files'].append(row);record(out/'summary.json',summary)
        print(test,row['tests'],'passed',round(row['seconds'],2),'s',flush=True)
    summary['status']='passed';summary['tests']=sum(row['tests'] for row in summary['files'])
    record(out/'summary.json',summary)
    print('Total',summary['tests'],'tests passed; reserved constructor excluded',flush=True)
    return 0

if __name__=='__main__':
    sys.exit(main())
