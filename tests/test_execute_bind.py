from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import BaseModel

from oriphim.core.brief.envelope import Envelope
from oriphim.core.brief.provenance import Provenance, Provenanced
from oriphim.core.execute.bind import SpecBriefMismatch, bind_spec_to_brief
from oriphim.core.execute.spec import BoundaryKind, Glue, GridSpec, RunSpec, TimeSpec
from oriphim.core.report.tier import Tier


class _Block(BaseModel):
    pass


def _brief(**overrides: Any) -> Envelope[_Block]:
    defaults: dict[str, Any] = dict(
        run_id="run-1",
        title="Laser-plasma slab",
        revision=2,
        created_at=datetime.now(UTC),
        objective=Provenanced[str](value="Reproduce E1/E2 growth", provenance=Provenance.STATED),
        quantities_of_interest=[
            Provenanced[str](value="field energy", provenance=Provenance.STATED),
        ],
        assumptions=[],
        checks_planned=["convergence"],
        tier=Tier.VERIFICATION,
        domain="plasma",
        block=_Block(),
        approved_by="Dr Vega",
        approved_at=datetime.now(UTC),
    )
    defaults.update(overrides)
    return Envelope[_Block](**defaults)


def _spec(**overrides: Any) -> RunSpec[_Block]:
    defaults: dict[str, Any] = dict(
        run_id="run-1",
        brief_revision=2,
        domain="plasma",
        grid=GridSpec(cells=[64], extent_m=[(0.0, 1e-4)], boundaries=[BoundaryKind.PERIODIC]),
        time=TimeSpec(physical_time_s=1e-12, frame_interval_s=1e-14),
        block=_Block(),
    )
    defaults.update(overrides)
    return RunSpec[_Block](**defaults)


def test_bind_passes_for_a_matching_approved_brief() -> None:
    bind_spec_to_brief(_spec(), _brief())  # must not raise


def test_bind_rejects_an_unapproved_brief() -> None:
    with pytest.raises(SpecBriefMismatch, match="not approved"):
        bind_spec_to_brief(_spec(), _brief(approved_by=None))


def test_bind_rejects_a_run_id_mismatch() -> None:
    with pytest.raises(SpecBriefMismatch, match="run_id"):
        bind_spec_to_brief(_spec(run_id="other"), _brief())


def test_bind_rejects_a_domain_mismatch() -> None:
    with pytest.raises(SpecBriefMismatch, match="domain"):
        bind_spec_to_brief(_spec(domain="mechanical"), _brief())


def test_bind_rejects_a_stale_brief_revision() -> None:
    with pytest.raises(SpecBriefMismatch, match="revision"):
        bind_spec_to_brief(_spec(brief_revision=1), _brief(revision=2))


def test_bind_rejects_unreviewed_escape_hatch_glue() -> None:
    glue = Glue(
        justification="a coupling the schema can't state",
        entrypoint="run_glue:build",
        source="def build(core): return core.pic_loop()",
    )
    with pytest.raises(SpecBriefMismatch, match="reviewer"):
        bind_spec_to_brief(_spec(glue=glue), _brief())


def test_bind_accepts_reviewed_escape_hatch_glue() -> None:
    glue = Glue(
        justification="a coupling the schema can't state",
        entrypoint="run_glue:build",
        source="def build(core): return core.pic_loop()",
        reviewed_by="Dr Vega",
    )
    bind_spec_to_brief(_spec(glue=glue), _brief())  # must not raise
