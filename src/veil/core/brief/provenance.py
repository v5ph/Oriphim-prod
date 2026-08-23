"""Provenance tracking: every field in a run brief carries provenance.

Provenance answers one question: how did this value get here? The user
stated it, Veil inferred it from context, or it was defaulted from a
standard or convention. A human reviewer's attention should go to
inferred fields first — that is the whole point of tracking this.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Provenance(StrEnum):
    """How a field's value came to be."""

    STATED = "stated"
    """The user said this explicitly."""

    INFERRED = "inferred"
    """Veil derived it; requires review."""

    DEFAULTED = "defaulted"
    """Pulled from a standard or convention; cite the source."""


class Provenanced(BaseModel, Generic[T]):
    """A value paired with where it came from."""

    value: T
    provenance: Provenance
    inference_note: str | None = None
    """Why Veil inferred this value. Required in spirit when provenance is INFERRED."""
    source: str | None = None
    """Standard and table reference, e.g. "GSFC-STD-7000 Table 2.4-3"."""
