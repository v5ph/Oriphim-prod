"""Capture a correction when a human edits an inferred or defaulted field.

The record carries no value — it cannot, by the schema's construction. It says
only *that* a field was corrected, from which provenance, and why.
"""

from __future__ import annotations

from datetime import UTC, datetime

from oriphim.core.brief.provenance import Provenance
from oriphim.core.corrections.schema import Correction, CorrectionCategory


def capture_correction(
    *,
    run_id: str,
    domain: str,
    field_path: str,
    original_provenance: Provenance,
    category: CorrectionCategory,
    context_tag: str | None = None,
) -> Correction:
    """Record that a field was corrected, without recording its value."""
    return Correction(
        run_id=run_id,
        domain=domain,
        field_path=field_path,
        original_provenance=original_provenance,
        category=category,
        timestamp=datetime.now(UTC),
        context_tag=context_tag,
    )
