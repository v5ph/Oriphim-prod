from __future__ import annotations

import pytest
from pydantic import ValidationError

from oriphim.core.brief.provenance import Provenance
from oriphim.core.corrections.schema import Correction, CorrectionCategory

# The exact, closed set of fields a Correction is allowed to carry. No field
# here can hold the proposed or accepted value of the thing being corrected.
_ALLOWED_FIELDS = {
    "run_id",
    "domain",
    "field_path",
    "original_provenance",
    "category",
    "timestamp",
    "context_tag",
}


def test_correction_has_no_field_capable_of_holding_a_value() -> None:
    assert set(Correction.model_fields) == _ALLOWED_FIELDS


def test_correction_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        Correction(
            run_id="run-1",
            domain="mechanical",
            field_path="block.boundary_conditions.0.type",
            original_provenance=Provenance.INFERRED,
            category=CorrectionCategory.WRONG_ASSUMPTION,
            timestamp="2026-08-23T00:00:00Z",
            value=1e9,  # type: ignore[call-arg]
        )


def test_correction_category_values() -> None:
    assert {c.value for c in CorrectionCategory} == {
        "wrong_value",
        "wrong_assumption",
        "not_applicable",
        "missing",
        "too_conservative",
        "not_conservative_enough",
    }
