"""Grid Convergence Index (Roache).

Implements the three-grid GCI procedure (Roache, 1994; formalized by Celik
et al., 2008, "Procedure for Estimation and Reporting of Uncertainty Due to
Discretization in CFD Applications", ASME J. Fluids Eng.). Works on plain
numbers — no solver, no domain, no model involved.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from pydantic import BaseModel

DEFAULT_SAFETY_FACTOR = 1.25
"""Recommended by Roache for studies with three or more grids."""


class GCIResult(BaseModel):
    """Structured result of a Grid Convergence Index study."""

    observed_order: float
    """The apparent order of convergence, p."""
    richardson_extrapolated_value: float
    """The Richardson-extrapolated estimate of the grid-independent value."""
    gci_fine: float
    """GCI between the two finest grids used, as a fraction (not a percentage)."""
    gci_coarse: float
    """GCI between the two coarsest of the three grids used, as a fraction."""
    asymptotic_ratio: float
    """gci_coarse / (r21^p * gci_fine); close to 1 when in the asymptotic range."""
    in_asymptotic_range: bool
    safety_factor: float


def grid_convergence_index(
    levels: Sequence[tuple[float, float]],
    *,
    safety_factor: float = DEFAULT_SAFETY_FACTOR,
) -> GCIResult:
    """Compute the Grid Convergence Index from three or more refinement levels.

    Args:
        levels: (representative grid size, quantity of interest) pairs, three
            or more. Grid size follows the usual convention: larger is
            coarser. Order is not significant; the three most-refined levels
            are used for the classic three-grid procedure.
        safety_factor: Defaults to 1.25, per Roache's recommendation for
            three-or-more-grid studies.

    Returns:
        A GCIResult with the observed order of convergence, the
        Richardson-extrapolated value, GCI for each of the two finest grid
        pairs, and whether the solutions are in the asymptotic range.
    """
    if len(levels) < 3:
        raise ValueError("Grid Convergence Index requires at least three refinement levels.")

    ordered = sorted(levels, key=lambda level: level[0])
    (h1, f1), (h2, f2), (h3, f3) = ordered[0], ordered[1], ordered[2]

    r21 = h2 / h1
    r32 = h3 / h2
    if r21 <= 1 or r32 <= 1:
        raise ValueError("Grid sizes must be strictly increasing from finest to coarsest.")

    eps21 = f2 - f1
    eps32 = f3 - f2
    if eps21 == 0 or eps32 == 0:
        raise ValueError(
            "No change in the quantity of interest between two grids; "
            "order of convergence is undefined."
        )

    p = _apparent_order(r21, r32, eps21, eps32)

    r21_p = r21**p
    r32_p = r32**p

    f_ext = (r21_p * f1 - f2) / (r21_p - 1)

    e_a21 = abs((f1 - f2) / f1)
    gci_fine = safety_factor * e_a21 / (r21_p - 1)

    e_a32 = abs((f2 - f3) / f2)
    gci_coarse = safety_factor * e_a32 / (r32_p - 1)

    asymptotic_ratio = gci_coarse / (r21_p * gci_fine)
    in_asymptotic_range = math.isclose(asymptotic_ratio, 1.0, rel_tol=0.1)

    return GCIResult(
        observed_order=p,
        richardson_extrapolated_value=f_ext,
        gci_fine=gci_fine,
        gci_coarse=gci_coarse,
        asymptotic_ratio=asymptotic_ratio,
        in_asymptotic_range=in_asymptotic_range,
        safety_factor=safety_factor,
    )


def _apparent_order(
    r21: float,
    r32: float,
    eps21: float,
    eps32: float,
    *,
    max_iter: int = 100,
    tol: float = 1e-12,
) -> float:
    """Solve for the apparent order of convergence p (Celik et al., 2008).

    p = (1 / ln r21) * | ln|eps32/eps21| + q |
    q = ln( (r21^p - s) / (r32^p - s) )
    s = sign(eps32 / eps21)

    q depends on p, so this is solved by fixed-point iteration starting from
    q = 0. When r21 == r32 (constant refinement ratio), q is identically
    zero and the loop converges on its first pass.
    """
    s = 1.0 if (eps32 / eps21) > 0 else -1.0
    ln_ratio = math.log(abs(eps32 / eps21))
    ln_r21 = math.log(r21)

    p = abs(ln_ratio) / ln_r21
    for _ in range(max_iter):
        numerator = r21**p - s
        denominator = r32**p - s
        if denominator == 0 or numerator / denominator <= 0:
            break
        q = math.log(numerator / denominator)
        p_new = abs(ln_ratio + q) / ln_r21
        if abs(p_new - p) < tol:
            p = p_new
            break
        p = p_new
    return p
