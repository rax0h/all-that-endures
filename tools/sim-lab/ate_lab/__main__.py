"""Launch the laboratory. Update first, then serve, then open a window."""

from __future__ import annotations

import argparse
import os
import sys
import threading

from . import __version__
from .desktop import open_window
from .laboratory import Laboratory
from .paths import repo_root
from .server import serve
from .settings import load
from .updater import check_update
from .version import describe


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="All That Endures simulation laboratory")
    parser.add_argument("--no-window", action="store_true", help="Serve the interface without opening a desktop window.")
    parser.add_argument("--no-update", action="store_true", help="Do not check the tracked branch before launching.")
    parser.add_argument("--update-only", action="store_true", help="Fast-forward this install if it is clean, then exit.")
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--data-root", default=None, help="Read-only folder of checkpoints and outputs. Never written.")
    args = parser.parse_args(argv)

    if args.data_root:
        os.environ["ATE_DATA_ROOT"] = args.data_root

    if args.update_only:
        result = check_update(apply=True)
        print(result.get("reason") or result.get("action"))
        return 0

    settings = load()
    if not args.no_update and settings.get("update_on_launch", True):
        result = check_update(apply=True)
        if result.get("updated"):
            os.execv(sys.executable, [sys.executable, *sys.argv, "--no-update"])
        print(f"Update: {result.get('action')} — {result.get('reason')}")

    lab = Laboratory(load())
    port = args.port or int(lab.settings["port"])
    try:
        httpd = serve(lab, "127.0.0.1", port)
    except OSError:
        httpd = serve(lab, "127.0.0.1", 0)
    host, bound = httpd.server_address
    url = f"http://{host}:{bound}/"
    identity = describe(repo_root())
    commit = (identity.get("commit_short") or {}).get("value") or "unknown"
    branch = (identity.get("branch") or {}).get("value") or "unknown"
    print(f"ATE Simulation Laboratory {__version__}")
    print(f"Running {branch} @ {commit}")
    print(f"Engine: {identity.get('engine_root')}")
    print(f"Open {url}")
    print("Checkpoints are read-only. New files are written only under this install's tools/sim-lab/var.")
    if args.no_window:
        try:
            threading.Event().wait()
        except KeyboardInterrupt:
            pass
        finally:
            lab.close()
            httpd.shutdown()
        return 0
    opened, message = open_window(url)
    if not opened:
        print(message)
        try:
            threading.Event().wait()
        except KeyboardInterrupt:
            pass
    lab.close()
    httpd.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
