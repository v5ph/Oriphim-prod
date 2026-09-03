from __future__ import annotations

import pytest

from oriphim.core import domain as domain_registry


def test_get_unregistered_domain_raises() -> None:
    with pytest.raises(KeyError):
        domain_registry.get("no-such-domain")


def test_importing_mechanical_registers_it() -> None:
    import oriphim.domains.mechanical  # noqa: F401

    mechanical = domain_registry.get("mechanical")
    assert mechanical.name == "mechanical"

    from oriphim.domains.mechanical.block import MechanicalBlock

    assert mechanical.block_schema() is MechanicalBlock


def test_importing_plasma_registers_it() -> None:
    import oriphim.domains.plasma  # noqa: F401

    plasma = domain_registry.get("plasma")
    assert plasma.name == "plasma"

    from oriphim.domains.plasma.block import PlasmaBlock
    from oriphim.domains.plasma.spec import PlasmaSpecBlock

    assert plasma.block_schema() is PlasmaBlock
    assert plasma.spec_schema() is PlasmaSpecBlock
