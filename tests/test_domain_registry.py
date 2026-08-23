from __future__ import annotations

import pytest

from veil.core import domain as domain_registry


def test_get_unregistered_domain_raises() -> None:
    with pytest.raises(KeyError):
        domain_registry.get("no-such-domain")


def test_importing_mechanical_registers_it() -> None:
    import veil.domains.mechanical  # noqa: F401

    mechanical = domain_registry.get("mechanical")
    assert mechanical.name == "mechanical"

    from veil.domains.mechanical.block import MechanicalBlock

    assert mechanical.block_schema() is MechanicalBlock
