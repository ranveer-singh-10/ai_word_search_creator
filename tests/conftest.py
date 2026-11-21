"""Shared fixtures. No test calls the real Claude API."""
import json
import os
from types import SimpleNamespace
from unittest.mock import patch

import pytest

# generate.py creates the Anthropic client at import time; tests mock it, so any key will do.
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

from fastapi.testclient import TestClient  # noqa: E402  (imports need the key set first)

from wordsearch import generate  # noqa: E402
from wordsearch.api import app  # noqa: E402

USAGE = SimpleNamespace(input_tokens=10, output_tokens=20)


@pytest.fixture
def usage():
    """Token usage attached to every fake Claude reply."""
    return USAGE


@pytest.fixture
def api():
    """HTTP client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def fake_claude():
    """Stands in for the Anthropic client's messages.create.

    Call fake_claude.reply(payload, stop_reason) to set what "Claude" sends back;
    payload is a dict (sent as JSON) or a raw string.
    """
    with patch.object(generate.client.messages, "create") as create:
        def reply(payload="", stop_reason="end_turn"):
            text = payload if isinstance(payload, str) else json.dumps(payload)
            create.return_value = SimpleNamespace(
                content=[SimpleNamespace(type="text", text=text)],
                stop_reason=stop_reason,
                usage=USAGE,
            )
            return create

        create.reply = reply
        yield create


@pytest.fixture
def fake_words():
    """Skips Claude entirely: generate_words returns the given words.

    Call fake_words.returns([...]) to set them, or set fake_words.side_effect to raise.
    """
    with patch.object(generate, "generate_words") as mock:
        def returns(words, usage=USAGE):
            mock.return_value = {"words": words, "usage": usage}
            return mock

        mock.returns = returns
        yield mock
