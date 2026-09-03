from __future__ import annotations

import pytest
from pydantic import ValidationError

from oriphim.core.render.data import RenderData


def _two_frames() -> dict:
    return {
        "meta": {"run_id": "T-1"},
        "frames": 2,
        "tracks": {
            "pts": {
                "kind": "points",
                "positions": [[0.0, 0.0, 0.0, 1.0, 1.0, 1.0], [0.1, 0.0, 0.0, 1.1, 1.0, 1.0]],
                "scalars": {"e": [[0.0, 1.0], [0.5, 1.5]]},
            }
        },
    }


def test_valid_data_parses() -> None:
    data = RenderData.model_validate(_two_frames())
    assert data.frames == 2
    assert data.tracks["pts"].kind == "points"


def test_declared_frame_count_must_match_track_length() -> None:
    bad = _two_frames()
    bad["frames"] = 3
    with pytest.raises(ValidationError):
        RenderData.model_validate(bad)


def test_element_count_must_be_constant_across_frames() -> None:
    bad = _two_frames()
    bad["tracks"]["pts"]["positions"][1] = [0.1, 0.0, 0.0]  # 1 element, was 2
    with pytest.raises(ValidationError):
        RenderData.model_validate(bad)


def test_frame_length_must_be_a_multiple_of_three() -> None:
    bad = _two_frames()
    bad["tracks"]["pts"]["positions"] = [[0.0, 0.0], [0.0, 0.0]]
    bad["tracks"]["pts"]["scalars"] = {}
    with pytest.raises(ValidationError):
        RenderData.model_validate(bad)


def test_scalar_series_must_be_parallel_to_positions() -> None:
    bad = _two_frames()
    bad["tracks"]["pts"]["scalars"]["e"] = [[0.0, 1.0]]  # 1 frame, positions has 2
    with pytest.raises(ValidationError):
        RenderData.model_validate(bad)


def test_scalar_element_count_must_match_positions() -> None:
    bad = _two_frames()
    bad["tracks"]["pts"]["scalars"]["e"] = [[0.0], [0.5]]  # 1 value, expected 2
    with pytest.raises(ValidationError):
        RenderData.model_validate(bad)
