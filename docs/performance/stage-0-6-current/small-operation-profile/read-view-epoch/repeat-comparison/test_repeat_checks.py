"""Controls for safely stopping a trial and checking its execution source."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import pytest


path = Path(__file__).with_name('repeat.py')
spec = importlib.util.spec_from_file_location('ate_repeat_check', path)
repeat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(repeat)


def running(pid):
    try:
        state = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[0]
        return state not in ('Z', 'X')
    except FileNotFoundError:
        return False


@pytest.mark.parametrize('parent_exits', [False, True])
def test_stopping_group_kills_child_even_after_leader_exits(tmp_path, monkeypatch, parent_exits):
    child = ("import os,signal,sys,time; from pathlib import Path; "
             "signal.signal(signal.SIGTERM,signal.SIG_IGN); "
             "p=Path(sys.argv[1]); q=p.with_suffix('.tmp'); "
             "q.write_text(str(os.getpid())); q.replace(p); time.sleep(60)")
    parent = ("import subprocess,sys,time; from pathlib import Path; "
              "subprocess.Popen([sys.executable,'-c',sys.argv[2],sys.argv[1]], "
              "stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); "
              "p=Path(sys.argv[1]); "
              "exec('while not p.exists():\\n time.sleep(0.01)'); "
              "time.sleep(0 if sys.argv[3]=='exit' else 60)")
    pidfile = tmp_path / 'child.pid'
    proc = subprocess.Popen([sys.executable, '-c', parent, str(pidfile), child,
                             'exit' if parent_exits else 'wait'],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            start_new_session=True)
    child_pid = None
    try:
        deadline = time.monotonic() + 5
        while not pidfile.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert pidfile.exists()
        child_pid = int(pidfile.read_text())
        if parent_exits:
            assert proc.wait(timeout=5) == 0
        assert running(child_pid)
        monkeypatch.setattr(repeat, '_STOP_GRACE_SECONDS', 0.15, raising=False)
        repeat.stop_group(proc)
        deadline = time.monotonic() + 2
        while running(child_pid) and time.monotonic() < deadline:
            time.sleep(0.01)
        assert not running(child_pid)
    finally:
        try:os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:pass
        proc.wait(timeout=5)


@pytest.mark.parametrize('change', ['staged', 'untracked', 'ignored'])
def test_preflight_rejects_runtime_bytes_outside_pinned_tree(tmp_path, monkeypatch, change):
    repo = tmp_path / 'repo'
    repo.mkdir()
    subprocess.run(['git', 'init', '-q'], cwd=repo, check=True)
    subprocess.run(['git', 'config', 'user.name', 'Test'], cwd=repo, check=True)
    subprocess.run(['git', 'config', 'user.email', 'test@example.invalid'], cwd=repo, check=True)
    runtime = repo / 'simulation/ate_sim'
    runtime.mkdir(parents=True)
    (runtime / 'tracked.py').write_text('value = 1\n')
    (repo / '.gitignore').write_text('simulation/ate_sim/ignored.py\n')
    (repo / 'driver.py').write_text('# test driver\n')
    subprocess.run(['git', 'add', '.'], cwd=repo, check=True)
    subprocess.run(['git', 'commit', '-q', '-m', 'baseline'], cwd=repo, check=True)
    tree = subprocess.check_output(['git', 'rev-parse', 'HEAD:simulation/ate_sim'], cwd=repo, text=True).strip()
    if change == 'staged':
        (runtime / 'tracked.py').write_text('value = 2\n')
        subprocess.run(['git', 'add', 'simulation/ate_sim/tracked.py'], cwd=repo, check=True)
    else:
        (runtime / ('ignored.py' if change == 'ignored' else 'new.py')).write_text('value = 2\n')
    source = tmp_path / 'source.bin'
    source.write_bytes(b'deterministic fixture')
    info = tmp_path / 'input.json'
    info.write_text(json.dumps({'database': {'sha256': hashlib.sha256(source.read_bytes()).hexdigest()}}))
    monkeypatch.setattr(repeat, 'SOURCES', {'baseline': repo, 'candidate': repo})
    monkeypatch.setattr(repeat, 'EXPECTED_TREES', {'baseline': tree, 'candidate': tree})
    monkeypatch.setattr(repeat, 'SOURCE', source)
    monkeypatch.setattr(repeat, 'INPUT', info)
    monkeypatch.setattr(repeat, 'DRIVER', Path('driver.py'))
    monkeypatch.setattr(sys, 'argv', ['repeat.py', '--dry-run'])
    with pytest.raises((ValueError, subprocess.CalledProcessError)):
        repeat.main()
