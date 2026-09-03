"""Cross-check a SCENE against the DATA it refers to.

Pydantic validates each document alone; only together can you see that an
object points at a track that exists, of the kind that object needs, carrying
the scalar it asks for. The scene spec's rule 4 — "the report needs to name
what it's pointing at" — is enforced here.
"""

from __future__ import annotations

from oriphim.core.render.data import RenderData
from oriphim.core.render.scene import ParticlesObject, Scene

_REQUIRED_KIND = {"shell": "rigid", "curve": "polyline", "particles": "points"}


class SceneDataMismatch(ValueError):
    """A SCENE object refers to something the DATA does not provide."""


def validate_scene_against_data(scene: Scene, data: RenderData) -> None:
    """Raise `SceneDataMismatch` if any object cannot be drawn from this DATA."""
    for obj in scene.objects:
        track = data.tracks.get(obj.track)
        if track is None:
            raise SceneDataMismatch(
                f"object {obj.id!r} refers to track {obj.track!r}, "
                f"which is not in the data ({sorted(data.tracks)})"
            )
        want = _REQUIRED_KIND[obj.type]
        if track.kind != want:
            raise SceneDataMismatch(
                f"object {obj.id!r} is a {obj.type} and needs a {want!r} track, "
                f"but {obj.track!r} is {track.kind!r}"
            )
        if isinstance(obj, ParticlesObject) and obj.scalar is not None:
            if obj.scalar not in track.scalars:
                raise SceneDataMismatch(
                    f"object {obj.id!r} asks for scalar {obj.scalar!r}, which track "
                    f"{obj.track!r} does not carry ({sorted(track.scalars)})"
                )
