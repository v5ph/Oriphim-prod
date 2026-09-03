"""The plasma domain.

Registers itself with the core domain registry on import, exactly like the
mechanical domain. There is no plugin-discovery system: a caller (currently
`oriphim.cli`) imports this module directly, and that import is what makes the
domain available.

Only `block_schema` is real in this slice — enough to give the interpretation
step a typed home for what it extracts from a plasma paper. `solve`, `checks`,
`benchmarks`, and `priors` are picked by a run that needs them.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from oriphim.core import domain as domain_registry
from oriphim.core.brief.envelope import Envelope
from oriphim.core.checks.base import Check
from oriphim.domains.plasma.block import PlasmaBlock


class PlasmaDomain:
    """Particle-in-cell and fluid plasma: governing equations, regime, geometry."""

    name = "plasma"

    def block_schema(self) -> type[BaseModel]:
        return PlasmaBlock

    def solve(self, brief: Envelope[Any]) -> Any:
        raise NotImplementedError

    def checks(self) -> list[Check]:
        raise NotImplementedError

    def benchmarks(self) -> list[Any]:
        raise NotImplementedError

    def priors(self) -> str:
        raise NotImplementedError


domain_registry.register(PlasmaDomain())
