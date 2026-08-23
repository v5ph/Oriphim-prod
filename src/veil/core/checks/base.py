"""The Check protocol and its result type.

A check inspects results and licenses (or refuses to license) a conclusion.
It never overstates what it actually established.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Protocol

from pydantic import BaseModel

from veil.core.report.tier import Tier


class CheckOutcome(StrEnum):
    """Whether a check passed, failed, or could not be determined."""

    PASS = "pass"
    FAIL = "fail"
    INCONCLUSIVE = "inconclusive"


class CheckResult(BaseModel):
    """The outcome of running one check."""

    outcome: CheckOutcome
    measure: float | None = None
    """A numeric measure of the check, where one exists (e.g. a GCI value)."""
    statement: str
    """Plain language: what this result licenses the user to conclude."""


class Check(Protocol):
    """A single verification or validation check."""

    name: str
    tier: Tier

    def run(self, results: Any) -> CheckResult: ...
