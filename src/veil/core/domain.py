"""The Domain protocol and its registry.

Domains depend on core; core never depends on a domain. Adding a new domain
must require zero edits inside core/ — a domain module registers itself on
import.
"""

from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel

from veil.core.brief.envelope import Envelope
from veil.core.checks.base import Check


class Benchmark(Protocol):
    """A known-answer system a domain can be checked against.

    # TODO(veil): the shape of a benchmark (inputs, expected result, and how
    # comparison/tolerance is judged) isn't specified yet. Keeping this
    # minimal until a domain actually needs it.
    """

    name: str


class Domain(Protocol):
    """A physical domain: mechanical, thermal, fluid, and so on."""

    name: str

    def block_schema(self) -> type[BaseModel]:
        """The Pydantic model type for this domain's brief block."""
        ...

    def solve(self, brief: Envelope[Any]) -> Any:
        """Run the domain's solver against an approved brief."""
        ...

    def checks(self) -> list[Check]:
        """The checks this domain can run against its own results."""
        ...

    def benchmarks(self) -> list[Benchmark]:
        """Known-answer systems this domain can be validated against."""
        ...

    def priors(self) -> str:
        """A short statement of this domain's governing assumptions."""
        ...


_registry: dict[str, Domain] = {}


def register(domain: Domain) -> None:
    """Register a domain by name. A later registration under the same name replaces it."""
    _registry[domain.name] = domain


def get(name: str) -> Domain:
    """Look up a registered domain by name."""
    try:
        return _registry[name]
    except KeyError:
        raise KeyError(f"No domain registered under {name!r}.") from None
