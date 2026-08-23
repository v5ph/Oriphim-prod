"""Persistence for runs and their artifacts.

Stub for this slice. Signature only.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


class RunStore:
    """Local persistence for briefs, results, and reports."""

    def __init__(self, workspace_dir: Path) -> None:
        self.workspace_dir = workspace_dir

    def save(self, run_id: str, artifact: Any) -> Path:
        raise NotImplementedError

    def load(self, run_id: str) -> Any:
        raise NotImplementedError
