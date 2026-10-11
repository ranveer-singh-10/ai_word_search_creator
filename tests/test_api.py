import json
import string
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import server
from wordsearch import generate

USAGE = SimpleNamespace(input_tokens=10, output_tokens=20)


def fake_words(words):
    return {"words": words, "usage": USAGE}


def fake_response(text, stop_reason="end_turn"):
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)],
        stop_reason=stop_reason,
        usage=USAGE,
    )


@pytest.fixture
def api():
    return TestClient(server.app)


def test_claude_called_once():
    with patch.object(generate, "generate_words", return_value=fake_words(
        [{"word": "COMET", "description": "Icy body"}]
    )) as mock:
        generate.generate_populated_wordsearch("Space", 8, "easy", 8)
    assert mock.call_count == 1


def test_invalid_words_never_reach_grid_or_response(api):
    raw = [
        {"word": "comet", "description": "Icy body"},           # lowercase: valid once upper-cased
        {"word": "COMET", "description": "Duplicate"},          # duplicate
        {"word": "Black hole", "description": "Has a space"},   # not A-Z
        {"word": "X-RAY", "description": "Has a hyphen"},       # not A-Z
        {"word": "", "description": "Empty"},                   # empty
        {"word": "SUPERCALIFRAGILISTIC", "description": "Too long"},
        {"word": "ORBIT", "description": "Curved path"},
    ]
    with patch.object(generate, "generate_words", return_value=fake_words(raw)):
        resp = api.post("/api/puzzle", json={"category": "Space", "difficulty": "hard"})

    assert resp.status_code == 200
    body = resp.json()
    assert [w["word"] for w in body["words"]] == ["COMET", "ORBIT"]
    assert body["words"][0]["description"] == "Icy body"
    for row in body["grid"]:
        for cell in row:
            assert cell in string.ascii_uppercase


@pytest.mark.parametrize("difficulty", ["easy", "medium", "hard"])
def test_placements_spell_each_word(api, difficulty):
    raw = [{"word": w, "description": "d"} for w in ["COMET", "ORBIT", "MOON", "STAR"]]
    with patch.object(generate, "generate_words", return_value=fake_words(raw)):
        resp = api.post("/api/puzzle", json={"category": "Space", "difficulty": difficulty})

    body = resp.json()
    grid = body["grid"]
    for item in body["words"]:
        (r0, c0), (r1, c1) = item["start"], item["end"]
        last = len(item["word"]) - 1
        step_r, step_c = (r1 - r0) // last, (c1 - c0) // last
        assert (r1 - r0, c1 - c0) == (step_r * last, step_c * last)
        letters = "".join(grid[r0 + step_r * i][c0 + step_c * i] for i in range(last + 1))
        assert letters == item["word"]


def test_generate_words_parses_structured_output():
    payload = {"words": [{"word": "COMET", "description": "Icy body"}]}
    with patch.object(generate.client.messages, "create",
                      return_value=fake_response(json.dumps(payload))) as mock:
        result = generate.generate_words("Space", "easy", 5, max_length=8)

    assert result["words"] == payload["words"]
    fmt = mock.call_args.kwargs["output_config"]["format"]
    assert fmt["type"] == "json_schema"


def test_generate_words_raises_when_cut_off():
    with patch.object(generate.client.messages, "create",
                      return_value=fake_response('{"words": [', stop_reason="max_tokens")):
        with pytest.raises(RuntimeError):
            generate.generate_words("Space", "easy")


def test_generation_failure_returns_502(api):
    with patch.object(generate, "generate_words", side_effect=RuntimeError("boom")):
        resp = api.post("/api/puzzle", json={"category": "Space"})
    assert resp.status_code == 502


def test_dynamic_returns_501(api):
    resp = api.post("/api/puzzle", json={"category": "Space", "dynamic": True})
    assert resp.status_code == 501
