"""The seam between an approved brief and a run.

`spec.py` is the declarative contract the LLM fills after approval — a typed
description of *this run*, never solver code. `bind.py` checks a filled spec
against the brief it claims to be for. The numerics that consume the spec are
Oriphim's verified core; see `docs/standards/visualization.md` for why the
split is shaped this way.
"""
