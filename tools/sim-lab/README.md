# ATE Simulation Laboratory

A local desktop instrument for running, watching, inspecting, and measuring the All That Endures simulation. It talks to the engine through `generate_world`, `Simulation.step`, `ate_sim.checkpoint`, and the benchmark files that are already in the repository. It does not change simulation rules, canon, balance, determinism, or checkpoint schema.

The laboratory runs on your PC. There is no account, no subscription, and no hosted service. The only network use is an optional fast-forward of **this install's** git branch.

## What you are installing

Install into a **new clone**. Do not run it inside `C:\Users\Owner\Projects\all-that-endures`, and do not point it at that folder as a Python path. That checkout may have uncommitted work. This program never writes there and never imports code from there.

Checkpoints already stored in the main checkout can be **read**. Set the data root, below, after the first launch.

## Prerequisites

- Windows 11
- Git
- Python **3.12** 64-bit from [python.org](https://www.python.org/downloads/windows/). During setup, enable "Add python.exe to PATH" or leave the `py` launcher selected. The project standard is 3.12. This launcher refuses other versions.
- WebView2, which Windows 11 already includes. `pywebview` uses it for the desktop window.

Node.js is not required.

## Install

In PowerShell:

```powershell
cd C:\Users\Owner\Projects
git clone --branch cursor/simulation-laboratory-54c5 --single-branch https://github.com/rax0h/all-that-endures.git C:\Users\Owner\Projects\ate-sim-lab
cd C:\Users\Owner\Projects\ate-sim-lab
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -r tools\sim-lab\requirements.txt
```

A linked worktree is also possible, and the updater will still only fast-forward the branch checked out in that worktree. A separate clone is the safer default because `git fetch` then cannot update remote-tracking names shared with the main checkout. Either way, the updater will not checkout, reset, or merge any other branch, and it will not touch files in `C:\Users\Owner\Projects\all-that-endures`.

## Launch

```powershell
C:\Users\Owner\Projects\ate-sim-lab\tools\sim-lab\windows\Launch-SimLab.cmd
```

The launcher:

1. Finds Python 3.12 and creates `.venv` in the laboratory clone if it is missing.
2. Installs `tools\sim-lab\requirements.txt` when that file changes.
3. Runs `simlab.py --update-only`, which fetches this clone's tracked branch and fast-forwards only when the worktree is clean and the pull is a fast-forward. Offline, dirty, or diverged histories are skipped and the current version launches.
4. Starts the window with `--no-update` so it does not update twice.

A console window shows the update result, then the desktop window opens. The running commit is in the top-right of the window. A log is written to `%LOCALAPPDATA%\ATE-SimLab\launch.log`.

### Desktop and Start menu

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\Owner\Projects\ate-sim-lab\tools\sim-lab\windows\Install-Shortcut.ps1
```

That creates **ATE Simulation Laboratory** on the Desktop and in the Start menu. Both shortcuts run the launcher above.

### Read the main checkout's files

In the laboratory, open **Settings** and set **Read-only data root** to:

```text
C:\Users\Owner\Projects\all-that-endures
```

On the first launch, before a settings file exists, the same path can be supplied as `ATE_DATA_ROOT`. Settings live in `%LOCALAPPDATA%\ATE-SimLab\settings.json`, outside both checkouts.

The laboratory adds a folder only when it already exists. It looks for:

- `checkpoints`, `simulation\checkpoints`
- `outputs`, `simulation\outputs`
- `simulation\performance`, `performance`

It lists those directories. It does not walk the rest of the checkout, it does not import that code, and it does not create or modify files there. `simulation\performance\millennium-pass.json` in **this** install is watched as well, so the recorded 1,000-year benchmark is available without a data root.

New checkpoints and run logs are written only under:

```text
C:\Users\Owner\Projects\ate-sim-lab\tools\sim-lab\var\
```

### Check for updates

**Settings → Check for updates** reports whether the tracked branch can fast-forward. It applies the fast-forward only after confirmation, and it refuses to apply one while a run is active. **Check this install's branch on launch** is on by default.

The update is skipped, and the current version still opens, when:

- the machine is offline or `git fetch` fails
- this install has uncommitted changes
- the remote history is not a fast-forward
- HEAD is detached

### Studio Command

The rax0h studio hub can start the laboratory with this command and the laboratory clone as the working directory:

```text
C:\Users\Owner\Projects\ate-sim-lab\.venv\Scripts\pythonw.exe C:\Users\Owner\Projects\ate-sim-lab\tools\sim-lab\simlab.py --no-update
```

`--no-window` serves `http://127.0.0.1:8765/` and prints the URL instead of opening a window. The server binds to localhost only.

## Modules

| Module | What it shows |
| --- | --- |
| Control | New world (`generate_world` seed, width, height, settlements), continue, pause, resume, stop, per-year time, population, memory. Optional subsystem instrumentation. |
| Observatory | Population, births, deaths, ranks, species, age, settlement stocks, cell fields, and the recorded year-1000 benchmark snapshot. |
| Inspector | Person, household, genealogy, skills, essence path, relationships, wallet. No invented names. |
| Timeline | One year of `events_between`, filtered by kind and layer. |
| Performance | The documented 120-second gate, `millennium-pass.json`, and this session's measured step times. |
| Checkpoints | Discover, read stored year/seed/digest, verify with the official loader, compare headers, open. |
| Settings | Update toggle, data root, year cap, extra folders. |

Every number is tagged **measured**, **calculated**, **documented**, or **unavailable**. A chart is omitted when its series was not produced. **Pass recorded** appears only when a benchmark file contains `performance_passed: true`. Laboratory runs are not the 1,000-year gate and do not receive a pass.

Pause, stop, and the timebox take effect at the next year boundary. `Simulation.step` is one whole year; interrupting it would break determinism. Replay pacing is a sleep *after* the measured step.

The year cap defaults to 250 and cannot be set higher. The 1,000-year benchmark stays on the existing command:

```text
PYTHONPATH=.:simulation python simulation/run_long_history.py 843000 1000 --max-seconds 120
```

## Engine hooks

None. No file under `simulation/` is modified. Opt-in subsystem timing uses the existing `scaling_telemetry.ScalingTelemetry` wrappers, which a laboratory test checks against `Simulation.run` for an identical canonical digest. Checkpoint saves use `ate_sim.checkpoint.save` and only create a new file under `tools/sim-lab/var/checkpoints`. Official `checkpoint.load` is used to open or verify, and those calls are timed. The stored digest is not recomputed during a directory listing.

## Tests

From the laboratory clone, with the venv active:

```powershell
.\.venv\Scripts\python -m pip install -r tools\sim-lab\requirements-dev.txt
.\.venv\Scripts\python -m pytest -q tools\sim-lab\tests
```

## Extending

`ate_lab/extensions.py` lists implemented modules and modules that are intentionally not built (world map, family tree, economic flow, progression studio, replay). The observatory already exposes cell fields and settlement coordinates. The inspector already exposes genealogy links. A new module is a view in `static/app.js`, a route in `ate_lab/server.py`, and an entry in `MODULES`.

## Limits

- People have no personal names in the current world state.
- Settlement population over past years is not retained. The current year is measured. Bucket-end living counts in `millennium-pass.json` are shown separately and are not an annual series.
- Population over time is replayed from founders (`born <= 0`) and birth, death, and resurrection events, then checked against the living set. If the check fails, the series is withheld.
- One world is loaded at a time. Opening a checkpoint or starting a world replaces memory only.
- Checkpoints are pickle files. Only open files you produced. The loader is the project's own `pickle` format, schema 4.
- There is no in-app editor for canon, balance, or persistence.
- The repository's performance and persistence work is Stage 0.5 (the 120-second millennium gate and checkpoint schema 4). This laboratory does not change it. There is no Stage 0.6 implementation in the tree.
