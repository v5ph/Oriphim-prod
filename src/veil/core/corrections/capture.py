"""Capture a correction when a human edits an inferred or defaulted field.

Stub for this slice. Signature only.
"""

from __future__ import annotations

from veil.core.brief.provenance import Provenance
from veil.core.corrections.schema import Correction, CorrectionCategory


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
    raise NotImplementedError
