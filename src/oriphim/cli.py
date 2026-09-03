"""Command-line entry point.

Importing this module registers every domain (see `oriphim.domains.*`) — there
is no plugin-discovery system, so each domain is imported directly here.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import typer

import oriphim.domains.mechanical  # noqa: F401  (registers the mechanical domain)
import oriphim.domains.plasma  # noqa: F401  (registers the plasma domain)
from oriphim.core.brief.envelope import Envelope
from oriphim.core.brief.provenance import Provenance, Provenanced
from oriphim.core.interpret.ingest import extract_text
from oriphim.core.interpret.propose import propose_brief
from oriphim.core.render.bundle import write_bundle
from oriphim.core.render.data import RenderData
from oriphim.core.render.demo import demo_data
from oriphim.core.render.link import validate_scene_against_data
from oriphim.core.render.scene import Scene
from oriphim.core.render.stamp import stamp
from oriphim.domains.plasma.scene import default_plasma_scene

app = typer.Typer(help="oriphim: turn a described physical system into a computational experiment.")


@app.command()
def propose(
    description: str,
    paper: Path | None = typer.Option(
        None, "--paper", help="A paper to ingest as context (PDF, HTML, or text)."
    ),
) -> None:
    """Propose a draft run brief from a prose description of a system."""
    paper_text = extract_text(paper) if paper is not None else None
    brief = propose_brief(description, paper_text=paper_text)
    _print_brief(brief)


@app.command()
def run(run_id: str) -> None:
    """Execute an approved run brief."""
    raise NotImplementedError


@app.command()
def render(
    demo: bool = typer.Option(False, "--demo", help="Use built-in synthetic data."),
    data: Path | None = typer.Option(None, "--data", help="DATA JSON file."),
    scene: Path | None = typer.Option(None, "--scene", help="SCENE JSON file."),
    out: Path = typer.Option(Path("figure.html"), "--out", help="Where to write the bundle."),
) -> None:
    """Bundle a SCENE + DATA into a self-contained animated HTML figure."""
    if demo:
        render_data = demo_data()
        render_scene = default_plasma_scene(None, render_data)
    elif data is not None and scene is not None:
        render_data = RenderData.model_validate_json(data.read_text(encoding="utf-8"))
        render_scene = Scene.model_validate_json(scene.read_text(encoding="utf-8"))
    else:
        raise typer.BadParameter("pass --demo, or both --data and --scene")

    validate_scene_against_data(render_scene, render_data)
    write_bundle(out, render_scene, render_data)
    typer.echo(f"wrote {out}")
    typer.echo(stamp(render_scene, render_data).model_dump_json(indent=2))


def _print_brief(brief: Envelope[Any]) -> None:
    """Inferred fields first — that is what a reviewer must check — then the full brief."""
    needing_review, total = brief.review_debt()
    typer.echo(f"{needing_review} of {total} provenanced fields inferred — review these first:")
    for label, field in _provenanced_fields(brief):
        if field.provenance is Provenance.INFERRED:
            typer.echo(f"  - {label}: {field.value!r}")
            typer.echo(f"      {field.inference_note or '(no note)'}")
    typer.echo()
    typer.echo(brief.model_dump_json(indent=2))


def _provenanced_fields(brief: Envelope[Any]) -> Iterator[tuple[str, Provenanced[Any]]]:
    yield "objective", brief.objective
    for i, qoi in enumerate(brief.quantities_of_interest):
        yield f"quantities_of_interest[{i}]", qoi
    for i, assumption in enumerate(brief.assumptions):
        yield f"assumptions[{i}]", assumption


if __name__ == "__main__":
    app()
