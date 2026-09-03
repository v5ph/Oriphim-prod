"""Local HTTP bridge between the desktop app and the engine.

The Electron app spawns this as a sidecar (`oriphim-api`) bound to 127.0.0.1
and talks to it from the renderer. It is the same engine the CLI drives — this
module only adds a transport. Like `oriphim.cli`, importing it registers every
domain; there is no plugin discovery.

Not a public API: no auth, no CORS, no stability guarantees. It exists so one
desktop process can reach one engine on the same machine.
"""

from __future__ import annotations

import json
import os
import socket
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ValidationError

import oriphim.domains.mechanical  # noqa: F401  (registers the mechanical domain)
import oriphim.domains.plasma  # noqa: F401  (registers the plasma domain)
from oriphim.core import domain as domain_registry
from oriphim.core.brief.envelope import Envelope
from oriphim.core.brief.provenance import Provenance
from oriphim.core.corrections.capture import capture_correction
from oriphim.core.corrections.schema import CorrectionCategory
from oriphim.core.interpret.ingest import extract_text
from oriphim.core.interpret.propose import ProposeError, propose_brief
from oriphim.core.store.runs import RunStore

_MODEL_ENV = ("ORIPHIM_API_BASE", "ORIPHIM_API_KEY", "ORIPHIM_MODEL")


def _workspace() -> Path:
    return Path(os.environ.get("ORIPHIM_WORKSPACE", ".oriphim-workspace"))


app = FastAPI(title="oriphim engine bridge", docs_url=None, redoc_url=None)


class ProposeRequest(BaseModel):
    description: str
    paper_path: str | None = None


class CorrectionInput(BaseModel):
    field_path: str
    original_provenance: str
    category: str
    context_tag: str | None = None


class ApproveRequest(BaseModel):
    brief: dict[str, Any]
    approved_by: str
    corrections: list[CorrectionInput] = []


@app.get("/health")
def health() -> dict:
    """Liveness plus whether the model client has everything it needs to run."""
    return {"ok": True, "model_configured": all(os.environ.get(k) for k in _MODEL_ENV)}


@app.post("/propose")
def propose(req: ProposeRequest) -> dict:
    """Prose (+ optional paper path) -> a draft `Envelope`, unapproved by construction."""
    paper_text: str | None = None
    if req.paper_path:
        try:
            paper_text = extract_text(Path(req.paper_path))
        except Exception as exc:  # bad suffix, missing file, unreadable PDF
            raise HTTPException(
                status_code=422, detail={"kind": "paper", "message": str(exc)}
            ) from exc

    try:
        brief = propose_brief(req.description, paper_text=paper_text)
    except ProposeError as exc:
        raise HTTPException(
            status_code=422, detail={"kind": "propose", "message": str(exc)}
        ) from exc
    except RuntimeError as exc:  # unconfigured, provider unreachable, junk response
        raise HTTPException(
            status_code=502, detail={"kind": "model", "message": str(exc)}
        ) from exc

    needing, total = brief.review_debt()
    return {"brief": json.loads(brief.model_dump_json()), "review_debt": [needing, total]}


@app.post("/approve")
def approve(req: ApproveRequest) -> dict:
    """Lock a reviewed brief: re-validate the edited envelope, stamp approval, persist.

    Correction records are stored alongside — they carry no field values, only
    that a field was corrected and from which provenance.
    """
    domain_name = req.brief.get("domain")
    if not isinstance(domain_name, str):
        raise HTTPException(
            status_code=422, detail={"kind": "approve", "message": "brief is missing 'domain'"}
        )
    try:
        block_type = domain_registry.get(domain_name).block_schema()
        env = Envelope[block_type].model_validate(req.brief)  # type: ignore[valid-type]
    except KeyError as exc:
        raise HTTPException(
            status_code=422,
            detail={"kind": "approve", "message": f"unknown domain {domain_name!r}"},
        ) from exc
    except ValidationError as exc:
        raise HTTPException(
            status_code=422, detail={"kind": "approve", "message": str(exc)}
        ) from exc

    try:
        records = [
            capture_correction(
                run_id=env.run_id,
                domain=env.domain,
                field_path=c.field_path,
                original_provenance=Provenance(c.original_provenance),
                category=CorrectionCategory(c.category),
                context_tag=c.context_tag,
            )
            for c in req.corrections
        ]
    except ValueError as exc:  # unknown provenance or category string
        raise HTTPException(
            status_code=422, detail={"kind": "approve", "message": f"bad correction — {exc}"}
        ) from exc

    env.approved_by = req.approved_by
    env.approved_at = datetime.now(UTC)
    env.revision += 1

    store = RunStore(_workspace())
    store.save(env.run_id, env)
    if records:
        store.save(f"{env.run_id}.corrections", records)

    return {"brief": json.loads(env.model_dump_json()), "corrections_saved": len(records)}


def _pick_port() -> int:
    override = os.environ.get("ORIPHIM_API_PORT")
    if override:
        return int(override)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def main() -> None:
    """Console-script entry point. Prints the bound port so the parent can find us."""
    import uvicorn

    port = _pick_port()
    print(f"ORIPHIM_API_PORT={port}", flush=True)
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    main()
