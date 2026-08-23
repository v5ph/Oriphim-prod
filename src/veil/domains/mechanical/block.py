"""The mechanical domain's brief block.

A minimal, domain-specific spec: material, boundary conditions, load cases,
and mesh sizes. This is the `block` slot in a run brief's Envelope.
"""

from __future__ import annotations

from pydantic import BaseModel


class Material(BaseModel):
    """A linear-elastic material definition."""

    name: str
    youngs_modulus_pa: float
    poissons_ratio: float
    density_kg_m3: float


class BoundaryCondition(BaseModel):
    """A constraint applied at some location on the structure."""

    name: str
    type: str
    """e.g. "fixed", "pinned", "roller"."""
    location: str
    """A description of where this constraint applies."""


class LoadCase(BaseModel):
    """One applied load scenario."""

    name: str
    description: str
    magnitude_n: float | None = None


class MeshSize(BaseModel):
    """A target discretization size for one region or the whole model."""

    target_element_size_m: float
    region: str | None = None


class MechanicalBlock(BaseModel):
    """The mechanical domain's block: everything domain-specific about the brief."""

    material: Material
    boundary_conditions: list[BoundaryCondition]
    load_cases: list[LoadCase]
    mesh_sizes: list[MeshSize]
