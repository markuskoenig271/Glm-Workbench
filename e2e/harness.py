"""Shared helpers for the manual E2E runners in this directory.

These scripts run against the real app and real data. They are run manually
from the repo root (see README.md) and are intentionally NOT collected by
pytest (`testpaths = ["tests"]` in pyproject.toml).
"""

from __future__ import annotations

import subprocess
import time
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

PORT = 8598
URL = f"http://localhost:{PORT}"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


@contextmanager
def streamlit_app(port: int = PORT) -> Iterator[str]:
    """Launch the app headless on `port`, yield its URL, kill the process tree on exit.

    Must be entered with the repo root as the working directory (`app.py` is
    resolved relative to it). Teardown uses `taskkill` — Windows only.
    """
    url = f"http://localhost:{port}"
    app = subprocess.Popen(
        [
            "uv",
            "run",
            "streamlit",
            "run",
            "app.py",
            "--server.port",
            str(port),
            "--server.headless",
            "true",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(30):
            try:
                with urllib.request.urlopen(url, timeout=2) as r:
                    if r.status == 200:
                        break
            except Exception:
                time.sleep(1)
        else:
            raise SystemExit(f"FAIL: app did not come up on {port}")
        yield url
    finally:
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(app.pid)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
