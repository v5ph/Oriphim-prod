"""The mechanical domain.

Registers itself with the core domain registry on import. There is no
plugin-discovery system: a caller (currently `oriphim.cli`) imports this module
directly, and that import is what makes the domain available.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from oriphim.core import domain as domain_registry
from oriphim.core.brief.envelope import Envelope
from oriphim.core.checks.base import Check
from oriphim.domains.mechanical import checks as checks_module
from oriphim.domains.mechanical import priors as priors_module
from oriphim.domains.mechanical import solver as solver_module
from oriphim.domains.mechanical.block import MechanicalBlock


class MechanicalDomain:
    """Materials, boundary conditions, load cases, mesh sizes."""

    name = "mechanical"

    def block_schema(self) -> type[BaseModel]:
        return MechanicalBlock

    def spec_schema(self) -> type[BaseModel]:
        raise NotImplementedError  # picked when a mechanical run needs a RunSpec

    def solve(self, brief: Envelope[Any]) -> Any:
        return solver_module.solve(brief)

    def checks(self) -> list[Check]:
        return checks_module.checks()

    def benchmarks(self) -> list[Any]:
        raise NotImplementedError

    def priors(self) -> str:
        return priors_module.priors()


domain_registry.register(MechanicalDomain())
