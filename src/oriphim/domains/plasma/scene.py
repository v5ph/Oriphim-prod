"""Author a SCENE for a plasma run.

The "model writes the SCENE" seam. For now this is a deterministic default: it
reads what the DATA actually contains and points a `particles` object at each
points track, keyed on whatever scalar is there. When the model writes SCENEs
itself, this stays as the fallback.
"""

from __future__ import annotations

from typing import Any

from oriphim.core.brief.envelope import Envelope
from oriphim.core.render.data import RenderData
from oriphim.core.render.scene import Camera, ParticlesObject, Scene, SceneObject, World


def default_plasma_scene(brief: Envelope[Any] | None, data: RenderData) -> Scene:
    """A report-ready SCENE for `data`, provenance drawn from `brief` when given."""
    objects: list[SceneObject] = [
        ParticlesObject(
            id=name,
            track=name,
            scalar=next(iter(track.scalars), None),
            radius=0.004,
            floor=0.28,
        )
        for name, track in data.tracks.items()
        if track.kind == "points"
    ]
    return Scene(
        camera=Camera(interactive=False),  # a report figure, not the live view
        world=World(fit="once"),
        objects=objects,
        provenance={
            "run_id": brief.run_id if brief is not None else data.meta.get("run_id"),
            "figure": brief.title if brief is not None else "",
        },
    )
