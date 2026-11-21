"""Watch configured folders for new files without rereading their contents."""

from __future__ import annotations

import threading
from pathlib import Path


class FolderWatcher:
    def __init__(self, on_path):
        self.on_path = on_path
        self._observer = None
        self._lock = threading.Lock()
        self.mode = "stopped"
        self.roots: list[str] = []

    def set_roots(self, roots: list[str]) -> None:
        resolved = []
        seen = set()
        for root in roots:
            path = Path(root)
            if not path.is_dir():
                continue
            text = str(path.resolve())
            if text in seen:
                continue
            seen.add(text)
            resolved.append(text)
        with self._lock:
            self._stop_unlocked()
            self.roots = resolved
            if not resolved:
                self.mode = "idle"
                return
            try:
                from watchdog.events import FileSystemEventHandler
                from watchdog.observers import Observer
            except ImportError:
                self.mode = "unavailable"
                return

            watcher = self

            class Handler(FileSystemEventHandler):
                def on_created(self, event):
                    watcher._emit(event)

                def on_modified(self, event):
                    watcher._emit(event)

                def on_deleted(self, event):
                    watcher._emit(event)

                def on_moved(self, event):
                    watcher._emit(event, getattr(event, "src_path", None))
                    watcher._emit(event, getattr(event, "dest_path", None))

            observer = Observer()
            handler = Handler()
            for root in resolved:
                observer.schedule(handler, root, recursive=False)
            observer.start()
            self._observer = observer
            self.mode = "watchdog"

    def _emit(self, event, path=None):
        if getattr(event, "is_directory", False):
            return
        target = path or getattr(event, "src_path", None)
        if not target:
            return
        try:
            self.on_path(str(target), getattr(event, "event_type", "changed"))
        except Exception:
            return

    def _stop_unlocked(self) -> None:
        observer = self._observer
        self._observer = None
        if observer is not None:
            observer.stop()
            observer.join(timeout=2)

    def stop(self) -> None:
        with self._lock:
            self._stop_unlocked()
            self.mode = "stopped"
