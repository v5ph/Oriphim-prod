"""Propose a draft run brief from prose (and, when available, a paper).

Prose and paper text in, a typed `Envelope` out — never prose out. The model
supplies the interpretive fields (what system is posed, what to check); this
module supplies identity and status (`run_id`, timestamps, domain). Nothing
here is trusted until a human reviews it: the returned brief is unapproved by
construction, and `Envelope.require_approved` is what stops it from running.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import uuid4

from pydantic import BaseModel, ValidationError

from oriphim.core import domain as domain_registry
from oriphim.core.brief.envelope import Envelope
from oriphim.core.interpret.client import ModelClient

# One interpretation attempt, then one repair pass if it doesn't validate.
_MAX_ATTEMPTS = 2

# Paper text past this point is dropped before sending. The default suits a
# large-context provider (Gemini); set ORIPHIM_MAX_PAPER_CHARS lower for a
# provider with a tight per-request or per-minute token budget (Groq free tier
# is 8k tokens/min — roughly 30k characters, shared with prompt and response).
_MAX_PAPER_CHARS = int(os.environ.get("ORIPHIM_MAX_PAPER_CHARS", 200_000))

# The fields the model fills. Everything else on the Envelope — `run_id`,
# `revision`, `created_at`, `domain`, approval — is set by `_assemble`.
_MODEL_FIELDS = (
    "title",
    "objective",
    "quantities_of_interest",
    "assumptions",
    "checks_planned",
    "tier",
    "block",
)

_SYSTEM_PROMPT = """\
You are Oriphim's interpretation step. You read a description of a physical
system - and, when provided, the paper it comes from - and produce a draft
"run brief": a structured statement of what system is being posed and what
will be checked. You do not solve anything. You do not produce a number that
is not already in the source.

Every interpretive field carries provenance:
  "stated"    - the description or paper says this explicitly
  "inferred"  - you derived it from context; include an "inference_note"
  "defaulted" - taken from a standard or convention; name it in "source"

Be conservative. Prefer "inferred" with a clear note over a confident
"stated". Mark anything you are supplying rather than reading.

The report tier is "verification" unless reference measurements for this exact
system are described. Default to "verification".

Return one JSON object and nothing else. No prose, no code fences.
"""

_FIELD_GUIDE = """\
`title` is a short string. `objective` is one provenanced string.
`quantities_of_interest` and `assumptions` are lists of provenanced strings.
`checks_planned` is a list of plain strings. `tier` is "verification" or
"validation". `block` matches the JSON schema below.

A provenanced value looks like:
{"value": ..., "provenance": "stated|inferred|defaulted", "inference_note": null, "source": null}
"""


class _Completer(Protocol):
    """Anything that turns a system+user prompt into text. `ModelClient` is one."""

    def complete(self, *, system: str, prompt: str) -> str: ...


class ProposeError(RuntimeError):
    """The model did not return a brief that validates, even after a repair pass."""


def propose_brief(
    description: str,
    *,
    paper_text: str | None = None,
    domain: str = "plasma",
    client: _Completer | None = None,
) -> Envelope[Any]:
    """Turn a prose description (and optional paper text) into a draft brief.

    Calls the model, parses its JSON into an `Envelope` for `domain`, and fills
    in the system-owned fields. A validation failure buys one more attempt with
    the error fed back to the model; a second failure raises `ProposeError`.
    The brief comes back unapproved — a human reviews it before anything runs.
    """
    client = client or ModelClient()
    block_type = domain_registry.get(domain).block_schema()
    prompt = _build_user_prompt(description, paper_text, block_type)

    failure: ValidationError | ValueError | None = None
    for _ in range(_MAX_ATTEMPTS):
        raw = client.complete(system=_SYSTEM_PROMPT, prompt=prompt)
        try:
            return _assemble(raw, domain=domain, block_type=block_type)
        except (ValidationError, ValueError) as exc:
            failure = exc
            prompt = _repair_prompt(prompt, exc)  # next attempt sees what went wrong
    raise ProposeError(str(failure))


def _build_user_prompt(
    description: str, paper_text: str | None, block_type: type[BaseModel]
) -> str:
    schema = json.dumps(block_type.model_json_schema(), indent=2)
    sections = [
        f"## Description (from the user)\n{description.strip()}",
        f"## Fields to fill\n{', '.join(_MODEL_FIELDS)}",
        f"{_FIELD_GUIDE}\n{schema}",
    ]
    if paper_text:
        sections.append(f"## Paper\n{paper_text[:_MAX_PAPER_CHARS]}")
    return "\n\n".join(sections)


def _repair_prompt(prompt: str, error: Exception) -> str:
    return (
        f"{prompt}\n\n"
        f"Your previous response did not validate:\n{error}\n"
        "Return a corrected JSON object and nothing else."
    )


def _assemble(raw: str, *, domain: str, block_type: type[BaseModel]) -> Envelope[Any]:
    """Merge the model's JSON with the system-owned fields, then validate."""
    data = _parse_json_object(raw)
    data.update(
        {
            "run_id": str(uuid4()),
            "revision": 1,
            "created_at": datetime.now(UTC),
            "domain": domain,
            "approved_by": None,
            "approved_at": None,
        }
    )
    # Envelope is generic; parametrising it with a runtime type is correct at
    # runtime but not something the type checker can follow.
    return Envelope[block_type].model_validate(data)  # type: ignore


def _parse_json_object(raw: str) -> dict[str, Any]:
    text = _strip_code_fences(raw)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError(f"Response was not valid JSON: {error}") from error
    if not isinstance(data, dict):
        raise ValueError(f"Expected a JSON object, got {type(data).__name__}.")
    return data


def _strip_code_fences(raw: str) -> str:
    """Drop a leading ```/```json line and a trailing ``` line, if the model added them."""
    text = raw.strip()
    if not text.startswith("```"):
        return text
    lines = text.splitlines()
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines[1:])
