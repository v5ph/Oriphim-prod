from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from oriphim.core.brief.provenance import Provenance
from oriphim.core.corrections.schema import Correction, CorrectionCategory
from oriphim.core.store.runs import RunStore


def _correction(field_path: str) -> Correction:
    return Correction(
        run_id="r1",
        domain="plasma",
        field_path=field_path,
        original_provenance=Provenance.INFERRED,
        category=CorrectionCategory.WRONG_ASSUMPTION,
        timestamp=datetime.now(UTC),
    )


def test_runstore_round_trips_a_model(tmp_path: Path) -> None:
    store = RunStore(tmp_path)
    path = store.save("r1", _correction("assumptions.0"))
    assert path.is_file()
    loaded = store.load("r1")
    assert loaded["field_path"] == "assumptions.0"
    assert loaded["run_id"] == "r1"


def test_runstore_round_trips_a_list(tmp_path: Path) -> None:
    store = RunStore(tmp_path)
    store.save("r1.corrections", [_correction(f"assumptions.{i}") for i in range(3)])
    loaded = store.load("r1.corrections")
    assert [rec["field_path"] for rec in loaded] == [
        "assumptions.0",
        "assumptions.1",
        "assumptions.2",
    ]


def test_runstore_creates_missing_workspace_dir(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "nested" / "workspace")
    assert not store.exists("r1")
    store.save("r1", {"hello": "world"})
    assert store.load("r1") == {"hello": "world"}
    assert store.exists("r1")
