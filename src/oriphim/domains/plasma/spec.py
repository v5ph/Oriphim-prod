"""The plasma domain's run-spec block: what the core PIC solver needs to run.

Distinct from `PlasmaBlock`, which is the *brief* block. The brief block records
what a paper poses — the governing equations, the regime, the geometry in prose.
This records what to actually run: one normalization, concrete species with
resolved numbers, a concrete driver. The interpretation is done; this is the
setup.

Every physical number here should trace to a field of the approved brief.
`brief_source` carries that pointer where it applies; resolving those paths
against the brief is a later check, not enforced here yet.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

_Vec3 = tuple[float, float, float]


class Normalization(StrEnum):
    """The unit system the solver works in. Sets how the core non-dimensionalizes."""

    SI = "si"
    PLASMA = "plasma"
    """Lengths in c/omega_p, times in 1/omega_p."""
    LASER = "laser"
    """Lengths in 1/k0, times in 1/omega0."""


class DensityProfile(BaseModel):
    """An initial number-density field for a species."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["uniform", "linear_ramp", "step", "gaussian"]
    reference_m3: float
    """Peak or plateau number density in m^-3."""
    params: dict[str, float] = Field(default_factory=dict)
    """Profile shape parameters, e.g. {"ramp_start_m": ..., "sigma_m": ...}."""

    @model_validator(mode="after")
    def _check_density(self) -> Self:
        if self.reference_m3 <= 0:
            raise ValueError("reference_m3 must be positive")
        return self


class Species(BaseModel):
    """One kinetic species: how many, how heavy, how hot, moving how fast."""

    model_config = ConfigDict(extra="forbid")

    name: str
    charge_e: float
    """Charge in units of the elementary charge (electron = -1)."""
    mass_me: float
    """Mass in units of the electron mass (proton ~ 1836)."""
    density: DensityProfile
    temperature_ev: float = 0.0
    drift_velocity_c: _Vec3 = (0.0, 0.0, 0.0)
    """Bulk drift as a fraction of c, per axis."""
    particles_per_cell: int = 64
    brief_source: str | None = None
    """Dotted path to the brief field this species was drawn from."""

    @model_validator(mode="after")
    def _check_species(self) -> Self:
        if self.mass_me <= 0:
            raise ValueError(f"species {self.name!r}: mass_me must be positive")
        if self.temperature_ev < 0:
            raise ValueError(f"species {self.name!r}: temperature_ev is negative")
        if self.particles_per_cell < 1:
            raise ValueError(f"species {self.name!r}: particles_per_cell must be >= 1")
        return self


class LaserDriver(BaseModel):
    """An electromagnetic drive injected at one boundary."""

    model_config = ConfigDict(extra="forbid")

    a0: float
    """Peak normalized vector potential."""
    wavelength_m: float
    polarization: Literal["linear_x", "linear_y", "circular"]
    envelope: Literal["gaussian", "flat_top", "sin2"]
    duration_s: float
    """FWHM for a gaussian envelope; plateau length for flat_top."""
    injection_boundary: str
    """Which grid boundary the wave enters at, e.g. "x_lo"."""
    brief_source: str | None = None

    @model_validator(mode="after")
    def _check_laser(self) -> Self:
        if self.a0 <= 0:
            raise ValueError("a0 must be positive")
        if self.wavelength_m <= 0:
            raise ValueError("wavelength_m must be positive")
        if self.duration_s <= 0:
            raise ValueError("duration_s must be positive")
        return self


class PlasmaSpecBlock(BaseModel):
    """The plasma domain's block of a RunSpec."""

    model_config = ConfigDict(extra="forbid")

    normalization: Normalization
    species: list[Species]
    laser: LaserDriver | None = None
    external_b_tesla: _Vec3 = (0.0, 0.0, 0.0)
    external_e_vm: _Vec3 = (0.0, 0.0, 0.0)

    @model_validator(mode="after")
    def _check_block(self) -> Self:
        if not self.species:
            raise ValueError("a plasma run needs at least one species")
        names = [s.name for s in self.species]
        if len(set(names)) != len(names):
            raise ValueError(f"species names must be unique, got {names}")
        return self
