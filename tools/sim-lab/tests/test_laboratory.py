import json
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from ate_lab.checkpoints import save_new
from ate_lab.engine_loader import import_engine
from ate_lab.errors import LabError
from ate_lab.extract import person_detail, population_replay
from ate_lab.laboratory import Laboratory
from ate_lab.memory_probe import rss_bytes
from ate_lab.server import serve


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("ATE_LAB_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("ATE_LAB_VAR", str(tmp_path / "var"))
    monkeypatch.delenv("ATE_DATA_ROOT", raising=False)
    return tmp_path


@pytest.fixture
def lab(isolated):
    instance = Laboratory()
    try:
        yield instance
    finally:
        instance.close()


def _wait_idle(instance, timeout=20):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if instance.state in ("idle", "error") and not (instance.thread and instance.thread.is_alive()):
            return
        time.sleep(0.02)
    raise AssertionError(f"run did not settle: {instance.state} {instance.reason} {instance.error}")


def test_memory_probe_on_this_host():
    sample = rss_bytes()
    assert sample["quality"] == "measured"
    assert sample["value"] > 0


def test_population_replay_matches_the_living_set():
    eng = import_engine()
    world = eng["worldgen"].generate_world(843000)
    eng["engine"].Simulation(world).run(12)
    replay = population_replay(world)
    assert replay["check_ok"] is True
    assert replay["population"]["quality"] == "calculated"
    assert replay["population"]["value"][-1]["value"] == sum(person.alive for person in world.people.values())
    births = sum(1 for event in world.events if event.kind == "birth")
    assert sum(point["value"] for point in replay["births"]["value"]) == births
    assert replay["births"]["quality"] == "measured"


def test_run_matches_engine_digest_with_and_without_instrumentation(lab):
    eng = import_engine()
    direct = eng["worldgen"].generate_world(843000)
    eng["engine"].Simulation(direct).run(6)
    expected = direct.digest()
    lab.start_new(seed=843000, years=6, width=24, height=18, settlements=5, timebox_seconds=0, pace_seconds=0, instrument=False)
    _wait_idle(lab)
    assert lab.error is None
    assert lab.world.digest() == expected
    assert lab.samples[0]["step_seconds"]["quality"] == "measured"
    assert lab.samples[-1]["population"]["value"] == sum(person.alive for person in direct.people.values())
    assert lab.overview["series"]["population"]["quality"] == "calculated"
    log = Path(lab.run_meta["log_path"]).read_text(encoding="utf-8")
    assert '"performance_passed": null' in log or '"performance_passed":null' in log
    lab.close()
    other = Laboratory()
    try:
        other.start_new(seed=843000, years=6, width=24, height=18, settlements=5, timebox_seconds=0, pace_seconds=0, instrument=True)
        _wait_idle(other)
        assert other.world.digest() == expected
        assert other.samples[-1]["subsystem_seconds"]["quality"] == "measured"
    finally:
        other.close()


def test_stop_and_pause_are_year_boundaries(lab):
    lab.start_new(seed=843000, years=40, width=24, height=18, settlements=5, timebox_seconds=0, pace_seconds=0.08, instrument=False)
    time.sleep(0.15)
    lab.pause()
    deadline = time.time() + 5
    while time.time() < deadline and lab.state != "paused":
        time.sleep(0.02)
    assert lab.state == "paused"
    held = lab.world.year
    time.sleep(0.25)
    assert lab.world.year == held
    lab.resume()
    lab.request_stop()
    _wait_idle(lab)
    assert lab.world.year < 40
    assert "benchmark" not in (lab.reason or "").lower() or "not" in (lab.reason or "")


def test_year_cap_refuses_a_millennium(lab):
    with pytest.raises(LabError):
        lab.start_new(seed=1, years=1000, width=24, height=18, settlements=5, timebox_seconds=0, pace_seconds=0, instrument=False)


def test_checkpoint_roundtrip_is_read_only(lab, tmp_path):
    eng = import_engine()
    world = eng["worldgen"].generate_world(7)
    eng["engine"].Simulation(world).run(3)
    lab._attach(world, {"kind": "generated-for-test"})
    saved = lab.save_checkpoint("sample.checkpoint")
    path = Path(saved["path"])
    assert path.is_file()
    digest = path.read_bytes()
    stamp = path.stat().st_mtime_ns
    header = lab.read_checkpoint(str(path))
    verified = lab.verify_checkpoint(str(path))
    loaded = lab.load_checkpoint(str(path))
    assert path.read_bytes() == digest
    assert path.stat().st_mtime_ns == stamp
    assert header["year"]["value"] == 3
    assert verified["ok"] is True
    assert verified["mtime_unchanged"]["value"] is True
    assert loaded["year"] == 3
    with pytest.raises(LabError):
        lab.save_checkpoint("sample.checkpoint")
    outside = tmp_path / "escape.checkpoint"
    escaped = save_new(world, "../" + outside.name)
    assert Path(escaped["path"]).parent == path.parent
    assert not outside.exists()
    broken = path.with_name("broken.checkpoint")
    data = bytearray(path.read_bytes())
    data[-1] ^= 0xFF
    broken.write_bytes(data)
    broken_stamp = broken.stat().st_mtime_ns
    failure = lab.verify_checkpoint(str(broken))
    assert failure["ok"] is False
    assert broken.stat().st_mtime_ns == broken_stamp


def test_person_inspection_does_not_invent_names_or_edges(lab):
    lab.start_new(seed=843000, years=4, width=24, height=18, settlements=5, timebox_seconds=0, pace_seconds=0, instrument=False)
    _wait_idle(lab)
    person_id = next(iter(lab.world.people))
    edges = len(lab.world.social.edges)
    wallets = len(lab.world.currency.wallets)
    detail = lab.person(person_id)
    assert detail["name"]["quality"] == "unavailable"
    assert all(item["quality"] == "unavailable" for item in detail["capabilities"].values())
    assert len(lab.world.social.edges) == edges
    assert len(lab.world.currency.wallets) == wallets
    direct = person_detail(lab.world, person_id, lab.event_index[person_id], lab.by_id)
    assert direct["name"]["quality"] == "unavailable"


def test_watcher_indexes_a_new_file_without_a_second_directory_walk(lab, monkeypatch):
    calls = {"n": 0}
    original = lab._scan_root

    def counting(kind, root):
        calls["n"] += 1
        return original(kind, root)

    monkeypatch.setattr(lab, "_scan_root", counting)
    folder = Path(lab.folders["checkpoints"][0])
    target = folder / "appeared.checkpoint"
    target.write_bytes(b"not-a-real-checkpoint")
    deadline = time.time() + 5
    while time.time() < deadline and str(target.resolve()) not in lab.files["checkpoints"]:
        time.sleep(0.05)
    assert str(target.resolve()) in lab.files["checkpoints"]
    assert calls["n"] == 0


def _request(port, path, body=None):
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST" if body is not None else "GET",
    )
    with urllib.request.urlopen(request) as response:
        return response.status, json.load(response)


def test_http_smoke_against_real_benchmark_and_a_short_run(lab):
    httpd = serve(lab, "127.0.0.1", 0)
    port = httpd.server_address[1]
    try:
        _, status = _request(port, "/api/status")
        assert status["version"]["commit"]["quality"] == "measured"
        assert status["folders"]["watcher"] == "watchdog"
        _, report = _request(port, "/api/benchmarks")
        accepted = next(
            run for source in report["sources"] if source["kind"] == "millennium-pass" for run in source["runs"]
            if run["title"] == "first accepted"
        )
        assert accepted["metrics"]["performance_passed"]["value"] is True
        code, started = _request(port, "/api/run/new", {"seed": 843000, "years": 4, "timebox_seconds": 30, "pace_seconds": 0})
        assert code == 200
        deadline = time.time() + 20
        current = started
        while time.time() < deadline and current["state"] not in ("idle", "error"):
            time.sleep(0.05)
            _, current = _request(port, "/api/run")
        assert current["state"] == "idle"
        assert current["year"] == 4
        assert current["samples"][-1]["rss_bytes"]["quality"] == "measured"
        _, overview = _request(port, "/api/overview")
        assert overview["loaded"] is True
        assert overview["population"]["quality"] == "measured"
        _, people = _request(port, "/api/people?limit=5")
        assert people["total"] > 0
        person_id = people["people"][0]["id"]
        _, detail = _request(port, f"/api/people/{person_id}")
        assert detail["name"]["quality"] == "unavailable"
        _, timeline = _request(port, "/api/timeline?year=1")
        assert timeline["events"]["quality"] == "measured"
        refused = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/run/new",
            data=json.dumps({"seed": 1, "years": 1000}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            urllib.request.urlopen(refused)
            raise AssertionError("1000-year run was accepted")
        except urllib.error.HTTPError as exc:
            assert exc.code == 400
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_server_static_page_mentions_the_laboratory(lab):
    httpd = serve(lab, "127.0.0.1", 0)
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{httpd.server_address[1]}/") as response:
            html = response.read().decode("utf-8")
        assert "Simulation Laboratory" in html
        assert "app.js" in html
    finally:
        httpd.shutdown()
        httpd.server_close()
