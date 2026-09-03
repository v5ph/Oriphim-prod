from __future__ import annotations

from oriphim.core.brief.provenance import Provenance, Provenanced


def test_stated_value_round_trips() -> None:
    wrapped = Provenanced[str](value="titanium", provenance=Provenance.STATED)
    assert wrapped.value == "titanium"
    assert wrapped.provenance is Provenance.STATED
    assert wrapped.inference_note is None
    assert wrapped.source is None


def test_inferred_value_carries_a_note() -> None:
    wrapped = Provenanced[str](
        value="fixed",
        provenance=Provenance.INFERRED,
        inference_note="Inferred from 'bolted to the bus structure'.",
    )
    assert wrapped.provenance is Provenance.INFERRED
    assert wrapped.inference_note is not None


def test_defaulted_value_cites_a_source() -> None:
    wrapped = Provenanced[float](
        value=14.1,
        provenance=Provenance.DEFAULTED,
        source="GSFC-STD-7000 Table 2.4-3",
    )
    assert wrapped.provenance is Provenance.DEFAULTED
    assert wrapped.source == "GSFC-STD-7000 Table 2.4-3"


def test_provenance_values_are_exactly_three() -> None:
    assert {p.value for p in Provenance} == {"stated", "inferred", "defaulted"}
