"""Reporting: HTML / PDF / CSV export of model results."""

from pathlib import Path
from typing import Any


def export_html(model_summary: Any, path: str | Path) -> Path:
    """Write an HTML model report and return its path."""
    raise NotImplementedError
