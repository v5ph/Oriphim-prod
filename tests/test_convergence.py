from __future__ import annotations

import pytest

from veil.core.checks.convergence import grid_convergence_index

# Published worked example: pressure recovery for a supersonic ramp inlet,
# NPARC Alliance CFD Verification and Validation Web Site, "Examining
# Spatial (Grid) Convergence":
# https://www.grc.nasa.gov/www/wind/valid/tutorial/spatconv.html
#
# Three grids with a constant refinement ratio r=2; normalized grid spacing
# h and pressure-recovery values f:
#   h1=1, f1=0.97050
#   h2=2, f2=0.96854
#   h3=4, f3=0.96178
# Published results: p=1.786170, f_ext=0.97130, GCI21=0.103083%,
# GCI32=0.356249%, asymptotic ratio approx 1 (solutions well within the
# asymptotic range).

_LEVELS = [(1.0, 0.97050), (2.0, 0.96854), (4.0, 0.96178)]


def test_gci_matches_nparc_worked_example() -> None:
    result = grid_convergence_index(_LEVELS)

    assert result.observed_order == pytest.approx(1.786170, rel=1e-4)
    assert result.richardson_extrapolated_value == pytest.approx(0.97130, rel=1e-4)
    assert result.gci_fine == pytest.approx(0.00103083, rel=5e-3)
    assert result.gci_coarse == pytest.approx(0.00356249, rel=5e-3)
    assert result.safety_factor == pytest.approx(1.25)
    assert result.in_asymptotic_range is True


def test_gci_accepts_levels_in_any_order() -> None:
    shuffled = [_LEVELS[2], _LEVELS[0], _LEVELS[1]]
    result = grid_convergence_index(shuffled)
    assert result.observed_order == pytest.approx(1.786170, rel=1e-4)


def test_gci_requires_at_least_three_levels() -> None:
    with pytest.raises(ValueError):
        grid_convergence_index(_LEVELS[:2])


def test_gci_rejects_non_increasing_grid_sizes() -> None:
    with pytest.raises(ValueError):
        grid_convergence_index([(1.0, 1.0), (1.0, 1.0), (2.0, 1.0)])
