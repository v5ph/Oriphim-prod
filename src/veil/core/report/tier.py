"""Report tier: a report is VERIFICATION or VALIDATION, never both, never ambiguous.

Verification asks whether the mathematics was solved correctly. Validation asks
how far the model is from reality. Veil never conflates them.
"""

from __future__ import annotations

from enum import StrEnum

VERIFICATION_LIMIT_STATEMENT = (
    "No reference data was available. This report makes no claim about "
    "agreement with reality."
)


class Tier(StrEnum):
    """Which kind of evidence a report provides."""

    VERIFICATION = "verification"
    VALIDATION = "validation"


def limit_statement(tier: Tier) -> str:
    """The mandatory limit statement accompanying a report of the given tier.

    A VERIFICATION report must never be read as a claim about reality; this
    statement is the guardrail. VALIDATION reports carry no blanket limit
    statement here — their limits are quantified per-comparison, not generic.
    """
    if tier is Tier.VERIFICATION:
        return VERIFICATION_LIMIT_STATEMENT
    return ""
