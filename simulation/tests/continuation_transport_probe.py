"""Test-only HTTP boundary for the real serial GitHub ZIP transport in child processes."""
import base64
import io
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.parse
import urllib.request


def main():
    state = json.loads(Path(sys.argv[1]).read_text())
    role,root = sys.argv[2],Path(sys.argv[3])
    from simulation import continuation_checkpoint_ci as ci
    ci.ROOT = root
    # Test-local fake API authority follows the checkout being exercised. The
    # production mature harness retains its frozen, independently reviewed pins.
    ci.runner.original.EXECUTION_RUNTIME_SHA = state['head']
    ci.runner.original.EXECUTION_RUNTIME_TREE = state['runtime_tree']
    runtime_tree = state['runtime_tree']
    def api(path):
        parsed = urllib.parse.urlsplit(path)
        path = parsed.path
        if path == '/actions/runs/500/artifacts':return dict(artifacts=state['artifacts'])
        if path == '/actions/runs/500/jobs':return dict(jobs=state['jobs'])
        if path == '/actions/runs/500':return dict(id=500,head_sha=state['head'],
            path=ci.runner.PROOF_WORKFLOW,head_branch='sol/stage-0-5-continuation-checkpoints',status='in_progress')
        if path.startswith('/actions/artifacts/'):
            identity=int(path.rsplit('/',1)[1])
            matches=[row for row in state['artifacts'] if row['id']==identity]
            assert len(matches)==1
            return matches[0]
        if path.startswith('/contents/'):
            assert path=='/contents/'+ci.runner.PROOF_WORKFLOW
            return dict(encoding='base64',content=base64.b64encode(state['workflow'].encode()).decode())
        if path.startswith('/git/trees/'):
            assert path.rsplit('/',1)[1] in {state['head'],os.environ['RUNTIME_SHA']}
            return dict(truncated=False,tree=[dict(path='simulation/ate_sim',type='tree',sha=runtime_tree)])
        raise AssertionError('unexpected API '+path)
    def opening(request,**kwargs):
        url = request.full_url if isinstance(request,urllib.request.Request) else request
        if url.startswith('https://api.github.com/repos/rax0h/all-that-endures'):
            assert isinstance(request,urllib.request.Request)
            assert request.get_header('Authorization')=='Bearer bounded-test-token'
            path=url.removeprefix('https://api.github.com/repos/rax0h/all-that-endures')
            return io.BytesIO(json.dumps(api(path)).encode())
        assert url.startswith('https://bounded-artifacts.test/')
        assert not isinstance(request,urllib.request.Request) or request.get_header('Authorization') is None
        identity=url.rsplit('/',1)[1].removesuffix('.zip')
        return Path(state['archives'][identity]).open('rb')
    class Redirect:
        def open(self,request,**kwargs):
            assert request.get_header('Authorization')=='Bearer bounded-test-token'
            parts=request.full_url.split('/')
            assert parts[-1]=='zip'
            identity=parts[-2]
            assert identity in state['archives']
            raise urllib.error.HTTPError(request.full_url,302,'Found',
                {'Location':'https://bounded-artifacts.test/'+identity+'.zip'},None)
    urllib.request.urlopen = opening
    urllib.request.build_opener = lambda *args:Redirect()
    ci.main(['--job',role])


if __name__=='__main__':main()
