from __future__ import annotations

import json
from typing import Any

import pytest

import oriphim.domains.plasma  # noqa: F401  (registers the plasma domain)
from oriphim.core.interpret.propose import ProposeError, propose_brief


class _ScriptedClient:
    """Returns queued responses in order; records the prompts it was given."""

    def __init__(self, *responses: str) -> None:
        self._responses = list(responses)
        self.calls: list[tuple[str, str]] = []

    def complete(self, *, system: str, prompt: str) -> str:
        self.calls.append((system, prompt))
        return self._responses.pop(0)


def _prov(value: str, provenance: str = "stated") -> dict[str, Any]:
    return {"value": value, "provenance": provenance, "inference_note": None, "source": None}


def _valid_payload() -> dict[str, Any]:
    return {
        "title": "Warm dense plasma slab",
        "objective": _prov("Reproduce the PIC field-energy history", "inferred"),
        "quantities_of_interest": [_prov("total field energy vs time")],
        "assumptions": [_prov("collisionless", "inferred")],
        "checks_planned": ["energy conservation", "grid convergence"],
        "tier": "verification",
        "block": {
            "governing_equations": ["Vlasov-Maxwell"],
            "key_parameters": [_prov("n_e = 1e20 cm^-3")],
            "dimensionless_groups": {"magnetization": 3.2},
            "domain_geometry": "1D periodic slab",
            "regime_notes": "collisionless, non-relativistic",
        },
    }


def test_propose_builds_a_validated_unapproved_brief() -> None:
    client = _ScriptedClient(json.dumps(_valid_payload()))
    brief = propose_brief("Model a plasma slab", paper_text="...", client=client)

    assert brief.domain == "plasma"
    assert brief.run_id
    assert brief.revision == 1
    assert brief.approved_by is None
    assert brief.block.governing_equations == ["Vlasov-Maxwell"]

    needing, total = brief.review_debt()
    assert needing >= 1
    assert total >= 1


def test_propose_strips_code_fences() -> None:
    client = _ScriptedClient("```json\n" + json.dumps(_valid_payload()) + "\n```")
    brief = propose_brief("x", client=client)
    assert brief.title == "Warm dense plasma slab"


def test_propose_retries_once_then_raises() -> None:
    client = _ScriptedClient("not json", "still not json")
    with pytest.raises(ProposeError):
        propose_brief("x", client=client)
    assert len(client.calls) == 2


def test_propose_recovers_on_second_try() -> None:
    client = _ScriptedClient("garbage", json.dumps(_valid_payload()))
    brief = propose_brief("x", client=client)
    assert brief.title == "Warm dense plasma slab"
    assert len(client.calls) == 2
