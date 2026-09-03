from __future__ import annotations

import io
import json
import urllib.error
from email.message import Message

import pytest

from oriphim.core.interpret.client import ModelClient, ModelClientConfig

_CONFIG = ModelClientConfig(
    api_base="https://example.test/v1",
    api_key="sekret",
    model="test-model",
)
_URLOPEN = "oriphim.core.interpret.client.urllib.request.urlopen"


class _FakeResponse(io.BytesIO):
    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def test_complete_posts_openai_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}

    def fake_urlopen(request, timeout=None):
        seen["url"] = request.full_url
        seen["headers"] = dict(request.header_items())
        seen["body"] = json.loads(request.data)
        return _FakeResponse(json.dumps({"choices": [{"message": {"content": "hi"}}]}).encode())

    monkeypatch.setattr(_URLOPEN, fake_urlopen)

    out = ModelClient(_CONFIG).complete(system="S", prompt="P")

    assert out == "hi"
    assert seen["url"] == "https://example.test/v1/chat/completions"
    body = seen["body"]
    assert isinstance(body, dict)
    assert body["model"] == "test-model"
    assert body["messages"] == [
        {"role": "system", "content": "S"},
        {"role": "user", "content": "P"},
    ]
    headers = seen["headers"]
    assert isinstance(headers, dict)
    assert headers.get("Authorization") == "Bearer sekret"
    assert headers.get("User-agent") == "oriphim/0.1"  # urllib title-cases the key


def test_complete_requires_configuration() -> None:
    client = ModelClient(ModelClientConfig(api_base=None, api_key=None, model=None))
    with pytest.raises(RuntimeError, match="not configured"):
        client.complete(system="S", prompt="P")


def test_complete_raises_on_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(request, timeout=None):
        raise urllib.error.HTTPError(
            request.full_url, 429, "Too Many", Message(), io.BytesIO(b"slow down")
        )

    monkeypatch.setattr(_URLOPEN, fake_urlopen)
    with pytest.raises(RuntimeError, match="429"):
        ModelClient(_CONFIG).complete(system="S", prompt="P")
