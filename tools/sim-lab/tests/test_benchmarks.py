import json
import subprocess
from pathlib import Path

from ate_lab.benchmarks import discover, documented_gate
from ate_lab.paths import repo_root


def test_gate_is_the_documented_120_seconds():
    gate = documented_gate(repo_root())
    assert gate["quality"] == "documented"
    assert gate["value"] == 120
    assert gate["seed"] == 843000
    assert gate["years"] == 1000


def test_millennium_file_is_parsed_not_recomputed():
    path = repo_root() / "simulation" / "performance" / "millennium-pass.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    report = discover([str(path.parent)])
    source = next(item for item in report["sources"] if item["kind"] == "millennium-pass")
    assert source["note"] == raw["note"]
    assert source["comparison"]["same_canonical_digest"]["value"] is True
    assert source["comparison"]["different_shared_fields"]["value"] == []
    by_title = {run["title"]: run for run in source["runs"]}
    accepted = by_title["first accepted"]
    baseline = by_title["baseline"]
    assert accepted["metrics"]["simulation_seconds"]["value"] == raw["first_accepted"]["benchmark"]["simulation_seconds"]
    assert accepted["metrics"]["simulation_seconds"]["quality"] == "measured"
    assert accepted["metrics"]["performance_passed"]["value"] is True
    assert accepted["metrics"]["performance_passed"]["quality"] == "measured"
    assert accepted["metrics"]["digest"]["value"] == raw["first_accepted"]["benchmark"]["digest"]
    assert accepted["metrics"]["gate_comparison"]["value"] is True
    assert accepted["metrics"]["gate_comparison"]["quality"] == "calculated"
    assert baseline["metrics"]["performance_passed"]["quality"] == "unavailable"
    assert baseline["metrics"]["simulation_seconds"]["value"] == raw["baseline"]["benchmark"]["simulation_seconds"]
    assert baseline["metrics"]["gate_comparison"]["value"] is False
    living = [bucket["living"]["value"] for bucket in accepted["buckets"]]
    assert living == [bucket["collections"]["living"] for bucket in raw["first_accepted"]["buckets"]]
    assert accepted["snapshot"]["fields"]["alive"]["value"] == raw["first_accepted"]["snapshot"]["alive"]


def test_unparsed_json_is_not_turned_into_numbers(tmp_path: Path):
    odd = tmp_path / "notes.json"
    odd.write_text(json.dumps({"hello": "world"}), encoding="utf-8")
    report = discover([str(tmp_path)])
    source = report["sources"][0]
    assert source["kind"] == "unparsed"
    assert source["runs"] == []
    assert source["detail"]["quality"] == "unavailable"


def test_partial_jsonl_tail_is_not_a_metric(tmp_path: Path):
    path = tmp_path / "run.jsonl"
    path.write_text('{"record":"lab_year","year":1,"step_seconds":0.01}\n{"record":"lab_y', encoding="utf-8")
    report = discover([str(tmp_path)])
    source = report["sources"][0]
    assert source["incomplete_tail"] == 1
    assert source["runs"][0]["metrics"]["performance_passed"]["quality"] == "unavailable"
