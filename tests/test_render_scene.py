from __future__ import annotations

import pytest
from pydantic import ValidationError

from oriphim.core.render.scene import ParticlesObject, Scene, ShellObject

# The worked example from docs/standards/scene-spec.md.
_WORKED_EXAMPLE = {
    "version": "1.0.0",
    "camera": {"size": 0.30, "tilt": -0.34, "spin": 0.45},
    "playback": {"fps": 60, "loop": True},
    "world": {"scale": 1.0, "fit": "once"},
    "objects": [
        {"id": "hole", "type": "shell", "track": "bh", "radius": 0.20, "dark": True},
        {"id": "m1", "type": "shell", "track": "body1", "radius": 0.30, "points": 9000},
        {"id": "m2", "type": "shell", "track": "body2", "radius": 0.26, "points": 9000},
        {
            "id": "stream",
            "type": "particles",
            "track": "debris",
            "scalar": "specific_energy",
            "range": [-2.0, 0.5],
            "radius": 0.004,
        },
        {"id": "L1", "type": "curve", "track": "orbit1", "width": 0.0},
        {"id": "L2", "type": "curve", "track": "orbit2", "width": 0.0},
    ],
    "provenance": {"run_id": "3B-0142", "figure": "Fig 6.1"},
}


def test_worked_example_parses_with_the_right_object_types() -> None:
    scene = Scene.model_validate(_WORKED_EXAMPLE)
    assert isinstance(scene.objects[0], ShellObject)
    assert scene.objects[0].dark is True
    stream = scene.objects[3]
    assert isinstance(stream, ParticlesObject)
    assert stream.range == (-2.0, 0.5)


def test_omitted_sections_fall_back_to_the_spec_defaults() -> None:
    scene = Scene.model_validate(_WORKED_EXAMPLE)
    assert scene.style.cell == 2
    assert scene.style.depthFade == pytest.approx(0.38)
    assert scene.camera.zoom == pytest.approx(1.0)  # not in the example
    assert scene.playback.interpolate is False


def test_spec_key_names_round_trip_unchanged() -> None:
    scene = Scene.model_validate(
        {
            "objects": [
                {"id": "p", "type": "particles", "track": "t", "maxVoxels": 6},
            ],
            "style": {"depthFade": 0.5},
        }
    )
    assert scene.style.depthFade == pytest.approx(0.5)
    dumped = scene.for_renderer()
    assert dumped["style"]["depthFade"] == pytest.approx(0.5)
    assert dumped["objects"][0]["maxVoxels"] == 6


def test_unknown_object_type_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Scene.model_validate({"objects": [{"id": "x", "type": "blob", "track": "t"}]})
