"""Sensitivity of the conclusion to each free parameter (tornado).

Stub for this slice. Signature only.
"""

from __future__ import annotations

from typing import Any

from veil.core.checks.base import CheckResult


def sensitivity_check(results: Any, *, parameters: list[str]) -> CheckResult:
    """Perturb each parameter and measure the effect on the conclusion."""
    raise NotImplementedError
