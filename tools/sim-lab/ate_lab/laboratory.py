"""In-memory laboratory session: one world, one run, read-only files elsewhere."""

from __future__ import annotations

import copy
import json
import platform
import queue
import threading
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter, sleep

from . import benchmarks, checkpoints, extract
from .errors import LabError
from .memory_probe import rss_bytes
from .paths import contained, output_write_dir
from .settings import load, save, watched_folders
from .values import calculated, jsonable, measured, unavailable
from .watcher import FolderWatcher

HEADER_BYTES = 4_000_000


class EventBus:
    def __init__(self):
        self._lock = threading.Lock()
        self._subs: list[queue.Queue] = []

    def subscribe(self) -> queue.Queue:
        inbox: queue.Queue = queue.Queue(maxsize=400)
        with self._lock:
            self._subs.append(inbox)
        return inbox

    def unsubscribe(self, inbox: queue.Queue) -> None:
        with self._lock:
            if inbox in self._subs:
                self._subs.remove(inbox)

    def publish(self, event: str, data: dict) -> None:
        message = f"event: {event}\ndata: {json.dumps(jsonable(data), separators=(',', ':'))}\n\n"
        with self._lock:
            subscribers = list(self._subs)
        for inbox in subscribers:
            try:
                inbox.put_nowait(message)
            except queue.Full:
                try:
                    inbox.get_nowait()
                except queue.Empty:
                    pass
                try:
                    inbox.put_nowait(message)
                except queue.Full:
                    pass


class Laboratory:
    def __init__(self, settings: dict | None = None):
        self.settings = settings or load()
        self.lock = threading.RLock()
        self.bus = EventBus()
        self.world = None
        self.source = None
        self.overview = None
        self.people_index: list[dict] = []
        self.event_index: dict[int, list[int]] = defaultdict(list)
        self.by_id: dict = {}
        self.series: dict = {}
        self.population_ok = False
        self.alive_ids: set[int] = set()
        self.samples: list[dict] = []
        self.state = "idle"
        self.reason = "no world loaded"
        self.error = None
        self.run_meta: dict = {}
        self.thread: threading.Thread | None = None
        self._pause = threading.Event()
        self._pause.set()
        self._stop = threading.Event()
        self._log = None
        self.files = {"checkpoints": {}, "outputs": {}, "benchmarks": {}}
        self.folders = {"checkpoints": [], "outputs": [], "benchmarks": []}
        self.benchmark_cache = None
        self._header_queue: queue.Queue = queue.Queue()
        self._header_thread = threading.Thread(target=self._header_loop, name="ate-lab-headers", daemon=True)
        self._header_thread.start()
        self.watcher = FolderWatcher(self._on_watch)
        self.configure_folders()

    def close(self) -> None:
        self.request_stop()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=3)
        self._header_queue.put(None)
        self.watcher.stop()
        self._close_log()

    def configure_folders(self) -> dict:
        folders = watched_folders(self.settings)
        with self.lock:
            self.folders = {
                "checkpoints": folders["checkpoints"],
                "outputs": folders["outputs"],
                "benchmarks": folders["benchmarks"],
            }
            self.files = {"checkpoints": {}, "outputs": {}, "benchmarks": {}}
            self.benchmark_cache = None
            for kind, roots in self.folders.items():
                for root in roots:
                    self._scan_root(kind, Path(root))
        roots = folders["checkpoints"] + folders["outputs"] + folders["benchmarks"]
        self.watcher.set_roots(roots)
        self.bus.publish("files", {"change": "rescan", "watcher": self.watcher.mode})
        folders["watcher"] = self.watcher.mode
        return folders

    def _scan_root(self, kind: str, root: Path) -> None:
        try:
            children = list(root.iterdir())
        except OSError:
            return
        for path in children:
            if path.is_file():
                self._index_file(kind, path)

    def _folder_kind(self, path: Path) -> str | None:
        try:
            parent = str(path.resolve().parent)
        except OSError:
            return None
        for kind, roots in self.folders.items():
            if parent in roots:
                return kind
        return None

    def _index_file(self, kind: str, path: Path) -> None:
        resolved = path.resolve()
        if kind == "checkpoints" and not checkpoints.is_checkpoint_name(resolved):
            return
        if kind == "outputs" and resolved.suffix.lower() not in {".jsonl", ".json", ".log", ".txt"}:
            return
        if kind == "benchmarks" and resolved.suffix.lower() not in {".json", ".jsonl"}:
            return
        key = str(resolved)
        try:
            stat = resolved.stat()
        except OSError:
            self.files[kind].pop(key, None)
            return
        previous = self.files[kind].get(key, {})
        row = {
            "path": key,
            "name": resolved.name,
            "bytes": stat.st_size,
            "mtime": stat.st_mtime,
            "kind": kind,
        }
        header = previous.get("header")
        if header and previous.get("mtime") == stat.st_mtime and previous.get("bytes") == stat.st_size:
            row["header"] = header
        self.files[kind][key] = row

    def _on_watch(self, path_str: str, event_type: str) -> None:
        path = Path(path_str)
        kind = self._folder_kind(path)
        if kind is None:
            return
        with self.lock:
            if event_type == "deleted" or not path.exists():
                self.files[kind].pop(str(path.resolve()) if path.exists() else path_str, None)
                try:
                    self.files[kind].pop(str(path.resolve()), None)
                except OSError:
                    pass
            else:
                self._index_file(kind, path)
            if kind == "benchmarks":
                self.benchmark_cache = None
            indexed = path.exists() and str(path.resolve()) in self.files[kind]
            size = self.files[kind].get(str(path.resolve()), {}).get("bytes") if path.exists() else None
        self.bus.publish("files", {"path": path_str, "change": event_type, "kind": kind})
        if (
            kind == "checkpoints"
            and indexed
            and event_type != "deleted"
            and isinstance(size, int)
            and size <= HEADER_BYTES
        ):
            self._header_queue.put(str(path.resolve()))

    def _header_loop(self) -> None:
        while True:
            path = self._header_queue.get()
            if path is None:
                return
            try:
                header = checkpoints.read_header(Path(path))
            except Exception as exc:
                header = {"path": path, "error": f"{type(exc).__name__}: {exc}"}
            with self.lock:
                row = self.files["checkpoints"].get(path)
                if row is not None:
                    row["header"] = header
            self.bus.publish("files", {"path": path, "change": "header", "kind": "checkpoints"})

    def update_settings(self, updates: dict) -> dict:
        self.settings = save(updates)
        self.configure_folders()
        return self.settings

    def request_stop(self) -> dict:
        self._stop.set()
        self._pause.set()
        if self.thread and self.thread.is_alive():
            self.state = "stopping"
            self.reason = "stop requested; it takes effect at the next year boundary"
        return self.run_status()

    def pause(self) -> dict:
        if self.state not in ("running", "pausing"):
            raise LabError("nothing is running")
        self._pause.clear()
        self.state = "pausing"
        self.reason = "pause requested; it takes effect at the next year boundary"
        self.bus.publish("run", self._run_status_unlocked())
        return self._run_status_unlocked()

    def resume(self) -> dict:
        if self.state not in ("paused", "pausing"):
            raise LabError("the run is not paused")
        self._pause.set()
        self.state = "running"
        self.reason = "running"
        self.bus.publish("run", self._run_status_unlocked())
        return self._run_status_unlocked()

    def _require_idle(self) -> None:
        if self.thread and self.thread.is_alive():
            raise LabError("a run is active; stop it before loading or starting another")

    def _bounds(self, years: int) -> int:
        cap = int(self.settings["year_cap"])
        if years < 1:
            raise LabError("years must be at least 1")
        if years > cap:
            raise LabError(
                f"this laboratory refuses runs longer than {cap} years. "
                "The 1,000-year benchmark stays on the existing command line and is not launched from here."
            )
        return years

    def start_new(self, *, seed: int, years: int, width: int, height: int, settlements: int,
                  timebox_seconds: float, pace_seconds: float, instrument: bool) -> dict:
        years = self._bounds(int(years))
        if not 8 <= int(width) <= 36 or not 8 <= int(height) <= 28 or not 1 <= int(settlements) <= 8:
            raise LabError("world size is limited to width 8–36, height 8–28, and 1–8 settlements")
        pace_seconds = max(0.0, min(2.0, float(pace_seconds)))
        timebox_seconds = max(0.0, float(timebox_seconds))
        with self.lock:
            self._require_idle()
            eng = extract.engine()
            world = eng["worldgen"].generate_world(int(seed), int(width), int(height), int(settlements))
            self.samples = []
            self.error = None
            self._attach(world, {
                "kind": "new",
                "seed": int(seed),
                "width": int(width),
                "height": int(height),
                "settlements": int(settlements),
                "checkpoint": None,
            })
            self._start_thread(years, timebox_seconds, pace_seconds, instrument, continued=False)
        status = self.run_status()
        self.bus.publish("run", status)
        self.bus.publish("world", {"reason": "new"})
        return status

    def start_continue(self, *, years: int, timebox_seconds: float, pace_seconds: float, instrument: bool) -> dict:
        years = self._bounds(int(years))
        pace_seconds = max(0.0, min(2.0, float(pace_seconds)))
        timebox_seconds = max(0.0, float(timebox_seconds))
        with self.lock:
            self._require_idle()
            if self.world is None:
                raise LabError("load a checkpoint or start a world before continuing")
            self.error = None
            self._start_thread(years, timebox_seconds, pace_seconds, instrument, continued=True)
        status = self.run_status()
        self.bus.publish("run", status)
        return status

    def _start_thread(self, years, timebox_seconds, pace_seconds, instrument, continued: bool) -> None:
        self._stop.clear()
        self._pause.set()
        self.state = "running"
        self.reason = "running"
        self.run_meta = {
            "years_requested": years,
            "timebox_seconds": timebox_seconds,
            "pace_seconds": pace_seconds,
            "instrument": bool(instrument),
            "continued": continued,
            "started": datetime.now(timezone.utc).isoformat(),
        }
        self._open_log()
        self.thread = threading.Thread(target=self._run, name="ate-lab-run", daemon=True)
        self.thread.start()

    def _open_log(self) -> None:
        self._close_log()
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        seed = self.world.seed if self.world is not None else "none"
        path = output_write_dir() / f"lab-seed{seed}-{stamp}.jsonl"
        self._log = path.open("a", encoding="utf-8")
        self.run_meta["log_path"] = str(path)

    def _close_log(self) -> None:
        if self._log is not None:
            self._log.close()
            self._log = None

    def _write_log(self, record: dict) -> None:
        if self._log is None:
            return
        self._log.write(json.dumps(jsonable(record), separators=(",", ":")) + "\n")
        self._log.flush()

    def _run(self) -> None:
        years = self.run_meta["years_requested"]
        timebox = self.run_meta["timebox_seconds"]
        pace = self.run_meta["pace_seconds"]
        instrument = self.run_meta["instrument"]
        telemetry = None
        stopped = False
        timeboxed = False
        started = perf_counter()
        try:
            if instrument:
                import scaling_telemetry
                telemetry = scaling_telemetry.ScalingTelemetry(self.world)
                telemetry.__enter__()
            # One Simulation for the whole run, matching Simulation.run's loop.
            sim = extract.engine()["engine"].Simulation(self.world)
            for _ in range(years):
                if self._stop.is_set():
                    stopped = True
                    break
                if not self._pause.is_set():
                    self.state = "paused"
                    self.reason = "paused at a year boundary"
                    with self.lock:
                        self._refresh_overview(force=True)
                    self.bus.publish("run", self._run_status_unlocked())
                    while not self._pause.is_set() and not self._stop.is_set():
                        self._pause.wait(0.2)
                    if self._stop.is_set():
                        stopped = True
                        break
                    self.state = "running"
                    self.reason = "running"
                if timebox and (perf_counter() - started) >= timebox:
                    timeboxed = True
                    break
                with self.lock:
                    step_started = perf_counter()
                    sim.step()
                    step_seconds = perf_counter() - step_started
                    sample = self._note_year(step_seconds, telemetry)
                self._write_log({"record": "lab_year", **_flat_sample(sample)})
                self.bus.publish("run", {"state": self.state, "sample": sample, "reason": self.reason})
                if self.world.events and len(self.world.events) < 8000:
                    self.bus.publish("world", {"reason": "year", "year": self.world.year})
                elif self.world.year % 5 == 0:
                    self.bus.publish("world", {"reason": "year", "year": self.world.year})
                remaining = pace
                while remaining > 0 and not self._stop.is_set():
                    chunk = min(0.1, remaining)
                    sleep(chunk)
                    remaining -= chunk
            with self.lock:
                self._refresh_overview(force=True)
        except Exception as exc:
            self.error = f"{type(exc).__name__}: {exc}"
            self.reason = "the year step raised; in-memory state may be partial"
            self.state = "error"
        finally:
            if telemetry is not None:
                telemetry.__exit__(None, None, None)
            simulation_seconds = sum(sample["step_seconds"]["value"] or 0 for sample in self.samples)
            summary = {
                "record": "lab_run",
                "seed": None if self.world is None else self.world.seed,
                "year": None if self.world is None else self.world.year,
                "years_requested": years,
                "years_completed": len(self.samples),
                "stopped_early": stopped,
                "timeboxed": timeboxed,
                "simulation_seconds": simulation_seconds,
                "performance_passed": None,
                "gate": "not the 1000-year unprofiled benchmark",
                "instrument": instrument,
                "pace_seconds": pace,
                "python": platform.python_version(),
                "platform": platform.platform(),
                "error": self.error,
            }
            self._write_log(summary)
            self._close_log()
            if self.state != "error":
                self.state = "idle"
                if timeboxed:
                    self.reason = "stopped at a year boundary because the timebox elapsed; this is a partial run, not a benchmark result"
                elif stopped:
                    self.reason = "stopped at a year boundary"
                else:
                    self.reason = "finished the requested years"
            self.bus.publish("run", self._run_status_unlocked())
            self.bus.publish("world", {"reason": "settled"})

    def _note_year(self, step_seconds: float, telemetry) -> dict:
        world = self.world
        year = world.year
        births = deaths = resurrections = 0
        for event in world.events_between(year, year):
            self.by_id[event.id] = event
            seen = set()
            for actor in event.actors:
                if actor.kind == "person" and actor.id not in seen:
                    seen.add(actor.id)
                    self.event_index[actor.id].append(event.id)
            if event.kind == "birth":
                births += 1
                person_id = extract._actor(event)
                if person_id is not None:
                    self.alive_ids.add(person_id)
            elif event.kind == "death":
                deaths += 1
                person_id = extract._actor(event)
                if person_id is not None:
                    self.alive_ids.discard(person_id)
            elif event.kind == "resurrection":
                resurrections += 1
                person_id = extract._actor(event)
                if person_id is not None:
                    self.alive_ids.add(person_id)
        living = {person.id for person in world.people.values() if person.alive}
        if self.population_ok and living != self.alive_ids:
            self.population_ok = False
            self.series["population"] = unavailable(
                "incremental replay diverged from the living set at "
                f"year {year}; population series withheld"
            )
        elif self.population_ok:
            _append_point(self.series["population"], year, len(living))
        _append_point(self.series["births"], year, births)
        _append_point(self.series["deaths"], year, deaths)
        _append_point(self.series["resurrections"], year, resurrections)
        if len(world.events) < 8000 or year % 5 == 0:
            self._refresh_overview(force=True)
        else:
            self._touch_headlines()
        self.people_index = extract.build_people_index(world)
        subsystem = unavailable("subsystem timing is off; enable instrumentation for this run")
        if telemetry is not None:
            import scaling_telemetry
            bucket = scaling_telemetry.bucket_end(year)
            subsystem = measured(
                dict(telemetry.seconds[bucket]),
                "accumulated seconds in the current scaling bucket from ScalingTelemetry wrappers; "
                "copied at this year. Result-neutral, opt-in.",
            )
        sample = {
            "year": measured(year, "world.year after Simulation.step"),
            "step_seconds": measured(step_seconds, "perf_counter around Simulation.step; display pacing is not included"),
            "population": measured(len(living), "count of people with alive true"),
            "people_total": measured(len(world.people), "len(world.people)"),
            "living_households": calculated(
                extract.living_household_count(world),
                "household.alive and at least one living member",
            ),
            "events": measured(len(world.events), "len(world.events)"),
            "rss_bytes": rss_bytes(),
            "subsystem_seconds": subsystem,
        }
        self.samples.append(sample)
        return sample

    def _touch_headlines(self) -> None:
        if self.overview is None or self.world is None:
            return
        world = self.world
        living = sum(person.alive for person in world.people.values())
        self.overview["year"] = measured(world.year, "world.year")
        self.overview["population"] = measured(living, "count of people with alive true")
        self.overview["people_total"] = measured(len(world.people), "len(world.people)")
        self.overview["events"] = measured(len(world.events), "len(world.events)")
        self.overview["series"] = _public_series(self.series)
        self.overview["living_households"] = calculated(
            extract.living_household_count(world),
            "household.alive and at least one living member",
        )

    def _refresh_overview(self, force: bool = False) -> None:
        if self.world is None:
            return
        if not force and len(self.world.events) >= 8000 and self.world.year % 5 != 0:
            self._touch_headlines()
            return
        self.overview = extract.overview_from_world(self.world, _public_series(self.series), self.source or {})

    def _attach(self, world, source: dict) -> None:
        replay = extract.population_replay(world)
        self.alive_ids = set(replay["alive_ids"])
        self.population_ok = bool(replay["check_ok"])
        self.series = {
            "population": replay["population"],
            "births": replay["births"],
            "deaths": replay["deaths"],
            "resurrections": replay["resurrections"],
        }
        self.world = world
        self.source = source
        self.people_index = extract.build_people_index(world)
        self.event_index = defaultdict(list, extract.build_event_index(world))
        self.by_id = {event.id: event for event in world.events}
        self.overview = extract.overview_from_world(world, _public_series(self.series), source)

    def run_status(self) -> dict:
        with self.lock:
            return self._run_status_unlocked()

    def _run_status_unlocked(self) -> dict:
        world = self.world
        return {
            "state": self.state,
            "reason": self.reason,
            "error": self.error,
            "meta": self.run_meta,
            "samples": list(self.samples),
            "year": None if world is None else world.year,
            "seed": None if world is None else world.seed,
            "loaded": world is not None,
        }

    def public_overview(self) -> dict:
        with self.lock:
            return self._overview_unlocked()

    def _overview_unlocked(self) -> dict:
        if self.overview is None:
            return {"loaded": False, "reason": "no world is loaded"}
        payload = copy.deepcopy(self.overview)
        payload["loaded"] = True
        payload["run_state"] = self.state
        return payload

    def search_people(self, *, query: str, alive: str, species: str, settlement, essence: str,
                      limit: int, offset: int) -> dict:
        with self.lock:
            return self._search_unlocked(query, alive, species, settlement, essence, limit, offset)

    def _search_unlocked(self, query, alive, species, settlement, essence, limit, offset) -> dict:
        if self.world is None:
            raise LabError("no world is loaded")
        limit = max(1, min(200, int(limit)))
        offset = max(0, int(offset))
        rows = self.people_index
        if alive == "yes":
            rows = [row for row in rows if row["alive"]]
        elif alive == "no":
            rows = [row for row in rows if not row["alive"]]
        if species:
            rows = [row for row in rows if row["species"] == species]
        if settlement not in ("", None):
            rows = [row for row in rows if row["settlement"] == int(settlement)]
        if essence == "yes":
            rows = [row for row in rows if row["essence_user"]]
        elif essence == "no":
            rows = [row for row in rows if not row["essence_user"]]
        text = (query or "").strip().lower()
        if text:
            def matches(row: dict) -> bool:
                if text.isdigit() and (str(row["id"]) == text or str(row["id"]).startswith(text)):
                    return True
                return text in str(row["species"]).lower() or text in str(row["occupation"]).lower()
            rows = [row for row in rows if matches(row)]
        return {"total": len(rows), "offset": offset, "limit": limit, "people": rows[offset:offset + limit]}

    def person(self, person_id: int) -> dict:
        self._require_world()
        with self.lock:
            edges = len(self.world.social.edges)
            wallets = len(self.world.currency.wallets)
            detail = extract.person_detail(
                self.world, int(person_id), self.event_index.get(int(person_id), []), self.by_id
            )
            if len(self.world.social.edges) != edges or len(self.world.currency.wallets) != wallets:
                raise LabError("inspection mutated social edges or wallets; this is a laboratory bug")
            return detail

    def household(self, household_id: int) -> dict:
        self._require_world()
        with self.lock:
            return extract.household_detail(self.world, int(household_id))

    def timeline(self, year: int, kind: str, layer: str, limit: int, offset: int) -> dict:
        self._require_world()
        with self.lock:
            return extract.timeline(self.world, int(year), kind or None, layer or None, int(limit), int(offset))

    def event(self, event_id: int) -> dict:
        self._require_world()
        with self.lock:
            return extract.event_detail(self.world, int(event_id), self.by_id)

    def _require_world(self) -> None:
        if self.world is None:
            raise LabError("no world is loaded")

    def _readable(self, path: str, kinds: tuple[str, ...]) -> Path:
        resolved = Path(path).expanduser().resolve()
        roots = [Path(root) for kind in kinds for root in self.folders[kind]]
        if not any(contained(resolved, root) for root in roots):
            raise LabError("that file is outside the configured read folders")
        if not resolved.is_file():
            raise LabError("file does not exist")
        return resolved

    def read_checkpoint(self, path: str) -> dict:
        resolved = self._readable(path, ("checkpoints",))
        header = checkpoints.read_header(resolved)
        with self.lock:
            row = self.files["checkpoints"].get(str(resolved))
            if row is not None:
                row["header"] = header
        return header

    def verify_checkpoint(self, path: str) -> dict:
        resolved = self._readable(path, ("checkpoints",))
        return checkpoints.verify(resolved)

    def load_checkpoint(self, path: str) -> dict:
        resolved = self._readable(path, ("checkpoints",))
        with self.lock:
            self._require_idle()
            before = resolved.stat().st_mtime
            started = perf_counter()
            world = extract.engine()["checkpoint"].load(resolved)
            elapsed = perf_counter() - started
            if resolved.stat().st_mtime != before:
                raise LabError("checkpoint load changed the file mtime; refusing to keep the world")
            self.samples = []
            self._attach(world, {
                "kind": "checkpoint",
                "path": str(resolved),
                "load_seconds": measured(elapsed, "wall time of ate_sim.checkpoint.load, including the official digest check"),
                "mtime_unchanged": True,
            })
        self.bus.publish("world", {"reason": "loaded", "path": str(resolved)})
        return {"loaded": True, "path": str(resolved), "year": world.year, "seed": world.seed,
                "load_seconds": measured(elapsed, "wall time of ate_sim.checkpoint.load, including the official digest check")}

    def save_checkpoint(self, filename: str) -> dict:
        with self.lock:
            self._require_idle()
            self._require_world()
            saved = checkpoints.save_new(self.world, filename)
            self._index_file("checkpoints", Path(saved["path"]))
        self._header_queue.put(saved["path"])
        self.bus.publish("files", {"path": saved["path"], "change": "created", "kind": "checkpoints"})
        return saved

    def compare_checkpoints(self, left: str, right: str) -> dict:
        header_left = self.read_checkpoint(left)
        header_right = self.read_checkpoint(right)
        fields = ("year", "seed", "digest_stored", "bytes", "people", "living", "schema_stored", "file_sha256")
        rows = []
        for field in fields:
            raw_left = _metric_value(header_left.get(field))
            raw_right = _metric_value(header_right.get(field))
            if raw_left is None and raw_right is None and field not in header_left and field not in header_right:
                rows.append({"field": field, "left": unavailable("absent"), "right": unavailable("absent"), "equal": None})
            else:
                rows.append({
                    "field": field,
                    "left": header_left.get(field, unavailable("absent")),
                    "right": header_right.get(field, unavailable("absent")),
                    "equal": raw_left == raw_right,
                })
        return {"rows": rows, "note": "Comparison uses stored header fields. Digests are the stored values unless Verify was run."}

    def measure_digest(self) -> dict:
        with self.lock:
            self._require_idle()
            self._require_world()
            started = perf_counter()
            digest = self.world.digest()
            elapsed = perf_counter() - started
        return {
            "digest": measured(digest, "World.digest canonical hash"),
            "digest_seconds": measured(elapsed, "wall time of World.digest"),
        }

    def benchmark_report(self) -> dict:
        with self.lock:
            if self.benchmark_cache is None:
                self.benchmark_cache = benchmarks.discover(self.folders["benchmarks"])
            return self.benchmark_cache

    def checkpoint_rows(self) -> list[dict]:
        with self.lock:
            rows = list(self.files["checkpoints"].values())
        rows.sort(key=lambda row: row.get("mtime") or 0, reverse=True)
        return rows


def _append_point(metric: dict, year: int, value: int) -> None:
    if not isinstance(metric, dict) or metric.get("quality") == "unavailable":
        return
    points = metric.get("value")
    if not isinstance(points, list):
        return
    if points and points[-1].get("year") == year:
        points[-1]["value"] = value
    else:
        points.append({"year": year, "value": value})


def _public_series(series: dict) -> dict:
    return {key: series[key] for key in ("population", "births", "deaths", "resurrections") if key in series}


def _metric_value(value):
    if isinstance(value, dict) and "quality" in value:
        return value.get("value")
    return value


def _flat_sample(sample: dict) -> dict:
    flat = {}
    for key, value in sample.items():
        if isinstance(value, dict) and "quality" in value:
            flat[key] = value.get("value")
            flat[key + "_quality"] = value.get("quality")
        else:
            flat[key] = value
    return flat
