"""Provider-agnostic model client.

This is the only module in the codebase permitted to import or speak to a
model provider. Everything else is deterministic; if a provider call appears
anywhere else, that is a bug.

The client speaks the OpenAI chat-completions wire format, which nearly every
hosted provider now exposes. Configuration is entirely environment-driven, so
switching providers never touches code:

    ORIPHIM_API_BASE   e.g. https://generativelanguage.googleapis.com/v1beta/openai
    ORIPHIM_API_KEY    the provider key
    ORIPHIM_MODEL      e.g. gemini-3.6-flash

Google's Gemini free tier is the current default target: no card, an
OpenAI-compatible endpoint, and a context window large enough for a whole
paper. Not local AI.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass

# Generous: a whole paper of context through a "thinking" model is routinely
# slow. Tune down once ingestion sends less than the full document.
_TIMEOUT_SECONDS = 180

# urllib's default ("Python-urllib/x.y") trips Cloudflare bot filters in front
# of some providers (Groq returns 403 / error 1010). Identify ourselves.
_USER_AGENT = "oriphim/0.1"


@dataclass(frozen=True)
class ModelClientConfig:
    """Configuration read from the environment."""

    api_base: str | None
    api_key: str | None
    model: str | None

    @classmethod
    def from_env(cls) -> ModelClientConfig:
        return cls(
            api_base=os.environ.get("ORIPHIM_API_BASE"),
            api_key=os.environ.get("ORIPHIM_API_KEY"),
            model=os.environ.get("ORIPHIM_MODEL"),
        )


class ModelClient:
    """Provider-agnostic client for the interpretation model.

    Speaks the OpenAI `/chat/completions` format at `temperature` 0, so a given
    prompt varies as little as the provider allows.
    """

    def __init__(self, config: ModelClientConfig | None = None) -> None:
        self.config = config or ModelClientConfig.from_env()

    def complete(self, *, system: str, prompt: str) -> str:
        """Send a system+user exchange and return the assistant's text.

        Raises `RuntimeError` if the client is unconfigured, the provider is
        unreachable, or the response is not a usable completion.
        """
        base, key, model = self.config.api_base, self.config.api_key, self.config.model
        if not base or not key or not model:
            raise RuntimeError(
                "Model client is not configured. Set ORIPHIM_API_BASE, "
                "ORIPHIM_API_KEY, and ORIPHIM_MODEL."
            )

        url = f"{base.rstrip('/')}/chat/completions"
        body = json.dumps(
            {
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "User-Agent": _USER_AGENT,
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", "replace")
            raise RuntimeError(f"Model provider returned HTTP {error.code}: {detail}") from error
        except urllib.error.URLError as error:
            raise RuntimeError(
                f"Could not reach model provider at {url}: {error.reason}"
            ) from error

        try:
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise RuntimeError(f"Unexpected response from model provider: {payload!r}") from error
        if not isinstance(content, str):
            raise RuntimeError(f"Model provider returned non-text content: {content!r}")
        return content
