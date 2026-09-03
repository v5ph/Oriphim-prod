"""The run brief envelope: domain-general fields every brief carries.

The envelope is the product. It is reviewed and corrected by a human before
anything runs; `require_approved` is the gate that enforces that.
"""

from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel

from oriphim.core.brief.provenance import Provenance, Provenanced
from oriphim.core.report.tier import Tier

BlockT = TypeVar("BlockT", bound=BaseModel)


class Envelope(BaseModel, Generic[BlockT]):
    """A run brief: domain-general fields plus a domain-specific block."""

    run_id: str
    title: str
    revision: int
    created_at: datetime

    objective: Provenanced[str]
    quantities_of_interest: list[Provenanced[str]]
    assumptions: list[Provenanced[str]]
    checks_planned: list[str]

    tier: Tier
    domain: str
    block: BlockT

    approved_by: str | None = None
    approved_at: datetime | None = None

    def review_debt(self) -> tuple[int, int]:
        """Count of (fields needing review, total provenanced fields).

        A field "needs review" when its provenance is INFERRED.
        """
        provenanced_fields: list[Provenanced] = [
            self.objective,
            *self.quantities_of_interest,
            *self.assumptions,
        ]
        needing_review = sum(
            1 for field in provenanced_fields if field.provenance is Provenance.INFERRED
        )
        return needing_review, len(provenanced_fields)

    def require_approved(self) -> None:
        """Raise if this brief is executed before a human has approved it."""
        if self.approved_by is None:
            raise ValueError(
                f"Brief {self.run_id!r} has not been approved; it cannot be executed."
            )
