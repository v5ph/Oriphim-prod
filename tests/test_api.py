from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from oriphim import api
from oriphim.core.brief.envelope import Envelope
from oriphim.core.interpret.propose import ProposeError
from oriphim.domains.plasma.block import PlasmaBlock

client = TestClient(api.app)

_MODEL_ENV = ("ORIPHIM_API_BASE", "ORIPHIM_API_KEY", "ORIPHIM_MODEL")


def _prov(value: str, provenance: str = "stated") -> dict[str, Any]:
    return {"value": value, "provenance": provenance, "inference_note": None, "source": None}


def _brief() -> Envelope[PlasmaBlock]:
    """A schema-valid draft: objective + one assumption inferred, of three provenanced fields."""
    return Envelope[PlasmaBlock].model_validate(
        {
            "run_id": "run-test-1",
            "title": "Warm dense plasma slab",
            "revision": 1,
            "created_at": datetime.now(UTC),
            "objective": _prov("Reproduce the PIC field-energy history", "inferred"),
            "quantities_of_interest": [_prov("total field energy vs time")],
            "assumptions": [_prov("collisionless", "inferred")],
            "checks_planned": ["energy conservation"],
            "tier": "verification",
            "domain": "plasma",
            "block": {
                "governing_equations": ["Vlasov-Maxwell"],
                "key_parameters": [_prov("n_e = 1e20 cm^-3")],
                "dimensionless_groups": {"magnetization": 3.2},
                "domain_geometry": "1D periodic slab",
                "regime_notes": "collisionless, non-relativistic",
            },
            "approved_by": None,
            "approved_at": None,
        }
    )


def _patch_propose(monkeypatch: pytest.MonkeyPatch, fn: Any) -> None:
    monkeypatch.setattr(api, "propose_brief", fn)


def test_health_reports_model_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in _MODEL_ENV:
        monkeypatch.setenv(key, "x")
    assert client.get("/health").json() == {"ok": True, "model_configured": True}


def test_health_reports_missing_model_config(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in _MODEL_ENV:
        monkeypatch.delenv(key, raising=False)
    assert client.get("/health").json()["model_configured"] is False


def test_propose_returns_brief_and_review_debt(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_propose(monkeypatch, lambda description, *, paper_text=None: _brief())
    resp = client.post("/propose", json={"description": "a plasma slab"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["brief"]["domain"] == "plasma"
    assert body["brief"]["approved_by"] is None
    assert body["brief"]["block"]["governing_equations"] == ["Vlasov-Maxwell"]
    assert body["review_debt"] == [2, 3]


def test_propose_surfaces_propose_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(description: str, *, paper_text: str | None = None) -> Envelope[PlasmaBlock]:
        raise ProposeError("did not validate after a repair pass")

    _patch_propose(monkeypatch, boom)
    resp = client.post("/propose", json={"description": "x"})
    assert resp.status_code == 422
    assert resp.json()["detail"]["kind"] == "propose"


def test_propose_surfaces_model_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(description: str, *, paper_text: str | None = None) -> Envelope[PlasmaBlock]:
        raise RuntimeError("Model client is not configured.")

    _patch_propose(monkeypatch, boom)
    resp = client.post("/propose", json={"description": "x"})
    assert resp.status_code == 502
    assert resp.json()["detail"]["kind"] == "model"


def test_propose_rejects_unreadable_paper(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_propose(monkeypatch, lambda description, *, paper_text=None: _brief())
    resp = client.post("/propose", json={"description": "x", "paper_path": "/no/such/file.xyz"})
    assert resp.status_code == 422
    assert resp.json()["detail"]["kind"] == "paper"


def _approve_body(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "brief": json.loads(_brief().model_dump_json()),
        "approved_by": "Dr Vega",
        "corrections": [],
    }
    body.update(overrides)
    return body


def test_approve_stamps_locks_and_persists(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    monkeypatch.setenv("ORIPHIM_WORKSPACE", str(tmp_path))
    resp = client.post(
        "/approve",
        json=_approve_body(
            corrections=[
                {
                    "field_path": "assumptions.0",
                    "original_provenance": "inferred",
                    "category": "not_applicable",
                }
            ]
        ),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["brief"]["approved_by"] == "Dr Vega"
    assert body["brief"]["approved_at"] is not None
    assert body["brief"]["revision"] == 2
    assert body["corrections_saved"] == 1
    assert (tmp_path / "run-test-1.json").is_file()
    assert (tmp_path / "run-test-1.corrections.json").is_file()


def test_approve_without_corrections_writes_only_the_brief(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    monkeypatch.setenv("ORIPHIM_WORKSPACE", str(tmp_path))
    resp = client.post("/approve", json=_approve_body())
    assert resp.status_code == 200
    assert resp.json()["corrections_saved"] == 0
    assert (tmp_path / "run-test-1.json").is_file()
    assert not (tmp_path / "run-test-1.corrections.json").exists()


def test_approve_rejects_unknown_domain(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    monkeypatch.setenv("ORIPHIM_WORKSPACE", str(tmp_path))
    body = _approve_body()
    body["brief"]["domain"] = "nope"
    resp = client.post("/approve", json=body)
    assert resp.status_code == 422
    assert resp.json()["detail"]["kind"] == "approve"


def test_approve_rejects_a_bad_correction_category(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    monkeypatch.setenv("ORIPHIM_WORKSPACE", str(tmp_path))
    resp = client.post(
        "/approve",
        json=_approve_body(
            corrections=[
                {"field_path": "objective", "original_provenance": "inferred", "category": "bogus"}
            ]
        ),
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["kind"] == "approve"
