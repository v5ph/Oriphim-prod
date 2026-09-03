"""Bind a RunSpec to the approved brief it was built from.

Pydantic validates a RunSpec in isolation. Only against the brief can you check
that the spec is *for this run*, was built from an *approved* brief at its
*current* revision, targets the same domain — and that any escape-hatch glue has
a reviewer's name on it. Mirrors `oriphim.core.render.link` for the SCENE/DATA
pair.
"""

from __future__ import annotations

from typing import Any

from oriphim.core.brief.envelope import Envelope
from oriphim.core.execute.spec import RunSpec


class SpecBriefMismatch(ValueError):
    """A RunSpec does not correspond to the brief it is being run against."""


def bind_spec_to_brief(spec: RunSpec[Any], brief: Envelope[Any]) -> None:
    """Raise `SpecBriefMismatch` if `spec` may not be run against `brief`."""
    if brief.approved_by is None:
        raise SpecBriefMismatch(
            f"brief {brief.run_id!r} is not approved; no run spec may be built from it"
        )
    if spec.run_id != brief.run_id:
        raise SpecBriefMismatch(
            f"spec run_id {spec.run_id!r} != brief run_id {brief.run_id!r}"
        )
    if spec.domain != brief.domain:
        raise SpecBriefMismatch(
            f"spec domain {spec.domain!r} != brief domain {brief.domain!r}"
        )
    if spec.brief_revision != brief.revision:
        raise SpecBriefMismatch(
            f"spec was built from brief revision {spec.brief_revision}, "
            f"brief is now at revision {brief.revision} — rebuild the spec"
        )
    if spec.glue is not None and spec.glue.reviewed_by is None:
        raise SpecBriefMismatch(
            "escape-hatch glue has no reviewer; a human must review it before it runs"
        )
