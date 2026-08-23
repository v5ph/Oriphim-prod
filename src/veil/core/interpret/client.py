"""Provider-agnostic model client.

This is the only module in the codebase permitted to import a model client
library. Everything else is deterministic; if a model client import appears
anywhere else, that is a bug.

Stub for this slice. Signature only.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ModelClientConfig:
    """Configuration read from the environment."""

    api_base: str | None
    api_key: str | None
    model: str | None

    @classmethod
    def from_env(cls) -> ModelClientConfig:
        return cls(
            api_base=os.environ.get("VEIL_API_BASE"),
            api_key=os.environ.get("VEIL_API_KEY"),
            model=os.environ.get("VEIL_MODEL"),
        )


class ModelClient:
    """Provider-agnostic client for the interpretation model.

    Stub: construction only. The call itself is not implemented in this slice.
    """

    def __init__(self, config: ModelClientConfig | None = None) -> None:
        self.config = config or ModelClientConfig.from_env()

    def complete(self, *, system: str, prompt: str) -> str:
        raise NotImplementedError
