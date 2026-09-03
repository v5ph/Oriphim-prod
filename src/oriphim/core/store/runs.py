"""Persistence for runs and their artifacts.

A run's artifacts are written as JSON under a per-workspace directory, one file
per artifact, keyed by run id. This is the local-filesystem backing the desktop
app uses; it is deliberately dumb (no index, no migration) and grows a real
shape when a second consumer needs one.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel


def _to_jsonable(artifact: Any) -> Any:
    """A pydantic model, a list of them, or already-plain data — all to JSON-ready."""
    if isinstance(artifact, BaseModel):
        return json.loads(artifact.model_dump_json())
    if isinstance(artifact, (list, tuple)):
        return [_to_jsonable(item) for item in artifact]
    return artifact


class RunStore:
    """Local persistence for briefs, results, and reports.

    `key` is a run id, optionally suffixed to name a second artifact for the
    same run, e.g. ``store.save(f"{run_id}.corrections", records)``.
    """

    def __init__(self, workspace_dir: Path) -> None:
        self.workspace_dir = Path(workspace_dir)

    def _path(self, key: str) -> Path:
        return self.workspace_dir / f"{key}.json"

    def save(self, key: str, artifact: Any) -> Path:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(_to_jsonable(artifact), indent=2), encoding="utf-8")
        return path

    def load(self, key: str) -> Any:
        return json.loads(self._path(key).read_text(encoding="utf-8"))

    def exists(self, key: str) -> bool:
        return self._path(key).is_file()
