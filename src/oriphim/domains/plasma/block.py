"""The plasma domain's brief block.

Minimal by intent. The mechanical block enumerates materials, constraints, and
load cases because those recur in every mechanical run; the plasma block does
not yet know what recurs, because only one plasma paper has been run. It holds
what the interpreter can reliably pull from a paper — the governing equations,
the parameters that set the regime, the dimensionless groups that bound
validity — and grows when a second and third plasma run agree on what is
missing.
"""

from __future__ import annotations

from pydantic import BaseModel

from oriphim.core.brief.provenance import Provenanced


class PlasmaBlock(BaseModel):
    """The plasma domain's block: everything domain-specific about the brief."""

    governing_equations: list[str]
    """Each equation the model is expected to solve, written out."""

    key_parameters: list[Provenanced[str]]
    """Parameters that set the regime — density, temperature, field strength,
    drive intensity — each carrying where it came from."""

    dimensionless_groups: dict[str, float]
    """Named dimensionless numbers and their values where the paper gives or
    implies them, e.g. {"magnetization": ..., "collisionality": ...}."""

    domain_geometry: str
    """The spatial domain and its boundaries, in prose."""

    regime_notes: str
    """Operating regime and the bounds under which the chosen equations hold."""
