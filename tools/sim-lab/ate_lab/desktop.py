"""Open the laboratory in a native window when the desktop toolkit is installed."""

from __future__ import annotations


def open_window(url: str) -> tuple[bool, str]:
    try:
        import webview
    except Exception as exc:
        return False, (
            "pywebview is not available (" + f"{type(exc).__name__}: {exc}" + "). "
            "The interface is still being served. Open the printed URL, or install pywebview "
            "inside the laboratory virtual environment. Windows 11 uses WebView2 through pywebview."
        )
    webview.create_window(
        "ALL THAT ENDURES — Simulation Laboratory",
        url,
        width=1480,
        height=940,
        min_size=(1100, 720),
        background_color="#0c0e11",
    )
    webview.start()
    return True, ""
