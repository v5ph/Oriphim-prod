"""The render stamp — what makes an exhibit reproducible.

`renderer version + scene hash + data hash` fully determines the output. The
hashes here are SHA-256 over canonical JSON, matching the ledger schema's
`scene_sha256` / `data_sha256`. World scale and scalar ranges are resolved
once, here, exactly as the renderer resolves them — never re-fit per frame.
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any

from pydantic import BaseModel

from oriphim.core.render.data import RenderData
from oriphim.core.render.scene import ParticlesObject, Scene

RENDERER_VERSION = "1.0.0"


class ScalarRange(BaseModel):
    min: float
    max: float
    stated: bool
    """True when the SCENE gave the range; False means auto-ranged over this run."""


class Stamp(BaseModel):
    """Belongs in the figure caption or the report appendix."""

    renderer: str = RENDERER_VERSION
    scene_sha256: str
    data_sha256: str
    run_id: str | None
    frames: int
    world_scale: float
    world_fit: str
    interpolated: bool
    scalar_ranges: dict[str, ScalarRange]


def sha256(obj: Any) -> str:
    """SHA-256 of `obj` serialised to canonical JSON (sorted keys, no spaces)."""
    canonical = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def stamp(scene: Scene, data: RenderData) -> Stamp:
    """Compute the reproducibility stamp for a scene + data pair."""
    run_id = data.meta.get("run_id")
    return Stamp(
        scene_sha256=sha256(scene.for_renderer()),
        data_sha256=sha256(data.for_renderer()),
        run_id=run_id if isinstance(run_id, str) else None,
        frames=data.frames,
        world_scale=_resolve_world_scale(scene, data),
        world_fit=scene.world.fit,
        interpolated=scene.playback.interpolate,
        scalar_ranges=_resolve_scalar_ranges(scene, data),
    )


def _resolve_world_scale(scene: Scene, data: RenderData) -> float:
    if scene.world.fit != "once":
        return scene.world.scale
    cx, cy, cz = scene.world.center
    farthest = 0.0
    for track in data.tracks.values():
        for frame in track.positions:
            for i in range(0, len(frame), 3):
                d = math.dist((frame[i], frame[i + 1], frame[i + 2]), (cx, cy, cz))
                farthest = max(farthest, d)
    return 1.0 / farthest if farthest > 0 else scene.world.scale


def _resolve_scalar_ranges(scene: Scene, data: RenderData) -> dict[str, ScalarRange]:
    ranges: dict[str, ScalarRange] = {}
    for obj in scene.objects:
        if not isinstance(obj, ParticlesObject) or obj.scalar is None:
            continue
        key = f"{obj.track}::{obj.scalar}"
        if key in ranges:
            continue
        if obj.range is not None:
            ranges[key] = ScalarRange(min=obj.range[0], max=obj.range[1], stated=True)
            continue
        lo, hi = math.inf, -math.inf
        for values in data.tracks[obj.track].scalars.get(obj.scalar, []):
            for v in values:
                lo, hi = min(lo, v), max(hi, v)
        ranges[key] = (
            ScalarRange(min=lo, max=hi, stated=False)
            if lo < hi
            else ScalarRange(min=0.0, max=1.0, stated=False)
        )
    return ranges
