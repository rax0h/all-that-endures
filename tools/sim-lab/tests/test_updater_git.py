import subprocess
from pathlib import Path

from ate_lab.updater import check_update


def _git(path: Path, *args: str) -> None:
    subprocess.check_call(["git", "-C", str(path), *args], stdout=subprocess.DEVNULL)


def _pair(tmp_path: Path):
    origin = tmp_path / "origin"
    clone = tmp_path / "clone"
    origin.mkdir()
    _git(origin, "init", "-b", "lab")
    _git(origin, "config", "user.email", "lab@example.com")
    _git(origin, "config", "user.name", "Lab")
    (origin / "README").write_text("one\n", encoding="utf-8")
    _git(origin, "add", "README")
    _git(origin, "commit", "-m", "one")
    subprocess.check_call(["git", "clone", str(origin), str(clone)], stdout=subprocess.DEVNULL)
    _git(clone, "config", "user.email", "lab@example.com")
    _git(clone, "config", "user.name", "Lab")
    return origin, clone


def test_fast_forward_updates_only_the_install(tmp_path, monkeypatch):
    monkeypatch.setenv("ATE_LAB_HOME", str(tmp_path / "home"))
    origin, clone = _pair(tmp_path)
    current = subprocess.check_output(["git", "-C", str(clone), "rev-parse", "HEAD"], text=True).strip()
    first = check_update(clone, apply=True, pip=False)
    assert first["action"] == "up_to_date"
    (origin / "README").write_text("two\n", encoding="utf-8")
    _git(origin, "add", "README")
    _git(origin, "commit", "-m", "two")
    # The clone must not already have the commit; fetch happens inside check_update.
    applied = check_update(clone, apply=True, pip=False)
    updated = subprocess.check_output(["git", "-C", str(clone), "rev-parse", "HEAD"], text=True).strip()
    origin_head = subprocess.check_output(["git", "-C", str(origin), "rev-parse", "HEAD"], text=True).strip()
    assert applied["action"] == "fast_forward"
    assert applied["updated"] is True
    assert updated == origin_head
    assert updated != current
    assert (clone / "README").read_text(encoding="utf-8") == "two\n"


def test_dirty_and_diverged_installs_are_left_alone(tmp_path, monkeypatch):
    monkeypatch.setenv("ATE_LAB_HOME", str(tmp_path / "home"))
    origin, clone = _pair(tmp_path)
    (clone / "local-note.txt").write_text("do not touch\n", encoding="utf-8")
    head = subprocess.check_output(["git", "-C", str(clone), "rev-parse", "HEAD"], text=True).strip()
    dirty = check_update(clone, apply=True, pip=False)
    assert dirty["action"] == "skip"
    assert subprocess.check_output(["git", "-C", str(clone), "rev-parse", "HEAD"], text=True).strip() == head
    assert (clone / "local-note.txt").read_text(encoding="utf-8") == "do not touch\n"
    _git(clone, "add", "local-note.txt")
    _git(clone, "commit", "-m", "local")
    (origin / "README").write_text("remote\n", encoding="utf-8")
    _git(origin, "add", "README")
    _git(origin, "commit", "-m", "remote")
    local_head = subprocess.check_output(["git", "-C", str(clone), "rev-parse", "HEAD"], text=True).strip()
    diverged = check_update(clone, apply=True, pip=False)
    assert diverged["action"] == "skip"
    assert subprocess.check_output(["git", "-C", str(clone), "rev-parse", "HEAD"], text=True).strip() == local_head
    assert (origin / "README").read_text(encoding="utf-8") == "remote\n"
