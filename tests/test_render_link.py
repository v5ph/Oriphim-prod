from __future__ import annotations

import pytest

from oriphim.core.render.data import RenderData
from oriphim.core.render.link import SceneDataMismatch, validate_scene_against_data
from oriphim.core.render.scene import Scene


def _data() -> RenderData:
    return RenderData.model_validate(
        {
            "frames": 1,
            "tracks": {
                "cloud": {
                    "kind": "points",
                    "positions": [[0.0, 0.0, 0.0]],
                    "scalars": {"temp": [[300.0]]},
                },
                "body": {"kind": "rigid", "positions": [[0.0, 0.0, 0.0]]},
            },
        }
    )


def _scene(obj: dict) -> Scene:
    return Scene.model_validate({"objects": [obj]})


def test_matching_scene_and_data_pass() -> None:
    scene = _scene({"id": "c", "type": "particles", "track": "cloud", "scalar": "temp"})
    validate_scene_against_data(scene, _data())  # no raise


def test_object_pointing_at_a_missing_track_raises() -> None:
    scene = _scene({"id": "c", "type": "particles", "track": "ghost"})
    with pytest.raises(SceneDataMismatch, match="ghost"):
        validate_scene_against_data(scene, _data())


def test_object_pointing_at_the_wrong_track_kind_raises() -> None:
    scene = _scene({"id": "s", "type": "shell", "track": "cloud", "radius": 0.1})
    with pytest.raises(SceneDataMismatch, match="rigid"):
        validate_scene_against_data(scene, _data())


def test_particles_asking_for_a_missing_scalar_raises() -> None:
    scene = _scene({"id": "c", "type": "particles", "track": "cloud", "scalar": "pressure"})
    with pytest.raises(SceneDataMismatch, match="pressure"):
        validate_scene_against_data(scene, _data())
