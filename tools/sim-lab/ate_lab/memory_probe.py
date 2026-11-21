"""Process memory, measured from the operating system when it allows it."""

from __future__ import annotations

import sys

from .values import measured, unavailable


def rss_bytes() -> dict:
    try:
        if sys.platform.startswith("linux"):
            with open("/proc/self/status", encoding="utf-8") as handle:
                for line in handle:
                    if line.startswith("VmRSS:"):
                        kilobytes = int(line.split()[1])
                        return measured(kilobytes * 1024, "VmRSS from /proc/self/status")
            return unavailable("VmRSS was not present in /proc/self/status")
        if sys.platform == "win32":
            import ctypes
            from ctypes import wintypes

            class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
                _fields_ = [
                    ("cb", wintypes.DWORD),
                    ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                ]

            counters = PROCESS_MEMORY_COUNTERS()
            counters.cb = ctypes.sizeof(counters)
            process = ctypes.windll.kernel32.GetCurrentProcess()
            ok = ctypes.windll.psapi.GetProcessMemoryInfo(
                process, ctypes.byref(counters), counters.cb
            )
            if not ok:
                return unavailable("GetProcessMemoryInfo failed")
            return measured(int(counters.WorkingSetSize), "Windows working set via GetProcessMemoryInfo")
    except Exception as exc:  # probe must not take down a run
        return unavailable(f"memory probe failed: {type(exc).__name__}: {exc}")
    return unavailable(f"no memory probe for platform {sys.platform}")
