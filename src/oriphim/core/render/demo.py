"""Synthetic PIC-shaped DATA, for exercising the renderer without a solver.

Deterministic, and labelled `meta.solver = "none - synthetic"` so it cannot be
mistaken for solver output. A points track carrying a `field_energy` scalar:
a ring of excitation that sweeps out and back over the run.
"""

from __future__ import annotations

import math

from oriphim.core.render.data import RenderData, Track

_GOLDEN_ANGLE = math.pi * (3 - math.sqrt(5))


def demo_data(*, frames: int = 120, elements: int = 700) -> RenderData:
    """A small, deterministic synthetic field for `oriphim render --demo`."""
    positions: list[list[float]] = []
    field_energy: list[list[float]] = []

    for f in range(frames):
        phase = f / frames * 2 * math.pi
        ring = 0.30 + 0.50 * (0.5 + 0.5 * math.sin(phase))
        frame_xyz: list[float] = []
        frame_energy: list[float] = []
        for e in range(elements):
            ang = e * _GOLDEN_ANGLE
            rad = 0.15 + 0.85 * math.sqrt(e / elements)
            breathe = 1.0 + 0.06 * math.sin(phase + rad * 6.0)
            frame_xyz += [
                math.cos(ang) * rad * breathe,
                0.12 * rad * math.sin(phase * 2 + ang),
                math.sin(ang) * rad * breathe,
            ]
            frame_energy.append(0.20 + math.exp(-((rad - ring) ** 2) / 0.02))
        positions.append(frame_xyz)
        field_energy.append(frame_energy)

    return RenderData(
        meta={"run_id": "DEMO-SYNTHETIC", "solver": "none - synthetic", "units": "arbitrary"},
        frames=frames,
        tracks={
            "field": Track(
                kind="points",
                positions=positions,
                scalars={"field_energy": field_energy},
            )
        },
    )
