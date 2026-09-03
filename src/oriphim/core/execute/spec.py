"""RunSpec — the declarative contract between LLM-written glue and the verified core.

After a brief is approved, the LLM does not write solver code. It fills this
schema: a bounded, validated description of *this run* — grid, duration,
diagnostics, and a domain-specific block (species, driver, ...). Oriphim's
verified core reads the spec and does the numerics. An integrator bug cannot
originate here, because the LLM never writes an integrator — only states what to
integrate and over what.

Symmetry with the brief. `Envelope[BlockT]` carries the *interpretation* of a
paper; `RunSpec[SpecBlockT]` carries the *setup* of the run that follows. Both
are typed, both pair a domain-general shell with a domain block, both are
cross-checked against their neighbour (`Envelope.require_approved`; `bind.py`).

`extra="forbid"` on every model here is load-bearing, not tidiness: the spec's
surface is exactly what the core supports. A key the core does not recognise is
a validation error, not a silently honoured instruction.

The escape hatch (`RunSpec.glue`) is the minority path — when a run genuinely
needs something the schema cannot express, the LLM writes bounded code against
the core API. It is flagged for human review (`bind.py` refuses unreviewed glue)
and runs sandboxed. On the main path `glue` is `None`.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Generic, Literal, Self, TypeVar

from pydantic import BaseModel, ConfigDict, Field, model_validator

SpecBlockT = TypeVar("SpecBlockT", bound=BaseModel)

_MIN_LADDER_LEVELS = 3
"""A Grid Convergence Index study needs at least three levels — see
`oriphim.core.checks.convergence`."""


class BoundaryKind(StrEnum):
    """What happens at a domain edge. The domain gives each kind its physics."""

    PERIODIC = "periodic"
    REFLECTING = "reflecting"
    ABSORBING = "absorbing"
    OPEN = "open"


class GridSpec(BaseModel):
    """The spatial discretization the core starts its refinement ladder from."""

    model_config = ConfigDict(extra="forbid")

    cells: list[int]
    """Cell count per active axis. Length 1-3 sets the dimensionality."""
    extent_m: list[tuple[float, float]]
    """(low, high) physical bound in metres per axis, parallel to `cells`."""
    boundaries: list[BoundaryKind]
    """Boundary kind per axis, parallel to `cells`."""

    @model_validator(mode="after")
    def _check_axes(self) -> Self:
        n = len(self.cells)
        if not 1 <= n <= 3:
            raise ValueError(f"grid has {n} axes; 1 to 3 supported")
        if len(self.extent_m) != n or len(self.boundaries) != n:
            raise ValueError("cells, extent_m and boundaries must have the same length")
        for i, count in enumerate(self.cells):
            if count < 1:
                raise ValueError(f"axis {i} has {count} cells; need at least 1")
        for i, (lo, hi) in enumerate(self.extent_m):
            if not hi > lo:
                raise ValueError(f"axis {i} extent {(lo, hi)} is not increasing")
        return self


class TimeSpec(BaseModel):
    """How long to run and how often to emit a frame.

    The timestep is the core's to choose — it comes from a stability criterion
    (CFL), not from the model. An override is allowed but must say why, so a
    reviewer sees that the automatic choice was set aside.
    """

    model_config = ConfigDict(extra="forbid")

    physical_time_s: float
    frame_interval_s: float
    dt_override_s: float | None = None
    dt_override_reason: str | None = None

    @model_validator(mode="after")
    def _check_times(self) -> Self:
        if self.physical_time_s <= 0:
            raise ValueError("physical_time_s must be positive")
        if not 0 < self.frame_interval_s <= self.physical_time_s:
            raise ValueError("frame_interval_s must be in (0, physical_time_s]")
        if self.dt_override_s is not None:
            if self.dt_override_s <= 0:
                raise ValueError("dt_override_s must be positive")
            if not (self.dt_override_reason or "").strip():
                raise ValueError("dt_override_s requires dt_override_reason")
        return self


class ConvergenceLadder(BaseModel):
    """The refinement ladder for the convergence check.

    Proposed by the model, owned by the core — the core may widen it. Present in
    the spec so the plan is visible before anything runs.
    """

    model_config = ConfigDict(extra="forbid")

    levels: int = _MIN_LADDER_LEVELS
    ratio: float = 2.0
    refine: Literal["space", "time", "both"] = "both"

    @model_validator(mode="after")
    def _check_ladder(self) -> Self:
        if self.levels < _MIN_LADDER_LEVELS:
            raise ValueError(f"levels must be >= {_MIN_LADDER_LEVELS} for a GCI study")
        if self.ratio <= 1:
            raise ValueError("ratio must be > 1")
        return self


class Diagnostics(BaseModel):
    """What the run records — into DATA and into the check inputs.

    `fields` and `reductions` name quantities in the domain's own vocabulary;
    the domain solver rejects names it does not produce. `particle_tracks` maps
    a species to how many macroparticles to keep for the render (0 = none).
    """

    model_config = ConfigDict(extra="forbid")

    fields: list[str] = Field(default_factory=list)
    reductions: list[str] = Field(default_factory=list)
    spatial_stride: int = 1
    particle_tracks: dict[str, int] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check_diagnostics(self) -> Self:
        if self.spatial_stride < 1:
            raise ValueError("spatial_stride must be >= 1")
        for name, count in self.particle_tracks.items():
            if count < 0:
                raise ValueError(f"particle_tracks[{name!r}] is negative")
        return self


class Budget(BaseModel):
    """Hard caps the sandbox enforces. The core stops rather than exceed them."""

    model_config = ConfigDict(extra="forbid")

    max_wall_time_s: float = 300.0
    max_memory_mb: int = 2048
    max_frames: int = 1200

    @model_validator(mode="after")
    def _check_budget(self) -> Self:
        if self.max_wall_time_s <= 0 or self.max_memory_mb <= 0 or self.max_frames <= 0:
            raise ValueError("every budget cap must be positive")
        return self


class Glue(BaseModel):
    """The escape hatch: model-written code for a run the schema cannot express.

    Not the main path. `bind.py` refuses to run glue with no `reviewed_by`, so a
    human name is attached to every line of model-written numerics before it
    executes — and it executes sandboxed like any solver.
    """

    model_config = ConfigDict(extra="forbid")

    justification: str
    """Why the declarative spec was insufficient — written for the reviewer."""
    entrypoint: str
    """`module:function`, resolved against the core API inside the sandbox."""
    source: str
    """The glue module's text. Untrusted; never imported into this process."""
    reviewed_by: str | None = None

    @model_validator(mode="after")
    def _check_glue(self) -> Self:
        if not self.justification.strip():
            raise ValueError("glue requires a justification")
        if not self.source.strip():
            raise ValueError("glue requires source")
        if ":" not in self.entrypoint:
            raise ValueError("entrypoint must look like 'module:function'")
        return self


class RunSpec(BaseModel, Generic[SpecBlockT]):
    """The full setup for one run: a domain-general shell plus a domain block."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    """Identical to the approved brief's `run_id`."""
    brief_revision: int
    """The brief revision this spec was built from. `bind.py` checks it still matches."""
    domain: str

    grid: GridSpec
    time: TimeSpec
    ladder: ConvergenceLadder = Field(default_factory=ConvergenceLadder)
    diagnostics: Diagnostics = Field(default_factory=Diagnostics)
    budget: Budget = Field(default_factory=Budget)
    seed: int = 0
    """Every stochastic draw derives from this. Run twice, get the same DATA."""

    glue: Glue | None = None
    block: SpecBlockT
    notes: str = ""

    def uses_escape_hatch(self) -> bool:
        """True when this run carries model-written glue code."""
        return self.glue is not None
