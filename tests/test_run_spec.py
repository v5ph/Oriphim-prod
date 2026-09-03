from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from oriphim.core.execute.spec import (
    BoundaryKind,
    ConvergenceLadder,
    GridSpec,
    RunSpec,
    TimeSpec,
)
from oriphim.domains.plasma.spec import (
    DensityProfile,
    LaserDriver,
    Normalization,
    PlasmaSpecBlock,
    Species,
)


def _plasma_block(**overrides: Any) -> PlasmaSpecBlock:
    defaults: dict[str, Any] = dict(
        normalization=Normalization.LASER,
        species=[
            Species(
                name="electron",
                charge_e=-1.0,
                mass_me=1.0,
                density=DensityProfile(kind="uniform", reference_m3=1e25),
                temperature_ev=50.0,
            ),
        ],
        laser=LaserDriver(
            a0=2.0,
            wavelength_m=8e-7,
            polarization="linear_y",
            envelope="gaussian",
            duration_s=3e-14,
            injection_boundary="x_lo",
        ),
    )
    defaults.update(overrides)
    return PlasmaSpecBlock(**defaults)


def _run_spec(**overrides: Any) -> RunSpec[PlasmaSpecBlock]:
    defaults: dict[str, Any] = dict(
        run_id="run-1",
        brief_revision=2,
        domain="plasma",
        grid=GridSpec(
            cells=[128],
            extent_m=[(0.0, 1e-4)],
            boundaries=[BoundaryKind.PERIODIC],
        ),
        time=TimeSpec(physical_time_s=1e-12, frame_interval_s=1e-14),
        block=_plasma_block(),
    )
    defaults.update(overrides)
    return RunSpec[PlasmaSpecBlock](**defaults)


def test_valid_plasma_run_spec_builds_with_defaults() -> None:
    spec = _run_spec()
    assert spec.uses_escape_hatch() is False
    assert spec.ladder.levels == 3
    assert spec.budget.max_frames == 1200
    assert spec.seed == 0


def test_grid_axis_lengths_must_match() -> None:
    with pytest.raises(ValidationError, match="same length"):
        GridSpec(
            cells=[128, 64],
            extent_m=[(0.0, 1e-4)],
            boundaries=[BoundaryKind.PERIODIC, BoundaryKind.PERIODIC],
        )


def test_grid_extent_must_increase() -> None:
    with pytest.raises(ValidationError, match="not increasing"):
        GridSpec(cells=[8], extent_m=[(1.0, 0.0)], boundaries=[BoundaryKind.OPEN])


def test_frame_interval_cannot_exceed_the_run() -> None:
    with pytest.raises(ValidationError, match="frame_interval_s"):
        TimeSpec(physical_time_s=1e-12, frame_interval_s=1e-11)


def test_dt_override_requires_a_reason() -> None:
    with pytest.raises(ValidationError, match="dt_override_reason"):
        TimeSpec(physical_time_s=1e-12, frame_interval_s=1e-14, dt_override_s=1e-16)

    ok = TimeSpec(
        physical_time_s=1e-12,
        frame_interval_s=1e-14,
        dt_override_s=1e-16,
        dt_override_reason="paper fixes dt to resolve the laser period",
    )
    assert ok.dt_override_s == 1e-16


def test_convergence_ladder_rejects_fewer_than_three_levels() -> None:
    with pytest.raises(ValidationError, match="GCI study"):
        ConvergenceLadder(levels=2)


def test_run_spec_rejects_unknown_keys() -> None:
    # The anti-wrapper guarantee: the LLM cannot smuggle in a field the core
    # does not support.
    body = _run_spec().model_dump()
    body["custom_integrator"] = "rk45"
    with pytest.raises(ValidationError):
        RunSpec[PlasmaSpecBlock].model_validate(body)


def test_plasma_block_needs_at_least_one_species() -> None:
    with pytest.raises(ValidationError, match="at least one species"):
        _plasma_block(species=[])


def test_plasma_species_names_must_be_unique() -> None:
    dupe = Species(
        name="electron",
        charge_e=-1.0,
        mass_me=1.0,
        density=DensityProfile(kind="uniform", reference_m3=1e25),
    )
    with pytest.raises(ValidationError, match="unique"):
        _plasma_block(species=[dupe, dupe])


def test_glue_marks_the_escape_hatch() -> None:
    spec = _run_spec(
        glue={
            "justification": "needs a custom current-smoothing pass the schema can't state",
            "entrypoint": "run_glue:build",
            "source": "def build(core):\n    return core.pic_loop()\n",
        }
    )
    assert spec.uses_escape_hatch() is True
    assert spec.glue is not None
    assert spec.glue.reviewed_by is None


def test_glue_entrypoint_must_be_module_and_function() -> None:
    with pytest.raises(ValidationError, match="module:function"):
        _run_spec(
            glue={
                "justification": "x",
                "entrypoint": "no_colon_here",
                "source": "def f(): pass",
            }
        )
