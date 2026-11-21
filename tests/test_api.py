"""End-to-end tests for POST /api/puzzle, with Claude faked."""
import string
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from wordsearch import api as api_module
from wordsearch.config import DEFAULT_MODEL, PRICE_PER_MILLION


def test_invalid_words_never_reach_grid_or_response(api, fake_words):
    fake_words.returns([
        {"word": "comet", "description": "Icy body"},           # lowercase: valid once upper-cased
        {"word": "COMET", "description": "Duplicate"},          # duplicate
        {"word": "Black hole", "description": "Has a space"},   # not A-Z
        {"word": "X-RAY", "description": "Has a hyphen"},       # not A-Z
        {"word": "", "description": "Empty"},                   # empty
        {"word": "SUPERCALIFRAGILISTIC", "description": "Too long"},
        {"word": "ORBIT", "description": "Curved path"},
    ])
    resp = api.post("/api/puzzle", json={"category": "Space", "difficulty": "hard"})

    assert resp.status_code == 200
    body = resp.json()
    assert [w["word"] for w in body["words"]] == ["COMET", "ORBIT"]
    assert body["words"][0]["description"] == "Icy body"
    for row in body["grid"]:
        for cell in row:
            assert cell in string.ascii_uppercase


@pytest.mark.parametrize("difficulty", ["easy", "medium", "hard"])
def test_placements_spell_each_word(api, fake_words, difficulty):
    fake_words.returns([{"word": w, "description": "d"} for w in ["COMET", "ORBIT", "MOON", "STAR"]])
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


def test_response_includes_stats(api, fake_words):
    usage = SimpleNamespace(input_tokens=1_000_000, output_tokens=2_000_000)
    fake_words.returns([{"word": "COMET", "description": "Icy body"}], usage=usage)
    resp = api.post("/api/puzzle", json={"category": "Space"})

    stats = resp.json()["stats"]
    assert stats["model"] == DEFAULT_MODEL
    assert stats["input_tokens"] == 1_000_000
    assert stats["output_tokens"] == 2_000_000
    assert stats["seconds"] >= 0
    input_price, output_price = PRICE_PER_MILLION[DEFAULT_MODEL]
    assert stats["cost_usd"] == pytest.approx(input_price + 2 * output_price)


def test_unsuitable_category_returns_400(api, fake_claude):
    fake_claude.reply({"category_suitable": False, "words": []})
    resp = api.post("/api/puzzle", json={"category": "something nasty"})
    assert resp.status_code == 400
    assert "isn't suitable" in resp.json()["detail"]


def test_refusal_returns_400(api, fake_claude):
    fake_claude.reply("", stop_reason="refusal")
    resp = api.post("/api/puzzle", json={"category": "something nasty"})
    assert resp.status_code == 400


def test_generation_failure_returns_502(api, fake_words):
    fake_words.side_effect = RuntimeError("boom")
    resp = api.post("/api/puzzle", json={"category": "Space"})
    assert resp.status_code == 502


def test_unsuitable_category_error_includes_cost(api, fake_claude, usage):
    fake_claude.reply({"category_suitable": False, "words": []})
    resp = api.post("/api/puzzle", json={"category": "something nasty"})
    assert resp.status_code == 400
    assert resp.json()["stats"]["cost_usd"] == pytest.approx(api_module.puzzle_cost(usage))


def test_refusal_error_includes_cost(api, fake_claude, usage):
    fake_claude.reply("", stop_reason="refusal")
    resp = api.post("/api/puzzle", json={"category": "something nasty"})
    assert resp.status_code == 400
    assert resp.json()["stats"]["input_tokens"] == usage.input_tokens


def test_cut_off_reply_error_includes_cost(api, fake_claude, usage):
    fake_claude.reply('{"words": [', stop_reason="max_tokens")
    resp = api.post("/api/puzzle", json={"category": "Space"})
    assert resp.status_code == 502
    assert resp.json()["stats"]["output_tokens"] == usage.output_tokens


def test_words_not_fitting_error_includes_cost(api, fake_words, usage):
    fake_words.returns([{"word": "COMET", "description": "Icy body"}])
    with patch.object(api_module, "find_word", return_value=None):
        resp = api.post("/api/puzzle", json={"category": "Space"})
    assert resp.status_code == 500
    assert resp.json()["stats"]["cost_usd"] == pytest.approx(api_module.puzzle_cost(usage))


def test_failure_before_claude_replies_has_no_cost(api, fake_words):
    fake_words.side_effect = RuntimeError("network down")
    resp = api.post("/api/puzzle", json={"category": "Space"})
    assert resp.status_code == 502
    assert "stats" not in resp.json()


def test_straight_words_include_their_path(api, fake_words):
    fake_words.returns([{"word": "COMET", "description": "Icy body"}])
    body = api.post("/api/puzzle", json={"category": "Space"}).json()
    word = body["words"][0]
    assert word["path"][0] == word["start"] and word["path"][-1] == word["end"]
    assert "".join(body["grid"][r][c] for r, c in word["path"]) == "COMET"


@pytest.mark.parametrize("difficulty", ["easy", "medium", "hard"])
def test_dynamic_paths_spell_each_word(api, fake_words, difficulty):
    fake_words.returns([{"word": w, "description": "d"} for w in ["COMET", "ORBIT", "MOON", "PLANET"]])
    resp = api.post("/api/puzzle", json={"category": "Space", "difficulty": difficulty, "dynamic": True})

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["words"]) == 4
    for item in body["words"]:
        path = item["path"]
        assert "".join(body["grid"][r][c] for r, c in path) == item["word"]
        assert item["start"] == path[0] and item["end"] == path[-1]
        for (r0, c0), (r1, c1) in zip(path, path[1:]):
            assert max(abs(r1 - r0), abs(c1 - c0)) == 1      # each letter touches the one before


def test_dynamic_unsuitable_category_returns_400(api, fake_claude):
    fake_claude.reply({"category_suitable": False, "words": []})
    resp = api.post("/api/puzzle", json={"category": "something nasty", "dynamic": True})
    assert resp.status_code == 400


def test_dynamic_words_not_placed_error_includes_cost(api, fake_words, usage):
    fake_words.returns([{"word": "COMET", "description": "Icy body"}])
    with patch("wordsearch.dynamic.place_word_on_path", return_value=None):
        resp = api.post("/api/puzzle", json={"category": "Space", "dynamic": True})
    assert resp.status_code == 500
    assert resp.json()["stats"]["cost_usd"] == pytest.approx(api_module.puzzle_cost(usage))


def test_page_is_served(api):
    resp = api.get("/")
    assert resp.status_code == 200
    assert "<html" in resp.text.lower()
