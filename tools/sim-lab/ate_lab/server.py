"""Localhost HTTP API and static interface. No account system and no remote bind."""

from __future__ import annotations

import json
import mimetypes
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from queue import Empty
from urllib.parse import parse_qs, urlparse

from .errors import LabError
from .extensions import FUTURE, MODULES
from .paths import checkpoint_write_dir, lab_dir, output_write_dir
from .updater import check_update, read_last_update
from .values import jsonable
from .version import describe

STATIC = lab_dir() / "static"


class LabServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, lab, host: str, port: int):
        self.lab = lab
        super().__init__((host, port), LabHandler)


class LabHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args) -> None:
        return

    @property
    def lab(self):
        return self.server.lab

    def do_GET(self) -> None:
        self._dispatch("GET")

    def do_POST(self) -> None:
        self._dispatch("POST")

    def _dispatch(self, method: str) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        query = {key: values[-1] for key, values in parse_qs(parsed.query).items()}
        try:
            if method == "GET" and path in ("/", "/index.html"):
                self._file(STATIC / "index.html")
                return
            if method == "GET" and path.startswith("/static/"):
                name = path[len("/static/"):]
                target = (STATIC / name).resolve()
                if STATIC.resolve() not in target.parents and target != STATIC.resolve():
                    self._send(404, {"error": "not found"})
                    return
                self._file(target)
                return
            if method == "GET" and path == "/api/stream":
                self._stream()
                return
            body = self._body() if method == "POST" else {}
            payload, status = self._api(method, path, query, body)
            self._send(status, payload)
        except LabError as exc:
            self._send(400, {"error": str(exc)})
        except Exception as exc:
            self._send(500, {"error": f"{type(exc).__name__}: {exc}"})

    def _api(self, method: str, path: str, query: dict, body: dict):
        lab = self.lab
        if method == "GET" and path == "/api/status":
            return {
                "version": describe(),
                "modules": MODULES,
                "future": FUTURE,
                "folders": {
                    "checkpoints": lab.folders["checkpoints"],
                    "outputs": lab.folders["outputs"],
                    "benchmarks": lab.folders["benchmarks"],
                    "watcher": lab.watcher.mode,
                    "checkpoint_write_dir": str(checkpoint_write_dir()),
                    "output_write_dir": str(output_write_dir()),
                },
                "run": lab.run_status(),
                "last_update": read_last_update(),
                "loaded": lab.world is not None,
                "settings": lab.settings,
            }, 200
        if method == "GET" and path == "/api/modules":
            return {"modules": MODULES, "future": FUTURE}, 200
        if method == "GET" and path == "/api/settings":
            from .settings import watched_folders
            return {"settings": lab.settings, "folders": watched_folders(lab.settings), "version": describe(), "last_update": read_last_update()}, 200
        if method == "POST" and path == "/api/settings":
            return {"settings": lab.update_settings(body)}, 200
        if method == "POST" and path == "/api/update":
            if body.get("apply") and lab.thread and lab.thread.is_alive():
                raise LabError("a run is active; check for updates without applying, or stop the run first")
            result = check_update(apply=bool(body.get("apply")))
            return {"update": result}, 200
        if method == "GET" and path == "/api/overview":
            return lab.public_overview(), 200
        if method == "GET" and path == "/api/run":
            return lab.run_status(), 200
        if method == "POST" and path == "/api/run/new":
            return lab.start_new(
                seed=int(body.get("seed", lab.settings["default_seed"])),
                years=int(body.get("years", lab.settings["default_years"])),
                width=int(body.get("width", 24)),
                height=int(body.get("height", 18)),
                settlements=int(body.get("settlements", 5)),
                timebox_seconds=float(body.get("timebox_seconds", lab.settings["default_timebox_seconds"])),
                pace_seconds=float(body.get("pace_seconds", 0)),
                instrument=bool(body.get("instrument", False)),
            ), 200
        if method == "POST" and path == "/api/run/continue":
            return lab.start_continue(
                years=int(body.get("years", 1)),
                timebox_seconds=float(body.get("timebox_seconds", lab.settings["default_timebox_seconds"])),
                pace_seconds=float(body.get("pace_seconds", 0)),
                instrument=bool(body.get("instrument", False)),
            ), 200
        if method == "POST" and path == "/api/run/pause":
            return lab.pause(), 200
        if method == "POST" and path == "/api/run/resume":
            return lab.resume(), 200
        if method == "POST" and path == "/api/run/stop":
            return lab.request_stop(), 200
        if method == "GET" and path == "/api/people":
            return lab.search_people(
                query=query.get("q", ""),
                alive=query.get("alive", ""),
                species=query.get("species", ""),
                settlement=query.get("settlement", ""),
                essence=query.get("essence", ""),
                limit=int(query.get("limit", "80")),
                offset=int(query.get("offset", "0")),
            ), 200
        if method == "GET" and path.startswith("/api/people/"):
            return lab.person(int(path.rsplit("/", 1)[-1])), 200
        if method == "GET" and path.startswith("/api/households/"):
            return lab.household(int(path.rsplit("/", 1)[-1])), 200
        if method == "GET" and path == "/api/timeline":
            if lab.world is None:
                raise LabError("no world is loaded")
            year = int(query.get("year", lab.world.year))
            return lab.timeline(year, query.get("kind", ""), query.get("layer", ""), int(query.get("limit", "150")), int(query.get("offset", "0"))), 200
        if method == "GET" and path.startswith("/api/event/"):
            return lab.event(int(path.rsplit("/", 1)[-1])), 200
        if method == "GET" and path == "/api/checkpoints":
            return {"checkpoints": lab.checkpoint_rows(), "write_dir": lab.folders["checkpoints"][:1]}, 200
        if method == "POST" and path == "/api/checkpoints/read":
            return lab.read_checkpoint(str(body["path"])), 200
        if method == "POST" and path == "/api/checkpoints/verify":
            return lab.verify_checkpoint(str(body["path"])), 200
        if method == "POST" and path == "/api/checkpoints/load":
            return lab.load_checkpoint(str(body["path"])), 200
        if method == "POST" and path == "/api/checkpoints/save":
            return lab.save_checkpoint(str(body.get("filename") or "lab.checkpoint")), 200
        if method == "POST" and path == "/api/checkpoints/compare":
            return lab.compare_checkpoints(str(body["left"]), str(body["right"])), 200
        if method == "POST" and path == "/api/digest":
            return lab.measure_digest(), 200
        if method == "GET" and path == "/api/benchmarks":
            return lab.benchmark_report(), 200
        return {"error": "not found"}, 404

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length > 1_000_000:
            raise LabError("request body is too large")
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        if not raw:
            return {}
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            raise LabError("JSON body must be an object")
        return data

    def _send(self, status: int, payload: dict) -> None:
        raw = json.dumps(jsonable(payload)).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def _file(self, path) -> None:
        if not path.is_file():
            self._send(404, {"error": "not found"})
            return
        data = path.read_bytes()
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _stream(self) -> None:
        inbox = self.lab.bus.subscribe()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()
        try:
            hello = f"event: hello\ndata: {json.dumps(jsonable({'state': self.lab.state}))}\n\n"
            self.wfile.write(hello.encode("utf-8"))
            self.wfile.flush()
            while True:
                try:
                    message = inbox.get(timeout=15)
                except Empty:
                    self.wfile.write(b": keepalive\n\n")
                    self.wfile.flush()
                    continue
                self.wfile.write(message.encode("utf-8"))
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, TimeoutError):
            return
        finally:
            self.lab.bus.unsubscribe(inbox)


def serve(lab, host: str = "127.0.0.1", port: int = 8765) -> LabServer:
    if host not in ("127.0.0.1", "localhost"):
        host = "127.0.0.1"
    httpd = LabServer(lab, host, port)
    thread = threading.Thread(target=httpd.serve_forever, name="ate-lab-http", daemon=True)
    thread.start()
    return httpd
