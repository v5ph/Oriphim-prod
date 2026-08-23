"""Propose a draft run brief from prose.

Prose in, typed brief out — the brief is always typed, never returned as prose.
Stub for this slice. Signature only.
"""

from __future__ import annotations

from typing import Any

from veil.core.brief.envelope import Envelope
from veil.core.interpret.client import ModelClient


def propose_brief(description: str, *, client: ModelClient, domain: str) -> Envelope[Any]:
    """Turn a prose description of a system into a draft, unapproved brief."""
    raise NotImplementedError
