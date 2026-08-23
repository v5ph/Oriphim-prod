from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import BaseModel

from veil.core.brief.envelope import Envelope
from veil.core.brief.provenance import Provenance, Provenanced
from veil.core.report.tier import Tier


class _EmptyBlock(BaseModel):
    pass


def _make_envelope(**overrides: Any) -> Envelope[_EmptyBlock]:
    defaults: dict[str, Any] = dict(
        run_id="run-1",
        title="Bracket under static load",
        revision=1,
        created_at=datetime.now(UTC),
        objective=Provenanced[str](value="Check yield margin", provenance=Provenance.STATED),
        quantities_of_interest=[
            Provenanced[str](value="max von Mises stress", provenance=Provenance.STATED),
        ],
        assumptions=[
            Provenanced[str](value="Linear elastic", provenance=Provenance.INFERRED),
            Provenanced[str](value="Room temperature", provenance=Provenance.DEFAULTED),
        ],
        checks_planned=["convergence"],
        tier=Tier.VERIFICATION,
        domain="mechanical",
        block=_EmptyBlock(),
    )
    defaults.update(overrides)
    return Envelope[_EmptyBlock](**defaults)


def test_review_debt_counts_only_inferred_fields() -> None:
    envelope = _make_envelope()
    needing_review, total = envelope.review_debt()
    # objective (stated) + 1 QoI (stated) + 2 assumptions (1 inferred, 1 defaulted) = 4 total
    assert total == 4
    assert needing_review == 1


def test_review_debt_is_zero_when_everything_is_stated() -> None:
    envelope = _make_envelope(
        assumptions=[
            Provenanced[str](value="Linear elastic", provenance=Provenance.STATED),
        ],
    )
    needing_review, total = envelope.review_debt()
    assert needing_review == 0
    assert total == 3


def test_unapproved_brief_cannot_execute() -> None:
    envelope = _make_envelope(approved_by=None)
    with pytest.raises(ValueError):
        envelope.require_approved()


def test_approved_brief_executes() -> None:
    envelope = _make_envelope(approved_by="j.reviewer", approved_at=datetime.now(UTC))
    envelope.require_approved()  # must not raise
