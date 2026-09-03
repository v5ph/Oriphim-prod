from __future__ import annotations

import pytest

from oriphim.core.render.data import RenderData
from oriphim.core.render.scene import Scene
from oriphim.core.render.stamp import stamp


def _data() -> RenderData:
    return RenderData.model_validate(
        {
            "meta": {"run_id": "STAMP-1"},
            "frames": 1,
            "tracks": {
                "pts": {
                    "kind": "points",
                    "positions": [[2.0, 0.0, 0.0, 0.0, 0.0, 0.0]],  # farthest point at 2.0
                    "scalars": {"e": [[1.0, 3.0]]},
                }
            },
        }
    )


def _scene(*, fit: str, with_range: bool) -> Scene:
    obj: dict = {"id": "p", "type": "particles", "track": "pts", "scalar": "e"}
    if with_range:
        obj["range"] = [0.0, 10.0]
    return Scene.model_validate({"world": {"scale": 1.0, "fit": fit}, "objects": [obj]})


def test_hashes_are_deterministic_and_sha256_shaped() -> None:
    scene, data = _scene(fit="none", with_range=False), _data()
    a, b = stamp(scene, data), stamp(scene, data)
    assert a.scene_sha256 == b.scene_sha256
    assert a.data_sha256 == b.data_sha256
    assert len(a.scene_sha256) == 64 and all(c in "0123456789abcdef" for c in a.scene_sha256)


def test_fit_once_resolves_a_scale_from_the_data() -> None:
    s = stamp(_scene(fit="once", with_range=False), _data())
    assert s.world_fit == "once"
    assert s.world_scale == pytest.approx(0.5)  # 1 / farthest (2.0)


def test_fit_none_keeps_the_stated_scale() -> None:
    s = stamp(_scene(fit="none", with_range=False), _data())
    assert s.world_scale == pytest.approx(1.0)


def test_explicit_range_is_marked_stated() -> None:
    s = stamp(_scene(fit="none", with_range=True), _data())
    rng = s.scalar_ranges["pts::e"]
    assert rng.stated is True
    assert (rng.min, rng.max) == pytest.approx((0.0, 10.0))


def test_omitted_range_is_computed_and_marked_unstated() -> None:
    s = stamp(_scene(fit="none", with_range=False), _data())
    rng = s.scalar_ranges["pts::e"]
    assert rng.stated is False
    assert (rng.min, rng.max) == pytest.approx((1.0, 3.0))


def test_run_id_comes_from_data_meta() -> None:
    assert stamp(_scene(fit="none", with_range=False), _data()).run_id == "STAMP-1"
