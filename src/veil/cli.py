"""Command-line entry point.

Stub for this slice: command skeleton only. Importing this module registers
the mechanical domain (see `veil.domains.mechanical`) — there is no
plugin-discovery system, so every domain must be imported directly here.
"""

from __future__ import annotations

import typer

import veil.domains.mechanical  # noqa: F401  (registers the mechanical domain)

app = typer.Typer(help="Veil: turn a described physical system into a computational experiment.")


@app.command()
def propose(description: str) -> None:
    """Propose a draft run brief from a prose description of a system."""
    raise NotImplementedError


@app.command()
def run(run_id: str) -> None:
    """Execute an approved run brief."""
    raise NotImplementedError


if __name__ == "__main__":
    app()
