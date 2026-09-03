"""SCENE — the declarative half of a render.

Small, model-written, no motion in it. These models mirror
`docs/standards/scene-spec.md` field for field, JSON key for JSON key — including
the two camelCase keys, `depthFade` and `maxVoxels` — so a SCENE the model wrote
round-trips through this module unchanged.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field

_Vec3 = tuple[float, float, float]


class Style(BaseModel):
    """House rendering identity. Changed only when legibility demands it."""

    cell: int = 2
    voxpx: float = 1.8
    chroma: float = 1.0
    gamma: float = 0.88
    light: _Vec3 = (-0.44, 0.55, 0.71)
    depthFade: float = 0.38  # camelCase: matches the SCENE spec key exactly


class Camera(BaseModel):
    size: float = 0.34
    zoom: float = 1.0
    tilt: float = -0.30
    yaw: float = 0.0
    spin: float = 0.45
    interactive: bool = True
    """False removes the drag handle — the setting for report figures."""


class Playback(BaseModel):
    fps: int = 30
    speed: float = 1.0
    loop: bool = True
    interpolate: bool = False
    """True only when the frame rate is too coarse to read; recorded in the stamp."""


class World(BaseModel):
    scale: float = 1.0
    center: _Vec3 = (0.0, 0.0, 0.0)
    fit: Literal["none", "once"] = "none"
    """"none" uses `scale` as given (comparable across runs); "once" fits at load."""


class _Object(BaseModel):
    id: str
    track: str
    brightness: float = 1.0


class ShellObject(_Object):
    """A body with a radius, drawn as a lit point shell. Track must be `rigid`."""

    type: Literal["shell"] = "shell"
    radius: float
    points: int = 9000
    dark: bool = False
    """Near-black with a hard bright limb — event horizons, voids, silhouettes."""


class CurveObject(_Object):
    """A polyline, optionally widened into a ribbon. Track must be `polyline`."""

    type: Literal["curve"] = "curve"
    width: float = 0.0
    across: int = 7
    twist: float = 0.0


class ParticlesObject(_Object):
    """One drawn element per point in the track. Track must be `points`."""

    type: Literal["particles"] = "particles"
    scalar: str | None = None
    range: tuple[float, float] | None = None
    """State it whenever the physical range is known — it makes the figure comparable."""
    radius: float = 0.0
    maxVoxels: int = 4  # camelCase: matches the SCENE spec key exactly
    floor: float = 0.26
    gain: float = 1.05


SceneObject = Annotated[
    ShellObject | CurveObject | ParticlesObject,
    Field(discriminator="type"),
]


class Scene(BaseModel):
    """What to draw and how. Written by the model; carries no positions."""

    version: Literal["1.0.0"] = "1.0.0"
    style: Style = Field(default_factory=Style)
    camera: Camera = Field(default_factory=Camera)
    playback: Playback = Field(default_factory=Playback)
    world: World = Field(default_factory=World)
    objects: list[SceneObject]
    provenance: dict[str, Any] = Field(default_factory=dict)

    def for_renderer(self) -> dict[str, Any]:
        """The dict the renderer consumes — spec key names, defaults filled in."""
        return self.model_dump()
