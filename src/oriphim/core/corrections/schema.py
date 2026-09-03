"""The correction record schema.

This is an export-control requirement, not a policy choice: `Correction` must
be physically incapable of holding a field value. Not "we won't store
values" — no field exists that could. It holds only field path, domain tag,
provenance state, correction category, timestamp, and run id.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from oriphim.core.brief.provenance import Provenance


class CorrectionCategory(StrEnum):
    """Why a field was corrected."""

    WRONG_VALUE = "wrong_value"
    WRONG_ASSUMPTION = "wrong_assumption"
    NOT_APPLICABLE = "not_applicable"
    MISSING = "missing"
    TOO_CONSERVATIVE = "too_conservative"
    NOT_CONSERVATIVE_ENOUGH = "not_conservative_enough"


class Correction(BaseModel):
    """A record that a field was corrected. Never carries the value."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    domain: str
    field_path: str
    """Dotted path to the corrected field, e.g. "block.boundary_conditions.0.type"."""
    original_provenance: Provenance
    category: CorrectionCategory
    timestamp: datetime
    context_tag: str | None = None
    """A short abstracted descriptor, e.g. "bolted_interface" — never a part
    name, dimension, or program name."""
