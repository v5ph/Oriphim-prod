"""DATA — solver output frames. Written by the pipeline, never by the model.

Physics-agnostic on purpose: a track is a set of points, a rigid body, or a
polyline, moving over frames, with optional parallel scalars. See
`docs/standards/visualization.md` for why that is enough to draw any system
Oriphim can solve.
"""

from __future__ import annotations

from typing import Any, Literal, Self

from pydantic import BaseModel, Field, model_validator

TrackKind = Literal["rigid", "points", "polyline"]


class Track(BaseModel):
    """One named thing that moves. Element count is fixed across frames in 1.0.0."""

    kind: TrackKind
    positions: list[list[float]]
    """One entry per frame; each a flat [x,y,z, x,y,z, ...] array."""
    scalars: dict[str, list[list[float]]] = Field(default_factory=dict)
    """name -> per-frame, per-element values, parallel to `positions`."""

    @model_validator(mode="after")
    def _check_parallel(self) -> Self:
        if not self.positions:
            raise ValueError("track has no frames")
        width = len(self.positions[0])
        if width == 0 or width % 3 != 0:
            raise ValueError(f"frame length {width} is not a positive multiple of 3")
        for f, frame in enumerate(self.positions):
            if len(frame) != width:
                raise ValueError(
                    f"frame {f} has {len(frame)} values, expected {width} "
                    "(element count must be constant across frames in 1.0.0)"
                )
        n_elements = width // 3
        for name, series in self.scalars.items():
            if len(series) != len(self.positions):
                raise ValueError(
                    f"scalar {name!r} has {len(series)} frames, "
                    f"positions has {len(self.positions)}"
                )
            for f, values in enumerate(series):
                if len(values) != n_elements:
                    raise ValueError(
                        f"scalar {name!r} frame {f} has {len(values)} values, "
                        f"expected {n_elements}"
                    )
        return self


class RenderData(BaseModel):
    """A run's renderable output: metadata plus named tracks."""

    meta: dict[str, Any] = Field(default_factory=dict)
    frames: int
    tracks: dict[str, Track]

    @model_validator(mode="after")
    def _check_frame_count(self) -> Self:
        if self.frames < 1:
            raise ValueError("frames must be >= 1")
        for name, track in self.tracks.items():
            if len(track.positions) != self.frames:
                raise ValueError(
                    f"track {name!r} has {len(track.positions)} frames, "
                    f"data declares {self.frames}"
                )
        return self

    def for_renderer(self) -> dict[str, Any]:
        """The dict the renderer consumes."""
        return self.model_dump()
